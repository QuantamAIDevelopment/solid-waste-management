"""Vehicle service for fetching live vehicle data from SWM API."""
import os
import requests
import pandas as pd
from typing import List, Dict, Optional
from loguru import logger
from dotenv import load_dotenv
from .auth_service import get_auth_service

# Load environment variables
load_dotenv()

class VehicleService:
    def __init__(self):
        self.base_url = os.getenv('SWM_API_BASE_URL', 'https://uat-swm-main-service-hdaqcdcscbfedhhn.centralindia-01.azurewebsites.net')
        self.session = requests.Session()
        self.auth_service = get_auth_service()
        
        logger.info(f"VehicleService initialized with base URL: {self.base_url}")
        logger.info(f"Using automatic token management: {self.auth_service.is_token_valid()}")
    
    def get_live_vehicles(self) -> pd.DataFrame:
        """Fetch live vehicle data from SWM API."""
        try:
            # Get valid token from auth service
            token = self.auth_service.get_valid_token()
            
            if not token:
                logger.error("No valid token available")
                return self._create_fallback_vehicles()
            
            # Use the correct vehicle endpoint with pagination
            from datetime import datetime
            today = datetime.now().strftime('%Y-%m-%d')
            
            endpoint = f'/api/vehicles/paginated?date={today}&size=542&sortBy=vehicleNo'
            url = f"{self.base_url}{endpoint}"
            
            logger.info(f"Fetching vehicles from: {url}")
            
            # Use bearer token from auth service
            headers = {
                'accept': '*/*',
                'Authorization': f'Bearer {token}'
            }
            
            response = requests.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                vehicles_data = response.json()
                logger.success(f"Successfully fetched vehicle data")
                return self._process_vehicle_data(vehicles_data)
            elif response.status_code == 401:
                # Token might be invalid, force refresh and retry
                logger.warning("Token invalid, forcing refresh")
                if self.auth_service.force_refresh():
                    token = self.auth_service.get_valid_token()
                    headers['Authorization'] = f'Bearer {token}'
                    response = requests.get(url, headers=headers, timeout=30)
                    if response.status_code == 200:
                        vehicles_data = response.json()
                        logger.success(f"Successfully fetched vehicle data after token refresh")
                        return self._process_vehicle_data(vehicles_data)
                
                logger.error(f"API returned status {response.status_code}: {response.text[:200]}")
                return self._create_fallback_vehicles()
            else:
                logger.error(f"API returned status {response.status_code}: {response.text[:200]}")
                return self._create_fallback_vehicles()
            
        except Exception as e:
            logger.error(f"Error fetching live vehicle data: {e}")
            return self._create_fallback_vehicles()
    
    def get_vehicles_by_ward(self, ward_no: str) -> pd.DataFrame:
        """Get vehicles filtered by ward number."""
        try:
            # Get all vehicles first
            all_vehicles = self.get_live_vehicles()
            
            # Filter by ward - check multiple possible ward field names
            ward_fields = ['ward', 'wardNo', 'ward_no', 'wardNumber', 'zone', 'area']
            
            filtered_vehicles = None
            for field in ward_fields:
                if field in all_vehicles.columns:
                    filtered_vehicles = all_vehicles[all_vehicles[field].astype(str) == str(ward_no)]
                    if len(filtered_vehicles) > 0:
                        logger.info(f"Found {len(filtered_vehicles)} vehicles in ward {ward_no} using field '{field}'")
                        break
            
            # If no ward field found or no matches, return empty DataFrame
            if filtered_vehicles is None or len(filtered_vehicles) == 0:
                logger.warning(f"No vehicles found in ward {ward_no}")
                filtered_vehicles = pd.DataFrame()
            
            return filtered_vehicles
            
        except Exception as e:
            logger.error(f"Error filtering vehicles by ward {ward_no}: {e}")
            return self._create_fallback_vehicles()
    
    def get_token_info(self) -> Dict:
        """Get information about the current authentication token."""
        return self.auth_service.get_token_info()
    
    def refresh_token(self) -> bool:
        """Force refresh the authentication token."""
        return self.auth_service.force_refresh()
    
    def _process_vehicle_data(self, vehicles_data) -> pd.DataFrame:
        """Process and standardize vehicle data from API response."""
        # Convert to DataFrame - handle paginated response
        if isinstance(vehicles_data, list):
            df = pd.DataFrame(vehicles_data)
        elif isinstance(vehicles_data, dict):
            if 'content' in vehicles_data:  # Paginated response
                df = pd.DataFrame(vehicles_data['content'])
            elif 'data' in vehicles_data:
                df = pd.DataFrame(vehicles_data['data'])
            elif 'vehicles' in vehicles_data:
                df = pd.DataFrame(vehicles_data['vehicles'])
            else:
                df = pd.DataFrame([vehicles_data])
        else:
            return self._create_fallback_vehicles()
        
        df = self._standardize_vehicle_data(df)
        
        # Filter active vehicles - handle different status formats
        if 'status' in df.columns:
            active_vehicles = df[df['status'].str.upper().isin(['ACTIVE', 'AVAILABLE', 'ONLINE', 'OPERATIONAL'])].copy()
        else:
            # If no status column, assume all are active
            df['status'] = 'active'
            active_vehicles = df.copy()
        
        if len(active_vehicles) == 0:
            active_vehicles = df.copy()
        
        logger.success(f"Loaded {len(active_vehicles)} active vehicles from live API")
        return active_vehicles
    
    def _standardize_vehicle_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize vehicle data column names and format."""
        # Preserve all live API fields and add mappings
        live_api_fields = ['vehicleId', 'vehicleNo', 'driverName', 'imeiN', 'phoneNo', 'wardNo', 'vehicleType', 'department', 'timestamp']
        
        # Keep original fields from API
        for field in live_api_fields:
            if field in df.columns:
                continue  # Keep as-is
        
        # Add legacy mappings for compatibility
        column_mappings = {
            'id': 'vehicle_id',
            'vehicle_number': 'vehicle_id',
            'registration_number': 'vehicle_id',
            'wardNumber': 'ward_no',
            'name': 'vehicle_name',
            'vehicleName': 'vehicle_name',
            'type': 'vehicle_type',
            'capacity': 'capacity',
            'vehicleCapacity': 'capacity',
            'location': 'location',
            'currentLocation': 'location',
            'latitude': 'lat',
            'longitude': 'lon',
            'lng': 'lon'
        }
        
        # Rename columns
        for old_name, new_name in column_mappings.items():
            if old_name in df.columns:
                df = df.rename(columns={old_name: new_name})
        
        # Ensure required columns exist
        required_columns = ['vehicle_id', 'status']
        for col in required_columns:
            if col not in df.columns:
                if col == 'vehicle_id':
                    # Use vehicleNo as primary vehicle_id
                    if 'vehicleNo' in df.columns:
                        df['vehicle_id'] = df['vehicleNo']
                    elif 'vehicleId' in df.columns:
                        df['vehicle_id'] = df['vehicleId']
                    else:
                        df['vehicle_id'] = [f"vehicle_{i+1}" for i in range(len(df))]
                elif col == 'status':
                    df['status'] = 'active'
        
        # Add default values for missing columns
        if 'vehicle_type' not in df.columns:
            df['vehicle_type'] = 'garbage_truck'
        if 'capacity' not in df.columns:
            df['capacity'] = 500  # Default capacity in kg
        if 'ward_no' not in df.columns:
            df['ward_no'] = '1'  # Default ward
        
        return df
    
    def _create_fallback_vehicles(self) -> pd.DataFrame:
        """Create fallback vehicle data when API is unavailable."""
        logger.warning("Creating fallback vehicle data")
        
        fallback_data = [
            {'vehicle_id': 'SWM001', 'vehicleId': 'SWM001', 'vehicleNo': 'SWM001', 'driverName': 'Driver1', 'imeiN': '123456789', 'phoneNo': '9876543210', 'wardNo': '1', 'vehicleType': 'garbage_truck', 'department': 'SWM', 'timestamp': '2024-01-01T00:00:00Z', 'status': 'active', 'capacity': 500},
            {'vehicle_id': 'SWM002', 'vehicleId': 'SWM002', 'vehicleNo': 'SWM002', 'driverName': 'Driver2', 'imeiN': '123456790', 'phoneNo': '9876543211', 'wardNo': '1', 'vehicleType': 'garbage_truck', 'department': 'SWM', 'timestamp': '2024-01-01T00:00:00Z', 'status': 'active', 'capacity': 500},
            {'vehicle_id': 'SWM003', 'vehicleId': 'SWM003', 'vehicleNo': 'SWM003', 'driverName': 'Driver3', 'imeiN': '123456791', 'phoneNo': '9876543212', 'wardNo': '1', 'vehicleType': 'garbage_truck', 'department': 'SWM', 'timestamp': '2024-01-01T00:00:00Z', 'status': 'active', 'capacity': 500},
            {'vehicle_id': 'SWM004', 'vehicleId': 'SWM004', 'vehicleNo': 'SWM004', 'driverName': 'Driver4', 'imeiN': '123456792', 'phoneNo': '9876543213', 'wardNo': '1', 'vehicleType': 'garbage_truck', 'department': 'SWM', 'timestamp': '2024-01-01T00:00:00Z', 'status': 'active', 'capacity': 500},
            {'vehicle_id': 'SWM005', 'vehicleId': 'SWM005', 'vehicleNo': 'SWM005', 'driverName': 'Driver5', 'imeiN': '123456793', 'phoneNo': '9876543214', 'wardNo': '1', 'vehicleType': 'garbage_truck', 'department': 'SWM', 'timestamp': '2024-01-01T00:00:00Z', 'status': 'active', 'capacity': 500}
        ]
        
        return pd.DataFrame(fallback_data)
    
    def get_vehicle_by_id(self, vehicle_id: str) -> Optional[Dict]:
        """Get specific vehicle data by ID."""
        try:
            token = self.auth_service.get_valid_token()
            if not token:
                logger.error("No valid token available")
                return None
            
            url = f"{self.base_url}/api/vehicles/{vehicle_id}"
            headers = {'Authorization': f'Bearer {token}'}
            response = self.session.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Vehicle {vehicle_id} not found: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching vehicle {vehicle_id}: {e}")
            return None
    
    def update_vehicle_status(self, vehicle_id: str, status: str) -> bool:
        """Update vehicle status via API."""
        try:
            token = self.auth_service.get_valid_token()
            if not token:
                logger.error("No valid token available")
                return False
            
            url = f"{self.base_url}/api/vehicles/{vehicle_id}/status"
            data = {'status': status}
            headers = {'Authorization': f'Bearer {token}'}
            
            response = self.session.put(url, json=data, headers=headers, timeout=30)
            
            if response.status_code in [200, 204]:
                logger.info(f"Updated vehicle {vehicle_id} status to {status}")
                return True
            else:
                logger.error(f"Failed to update vehicle status: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating vehicle status: {e}")
            return False