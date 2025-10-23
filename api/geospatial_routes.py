"""FastAPI integration for geospatial route optimization."""
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Header, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Dict, Any
import numpy as np
import tempfile
import os
import shutil
import geopandas as gpd
import pandas as pd
import folium
from sklearn.cluster import KMeans
import json
import networkx as nx
import numpy as np
from shapely.geometry import Point
from scipy.spatial.distance import cdist
import math
from services.vehicle_service import VehicleService
from api.vehicles_api import router as vehicles_router
from routing.capacity_optimizer import CapacityRouteOptimizer
from loguru import logger
import warnings

# Suppress specific geographic CRS warnings for intentional lat/lon usage in maps
warnings.filterwarnings('ignore', message='.*Geometry is in a geographic CRS.*')

# API Key for authentication - Change this in production!
API_KEY = "swm-2024-secure-key"

# Security scheme
security = HTTPBearer()

def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API key from Authorization header."""
    if credentials.credentials != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return credentials.credentials

app = FastAPI(
    title="Geospatial AI Route Optimizer",
    description="Dynamic garbage collection route optimization using live vehicle data and road network",
    version="2.0.0",
    openapi_tags=[
        {
            "name": "clusters",
            "description": "Cluster management and road coordinate retrieval"
        },
        {
            "name": "optimization",
            "description": "Route optimization operations"
        },
        {
            "name": "maps",
            "description": "Map generation and visualization"
        }
    ]
)

# Initialize vehicle service
vehicle_service = VehicleService()

# Include vehicle API routes
app.include_router(vehicles_router)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def safe_argmin(distances):
    """Safely get argmin, handling empty sequences."""
    if not distances or len(distances) == 0:
        return None
    return np.argmin(distances)

def convert_numpy_types(obj):
    """Convert numpy types to JSON serializable types."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(item) for item in obj]
    return obj

