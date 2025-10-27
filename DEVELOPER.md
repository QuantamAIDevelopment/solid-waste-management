# Developer Guide

## Project Structure

```
swm/
├── src/                           # Source code modules
│   ├── agents/                    # Agen# SWM Geospatial AI Route Optimizer - Developer Guide

Comprehensive development guide for the Solid Waste Management (SWM) geospatial AI route optimization system.

## Project Structure

```
swm/
├── src/                           # Source code
│   ├── agents/                    # Agent-based route assignment
│   │   └── __init__.py
│   ├── api/                       # FastAPI REST endpoints
│   │   ├── __init__.py
│   │   ├── auth_api.py            # JWT authentication endpoints
│   │   ├── geospatial_routes.py   # Main route optimization API
│   │   └── vehicles_api.py        # Vehicle management endpoints
│   ├── clustering/                # Building clustering algorithms
│   │   ├── __init__.py
│   │   ├── assign_buildings.py    # KMeans/DBSCAN clustering
│   │   └── trip_assignment.py     # Trip capacity management
│   ├── configurations/            # System configuration
│   │   ├── __init__.py
│   │   └── config.py              # Environment and app settings
│   ├── core/                      # Core coordination system
│   │   ├── __init__.py
│   │   └── blackboard.py          # Shared state management
│   ├── data_processing/           # Geospatial data processing
│   │   ├── __init__.py
│   │   ├── load_road_network.py   # Road network loading and graph building
│   │   └── snap_buildings.py      # Building-to-road snapping
│   ├── models/                    # Data models and schemas
│   │   ├── __init__.py
│   │   └── blackboard_entry.py    # Pydantic models
│   ├── routing/                   # Route optimization
│   │   ├── __init__.py
│   │   ├── capacity_optimizer.py  # Capacity-based route optimization
│   │   ├── compute_routes.py      # OR-Tools VRP solver
│   │   ├── get_osrm_directions.py # OSRM turn-by-turn directions
│   │   └── hierarchical_clustering.py # Spatial clustering
│   ├── services/                  # External service integration
│   │   ├── __init__.py
│   │   ├── auth_service.py        # JWT token management
│   │   └── vehicle_service.py     # Live vehicle API integration
│   ├── storage/                   # Data persistence
│   │   ├── __init__.py
│   │   └── postgis_store.py       # PostGIS database operations
│   ├── tools/                     # Utility tools
│   │   ├── __init__.py
│   │   ├── directions_generator.py # Route directions generation
│   │   ├── improved_clustering.py # Advanced clustering algorithms
│   │   ├── osrm_routing.py        # OSRM routing utilities
│   │   ├── road_snapper.py        # Road network snapping
│   │   └── vrp_solver.py          # Vehicle Routing Problem solver
│   └── visualization/             # Map generation and export
│       ├── __init__.py
│       ├── export_to_geojson.py   # GeoJSON export utilities
│       └── folium_map.py          # Interactive map generation
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── test_cluster_endpoint.py   # API endpoint tests
│   ├── test_geographic_constraints.py # Geographic constraint tests
│   ├── test_improved_clustering.py # Clustering algorithm tests
│   ├── test_snapper_vrp.py        # Integration tests
│   └── test_trip_assignment.py    # Trip assignment tests
├── output/                        # Generated results (auto-created)
├── main.py                        # CLI and API entry point
├── requirements.txt               # Python dependencies
├── .env                          # Environment variables (not in git)
├── .env.example                  # Environment template
├── .gitignore                    # Git ignore patterns
├── Dockerfile                    # Docker container definition
├── DEVELOPER.md                  # This file
├── README.md                     # User documentation
└── test_auth.py                  # Authentication testing script
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
# SWM API Configuration (Required)
SWM_API_BASE_URL=https://uat-swm-main-service-hdaqcdcscbfedhhn.centralindia-01.azurewebsites.net
SWM_USERNAME=your_username
SWM_PASSWORD=your_password
SWM_TOKEN=auto_generated_by_auth_service

# Application Configuration
DEBUG=true
PORT=8081
API_KEY=swm-2024-secure-key

# External Services
OSRM_URL=http://router.project-osrm.org

# Route Optimization
MAX_HOUSES_PER_TRIP=100
MAX_TRIPS_PER_DAY=2
DEFAULT_CLUSTER_METHOD=kmeans
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

### Authentication System

The system uses a sophisticated JWT authentication system:

#### 1. Automatic Token Management
```python
from src.services.auth_service import get_auth_service

# Get auth service instance
auth_service = get_auth_service()

# Get valid token (auto-refreshes if needed)
token = auth_service.get_valid_token()

# Check token status
is_valid = auth_service.is_token_valid()

# Force refresh
auth_service.force_refresh()
```

#### 2. Authentication Endpoints
```python
# Token information
GET /api/auth/token/info

# Force token refresh
POST /api/auth/token/refresh

# Authentication status
GET /api/auth/status
```

