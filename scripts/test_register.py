from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

payload = {
    "full_name": "Test User",
    "email": "testuser@example.com",
    "password": "strongpassword123"
}

resp = client.post('/api/v1/auth/register', json=payload)
print('status', resp.status_code)
print(resp.json())