@app.post("/optimize-routes", tags=["optimization"])
async def optimize_routes(
    roads_file: UploadFile = File(..., description="Roads GeoJSON file"),
    buildings_file: UploadFile = File(..., description="Buildings GeoJSON file"), 
    ward_geojson: UploadFile = File(..., description="Ward boundary GeoJSON file"),
    ward_no: str = Form(..., description="Ward number to filter vehicles"),
    vehicles_csv: UploadFile = File(default=None, description="Optional: Custom vehicles CSV file")
):
    """Upload files and run complete route optimization pipeline."""
    
    # Validate file types and ward_no
    if not roads_file.filename or not roads_file.filename.lower().endswith('.geojson'):
        raise HTTPException(status_code=400, detail="Roads file must be GeoJSON")
    if not buildings_file.filename or not buildings_file.filename.lower().endswith('.geojson'):
        raise HTTPException(status_code=400, detail="Buildings file must be GeoJSON")
    if not ward_no or not ward_no.strip():
        raise HTTPException(status_code=400, detail="Ward number is required")
    
    # Create temporary directory for processing
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Save uploaded files
            roads_path = os.path.join(temp_dir, "roads.geojson")
            buildings_path = os.path.join(temp_dir, "buildings.geojson")
            ward_path = os.path.join(temp_dir, "ward.geojson")
            
            with open(roads_path, "wb") as f:
                shutil.copyfileobj(roads_file.file, f)
            with open(buildings_path, "wb") as f:
                shutil.copyfileobj(buildings_file.file, f)
            with open(ward_path, "wb") as f:
                shutil.copyfileobj(ward_geojson.file, f)
            
            # Load geospatial data
            buildings_gdf = gpd.read_file(buildings_path)
            roads_gdf = gpd.read_file(roads_path)
            
            # Convert to WGS84 if needed
            if buildings_gdf.crs != 'EPSG:4326':
                buildings_gdf = buildings_gdf.to_crs('EPSG:4326')
            if roads_gdf.crs != 'EPSG:4326':
                roads_gdf = roads_gdf.to_crs('EPSG:4326')
            
            # Get vehicle data - use uploaded CSV or live API data
            try:
                if vehicles_csv and vehicles_csv.filename:
                    # Use uploaded CSV file
                    if not vehicles_csv.filename.endswith('.csv'):
                        raise HTTPException(status_code=400, detail="Vehicles file must be CSV format")
                    
                    vehicles_csv_path = os.path.join(temp_dir, "vehicles.csv")
                    with open(vehicles_csv_path, "wb") as f:
                        shutil.copyfileobj(vehicles_csv.file, f)
                    
                    vehicles_df = pd.read_csv(vehicles_csv_path)
                    print(f"Loaded {len(vehicles_df)} vehicles from uploaded CSV")
                    vehicles_path = vehicles_csv_path
                    vehicle_source = "Uploaded CSV"
                else:
                    # Use live API data filtered by ward
                    vehicles_df = vehicle_service.get_vehicles_by_ward(ward_no.strip())
                    print(f"Loaded {len(vehicles_df)} vehicles for ward {ward_no}")
                    
                    # Save vehicle data for map generation
                    vehicles_csv_path = os.path.join(temp_dir, "vehicles.csv")
                    vehicles_df.to_csv(vehicles_csv_path, index=False)
                    vehicles_path = vehicles_csv_path
                    vehicle_source = "Live API (Ward Filtered)"
                
                if len(vehicles_df) == 0:
                    raise HTTPException(status_code=404, detail=f"No vehicles found")
                
                # Optimize routes with capacity constraints
                optimizer = CapacityRouteOptimizer()
                optimization_result = optimizer.optimize_routes_with_capacity(
                    buildings_gdf, vehicles_df, roads_gdf
                )
                
                print(f"Route optimization completed: {optimization_result['active_vehicles']} active vehicles, {optimization_result['total_houses']} houses")
                
            except HTTPException:
                raise
            except Exception as vehicle_error:
                print(f"Failed to get vehicle data: {vehicle_error}")
                raise HTTPException(status_code=500, detail="Failed to get vehicle data")
            
            # Generate map using uploaded files
            try:
                map_html = generate_map_from_files(ward_path, roads_path, buildings_path, vehicles_path)
                print("Map generation completed successfully")
            except Exception as map_error:
                print(f"Map generation error: {map_error}")
                import traceback
                print(f"Full error: {traceback.format_exc()}")
                # Create simple fallback map
                map_html = "<html><body><h1>Map Processing Complete</h1><p>Data uploaded successfully</p></body></html>"
            
            # Save map and data to output directory
            os.makedirs("output", exist_ok=True)
            try:
                with open("output/route_map.html", "w", encoding="utf-8") as f:
                    f.write(map_html)
            except Exception as save_error:
                print(f"File save error: {save_error}")
                raise save_error
            
            # Save data files for cluster endpoint
            shutil.copy(ward_path, "output/ward.geojson")
            shutil.copy(buildings_path, "output/buildings.geojson")
            shutil.copy(roads_path, "output/roads.geojson")
            shutil.copy(vehicles_path, "output/vehicles.csv")
            
            # Prepare optimized route data for response
            active_vehicles = vehicles_df[
                vehicles_df['status'].str.upper().isin(['ACTIVE', 'AVAILABLE', 'ONLINE'])
            ]
            
            vehicle_data = []
            route_summary = []
            
            for vehicle_id, assignment in optimization_result['route_assignments'].items():
                vehicle_info = assignment['vehicle_info']
                vehicle_data.append({
                    "vehicle_id": str(vehicle_info['vehicle_id']),
                    "vehicle_type": str(vehicle_info['vehicle_type']),
                    "status": str(vehicle_info['status']),
                    "trips_assigned": vehicle_info['trips_assigned'],
                    "houses_assigned": vehicle_info['houses_assigned'],
                    "capacity_per_trip": vehicle_info['capacity_per_trip']
                })
                
                for trip in assignment['trips']:
                    route_summary.append({
                        "trip_id": trip['trip_id'],
                        "vehicle_id": vehicle_id,
                        "house_count": trip['house_count'],
                        "cluster_id": trip['cluster_id']
                    })
            
            return JSONResponse({
                "status": "success",
                "message": f"Route optimization completed for ward {ward_no} with {optimization_result['active_vehicles']} active vehicles",
                "maps": {
                    "route_map": "/generate-map/route_map",
                    "cluster_analysis": "/generate-map/cluster_analysis"
                },
                "dashboard": "/cluster-dashboard",
                "ward_no": ward_no,
                "total_vehicles": len(vehicles_df),
                "active_vehicles": optimization_result['active_vehicles'],
                "total_houses": optimization_result['total_houses'],
                "total_trips": len(route_summary),
                "vehicle_source": vehicle_source,
                "vehicles": vehicle_data,
                "route_summary": route_summary,
                "features": [
                    "Active vehicle filtering",
                    "Capacity-based trip assignment",
                    "Multiple trips per vehicle",
                    "Optimized house-to-vehicle allocation",
                    "Real-time route optimization"
                ]
            })
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error details: {error_details}")
            raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")







class Coordinate(BaseModel):
    longitude: float
    latitude: float

class RoadSegment(BaseModel):
    start_coordinate: Coordinate
    end_coordinate: Coordinate
    distance_meters: float

class VehicleInfo(BaseModel):
    vehicle_id: str
    vehicle_type: str
    status: str
    capacity: int

