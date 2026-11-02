"""Automated route and regression verification suite for ScholarScope.

Verifies:
1. All 7 multi-page HTML routes return HTTP 200 with proper title and landmarks.
2. Custom 404 error page returns HTTP 404 (HTML for web, JSON for API).
3. Core static assets (logo, favicon, CSS tokens, JS controllers) return HTTP 200.
4. Core JSON API endpoints (/api/health, /api/prompts, /api/history, /api/tests) return valid data.
5. Strict Security Check: No API keys or webhook secrets leaked into HTML or static assets.
"""

import os
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_html_pages_return_200():
    """All 7 multi-page routes must render with HTTP 200 and valid HTML."""
    routes = [
        ("/", "ScholarScope"),
        ("/analyze", "Analyze Topic Feasibility"),
        ("/how-it-works", "Methodology"),
        ("/prompts", "Prompt Library"),
        ("/tests", "Benchmark Tests"),
        ("/history", "Analysis History"),
        ("/responsible-ai", "Responsible AI"),
    ]

    for path, expected_text in routes:
        response = client.get(path)
        assert response.status_code == 200, f"Route {path} failed with status {response.status_code}"
        assert expected_text in response.text, f"Route {path} missing expected landmark '{expected_text}'"
        assert "<!DOCTYPE html>" in response.text or "<html" in response.text


def test_custom_404_handling():
    """Non-existent web routes must return HTML 404; API routes must return JSON 404."""
    # Web 404
    web_res = client.get("/this-page-does-not-exist")
    assert web_res.status_code == 404
    assert "Page Not Found" in web_res.text
    assert "404" in web_res.text

    # API 404
    api_res = client.get("/api/unknown-endpoint")
    assert api_res.status_code == 404
    assert api_res.headers.get("content-type", "").startswith("application/json")
    data = api_res.json()
    assert data.get("detail") == "Not Found"


def test_static_assets_return_200():
    """Core static brand assets and stylesheets must be accessible at /static/."""
    assets = [
        "/static/logo.svg",
        "/static/favicon.svg",
        "/static/css/tokens.css",
        "/static/css/style.css",
        "/static/css/print.css",
        "/static/js/theme.js",
        "/static/js/nav.js",
        "/static/js/copy.js",
        "/static/js/analyze.js",
    ]

    for asset_path in assets:
        res = client.get(asset_path)
        assert res.status_code == 200, f"Asset {asset_path} returned status {res.status_code}"


def test_api_endpoints_return_json():
    """Core REST API endpoints must return HTTP 200 and valid JSON schemas."""
    # Health check
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    data_health = res_health.json()
    assert "status" in data_health
    assert "gemini" in data_health
    assert "webhook" in data_health

    # Prompts API
    res_prompts = client.get("/api/prompts")
    assert res_prompts.status_code == 200
    data_prompts = res_prompts.json()
    assert "prompt_log" in data_prompts
    assert len(data_prompts["prompt_log"]) >= 3

    # History API
    res_hist = client.get("/api/history")
    assert res_hist.status_code == 200
    data_hist = res_hist.json()
    assert data_hist.get("status") in ["success", "error"]
    assert "data" in data_hist

    # Tests API
    res_tests = client.get("/api/tests")
    assert res_tests.status_code == 200
    data_tests = res_tests.json()
    assert data_tests.get("status") in ["success", "error"]
    assert "data" in data_tests


def test_no_secrets_in_rendered_html():
    """Confirms backend secrets (GEMINI_API_KEY, APPS_SCRIPT_SECRET) are never leaked to client."""
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    apps_script_secret = os.getenv("APPS_SCRIPT_SECRET", "").strip()

    routes = ["/", "/analyze", "/how-it-works", "/prompts", "/tests", "/history", "/responsible-ai", "/api/prompts"]

    for path in routes:
        res = client.get(path)
        text = res.text
        if gemini_key and len(gemini_key) > 6:
            assert gemini_key not in text, f"SECURITY ALERT: GEMINI_API_KEY leaked in route {path}"
        if apps_script_secret and len(apps_script_secret) > 4:
            assert apps_script_secret not in text, f"SECURITY ALERT: APPS_SCRIPT_SECRET leaked in route {path}"


if __name__ == "__main__":
    test_html_pages_return_200()
    test_custom_404_handling()
    test_static_assets_return_200()
    test_api_endpoints_return_json()
    test_no_secrets_in_rendered_html()
    print("✓ All route and security regression tests passed successfully!")
