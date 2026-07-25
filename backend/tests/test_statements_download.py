from pathlib import Path
import pytest

from app.core.config import settings

CSV_CONTENT = """date,merchant,description,amount,currency,category
2026-07-01,Netflix,Netflix monthly subscription,15.49,USD,Entertainment
2026-07-02,Coffee Shop,Morning coffee,-4.50,USD,Food
"""


@pytest.fixture
def upload_dir(tmp_path, monkeypatch):
    directory = tmp_path / "uploads"
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(directory))
    return directory


def register_and_login(client, *, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Download User",
            "email": email,
            "password": "StrongPassword123",
        },
    )
    assert response.status_code == 201
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPassword123"},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_download_statement_success(client, upload_dir):
    headers = register_and_login(client, email="download-owner@example.com")

    upload_resp = client.post(
        "/api/v1/statements/upload",
        headers=headers,
        files={"file": ("july.csv", CSV_CONTENT, "text/csv")},
    )
    assert upload_resp.status_code == 201
    statement = upload_resp.json()

    download_resp = client.get(f"/api/v1/statements/{statement['id']}/download", headers=headers)
    assert download_resp.status_code == 200
    # Content-disposition should include the original filename
    content_disp = download_resp.headers.get("content-disposition", "")
    assert "attachment" in content_disp
    assert "july.csv" in content_disp
    # Content bytes should equal the uploaded content
    assert download_resp.content.decode("utf-8") == CSV_CONTENT


def test_download_scoped_to_owner(client, upload_dir):
    owner_headers = register_and_login(client, email="owner2@example.com")
    other_headers = register_and_login(client, email="other2@example.com")

    upload_resp = client.post(
        "/api/v1/statements/upload",
        headers=owner_headers,
        files={"file": ("owner.csv", CSV_CONTENT, "text/csv")},
    )
    statement = upload_resp.json()

    response = client.get(f"/api/v1/statements/{statement['id']}/download", headers=other_headers)
    assert response.status_code == 404


def test_download_missing_file_returns_404(client, upload_dir):
    headers = register_and_login(client, email="missingfile@example.com")

    upload_resp = client.post(
        "/api/v1/statements/upload",
        headers=headers,
        files={"file": ("missing.csv", CSV_CONTENT, "text/csv")},
    )
    statement = upload_resp.json()

    # Remove the underlying file to simulate a missing file on disk
    stored_path = Path(upload_dir) / statement["filename"]
    if stored_path.exists():
        stored_path.unlink()

    response = client.get(f"/api/v1/statements/{statement['id']}/download", headers=headers)
    assert response.status_code == 404
