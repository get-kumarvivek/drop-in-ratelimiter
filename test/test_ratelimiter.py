from fastapi.testclient import TestClient

from src import main


class FakeRedis:
    def __init__(self):
        self.store = {}

    def incr(self, key):
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    def expire(self, key, ttl):
        self.store[f"{key}:ttl"] = ttl

    def ttl(self, key):
        return 60


def setup_function():
    main.redis_client = FakeRedis()


def test_root_endpoint_returns_welcome_message():
    client = TestClient(main.app)

    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["message"] == "Welcome! You are accessing the rate-limited API."


def test_health_endpoint_returns_ok():
    client = TestClient(main.app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_successful_requests_include_rate_limit_headers():
    client = TestClient(main.app)

    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["X-RateLimit-Limit"] == str(main.RATE_LIMIT)
    assert response.headers["X-RateLimit-Remaining"] == str(main.RATE_LIMIT - 1)
    assert response.headers["X-RateLimit-Reset"]


def test_rate_limit_exceeded_returns_429():
    main.redis_client = FakeRedis()
    main.redis_client.store["ratelimit:testclient"] = main.RATE_LIMIT + 1
    client = TestClient(main.app)

    response = client.get("/")

    assert response.status_code == 429
    assert response.headers["X-RateLimit-Remaining"] == "0"
    assert "Retry-After" in response.headers
