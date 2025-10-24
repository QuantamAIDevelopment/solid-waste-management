# Developer Guide

## Project Structure

```
swm/
├── src/                           # Source code modules
│   ├── agents/                    # Agent-based route assignment
│   ├── api/                       # FastAPI REST endpoints
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

## Development Setup

### Prerequisites
- Python 3.11+
- PostgreSQL with PostGIS (optional)
- Git

### Environment Setup
```bash
# Clone repository
git clone <repository-url>
cd swm

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your configuration
```

### Environment Variables
```bash
# SWM API Configuration
SWM_API_BASE_URL=https://uat-swm-main-service-hdaqcdcscbfedhhn.centralindia-01.azurewebsites.net
SWM_USERNAME=superadmin
SWM_PASSWORD=admin123
SWM_TOKEN=<your-jwt-token>

# Application Configuration
DEBUG=true
PORT=8081
API_KEY=swm-2024-secure-key
```

## API Development

### Running the API Server
```bash
# Development mode
python main.py --api --port 8081

# Access Swagger UI
http://localhost:8081/docs
```

### Adding New Endpoints
1. Create endpoint in `src/api/geospatial_routes.py` or `src/api/vehicles_api.py`
2. Add Pydantic models in `src/models/`
3. Update OpenAPI tags and documentation

### Authentication
All API endpoints use Bearer token authentication:
```python
from fastapi.security import HTTPBearer
security = HTTPBearer()

@app.get("/protected-endpoint")
async def protected(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # Verify credentials.credentials against API_KEY
```

## Core Components

### 1. Route Optimization Pipeline
```python
# Main pipeline in GeospatialRouteOptimizer class
def process_ward_data(self, roads_geojson, buildings_geojson, vehicles_csv=None):
    # 1. Load and build road network graph
    # 2. Load and snap buildings to road network  
    # 3. Load vehicles and cluster buildings
    # 4. Compute optimal routes with trip assignments
    # 5. Get OSRM directions
    # 6. Export results and generate maps
```

### 2. Clustering Algorithm
```python
# Building clustering with vehicle capacity
from src.clustering.assign_buildings import BuildingClusterer

clusterer = BuildingClusterer()
vehicles_df = clusterer.load_vehicles()  # Live API or CSV
clustered_buildings = clusterer.cluster_buildings(buildings, num_vehicles)
```

### 3. Route Computation
```python
# OR-Tools VRP solver
from src.routing.compute_routes import RouteComputer

route_computer = RouteComputer(road_graph)
routes = route_computer.compute_cluster_routes(clustered_buildings)
```

### 4. Map Generation
```python
# Interactive Folium maps
from src.visualization.folium_map import FoliumMapGenerator

map_generator = FoliumMapGenerator()
route_map = map_generator.create_route_map(routes_gdf, clustered_buildings)
```

## Testing

### Running Tests
```bash
# All tests
pytest tests/ -v

# Specific test
pytest tests/test_snapper_vrp.py::TestIntegration::test_end_to_end_small_dataset -v

# With coverage
pytest tests/ --cov=src --cov-report=html
```

### Test Structure
- `tests/test_*.py` - Unit tests for individual modules
- `tests/test_*_integration.py` - Integration tests
- Mock external APIs and services in tests

### Adding Tests
```python
import pytest
from src.module import YourClass

class TestYourClass:
    def test_method(self):
        instance = YourClass()
        result = instance.method()
        assert result == expected_value
```

## Data Flow

### 1. Input Processing
```
GeoJSON Files → GeoPandas → CRS Conversion → NetworkX Graph
CSV Files → Pandas → Data Validation → Active Vehicle Filtering
```

### 2. Optimization Flow
```
Buildings → Snap to Roads → Cluster by Vehicle → VRP Solver → Routes
Vehicles → Filter Active → Assign to Clusters → Capacity Check → Trips
```

### 3. Output Generation
```
Routes → GeoJSON Export → Interactive Maps → Browser Display
Results → CSV Summary → API Response → Client Integration
```

## Configuration

### System Configuration
Edit `src/configurations/config.py`:
```python
class Config:
    DATABASE_URL = "postgresql://user:pass@localhost:5432/waste_db"
    TARGET_CRS = "EPSG:3857"  # Web Mercator
    RANDOM_SEED = 42
    VRP_TIME_LIMIT_SECONDS = 30
    MAX_HOUSES_PER_TRIP = 100
```

### API Configuration
```python
# FastAPI app configuration
app = FastAPI(
    title="Geospatial AI Route Optimizer",
    description="Dynamic garbage collection route optimization",
    version="2.0.0"
)
```

## Performance Optimization

### 1. Spatial Operations
- Use appropriate CRS for distance calculations (EPSG:3857)
- Spatial indexing for nearest neighbor queries
- Batch operations for large datasets

### 2. Clustering Optimization
- Limit cluster size for VRP solver performance
- Use hierarchical clustering for large datasets
- Cache distance matrices when possible

### 3. Memory Management
- Stream large GeoJSON files
- Clean up temporary files after processing
- Use generators for large data processing

## Debugging

### Logging Configuration
```python
from loguru import logger

# Enable debug logging
logger.add("debug.log", level="DEBUG")
logger.debug("Debug message")
logger.info("Info message")
logger.error("Error message")
```

### Common Issues
1. **Import Errors**: Ensure all imports use `src.` prefix
2. **CRS Mismatches**: Always convert to EPSG:4326 for display, EPSG:3857 for calculations
3. **Memory Issues**: Process large datasets in chunks
4. **API Timeouts**: Increase timeout for large optimization problems

## Deployment

### Production Setup
```bash
# Install production dependencies
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8081
```

### Docker Deployment
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8081
CMD ["python", "main.py", "--api", "--port", "8081"]
```

### Environment Variables for Production
```bash
DEBUG=false
API_KEY=<secure-production-key>
DATABASE_URL=<production-database-url>
```

## Contributing

### Code Style
- Follow PEP 8 style guidelines
- Use type hints for function parameters and returns
- Add docstrings for all public methods
- Keep functions focused and single-purpose

### Git Workflow
```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes and commit
git add .
git commit -m "Add new feature"

# Push and create PR
git push origin feature/new-feature
```

### Code Review Checklist
- [ ] All tests pass
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] No hardcoded values
- [ ] Error handling implemented
- [ ] Performance considerations addressed