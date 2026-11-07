from fastapi.testclient import TestClient
from app.main import app


def test_demo_dashboard_and_upload_boundary() -> None:
    with TestClient(app) as client:
        workspaces = client.get("/api/v1/workspaces")
        assert workspaces.status_code == 200
        workspace_id = workspaces.json()[0]["id"]
        dashboard = client.get("/api/v1/dashboard", params={"workspace_id": workspace_id})
        assert dashboard.status_code == 200
        assert dashboard.json()["workspace"]["is_demo"] is True
        blocked = client.post("/api/v1/scans/upload", params={"workspace_id": workspace_id}, files={"file": ("tool.exe", b"not executable", "application/octet-stream")})
        assert blocked.status_code == 415


def test_authorized_configuration_upload_creates_findings() -> None:
    with TestClient(app) as client:
        workspace_id = client.get("/api/v1/workspaces").json()[0]["id"]
        response = client.post("/api/v1/scans/upload", params={"workspace_id": workspace_id}, files={"file": ("tls.conf", b"signature_algorithm = sha1\nkey_type = RSA", "text/plain")})
        assert response.status_code == 200
        findings = response.json()["findings"]
        assert any(item["algorithm"] == "SHA-1" for item in findings)


def test_reports_export_stored_records() -> None:
    with TestClient(app) as client:
        workspace_id = client.get("/api/v1/workspaces").json()[0]["id"]
        csv_report = client.get("/api/v1/reports/findings.csv", params={"workspace_id": workspace_id})
        pdf_report = client.get("/api/v1/reports/summary.pdf", params={"workspace_id": workspace_id})
        assert csv_report.status_code == 200
        assert "finding" in csv_report.text
        assert pdf_report.status_code == 200
        assert pdf_report.headers["content-type"] == "application/pdf"
