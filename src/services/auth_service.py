"""Authentication service for automatic token generation and management."""
import os
import requests
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from loguru import logger
from dotenv import load_dotenv
import base64
import json
import threading
import time

# Load environment variables
load_dotenv()

class AuthService:
    def __init__(self):
        self.base_url = os.getenv('SWM_API_BASE_URL', 'https://uat-swm-main-service-hdaqcdcscbfedhhn.centralindia-01.azurewebsites.net')
        self.username = os.getenv('SWM_USERNAME', '')
        self.password = os.getenv('SWM_PASSWORD', '')
        self.current_token = None
        self.token_expires_at = None
        self.refresh_thread = None
        self.stop_refresh = False
        
        logger.info(f"AuthService initialized with base URL: {self.base_url}")
        logger.info(f"Username configured: {'Yes' if self.username else 'No'}")
        
        # Generate initial token
        self._generate_token()
        
        # Start automatic refresh thread
        self._start_token_refresh()
    
    def get_valid_token(self) -> Optional[str]:
        """Get a valid access token, refreshing if necessary."""
        if not self.current_token:
            logger.warning("No token available, generating new one")
            self._generate_token()
        
        # Check if token is about to expire (refresh 5 minutes before expiry)
        if self.token_expires_at and datetime.now() >= (self.token_expires_at - timedelta(minutes=5)):
            logger.info("Token expiring soon, refreshing")
            self._generate_token()
        
        return self.current_token
    
    def _generate_token(self) -> bool:
        """Generate a new access token using username and password."""
        try:
            if not self.username or not self.password:
                logger.error("Username or password not configured")
                return False
            
            url = f"{self.base_url}/auth/login"
            login_data = {
                'loginId': self.username,
                'password': self.password
            }
            
            headers = {
                'accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
            logger.info(f"Generating new token from {url}")
            response = requests.post(url, json=login_data, headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                logger.success("Login successful")
                
                # Extract token from response
                token = self._extract_token_from_response(data)
                if token:
                    self.current_token = token
                    self.token_expires_at = self._get_token_expiry(token)
                    
                    logger.success(f"Token generated successfully")
                    if self.token_expires_at:
                        logger.info(f"Token expires at: {self.token_expires_at}")
                    
                    # Update .env file with new token
                    self._update_env_token(token)
                    return True
                else:
                    logger.error("Could not extract token from response")
                    return False
            else:
                logger.error(f"Login failed with status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Token generation error: {e}")
            return False
    
    def _extract_token_from_response(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract token from API response."""
        # Common token field names
        token_fields = ['token', 'access_token', 'accessToken', 'authToken', 'jwt', 'bearerToken']
        
        # Check direct fields
        for field in token_fields:
            if field in data:
                return data[field]
        
        # Check nested data field
        if isinstance(data, dict) and 'data' in data and isinstance(data['data'], dict):
            for field in token_fields:
                if field in data['data']:
                    return data['data'][field]
        
        # Check if the entire response is a token (JWT format)
        if isinstance(data, str) and data.startswith('eyJ'):
            return data
        
        logger.warning(f"Token not found in response. Available keys: {list(data.keys()) if isinstance(data, dict) else 'Not dict'}")
        return None
    
    def _get_token_expiry(self, token: str) -> Optional[datetime]:
        """Extract expiry time from JWT token."""
        try:
            # Simple JWT decode without external library
            parts = token.split('.')
            if len(parts) >= 2:
                # Decode payload (second part)
                payload = parts[1]
                # Add padding if needed
                payload += '=' * (4 - len(payload) % 4)
                decoded_bytes = base64.urlsafe_b64decode(payload)
                decoded = json.loads(decoded_bytes)
                
                if 'exp' in decoded:
                    return datetime.fromtimestamp(decoded['exp'])
        except Exception as e:
            logger.warning(f"Could not decode token expiry: {e}")
        
        # Default to 24 hours if can't decode
        return datetime.now() + timedelta(hours=24)
    
    def _update_env_token(self, token: str):
        """Update the .env file with the new token."""
        try:
            env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
            
            # Read current .env content
            if os.path.exists(env_path):
                with open(env_path, 'r') as f:
                    lines = f.readlines()
            else:
                lines = []
            
            # Update or add SWM_TOKEN line
            token_updated = False
            for i, line in enumerate(lines):
                if line.startswith('SWM_TOKEN='):
                    lines[i] = f'SWM_TOKEN={token}\n'
                    token_updated = True
                    break
            
            if not token_updated:
                lines.append(f'SWM_TOKEN={token}\n')
            
            # Write back to .env file
            with open(env_path, 'w') as f:
                f.writelines(lines)
            
            logger.info("Updated .env file with new token")
            
        except Exception as e:
            logger.error(f"Failed to update .env file: {e}")
    
    def _start_token_refresh(self):
        """Start background thread for automatic token refresh."""
        def refresh_worker():
            while not self.stop_refresh:
                try:
                    # Check every 5 minutes
                    time.sleep(300)  # 5 minutes
                    
                    if self.stop_refresh:
                        break
                    
                    # Refresh if token expires in next 10 minutes
                    if self.token_expires_at and datetime.now() >= (self.token_expires_at - timedelta(minutes=10)):
                        logger.info("Auto-refreshing token")
                        self._generate_token()
                        
                except Exception as e:
                    logger.error(f"Token refresh thread error: {e}")
        
        self.refresh_thread = threading.Thread(target=refresh_worker, daemon=True)
        self.refresh_thread.start()
        logger.info("Started automatic token refresh thread")
    
    def stop_token_refresh(self):
        """Stop the automatic token refresh thread."""
        self.stop_refresh = True
        if self.refresh_thread:
            self.refresh_thread.join(timeout=1)
        logger.info("Stopped automatic token refresh")
    
    def is_token_valid(self) -> bool:
        """Check if current token is valid and not expired."""
        if not self.current_token:
            return False
        
        if self.token_expires_at and datetime.now() >= self.token_expires_at:
            return False
        
        return True
    
    def force_refresh(self) -> bool:
        """Force refresh the token immediately."""
        logger.info("Force refreshing token")
        return self._generate_token()
    
    def get_token_info(self) -> Dict[str, Any]:
        """Get information about the current token."""
        return {
            'has_token': bool(self.current_token),
            'expires_at': self.token_expires_at.isoformat() if self.token_expires_at else None,
            'is_valid': self.is_token_valid(),
            'time_until_expiry': str(self.token_expires_at - datetime.now()) if self.token_expires_at else None
        }

# Global instance
_auth_service = None

def get_auth_service() -> AuthService:
    """Get the global auth service instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service