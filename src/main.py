import time
from fastapi import FastAPI, HTTPException, Request, Response
import redis

app = FastAPI()

# Connect to Redis (adjust host/port as needed)
redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

# Rate limit configuration
RATE_LIMIT = 5  # Max requests allowed
WINDOW_SIZE = 60  # Time window in seconds (e.g., 1 minute)

@app.middleware("http")
async def rate_limiter_middleware(request: Request, call_next):
    # Skip rate limiting for documentation or health check routes if needed
    if request.url.path in ["/docs", "/openapi.json"]:
        return await call_next(request)

    # Identify the client by their IP address (or API key if authenticated)
    client_ip = request.client.host
    redis_key = f"ratelimit:{client_ip}"

    try:
        # Increment request count atomically
        requests_count = redis_client.incr(redis_key)

        # If this is the first request in the current window, set expiration
        if requests_count == 1:
            redis_client.expire(redis_key, WINDOW_SIZE)

        # Get the time-to-live (TTL) remaining for this window
        ttl = redis_client.ttl(redis_key)
        ttl = ttl if ttl > 0 else 0

        # Calculate remaining requests
        remaining_requests = max(0, RATE_LIMIT - requests_count)

        # Check if the rate limit has been exceeded
        if requests_count > RATE_LIMIT:
            # Return HTTP 429 Too Many Requests with a Retry-After header
            return Response(
                content='{"error": "Too many requests. Please try again later."}',
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": str(ttl),
                    "X-RateLimit-Limit": str(RATE_LIMIT),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(ttl)
                }
            )

        # Process the request and get the response
        response = await call_next(request)

        # Attach standard rate-limiting headers to successful responses
        response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT)
        response.headers["X-RateLimit-Remaining"] = str(remaining_requests)
        response.headers["X-RateLimit-Reset"] = str(ttl)

        return response

    except redis.RedisError as e:
        # Fail-open strategy: If Redis goes down, allow the request through 
        # to prevent complete service outage, but log the error.
        print(f"Redis error encountered: {e}")
        return await call_next(request)


@app.get("/")
def read_root():
    return {"message": "Welcome! You are accessing the rate-limited API."}