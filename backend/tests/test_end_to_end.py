import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_full_end_to_end_pipeline():
    # 1. Locate demo-repository
    demo_path = Path(__file__).resolve().parent.parent.parent / "demo-repository"
    if not demo_path.exists():
        demo_path = Path(__file__).resolve().parent.parent / "demo_repo"

    assert demo_path.exists(), f"Demo repository not found at {demo_path}"

    # 2. Trigger repository scan
    scan_resp = client.post(
        "/repository/scan",
        json={"path": str(demo_path), "name": "Software-Forensics-Demo"},
    )
    assert scan_resp.status_code == 201
    scan_data = scan_resp.json()
    assert scan_data["status"] == "completed"
    repo_id = scan_data["repository_id"]

    # Verify classification profile
    profile = scan_data["profile"]
    assert profile["primary_language"] == "Python"
    assert "FastAPI" in profile["frameworks"]

    # 3. Retrieve analysis details
    analysis_resp = client.get(f"/analysis/{repo_id}")
    assert analysis_resp.status_code == 200
    analysis = analysis_resp.json()
    assert analysis["summary"]["total_files"] >= 8
    assert analysis["summary"]["total_entities"] >= 10
    assert analysis["summary"]["total_relationships"] >= 5

    # 4. Verify Forensic Findings
    findings_resp = client.get(f"/findings/{repo_id}")
    assert findings_resp.status_code == 200
    findings_data = findings_resp.json()
    findings = findings_data["findings"]
    assert len(findings) >= 3

    finding_types = [f["finding_type"] for f in findings]
    assert "architecture_drift" in finding_types, "Architecture violation should be detected"
    assert "ghost_dependency" in finding_types, "Ghost dependency (numpy) should be detected"
    assert "dead_feature" in finding_types, "Dead feature (old_hasher) should be detected"

    # Verify individual finding endpoint
    sample_fid = findings[0]["finding_id"]
    single_finding_resp = client.get(f"/findings/{repo_id}/{sample_fid}")
    assert single_finding_resp.status_code == 200
    assert single_finding_resp.json()["finding_id"] == sample_fid

    # 5. Submit Change Impact Task
    task_str = "I need to modify the payment authentication flow"
    impact_resp = client.post(
        f"/impact/{repo_id}",
        json={"task": task_str},
    )
    assert impact_resp.status_code == 201
    impact = impact_resp.json()

    assert impact["task"] == task_str
    assert len(impact["affected_entities"]) >= 5

    affected_files = [ae["file"] for ae in impact["affected_entities"]]
    assert any("payment" in f for f in affected_files)
    assert any("auth" in f for f in affected_files)

    # 6. Verify Relationships and Tests
    assert len(impact["relationships"]) > 0
    assert len(impact["tests"]) > 0
    test_files = [t["test_file"] for t in impact["tests"]]
    assert any("test_payment" in tf or "test_auth" in tf for tf in test_files)

    # 7. Verify Multi-Factor Risk Assessment
    risk = impact["risk"]
    assert risk is not None
    assert risk["risk_score"] > 50
    assert risk["risk_level"] in ["HIGH", "CRITICAL"]
    assert len(risk["factors"]) >= 2

    # 8. Verify AI Explanation Fallback
    assert impact["ai_explanation"] is not None
    assert "[FACT]" in impact["ai_explanation"]
    assert "[INFERENCE]" in impact["ai_explanation"]

    # 9. Verify History retrieval of impact analysis
    analysis_id = impact["analysis_id"]
    get_impact_resp = client.get(f"/impact/{repo_id}/{analysis_id}")
    assert get_impact_resp.status_code == 200
    assert get_impact_resp.json()["analysis_id"] == analysis_id
