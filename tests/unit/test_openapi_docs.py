"""Unit tests for FastAPI OpenAPI schema, Swagger UI, and ReDoc documentation endpoints."""

from fastapi.testclient import TestClient

from main import VERSION, app


def test_swagger_ui_endpoint():
    """Verify GET /docs serves interactive Swagger UI HTML page."""
    client = TestClient(app)
    response = client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "swagger-ui" in response.text.lower()


def test_redoc_endpoint():
    """Verify GET /redoc serves ReDoc documentation HTML page."""
    client = TestClient(app)
    response = client.get("/redoc")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "redoc" in response.text.lower()


def test_openapi_schema_endpoint():
    """Verify GET /openapi.json serves valid OpenAPI 3.x metadata, tags, and routes."""
    client = TestClient(app)
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")

    schema = response.json()
    assert schema.get("openapi", "").startswith("3.")
    assert schema["info"]["title"] == "Water Meter Digitizer API"
    assert schema["info"]["version"] == VERSION
    assert "High-performance edge AI digitizer" in schema["info"]["description"]

    # Verify Tags
    tag_names = {tag["name"] for tag in schema.get("tags", [])}
    expected_tags = {"system", "health", "meter", "history", "services", "simulation"}
    assert expected_tags.issubset(tag_names)

    # Verify Core Paths
    paths = schema.get("paths", {})
    assert "/health" in paths
    assert "/version" in paths
    assert "/meter" in paths
    assert "/roi" in paths
    assert "/history/consumption" in paths
    assert "/leak/status" in paths
    assert "/poller/status" in paths
    assert "/mqtt/status" in paths
    assert "/api/mock_camera" in paths
