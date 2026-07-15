"""
Rate limiting configuration for API endpoints.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize limiter with default limits
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],  # 200 requests per minute per IP
    storage_uri="memory://"  # Use in-memory storage (for production, use Redis)
)

# Custom rate limits for different endpoint types
RATE_LIMITS = {
    "auth": "10/minute",  # Login/signup attempts
    "search": "20/minute",  # Prospect search operations
    "email": "100/hour",  # Email sending
    "general": "200/minute",  # General API requests
}

