import os
from fastapi import FastAPI, Request, Response
import redis

app = FastAPI()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

RATE_LIMIT = 5
WINDOW_SIZE = 60


@app.middleware("http")
async def rate_limiter_middleware(request: Request, call_next):
    if request.url.path in ["/docs", "/openapi.json", "/health"]:
        return await call_next(request)

    client_ip = getattr(request.client, "host", "unknown") if request.client else "unknown"
    redis_key = f"ratelimit:{client_ip}"

    try:
        requests_count = redis_client.incr(redis_key)

        if requests_count == 1:
            redis_client.expire(redis_key, WINDOW_SIZE)

        ttl = redis_client.ttl(redis_key)
        ttl = ttl if ttl > 0 else 0
        remaining_requests = max(0, RATE_LIMIT - requests_count)

        if requests_count > RATE_LIMIT:
            return Response(
                content='{"error": "Too many requests. Please try again later."}',
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": str(ttl),
                    "X-RateLimit-Limit": str(RATE_LIMIT),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(ttl),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT)
        response.headers["X-RateLimit-Remaining"] = str(remaining_requests)
        response.headers["X-RateLimit-Reset"] = str(ttl)
        return response

    except redis.RedisError as e:
        print(f"Redis error encountered: {e}")
        return await call_next(request)


@app.get("/")
def read_root():
    return {"message": "Welcome! You are accessing the rate-limited API."}


@app.get("/health")
def health_check():
    return {"status": "ok"}