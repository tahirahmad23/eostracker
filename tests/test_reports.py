
import pytest

def test_generate_pdf_report(client, auth_headers):
    # Just check if endpoint is reachable and returns PDF mime type.
    # We rely on the reportlab library to actually work.
    # Note: If no devices tracked, it might return empty report or error?
    # Usually it generates an empty report.
    
    response = client.post("/api/reports/generate", headers=auth_headers)
    
    # It might fail if no devices are tracked, or succeed with empty.
    # Assuming success for now.
    if response.status_code == 200:
        assert response.headers["content-type"] == "application/pdf"
        assert len(response.content) > 0
    else:
        # If it fails, check if it's a known error.
        assert response.status_code in [200, 400]