#### 3. API Endpoint Protection
```python
from fastapi.security import HTTPBearer
security = HTTPBearer()

@app.get("/protected-endpoint")
async def protected(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # Verify credentials.credentials against API_KEY or SWM token
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

### 2. Authentication Service Integration
```python
# JWT token management with SWM API
from src.services.auth_service import AuthService

auth_service = AuthService()
token = auth_service.get_valid_token()  # Auto-generates and refreshes
```

### 3. Clustering Algorithm
```python
# Building clustering with vehicle capacity and trip assignment
from src.clustering.assign_buildings import BuildingClusterer

clusterer = BuildingClusterer()
vehicles_df = clusterer.load_vehicles()  # Live SWM API or CSV fallback
clustered_buildings = clusterer.cluster_buildings(buildings, num_vehicles)

# Trip assignment with capacity constraints
trip_assignments = clusterer.assign_trips_to_vehicles(clustered_buildings, vehicles_df)
```

### 4. Route Computation
```python
# OR-Tools VRP solver with capacity constraints
from src.routing.compute_routes import RouteComputer

route_computer = RouteComputer(road_graph)
routes = route_computer.compute_cluster_routes(clustered_buildings)

# OSRM integration for real-world directions
from src.routing.get_osrm_directions import OSRMDirectionsProvider

osrm = OSRMDirectionsProvider()
directions = osrm.get_route_directions(coordinates)
```

### 5. Map Generation
```python
# Interactive Folium maps with cluster analysis
from src.visualization.folium_map import FoliumMapGenerator

map_generator = FoliumMapGenerator()
route_map = map_generator.create_route_map(routes_gdf, clustered_buildings)
cluster_map = map_generator.create_cluster_analysis_map(clustered_buildings)

# Export to GeoJSON
from src.visualization.export_to_geojson import RouteExporter

exporter = RouteExporter()
exporter.export_routes_geojson("routes.geojson")
exporter.export_summary_csv("summary.csv")
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

### 1. Authentication Flow
```
SWM Credentials → JWT Token Generation → Auto-Refresh → API Access
Token Validation → Background Refresh → Persistent Storage → .env Update
```

### 2. Input Processing
```
GeoJSON Files → GeoPandas → CRS Conversion (EPSG:4326→3857) → NetworkX Graph
SWM API → Live Vehicles → Data Validation → Active Vehicle Filtering
CSV Fallback → Pandas → Backup Vehicle Data → Testing Support
```

### 3. Optimization Flow
```
Buildings → Road Snapping → Spatial Clustering → Vehicle Assignment → Trip Planning
Vehicles → Capacity Check → Cluster Assignment → Route Optimization → OSRM Directions
```

### 4. Output Generation
```
Routes → GeoJSON Export → Interactive Maps → Browser Display
Trip Data → CSV Summary → API Response → Client Integration
Cluster Analysis → Folium Maps → Performance Metrics → Logging
```

## Configuration

### System Configuration
Edit `src/configurations/config.py`:
```python
class Config:
    # Coordinate Reference Systems
    TARGET_CRS = "EPSG:3857"  # Web Mercator for calculations
    DISPLAY_CRS = "EPSG:4326"  # WGS84 for display
    
    # Optimization Parameters
    RANDOM_SEED = 42
    VRP_TIME_LIMIT_SECONDS = 30
    MAX_HOUSES_PER_TRIP = 100
    MAX_TRIPS_PER_DAY = 2
    
    # Authentication
    TOKEN_REFRESH_INTERVAL = 300  # 5 minutes
    TOKEN_EXPIRY_BUFFER = 600     # 10 minutes before expiry
    
    # API Configuration
    API_TIMEOUT = 30
    MAX_RETRIES = 3
    
    # Optional Database
    DATABASE_URL = "postgresql://user:pass@localhost:5432/swm_db"
```

### API Configuration
```python
# FastAPI app configuration with authentication
from fastapi import FastAPI
from src.api.auth_api import router as auth_router
from src.api.geospatial_routes import router as routes_router
from src.api.vehicles_api import router as vehicles_router

app = FastAPI(
    title="SWM Geospatial AI Route Optimizer",
    description="Solid Waste Management route optimization with real-time API integration",
    version="2.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Include routers
app.include_router(auth_router)
app.include_router(routes_router)
app.include_router(vehicles_router)
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

1. **Authentication Failures**:
   ```bash
   # Check credentials in .env
   SWM_USERNAME=correct_username
   SWM_PASSWORD=correct_password
   
   # Test authentication
   python test_auth.py
   
   # Check auth status via API
   curl http://localhost:8081/api/auth/status
   ```

2. **Import Errors**: 
   - Ensure all imports use `src.` prefix
   - Check virtual environment activation
   - Verify all dependencies installed

3. **CRS Mismatches**: 
   - Input: EPSG:4326 (WGS84)
   - Calculations: EPSG:3857 (Web Mercator)
   - Output: EPSG:4326 (for display)

4. **Memory Issues**: 
   - Reduce MAX_HOUSES_PER_TRIP
   - Use hierarchical clustering for large datasets
   - Process wards in smaller batches

5. **API Timeouts**: 
   - Increase ROUTE_OPTIMIZATION_TIMEOUT
   - Check OSRM_URL accessibility
   - Verify SWM API connectivity

6. **Token Refresh Issues**:
   ```python
   # Force token refresh
   from src.services.auth_service import get_auth_service
   auth_service = get_auth_service()
   auth_service.force_refresh()
   ```

## Deployment

### Production Setup

#### 1. Environment Configuration
```bash
# Production .env settings
DEBUG=false
LOG_LEVEL=INFO
API_KEY=secure-production-key-here
SWM_USERNAME=production_username
SWM_PASSWORD=secure_production_password
```

#### 2. Gunicorn Deployment
```bash
# Install production dependencies
pip install gunicorn

