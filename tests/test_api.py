"""POST /ir 엔드포인트 스펙. 엔진 위에 얇게 얹힌 계층이라 얇게 테스트한다."""

from fastapi.testclient import TestClient

from ir_pptx.main import app

client = TestClient(app)


def test_마크다운을_ir_json_으로_돌려준다():
    r = client.post("/ir", json={"markdown": "# 제목\n\n- 하나\n- 둘\n"})
    assert r.status_code == 200
    deck = r.json()
    assert deck["slides"], "슬라이드가 있어야 한다"
    types = [e["type"] for e in deck["slides"][0]["elements"]]
    assert "text" in types


def test_깨진_차트_json_은_400():
    md = "# 차트\n\n```chart\n{나쁜 json}\n```\n"
    r = client.post("/ir", json={"markdown": md})
    assert r.status_code == 400
