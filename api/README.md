# Prospect Tool API

FastAPI backend for the Prospect Tool application.

## Architecture

```
api/
├── api/              # API routes
│   └── v1/          # API version 1
│       ├── routes/  # Route handlers
│       └── router.py
├── core/            # Core configuration
├── models/          # Pydantic models
├── services/        # Business logic
├── scrappers/       # Web scrapers
└── main.py         # Application entry point
```

## Setup

### 1. Install dependencies

```bash
cd api
pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env.example` to `.env` and update if needed:

```bash
cp .env.example .env
```

### 3. Run migrations

```bash
python migrations/run_migrations.py
```

### 4. Seed initial data (optional)

```bash
python seeders/run_seeders.py
```

### 5. Run the server

**Development mode (with auto-reload):**

```bash
python run_dev.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Production mode:**

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Endpoints

### Health Check
- `GET /health` - Check API health status

### Prospects
- `GET /api/v1/prospects` - List all prospects
- `GET /api/v1/prospects/{id}` - Get prospect by ID
- `POST /api/v1/prospects/search` - Search for prospects
- `POST /api/v1/prospects` - Create new prospect
- `PUT /api/v1/prospects/{id}` - Update prospect
- `DELETE /api/v1/prospects/{id}` - Delete prospect

## Development

### Code Style

- Follow PEP 8 guidelines
- Use type hints for all functions
- Document all classes and methods with docstrings
- Keep functions small and focused

### Adding New Scrapers

1. Create a new scraper class in `scrappers/`
2. Inherit from `BaseScraper`
3. Implement the `scrape()` method
4. Register it in `main.py` startup event

### Running Tests

```bash
pytest
```

## License

MIT