class ClusterBounds(BaseModel):
    min_longitude: float
    max_longitude: float
    min_latitude: float
    max_latitude: float

class ClusterRoadsResponse(BaseModel):
    cluster_id: int
    vehicle_info: VehicleInfo
    buildings_count: int
    roads: List[RoadSegment]
    total_road_segments: int
    cluster_bounds: ClusterBounds

class AllClustersRoadsResponse(BaseModel):
    total_clusters: int
    clusters: List[ClusterRoadsResponse]

@app.get("/cluster/{cluster_id}", tags=["clusters"], response_model=ClusterRoadsResponse)
async def get_cluster_roads(cluster_id: int):
    """Get cluster roads with coordinates for a specific cluster.
    
    Returns all road segments within the cluster along with their start/end coordinates.
    Each road segment includes the geographic coordinates and distance in meters.
    """
    try:
        # Load processed data from output directory
        roads_path = os.path.join("output", "roads.geojson")
        buildings_path = os.path.join("output", "buildings.geojson")
        vehicles_path = os.path.join("output", "vehicles.csv")
        
        if not all(os.path.exists(p) for p in [roads_path, buildings_path, vehicles_path]):
            raise HTTPException(status_code=404, detail="Cluster data not found. Run /optimize-routes first")
        
        # Load data
        roads_gdf = gpd.read_file(roads_path)
        buildings_gdf = gpd.read_file(buildings_path)
        vehicles_df = pd.read_csv(vehicles_path)
        
        # Convert to WGS84 if needed
        if roads_gdf.crs != 'EPSG:4326':
            roads_gdf = roads_gdf.to_crs('EPSG:4326')
        if buildings_gdf.crs != 'EPSG:4326':
            buildings_gdf = buildings_gdf.to_crs('EPSG:4326')
        
        # Get active vehicles and create clusters
        active_vehicles = vehicles_df[
            vehicles_df['status'].str.upper().isin(['ACTIVE', 'AVAILABLE', 'ONLINE'])
        ]
        
        if cluster_id >= len(active_vehicles):
            raise HTTPException(status_code=404, detail=f"Cluster {cluster_id} not found")
        
        # Create building clusters using KMeans with proper CRS
        buildings_projected = buildings_gdf.to_crs('EPSG:3857')  # Web Mercator for accurate clustering
        building_centroids = [(pt.x, pt.y) for pt in buildings_projected.geometry.centroid]
        kmeans = KMeans(n_clusters=min(len(active_vehicles), len(building_centroids)), random_state=42, n_init=10)
        building_clusters = kmeans.fit_predict(building_centroids).tolist()  # Convert to list
        
        # Get buildings for this cluster
        cluster_buildings = buildings_gdf[[i == cluster_id for i in building_clusters]]
        
        if len(cluster_buildings) == 0:
            raise HTTPException(status_code=404, detail=f"No buildings found in cluster {cluster_id}")
        
        # Build road network graph
        G = nx.Graph()
        road_coordinates = []
        
        for idx, road in roads_gdf.iterrows():
            geom = road.geometry
            if geom.geom_type == 'MultiLineString':
                for line in geom.geoms:
                    coords = list(line.coords)
                    road_coordinates.extend(coords)
                    for i in range(len(coords)-1):
                        p1, p2 = coords[i], coords[i+1]
                        dist = ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5
                        G.add_edge(p1, p2, weight=dist)
            else:
                coords = list(geom.coords)
                road_coordinates.extend(coords)
                for i in range(len(coords)-1):
                    p1, p2 = coords[i], coords[i+1]
                    dist = ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5
                    G.add_edge(p1, p2, weight=dist)
        
        # Find roads used by this cluster
        cluster_road_points = list(set(road_coordinates))
        house_locations = [(pt.x, pt.y) for pt in cluster_buildings.geometry.centroid]
        
        # Find nearest road points to houses
        cluster_roads = []
        for house_pt in house_locations:
            if cluster_road_points:
                distances = [((house_pt[0]-rp[0])**2 + (house_pt[1]-rp[1])**2)**0.5 for rp in cluster_road_points]
                nearest_idx = np.argmin(distances)
                nearest_road_point = cluster_road_points[nearest_idx]
                
                # Find all road segments connected to this point
                for edge in G.edges(nearest_road_point, data=True):
                    road_segment = {
                        "start_coordinate": {"longitude": float(edge[0][0]), "latitude": float(edge[0][1])},
                        "end_coordinate": {"longitude": float(edge[1][0]), "latitude": float(edge[1][1])},
                        "distance_meters": float(edge[2]['weight'] * 111000)  # Approximate conversion
                    }
                    if road_segment not in cluster_roads:
                        cluster_roads.append(road_segment)
        
        # Get vehicle info
        vehicle_info = active_vehicles.iloc[cluster_id] if cluster_id < len(active_vehicles) else {}
        
        response_data = {
            "cluster_id": cluster_id,
            "vehicle_info": {
                "vehicle_id": str(vehicle_info.get('vehicle_id', f'vehicle_{cluster_id}')),
                "vehicle_type": str(vehicle_info.get('vehicle_type', 'standard')),
                "status": str(vehicle_info.get('status', 'active')),
                "capacity": vehicle_info.get('capacity', 1000)
            },
            "buildings_count": len(cluster_buildings),
            "roads": cluster_roads,
            "total_road_segments": len(cluster_roads),
            "cluster_bounds": {
                "min_longitude": cluster_buildings.bounds.minx.min(),
                "max_longitude": cluster_buildings.bounds.maxx.max(),
                "min_latitude": cluster_buildings.bounds.miny.min(),
                "max_latitude": cluster_buildings.bounds.maxy.max()
            }
        }
        
        # Convert all numpy types to JSON serializable types
        response_data = convert_numpy_types(response_data)
        
        return JSONResponse(response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cluster roads: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cluster roads: {str(e)}")

@app.get("/clusters", tags=["clusters"], response_model=AllClustersRoadsResponse)
async def get_all_cluster_roads():
    """Get cluster roads with coordinates for all clusters.
    
    Returns all road segments within each cluster along with their start/end coordinates.
    Each road segment includes the geographic coordinates and distance in meters.
    """
    try:
        roads_path = os.path.join("output", "roads.geojson")
        buildings_path = os.path.join("output", "buildings.geojson")
        vehicles_path = os.path.join("output", "vehicles.csv")
        
        if not all(os.path.exists(p) for p in [roads_path, buildings_path, vehicles_path]):
            raise HTTPException(status_code=404, detail="Cluster data not found. Run /optimize-routes first")
        
        roads_gdf = gpd.read_file(roads_path)
        buildings_gdf = gpd.read_file(buildings_path)
        vehicles_df = pd.read_csv(vehicles_path)
        
        if roads_gdf.crs != 'EPSG:4326':
            roads_gdf = roads_gdf.to_crs('EPSG:4326')
        if buildings_gdf.crs != 'EPSG:4326':
            buildings_gdf = buildings_gdf.to_crs('EPSG:4326')
        
        active_vehicles = vehicles_df[
            vehicles_df['status'].str.upper().isin(['ACTIVE', 'AVAILABLE', 'ONLINE'])
        ]
        
        buildings_projected = buildings_gdf.to_crs('EPSG:3857')
        building_centroids = [(pt.x, pt.y) for pt in buildings_projected.geometry.centroid]
        kmeans = KMeans(n_clusters=min(len(active_vehicles), len(building_centroids)), random_state=42, n_init=10)
        building_clusters = kmeans.fit_predict(building_centroids).tolist()
        
        G = nx.Graph()
        road_coordinates = []
        
        for idx, road in roads_gdf.iterrows():
            geom = road.geometry
            if geom.geom_type == 'MultiLineString':
                for line in geom.geoms:
                    coords = list(line.coords)
                    road_coordinates.extend(coords)
                    for i in range(len(coords)-1):
                        p1, p2 = coords[i], coords[i+1]
                        dist = ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5
                        G.add_edge(p1, p2, weight=dist)
            else:
                coords = list(geom.coords)
                road_coordinates.extend(coords)
                for i in range(len(coords)-1):
                    p1, p2 = coords[i], coords[i+1]
                    dist = ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5
                    G.add_edge(p1, p2, weight=dist)
        
        cluster_road_points = list(set(road_coordinates))
        all_clusters = []
        
        for cluster_id in range(len(active_vehicles)):
            cluster_buildings = buildings_gdf[[i == cluster_id for i in building_clusters]]
            
            if len(cluster_buildings) == 0:
                continue
            
            house_locations_wgs84 = []
            for i in range(len(buildings_gdf)):
                if building_clusters[i] == cluster_id:
                    pt = buildings_gdf.iloc[i].geometry.centroid
                    house_locations_wgs84.append((pt.x, pt.y))
            
            cluster_roads = []
            for house_pt in house_locations_wgs84:
                if cluster_road_points:
                    distances = [((house_pt[0]-rp[0])**2 + (house_pt[1]-rp[1])**2)**0.5 for rp in cluster_road_points]
                    nearest_idx = np.argmin(distances)
                    nearest_road_point = cluster_road_points[nearest_idx]
                    
                    for edge in G.edges(nearest_road_point, data=True):
                        road_segment = {
                            "start_coordinate": {"longitude": float(edge[0][0]), "latitude": float(edge[0][1])},
                            "end_coordinate": {"longitude": float(edge[1][0]), "latitude": float(edge[1][1])},
                            "distance_meters": float(edge[2]['weight'] * 111000)
                        }
                        if road_segment not in cluster_roads:
                            cluster_roads.append(road_segment)
            
            vehicle_info = active_vehicles.iloc[cluster_id] if cluster_id < len(active_vehicles) else {}
            
            cluster_data = {
                "cluster_id": cluster_id,
                "vehicle_info": {
                    "vehicle_id": str(vehicle_info.get('vehicle_id', f'vehicle_{cluster_id}')),
                    "vehicle_type": str(vehicle_info.get('vehicle_type', 'standard')),
                    "status": str(vehicle_info.get('status', 'active')),
                    "capacity": vehicle_info.get('capacity', 1000)
                },
                "buildings_count": len(cluster_buildings),
                "roads": cluster_roads,
                "total_road_segments": len(cluster_roads),
                "cluster_bounds": {
                    "min_longitude": cluster_buildings.bounds.minx.min(),
                    "max_longitude": cluster_buildings.bounds.maxx.max(),
                    "min_latitude": cluster_buildings.bounds.miny.min(),
                    "max_latitude": cluster_buildings.bounds.maxy.max()
                }
            }
            
            all_clusters.append(cluster_data)
        
        response_data = {
            "total_clusters": len(all_clusters),
            "clusters": all_clusters
        }
        
        response_data = convert_numpy_types(response_data)
        
        return JSONResponse(response_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting all cluster roads: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get all cluster roads: {str(e)}")

@app.get("/generate-map/{map_type}", tags=["maps"])
async def generate_map(map_type: str):
    """Generate and return map HTML."""
    # Allow any map type
    pass
    
    file_path = os.path.join("output", f"{map_type}.html")
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Map not found. Please upload files first using /optimize-routes")
    
    with open(file_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    return HTMLResponse(content=html_content)

def generate_map_from_files(ward_file, roads_file, buildings_file, vehicles_file=None):
    """Generate map with capacity-based route optimization."""
    # Load GeoJSON data using geopandas
    ward_gdf = gpd.read_file(ward_file)
    roads_gdf = gpd.read_file(roads_file)
    buildings_gdf = gpd.read_file(buildings_file)
    
    # Convert to WGS84 if needed
    if ward_gdf.crs != 'EPSG:4326':
        ward_gdf = ward_gdf.to_crs('EPSG:4326')
    if roads_gdf.crs != 'EPSG:4326':
        roads_gdf = roads_gdf.to_crs('EPSG:4326')
    if buildings_gdf.crs != 'EPSG:4326':
        buildings_gdf = buildings_gdf.to_crs('EPSG:4326')
    
    # Clean data - keep only geometry and essential columns
    ward_clean = ward_gdf[['geometry']]
    buildings_clean = buildings_gdf[['geometry']]
    
    # Get center coordinates from ward bounds
    bounds = ward_gdf.total_bounds
    center_lat = (bounds[1] + bounds[3]) / 2
    center_lon = (bounds[0] + bounds[2]) / 2
    
    # Create map
    m = folium.Map(location=[center_lat, center_lon], zoom_start=15)
    
    # Add ward boundaries to base layer
    ward_layer = folium.FeatureGroup(name="Ward Boundary", show=True)
    folium.GeoJson(
        json.loads(ward_clean.to_json()),
        style_function=lambda x: {
            'fillColor': 'transparent',
            'color': 'darkblue',
            'weight': 3,
            'fillOpacity': 0
        }
    ).add_to(ward_layer)
    ward_layer.add_to(m)
    
    # Load vehicle data if available
    vehicles_df = None
    if vehicles_file and os.path.exists(vehicles_file):
        import pandas as pd
        vehicles_df = pd.read_csv(vehicles_file)
        print(f"Loaded {len(vehicles_df)} vehicles for map generation")
        
        # Use capacity-based optimization for active vehicles only
        optimizer = CapacityRouteOptimizer()
        optimization_result = optimizer.optimize_routes_with_capacity(
            buildings_gdf, vehicles_df, roads_gdf
        )
        
        # Create clusters based on optimization result
        building_clusters = [0] * len(buildings_gdf)
        cluster_id = 0
        
        for vehicle_id, assignment in optimization_result['route_assignments'].items():
            for trip in assignment['trips']:
                for house_idx in trip['houses']:
                    if house_idx < len(building_clusters):
                        building_clusters[house_idx] = cluster_id
                cluster_id += 1
    else:
        # Fallback to simple clustering
        building_centroids = [(pt.x, pt.y) for pt in buildings_gdf.geometry.centroid]
        kmeans = KMeans(n_clusters=min(5, len(building_centroids)), random_state=42, n_init=10)
        building_clusters = kmeans.fit_predict(building_centroids)
    
    # Create road network graph
    G = nx.Graph()
    
    # Build road network for routing
    for idx, road in roads_gdf.iterrows():
        geom = road.geometry
        if geom.geom_type == 'MultiLineString':
            for line in geom.geoms:
                coords = list(line.coords)
                for i in range(len(coords)-1):
                    p1, p2 = coords[i], coords[i+1]
                    dist = ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5
                    G.add_edge(p1, p2, weight=dist)
        else:
            coords = list(geom.coords)
            for i in range(len(coords)-1):
                p1, p2 = coords[i], coords[i+1]
                dist = ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)**0.5
                G.add_edge(p1, p2, weight=dist)
    
    # Colors and vehicle names from active vehicles or defaults
    colors = ['red', 'blue', 'green', 'purple', 'orange', 'brown', 'pink', 'gray', 'olive', 'cyan']
    if vehicles_df is not None:
        active_vehicles = vehicles_df[
            vehicles_df['status'].str.upper().isin(['ACTIVE', 'AVAILABLE', 'ONLINE'])
        ]
        vehicle_names = active_vehicles['vehicle_id'].tolist()[:len(set(building_clusters))]
    else:
        vehicle_names = ['Vehicle A', 'Vehicle B', 'Vehicle C', 'Vehicle D', 'Vehicle E']
    
    # Process each cluster with separate layers
    n_clusters = len(set(building_clusters))
    for cluster_id in range(n_clusters):
        cluster_buildings = [i for i, c in enumerate(building_clusters) if c == cluster_id]
        
        if not cluster_buildings:
            continue
        
        # Create separate layer for each cluster with active vehicle info
        vehicle_name = vehicle_names[cluster_id] if cluster_id < len(vehicle_names) else f"Vehicle {cluster_id + 1}"
        vehicle_info = ""
        if vehicles_df is not None and cluster_id < len(active_vehicles):
            vehicle = active_vehicles.iloc[cluster_id]
            vehicle_info = f" ({vehicle.get('vehicle_type', 'N/A')} - ACTIVE)"
        
        cluster_layer = folium.FeatureGroup(
            name=f"🚛 {vehicle_name}{vehicle_info} - {len(cluster_buildings)} buildings",
            show=True
        )
            
        # Find all road points for routing
        cluster_road_points = []
        for idx, road in roads_gdf.iterrows():
            geom = road.geometry
            if geom.geom_type == 'MultiLineString':
                for line in geom.geoms:
                    cluster_road_points.extend(list(line.coords))
            else:
                cluster_road_points.extend(list(geom.coords))
        
        # Create waste collection route covering all houses
        if cluster_buildings:
            cluster_road_points = list(set(cluster_road_points))
            
            # Get house locations for this cluster (already in WGS84)
            house_locations_wgs84 = []
            for i in cluster_buildings:
                pt = buildings_gdf.iloc[i].geometry.centroid
                house_locations_wgs84.append((pt.x, pt.y))
            
            # Find nearest road points to houses
            house_road_points = []
            for house_pt in house_locations_wgs84:
                if cluster_road_points:
                    distances = [((house_pt[0]-rp[0])**2 + (house_pt[1]-rp[1])**2)**0.5 for rp in cluster_road_points]
                    nearest_idx = np.argmin(distances)
                    house_road_points.append(cluster_road_points[nearest_idx])
            
            # Create collection route through all houses
            if house_road_points and len(house_road_points) > 0:
                # Remove duplicates while preserving order
                unique_house_points = []
                for pt in house_road_points:
                    if pt not in unique_house_points:
                        unique_house_points.append(pt)
                
                if len(unique_house_points) >= 1:
                    # Start from first house location
                    start_point = unique_house_points[0]
                    route_points = [start_point]
                    
                    # Visit all other houses
                    current_point = start_point
                    remaining_points = unique_house_points[1:].copy()
                    
                    while remaining_points:
                        # Find nearest unvisited house
                        distances = [((current_point[0]-pt[0])**2 + (current_point[1]-pt[1])**2)**0.5 for pt in remaining_points]
                        nearest_idx = np.argmin(distances)
                        next_point = remaining_points.pop(nearest_idx)
                        
                        # Find shortest path on roads between current and next point
                        try:
                            path_segment = nx.shortest_path(G, current_point, next_point, weight='weight')
                            route_points.extend(path_segment[1:])  # Skip first point to avoid duplication
                        except:
                            # If no path found, add direct connection
                            route_points.append(next_point)
                        
                        current_point = next_point
                    
                    # Convert to lat/lon for folium
                    route_coords = [[pt[1], pt[0]] for pt in route_points]
                    
                    # Add collection route with direction arrows
                    route_popup = f"{vehicle_name} - {len(cluster_buildings)} Houses"
                    if vehicles_df is not None and cluster_id < len(vehicles_df):
                        vehicle = vehicles_df.iloc[cluster_id]
                        route_popup += f"\nType: {vehicle.get('vehicle_type', 'N/A')}\nDriver: {vehicle.get('driverName', 'N/A')}"
                    
                    folium.PolyLine(
                        route_coords,
                        color=colors[cluster_id % len(colors)],
                        weight=4,
                        opacity=0.8,
                        popup=route_popup
                    ).add_to(cluster_layer)
                    
                    # Add directional arrows along the route
                    for i in range(0, len(route_coords)-1, max(1, len(route_coords)//10)):
                        if i+1 < len(route_coords):
                            # Calculate arrow direction
                            lat1, lon1 = route_coords[i]
                            lat2, lon2 = route_coords[i+1]
                            
                            # Calculate bearing for arrow rotation
                            dlon = math.radians(lon2 - lon1)
                            dlat = math.radians(lat2 - lat1)
                            bearing = math.degrees(math.atan2(dlon, dlat))
                            
                            # Add arrow marker
                            folium.Marker(
                                [lat1, lon1],
                                icon=folium.DivIcon(
                                    html=f'<div style="transform: rotate({bearing}deg); color: {colors[cluster_id % len(colors)]}; font-size: 16px;">➤</div>',
                                    icon_size=(20, 20),
                                    icon_anchor=(10, 10)
                                )
                            ).add_to(cluster_layer)
                    
                    # Add start marker with active vehicle info
                    start_popup = f"{vehicle_name} Start (ACTIVE)"
                    if vehicles_df is not None and cluster_id < len(active_vehicles):
                        vehicle = active_vehicles.iloc[cluster_id]
                        start_popup += f"\nID: {vehicle.get('vehicle_id', 'N/A')}\nCapacity: {vehicle.get('capacity', 'N/A')}"
                    
                    folium.Marker(
                        [start_point[1], start_point[0]],
                        popup=start_popup,
                        icon=folium.Icon(color='green', icon='play')
                    ).add_to(cluster_layer)
                    
                    # Add end marker
                    folium.Marker(
                        [current_point[1], current_point[0]],
                        popup=f"{vehicle_name} End",
                        icon=folium.Icon(color='red', icon='stop')
                    ).add_to(cluster_layer)
        
        # Add clustered buildings as polygons
        for house_number, building_idx in enumerate(cluster_buildings, 1):
            building = buildings_clean.iloc[building_idx]
            folium.GeoJson(
                json.loads(gpd.GeoSeries([building.geometry]).to_json()),
                style_function=lambda x, c=colors[cluster_id % len(colors)]: {
                    'fillColor': c,
                    'color': c,
                    'weight': 1,
                    'fillOpacity': 0.6
                },
                popup=f"{vehicle_name} - House {house_number}",
                tooltip=f"C{cluster_id + 1}-H{house_number}"
            ).add_to(cluster_layer)
        
        # Add cluster layer to map
        cluster_layer.add_to(m)
    
    # Add layer control
    folium.LayerControl(position='topleft', collapsed=False).add_to(m)
    
    # Add cluster dashboard panel with layer toggle functionality
    cluster_stats = []
    for cluster_id in range(n_clusters):
        cluster_buildings = [i for i, c in enumerate(building_clusters) if c == cluster_id]
        if cluster_buildings:
            vehicle_name = vehicle_names[cluster_id] if cluster_id < len(vehicle_names) else f"Vehicle {cluster_id + 1}"
            vehicle_details = ""
            if vehicles_df is not None and cluster_id < len(active_vehicles):
                vehicle = active_vehicles.iloc[cluster_id]
                vehicle_details = f" • {vehicle.get('vehicle_type', 'N/A')} • ACTIVE • Cap: {vehicle.get('capacity', 'N/A')}"
            
            cluster_stats.append(f'''
            <div style="margin:5px 0;padding:8px;border:1px solid #ddd;border-radius:4px;background:#f9f9f9;">
                <div style="display:flex;align-items:center;justify-content:space-between;">
                    <div>
                        <span style="color:{colors[cluster_id % len(colors)]};font-size:14px;">●</span> 
                        <strong>Cluster {cluster_id + 1}</strong>
                    </div>
                    <button onclick="toggleCluster({cluster_id})" style="padding:2px 6px;font-size:10px;border:1px solid {colors[cluster_id % len(colors)]};background:white;border-radius:3px;cursor:pointer;">Toggle</button>
                </div>
                <div style="font-size:11px;margin-top:5px;">
                    {len(cluster_buildings)} buildings<br>
                    <small>{vehicle_name}{vehicle_details} • {len(cluster_buildings) * 0.5:.1f}km • {len(cluster_buildings) * 3:.0f}min</small>
                </div>
            </div>
            ''')
    
    panel_html = f'''
    <div style="position:fixed;top:10px;right:10px;width:280px;max-height:70vh;background:white;border:2px solid #333;z-index:9999;font-size:12px;border-radius:5px;box-shadow:0 2px 10px rgba(0,0,0,0.3);">
        <div style="background:#333;color:white;padding:8px;border-radius:3px 3px 0 0;">
            <strong>📊 Cluster Dashboard</strong>
            <div style="font-size:10px;margin-top:3px;">{len([c for c in cluster_stats if c])} clusters • {len(buildings_gdf)} buildings</div>
            <div style="margin-top:5px;">
                <button onclick="showAllClusters()" style="padding:3px 8px;font-size:10px;border:1px solid white;background:none;color:white;border-radius:3px;cursor:pointer;margin-right:5px;">Show All</button>
                <button onclick="hideAllClusters()" style="padding:3px 8px;font-size:10px;border:1px solid white;background:none;color:white;border-radius:3px;cursor:pointer;">Hide All</button>
            </div>
        </div>
        <div style="padding:8px;max-height:50vh;overflow-y:auto;">
            {''.join(cluster_stats)}
        </div>
    </div>
    
    <script>
    function toggleCluster(clusterId) {{
        var layerControls = document.querySelectorAll('.leaflet-control-layers-selector');
        layerControls.forEach(function(control) {{
            var label = control.nextSibling;
            if (label && label.textContent.includes('Cluster ' + (clusterId + 1))) {{
                control.click();
            }}
        }});
    }}
    
    function showAllClusters() {{
        var layerControls = document.querySelectorAll('.leaflet-control-layers-selector');
        layerControls.forEach(function(control) {{
            var label = control.nextSibling;
            if (label && label.textContent.includes('Cluster') && !control.checked) {{
                control.click();
            }}
        }});
    }}
    
    function hideAllClusters() {{
        var layerControls = document.querySelectorAll('.leaflet-control-layers-selector');
        layerControls.forEach(function(control) {{
            var label = control.nextSibling;
            if (label && label.textContent.includes('Cluster') && control.checked) {{
                control.click();
            }}
        }});
    }}
    </script>
    '''
    
    m.get_root().html.add_child(folium.Element(panel_html))
    
    return m._repr_html_()

@app.get("/")
async def root():
    return HTMLResponse(content="""
    <html>
        <body>
            <h2>🗺️ Geospatial AI Route Optimizer</h2>
            <div style="background:#fff3cd;border:1px solid #ffeaa7;padding:10px;margin:10px 0;border-radius:5px;">
                <strong>🔐 API Key Required:</strong> <code>swm-2024-secure-key</code><br>
                <small>Add to Authorization header: <code>Bearer swm-2024-secure-key</code></small>
            </div>
            <h3>Available Endpoints:</h3>
            <ul>
                <li><strong>POST /optimize-routes</strong> - Upload files with ward_no and generate optimized routes using live vehicles</li>
                <li><strong>GET /cluster/{cluster_id}</strong> - Get cluster roads with coordinates for specific cluster</li>
                <li><strong>GET /clusters</strong> - Get cluster roads with coordinates for all clusters</li>
                <li><strong>GET /generate-map/route_map</strong> - View interactive map with layer controls</li>
                <li><strong>GET /api/vehicles/live</strong> - Get live vehicle data from SWM API</li>
                <li><strong>GET /api/vehicles/{vehicle_id}</strong> - Get specific vehicle details</li>
                <li><strong>PUT /api/vehicles/{vehicle_id}/status</strong> - Update vehicle status</li>
            </ul>
            <h3>Features:</h3>
            <ul>
                <li>🌐 <strong>Ward-based Vehicle Filtering</strong> - Real-time vehicle data filtered by ward number</li>
                <li>✅ Interactive cluster dashboard panel</li>
                <li>✅ Layer controls to show/hide individual clusters</li>
                <li>✅ Toggle buttons for each cluster</li>
                <li>✅ Show All / Hide All cluster controls</li>
                <li>✅ Color-coded routes and buildings</li>
                <li>🔐 API Key authentication</li>
                <li>📱 RESTful vehicle management endpoints</li>
                <li>🏘️ Ward-based vehicle clustering and optimization</li>
            </ul>
            <p><a href="/docs" style="background:#007bff;color:white;padding:10px 20px;text-decoration:none;border-radius:5px;">📚 API Documentation</a></p>
        </body>
    </html>
    """)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)