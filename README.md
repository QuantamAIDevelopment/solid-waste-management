# Solid Waste Management (SWM) - Geospatial AI Route Optimizer

A production-ready Python system for optimizing garbage collection routes using geospatial AI, clustering algorithms, and Vehicle Routing Problem (VRP) solving with real-time SWM API integration.

## Features

- **🔐 Automatic Authentication**: JWT token management with SWM API integration
- **🗺️ Multi-format Input Processing**: Supports GeoJSON (roads, buildings, wards) and CSV (vehicles)
- **🤖 AI-Powered Route Optimization**: KMeans/DBSCAN clustering with OR-Tools VRP solver
- **🚛 Live Vehicle Integration**: Real-time vehicle data from SWM API with fallback to CSV
- **📊 Trip Assignment Logic**: Intelligent capacity-based trip planning (max 2 trips/day)
- **🌐 OSRM Integration**: Real-world turn-by-turn driving directions
- **📍 Road Network Snapping**: Buildings automatically snapped to nearest road segments
- **🎨 Interactive Visualization**: Folium maps with cluster analysis and route visualization
- **🔄 RESTful API**: FastAPI with OpenAPI/Swagger documentation

## Architecture

```
├── src/
│   ├── agents/                    # Agent-based route assignment
│   ├── api/                       # FastAPI REST endpoints
│   │   ├── auth_api.py            # Authentication endpoints
│   │   ├── geospatial_routes.py   # Main route optimization API
│   │   └── vehicles_api.py        # Vehicle management endpoints
│   ├── clustering/                # Building clustering algorithms
│   │   ├── assign_buildings.py    # KMeans/DBSCAN clustering
│   │   └── trip_assignment.py     # Trip capacity management
│   ├── configurations/            # System configuration
│   │   └── config.py              # Environment and app settings
│   ├── core/                      # Core coordination system
│   │   └── blackboard.py          # Shared state management
│   ├── data_processing/           # Geospatial data processing
│   │   ├── load_road_network.py   # Road network loading and graph building
│   │   └── snap_buildings.py      # Building-to-road snapping
│   ├── models/                    # Data models and schemas
│   │   └── blackboard_entry.py    # Pydantic models
│   ├── routing/                   # Route optimization
│   │   ├── capacity_optimizer.py  # Capacity-based route optimization
│   │   ├── compute_routes.py      # OR-Tools VRP solver
│   │   ├── get_osrm_directions.py # OSRM turn-by-turn directions
│   │   └── hierarchical_clustering.py # Spatial clustering
│   ├── services/                  # External service integration
│   │   ├── auth_service.py        # JWT token management
│   │   └── vehicle_service.py     # Live vehicle API integration
│   ├── storage/                   # Data persistence
│   │   └── postgis_store.py       # PostGIS database operations
│   ├── tools/                     # Utility tools
│   │   ├── directions_generator.py # Route directions generation
│   │   ├── improved_clustering.py # Advanced clustering algorithms
│   │   ├── osrm_routing.py        # OSRM routing utilities
│   │   ├── road_snapper.py        # Road network snapping
│   │   └── vrp_solver.py          # Vehicle Routing Problem solver
│   └── visualization/             # Map generation and export
│       ├── export_to_geojson.py   # GeoJSON export utilities
│       └── folium_map.py          # Interactive map generation
├── tests/                         # Test suite
├── output/                        # Generated results (auto-created)
├── main.py                        # CLI and API entry point
├── requirements.txt               # Python dependencies
├── .env                          # Environment variables
└── README.md                     # User documentation
```

## Quick Start

### Prerequisites

- Python 3.11+
- Git
- Internet connection (for OSRM routing and SWM API)
- Optional: PostgreSQL with PostGIS extension

### Installation

1. **Clone and setup:**
```bash
git clone <repository-url>
cd swm
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

2. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your SWM API credentials
```

3. **Run the system:**

**API Mode (Recommended):**
```bash
python main.py --api --port 8081
```

**CLI Mode:**
```bash
python main.py --roads roads.geojson --buildings buildings.geojson --output results/
```

The API will be available at `http://localhost:8081` with Swagger UI at `http://localhost:8081/docs`.

## API Usage

### 1. Upload Files and Optimize Routes
```bash
curl -X POST "http://localhost:8081/optimize-routes" \
  -F "roads_file=@roads.geojson" \
  -F "buildings_file=@buildings.geojson" \
  -F "ward_geojson=@ward.geojson" \
  -F "ward_no=1" \
  -F "vehicles_csv=@vehicles.csv"
```

### 2. Get Cluster Roads with Coordinates
```bash
curl "http://localhost:8081/cluster/0"
```

**Response:**
```json
{
  "cluster_id": 0,
  "vehicle_info": {
    "vehicle_id": "V001",
    "vehicle_type": "truck",
    "status": "active",
    "capacity": 1000
  },
  "buildings_count": 15,
  "roads": [
    {
      "start_coordinate": {"longitude": 77.123, "latitude": 12.456},
      "end_coordinate": {"longitude": 77.124, "latitude": 12.457},
      "distance_meters": 125.5
    }
  ],
  "total_road_segments": 8,
  "cluster_bounds": {
    "min_longitude": 77.120,
    "max_longitude": 77.130,
    "min_latitude": 12.450,
    "max_latitude": 12.460
  }
}
```

### 3. Authentication Management
```bash
# Get token info
curl "http://localhost:8081/api/auth/token/info"

# Force token refresh
curl -X POST "http://localhost:8081/api/auth/token/refresh"

# Get auth status
curl "http://localhost:8081/api/auth/status"
```

