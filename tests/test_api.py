from fastapi.testclient import TestClient

import app.main as main


def test_health_endpoint():
    client = TestClient(main.app)
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["laws"] >= 30


def test_law_search_endpoint():
    client = TestClient(main.app)
    response = client.get("/laws/search", params={"q": "竞业限制补偿", "top_k": 3})

    assert response.status_code == 200
    results = response.json()["results"]
    assert results
    assert results[0]["article"]["id"].startswith("labor-")


def test_qa_endpoint(monkeypatch, qa_service):
    monkeypatch.setattr(main, "get_qa_service", lambda: qa_service)
    client = TestClient(main.app)
    response = client.post(
        "/qa", json={"question": "公司违法解除劳动合同，工作3年2个月，月薪2万，怎么赔？"}
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["calculation"]["amount"] == 140000
    assert payload["citations"]

    report = client.get(f"/qa/{payload['id']}/report")
    assert report.status_code == 200
    assert "法律咨询记录" in report.text


def test_review_endpoint(monkeypatch, review_service, contract_text):
    monkeypatch.setattr(main, "get_review_service", lambda: review_service)
    client = TestClient(main.app)
    response = client.post(
        "/contract/review",
        json={
            "contract_text": contract_text("labor_contract_risky.txt"),
            "contract_type": "labor",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["overall_risk"] == "high"
    assert payload["findings"]

    report = client.get(f"/reviews/{payload['id']}/report")
    assert report.status_code == 200
    assert "合同审查报告" in report.text
