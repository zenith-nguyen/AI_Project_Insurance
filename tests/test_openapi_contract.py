from src.api.app import app


def test_openapi_has_claim_lifecycle_endpoints():
    paths = app.openapi()["paths"]
    assert set(paths) >= {
        "/health",
        "/version",
        "/claims/{claim_id}/intake",
        "/claims/{claim_id}/evidence",
        "/claims/{claim_id}/analyze",
        "/claims/{claim_id}/analysis",
        "/claims/{claim_id}/review",
    }
    assert "post" in paths["/claims/{claim_id}/analyze"]
    assert "post" in paths["/claims/{claim_id}/review"]
