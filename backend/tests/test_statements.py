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
            "full_name": "Statement User",
            "email": email,
            "password": "StrongPassword123",
        },
    )
    assert response.status_code == 201
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "StrongPassword123"},
    )
    return {"Authorization": f"Bearer {login_response.json()['access_token']}"}


def test_upload_csv_persists_statement_and_transactions(client, upload_dir):
    headers = register_and_login(client, email="statement@example.com")

    response = client.post(
        "/api/v1/statements/upload",
        headers=headers,
        files={"file": ("july.csv", CSV_CONTENT, "text/csv")},
    )

    assert response.status_code == 201
    statement = response.json()
    assert statement["status"] == "processed"
    assert statement["original_filename"] == "july.csv"
    assert Path(upload_dir, statement["filename"]).is_file()

    transactions_response = client.get(
        f"/api/v1/statements/{statement['id']}/transactions", headers=headers
    )
    assert transactions_response.status_code == 200
    transactions = transactions_response.json()
    assert len(transactions) == 2
    assert transactions[0]["amount"] == "15.49"
    assert transactions[1]["amount"] == "-4.50"


def test_upload_rejects_invalid_csv_and_marks_statement_failed(client, upload_dir):
    headers = register_and_login(client, email="invalid-csv@example.com")

    response = client.post(
        "/api/v1/statements/upload",
        headers=headers,
        files={"file": ("invalid.csv", "date,merchant\n2026-07-01,Netflix\n", "text/csv")},
    )

    assert response.status_code == 422
    assert "missing required columns" in response.json()["detail"]
    statements_response = client.get("/api/v1/statements", headers=headers)
    assert statements_response.status_code == 200
    assert statements_response.json()[0]["status"] == "failed"


def test_upload_rejects_unsupported_file_type(client, upload_dir):
    headers = register_and_login(client, email="unsupported@example.com")

    response = client.post(
        "/api/v1/statements/upload",
        headers=headers,
        files={"file": ("statement.pdf", b"not-a-pdf", "application/pdf")},
    )

    assert response.status_code == 415


def test_upload_rejects_files_over_size_limit(client, upload_dir, monkeypatch):
    headers = register_and_login(client, email="oversized@example.com")
    monkeypatch.setattr(settings, "MAX_FILE_SIZE", 10)

    response = client.post(
        "/api/v1/statements/upload",
        headers=headers,
        files={"file": ("large.csv", b"date,merchant", "text/csv")},
    )

    assert response.status_code == 413


def test_statement_transactions_are_scoped_to_owner(client, upload_dir):
    owner_headers = register_and_login(client, email="owner@example.com")
    other_headers = register_and_login(client, email="other@example.com")
    upload_response = client.post(
        "/api/v1/statements/upload",
        headers=owner_headers,
        files={"file": ("owner.csv", CSV_CONTENT, "text/csv")},
    )
    statement_id = upload_response.json()["id"]

    response = client.get(
        f"/api/v1/statements/{statement_id}/transactions", headers=other_headers
    )

    assert response.status_code == 404