# Run with Gunicorn (recommended)
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app \
  --bind 0.0.0.0:8081 \
  --timeout 300 \
  --keep-alive 2 \
  --max-requests 1000 \
  --max-requests-jitter 100
```

#### 3. Systemd Service
```ini
# /etc/systemd/system/swm-optimizer.service
[Unit]
Description=SWM Geospatial Route Optimizer
After=network.target

[Service]
Type=exec
User=swm
Group=swm
WorkingDirectory=/opt/swm-optimizer
Environment=PATH=/opt/swm-optimizer/venv/bin
EnvironmentFile=/opt/swm-optimizer/.env
ExecStart=/opt/swm-optimizer/venv/bin/gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8081
Restart=always

[Install]
WantedBy=multi-user.target
```

### Docker Deployment

#### Dockerfile
```dockerfile
FROM python:3.11-slim

# Install system dependencies for geospatial libraries
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONPATH=/app
ENV GDAL_CONFIG=/usr/bin/gdal-config

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 swm && chown -R swm:swm /app
USER swm

# Expose port
EXPOSE 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8081/docs || exit 1

# Run application
CMD ["python", "main.py", "--api", "--port", "8081"]
```

#### Docker Compose
```yaml
# docker-compose.yml
version: '3.8'

services:
  swm-optimizer:
    build: .
    ports:
      - "8081:8081"
    env_file:
      - .env
    volumes:
      - ./output:/app/output
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8081/docs"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### Environment Variables for Production
```bash
# Security
DEBUG=false
API_KEY=secure-production-key-change-this

# SWM API (Production)
SWM_API_BASE_URL=https://prod-swm-api.example.com
SWM_USERNAME=production_user
SWM_PASSWORD=secure_production_password

# Performance
MAX_CONCURRENT_REQUESTS=20
ROUTE_OPTIMIZATION_TIMEOUT=600
TOKEN_REFRESH_INTERVAL=300

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/swm-optimizer/app.log

# Optional Database
DATABASE_URL=postgresql://swm_user:secure_password@db:5432/swm_production
```

## Contributing

### Code Style
- Follow PEP 8 style guidelines
- Use type hints for function parameters and returns
- Add docstrings for all public methods
- Keep functions focused and single-purpose

### Git Workflow

#### Branch Naming Convention
```bash
# Feature branches
feature/auth-improvements
feature/osrm-integration
feature/trip-assignment

# Bug fixes
bugfix/token-refresh-issue
bugfix/clustering-memory-leak

# Hotfixes
hotfix/security-patch
hotfix/api-timeout
```

#### Development Workflow
```bash
# Create feature branch
git checkout -b feature/new-feature

# Make changes with proper commits
git add .
git commit -m "feat: add JWT token auto-refresh functionality"

# Run tests before pushing
pytest tests/ -v

# Push and create PR
git push origin feature/new-feature
```

#### Commit Message Convention
```bash
# Format: type(scope): description
feat(auth): add automatic token refresh
fix(clustering): resolve memory leak in large datasets
docs(readme): update installation instructions
test(api): add integration tests for vehicle endpoints
refactor(routing): optimize VRP solver performance
```

### Code Review Checklist

#### Functionality
- [ ] All tests pass (pytest tests/ -v)
- [ ] Authentication integration works
- [ ] SWM API integration tested
- [ ] OSRM routing functional
- [ ] Map generation works
- [ ] Error handling implemented

#### Code Quality
- [ ] Code follows PEP 8 style guidelines
- [ ] Type hints added for new functions
- [ ] Docstrings for all public methods
- [ ] No hardcoded values (use .env or config)
- [ ] Proper logging with appropriate levels
- [ ] No sensitive data in code

#### Security
- [ ] No credentials in code
- [ ] API endpoints properly secured
- [ ] Input validation implemented
- [ ] SQL injection prevention (if using DB)
- [ ] Token handling secure

#### Performance
- [ ] Memory usage optimized
- [ ] Large dataset handling considered
- [ ] Spatial operations efficient
- [ ] API timeouts configured
- [ ] Caching implemented where appropriate

#### Documentation
- [ ] README.md updated
- [ ] DEVELOPER.md updated
- [ ] API documentation current
- [ ] Environment variables documented
- [ ] Deployment instructions updated