### 4. Get Live Vehicle Data
```bash
curl "http://localhost:8081/api/vehicles/live"
```

### 5. View Interactive Maps
- Route Map: `http://localhost:8081/generate-map`

### 6. API Documentation
Swagger UI: `http://localhost:8081/docs`

## Input File Formats

### Ward Boundaries (GeoJSON)
```json
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "properties": {"ward_id": 1, "ward_name": "Ward 1"},
    "geometry": {"type": "Polygon", "coordinates": [...]}
  }]
}
```

### Road Network (GeoJSON)
```json
{
  "type": "FeatureCollection", 
  "features": [{
    "type": "Feature",
    "properties": {"road_id": "R001", "road_name": "Main St"},
    "geometry": {"type": "LineString", "coordinates": [...]}
  }]
}
```

### Houses (GeoJSON)
```json
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature", 
    "properties": {"house_id": "H001", "ward_no": 1},
    "geometry": {"type": "Point", "coordinates": [...]}
  }]
}
```

### Vehicles (CSV) - Optional Fallback
```csv
vehicle_id,vehicle_type,ward_no,driver_info,status,start_location
V001,truck,1,John Doe,active,"12.34,56.78"
V002,truck,1,Jane Smith,unavailable,
```

**Note:** The system primarily uses live vehicle data from the SWM API. CSV is used as fallback when API is unavailable or for testing.

## Algorithm Details

### 1. Preprocessing
- Reprojects all spatial data to EPSG:3857 (Web Mercator)
- Snaps houses to nearest road segments
- Builds routable graph from road network

### 2. Clustering
- Uses KMeans with k = number of active vehicles
- Assigns clusters to vehicles based on proximity
- Ensures road segments belong to single clusters

### 3. Route Optimization
- Builds VRP distance matrix using road network shortest paths
- Solves using OR-Tools with distance minimization objective
- Generates ordered route polylines following road geometry

### 4. Conflict Resolution
- Detects overlapping road segments between routes
- Reassigns disputed segments to minimize cost increase
- Rebuilds affected routes

## Testing

Run unit tests:
```bash
pytest tests/ -v
```

Run integration test:
```bash
pytest tests/test_snapper_vrp.py::TestIntegration::test_end_to_end_small_dataset -v
```

## Configuration

### Environment Variables (.env)

```bash
# SWM API Configuration
SWM_API_BASE_URL=https://uat-swm-main-service-hdaqcdcscbfedhhn.centralindia-01.azurewebsites.net
SWM_USERNAME=your_username
SWM_PASSWORD=your_password
SWM_TOKEN=auto_generated_by_auth_service

# Application Configuration
DEBUG=true
PORT=8081
API_KEY=swm-2024-secure-key

# OSRM Configuration
OSRM_URL=http://router.project-osrm.org

# Optional Database
DATABASE_URL=postgresql://user:pass@localhost:5432/waste_db
```

### System Configuration (src/configurations/config.py)

```python
class Config:
    TARGET_CRS = "EPSG:3857"  # Web Mercator
    RANDOM_SEED = 42
    VRP_TIME_LIMIT_SECONDS = 30
    MAX_HOUSES_PER_TRIP = 100
    MAX_TRIPS_PER_DAY = 2
```

## Key Features

### 🔐 Automatic Authentication
- JWT token auto-generation using SWM API credentials
- Automatic token refresh before expiry
- Background refresh thread for continuous operation
- Token management endpoints for monitoring

### 🚛 Smart Trip Assignment
- Maximum 2 trips per vehicle per day
- Capacity-based building assignment
- Load balancing across available vehicles
- Handles vehicle unavailability gracefully

### 🗺️ Advanced Geospatial Processing
- Building-to-road snapping using NetworkX graphs
- CRS transformation (EPSG:4326 ↔ EPSG:3857)
- Spatial clustering with KMeans/DBSCAN
- Real-world routing with OSRM integration

### 📊 Performance & Scalability
- Optimized for ward sizes up to several thousand buildings
- Clustering reduces VRP problem complexity
- Deterministic results with configurable random seed
- Efficient spatial indexing and graph algorithms

### 📝 Comprehensive Logging
- Authentication status and token management
- Clustering decisions and vehicle assignments
- Route optimization metrics and performance
- API request/response logging with Loguru

## Docker Support

```dockerfile
FROM python:3.11-slim

# Install system dependencies for geospatial libraries
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8081

# Run API server by default
CMD ["python", "main.py", "--api", "--port", "8081"]
```

**Build and run:**
```bash
docker build -t swm-optimizer .
docker run -p 8081:8081 --env-file .env swm-optimizer
```

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_snapper_vrp.py::TestIntegration::test_end_to_end_small_dataset -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Troubleshooting

### Common Issues

1. **Port already in use:**
   ```bash
   python main.py --api --port 8082  # Use different port
   ```

2. **Authentication failures:**
   - Check SWM_USERNAME and SWM_PASSWORD in .env
   - Verify SWM_API_BASE_URL is accessible
   - Use `/api/auth/status` endpoint to debug

3. **OSRM routing errors:**
   - Check internet connection
   - Verify OSRM_URL in .env
   - Use local OSRM server for offline operation

4. **Memory issues with large datasets:**
   - Reduce MAX_HOUSES_PER_TRIP in config
   - Use hierarchical clustering for large wards
   - Process wards in smaller batches

## License

MIT License - see LICENSE file for details.