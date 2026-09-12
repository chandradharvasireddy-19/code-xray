import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "endpoints" in data


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_scan_and_analysis_flow(tmp_path):
    # Setup miniature test repo
    (tmp_path / "hello.py").write_text("def hello(): return 'world'\n", encoding="utf-8")

    # 1. Trigger scan
    scan_resp = client.post(
        "/repository/scan",
        json={"path": str(tmp_path), "name": "mini_repo"},
    )
    assert scan_resp.status_code == 201
    scan_data = scan_resp.json()
    assert scan_data["status"] == "completed"
    repo_id = scan_data["repository_id"]

    # 2. Get analysis
    analysis_resp = client.get(f"/analysis/{repo_id}")
    assert analysis_resp.status_code == 200
    analysis_data = analysis_resp.json()
    assert analysis_data["repository_id"] == repo_id
    assert analysis_data["summary"]["total_files"] == 1

    # 3. Get findings
    findings_resp = client.get(f"/findings/{repo_id}")
    assert findings_resp.status_code == 200

    # 4. Trigger impact analysis
    impact_resp = client.post(
        f"/impact/{repo_id}",
        json={"task": "Modify the hello function"},
    )
    assert impact_resp.status_code == 201
    impact_data = impact_resp.json()
    assert impact_data["task"] == "Modify the hello function"
    assert "risk" in impact_data
    assert "summary" in impact_data


def test_local_repository_registration_and_retrieval(tmp_path):
    # Setup test repo
    (tmp_path / "index.py").write_text("print('test')", encoding="utf-8")

    # 1. Register local repository
    reg_resp = client.post(
        "/repository/local",
        json={"path": str(tmp_path), "name": "registered-repo"},
    )
    assert reg_resp.status_code == 201
    reg_data = reg_resp.json()
    assert "repository_id" in reg_data
    repo_id = reg_data["repository_id"]

    # 2. Immediately retrieve repository details
    get_resp = client.get(f"/repository/{repo_id}")
    assert get_resp.status_code == 200
    repo_data = get_resp.json()
    assert repo_data["repository_id"] == repo_id
    assert repo_data["name"] == "registered-repo"
    assert "index.py" in repo_data["files"]

