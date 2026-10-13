"""Gerçek katalog/motor, sahte HTTP görsel servisi; YOLO doğruluk testi değildir."""

import copy
import json
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from backend import main

client = TestClient(main.app)


@pytest.fixture
def request_data():
    return {"home": {"faz": "monofaz", "sozlesme_gucu_kw": 3},
            "user": {"gunluk_ortalama_km": 30, "evde_sarj_icin_uygun_sure_saat": 12,
                     "butce_tl": 30000, "kurulum_yeri": "İç mekan"},
            "vehicle_id": "EU_EVDB_3305_T10F_LONG_RANGE_RWD", "home_confirmed": True}


def test_real_catalog_and_engine(request_data):
    catalog = client.get("/api/catalog").json()
    assert len(catalog["vehicles"]) == 100
    before = copy.deepcopy(main.VEHICLES)
    response = client.post("/api/recommend", json=request_data)
    assert response.status_code == 200
    result = response.json()
    assert sum(result["counts"].values()) == 27
    tesla = next(i for i in result["candidates"]["eligible"] if i["charger_id"] == "TESLA_WALL_CONNECTOR_GEN3_TR_22_T2_7M3")
    assert tesla["metrics"]["gunluk_arac_enerji_ihtiyaci_kwh"] == 5.22
    assert tesla["metrics"]["arac_wallbox_teorik_etkin_guc_kw"] == 7.4
    assert main.VEHICLES == before
    assert all(not any(r["status"] == "ELE" for r in item["hard_rule"]["rules"]) for item in result["candidates"]["eligible"])


@pytest.mark.parametrize("confirmed", [False, "true", 1, None])
def test_confirmation_required(request_data, confirmed):
    request_data["home_confirmed"] = confirmed
    assert client.post("/api/recommend", json=request_data).status_code == 422


@pytest.mark.parametrize("field,value", [("gunluk_ortalama_km", 0), ("gunluk_ortalama_km", -1),
    ("gunluk_ortalama_km", True), ("gunluk_ortalama_km", "30"),
    ("evde_sarj_icin_uygun_sure_saat", 25), ("evde_sarj_icin_uygun_sure_saat", 0), ("butce_tl", 0)])
def test_invalid_user_inputs(request_data, field, value):
    request_data["user"][field] = value
    assert client.post("/api/recommend", json=request_data).status_code == 422


def test_nonfinite_value_rejected(request_data):
    body = json.dumps(request_data).replace('"gunluk_ortalama_km": 30', '"gunluk_ortalama_km": 1e999')
    assert client.post("/api/recommend", content=body, headers={"Content-Type": "application/json"}).status_code == 422


def test_unknown_vehicle_and_technical_override_rejected(request_data):
    request_data["vehicle_id"] = "UNKNOWN"
    assert client.post("/api/recommend", json=request_data).status_code == 422
    request_data["vehicle_id"] = "EU_EVDB_3305_T10F_LONG_RANGE_RWD"
    request_data["vehicle"] = {"ac_tek_faz_azami_guc_kw": 100}
    assert client.post("/api/recommend", json=request_data).status_code == 422


def test_optional_budget_wltp_and_unknown_phase_preserved(request_data):
    request_data["user"]["butce_tl"] = None
    request_data["vehicle_id"] = "EU_EVDB_3302_T10X_LONG_RANGE_RWD"
    result = client.post("/api/recommend", json=request_data).json()
    assert result["candidates"]["eligible"]
    for item in result["candidates"]["eligible"]:
        assert item["metrics"]["fiyat_butce_orani"] is None
        assert item["metrics"]["gunluk_arac_enerji_ihtiyaci_kwh"] is None
    request_data["home"]["faz"] = "belirsiz"
    result = client.post("/api/recommend", json=request_data).json()
    assert result["counts"]["eligible"] == 0
    assert result["counts"]["needs_verification"] == 27


def test_contract_power_is_context_only(request_data):
    first = client.post("/api/recommend", json=request_data).json()["candidates"]
    request_data["home"]["sozlesme_gucu_kw"] = 100
    second = client.post("/api/recommend", json=request_data).json()["candidates"]
    assert first == second


def test_ocr_receipt_required_validated_and_edits_traced(request_data, monkeypatch):
    request_data["input_source"] = "ocr"
    assert client.post("/api/recommend", json=request_data).status_code == 422
    home = main.HomeInput.model_validate(request_data["home"]).model_dump()
    token = main.sign_analysis(home)
    request_data["analysis_token"] = token[:-1] + ("0" if token[-1] != "0" else "1")
    assert client.post("/api/recommend", json=request_data).status_code == 422
    request_data["analysis_token"] = token
    request_data["home"]["sozlesme_gucu_kw"] = 4
    response = client.post("/api/recommend", json=request_data)
    assert response.status_code == 200
    assert response.json()["home_changes"]["sozlesme_gucu_kw"] == {"detected": 3, "confirmed": 4}
    expired_time = time.time() + main.TOKEN_TTL_SECONDS + 1
    monkeypatch.setattr(main.time, "time", lambda: expired_time)
    # Süresi dolmuş kaydın kabul edilmediğini deterministik kontrol et.
    assert client.post("/api/recommend", json=request_data).status_code == 422


def test_vision_unconfigured_has_manual_fallback(monkeypatch):
    monkeypatch.setattr(main, "VISION_KEY", "")
    response = client.post("/api/analyze-home", files={"meter_file": ("m.jpg", b"photo"), "bill_file": ("b.jpg", b"photo")})
    assert response.status_code == 503


def setup_vision_stub(monkeypatch, upstream_status=200):
    real_client = httpx.AsyncClient
    monkeypatch.setattr(main, "VISION_KEY", "server-test-key")
    def handle(request):
        assert request.url.path == "/analyze/home"
        assert request.headers["X-API-Key"] == "server-test-key"
        return httpx.Response(upstream_status, json={"home": {"faz": "trifaz", "sozlesme_gucu_kw": 3},
            "ocr_metinleri": [{"text": "PRIVATE DOCUMENT"}], "kdsye_dogrudan_aktarilabilir": True})
    monkeypatch.setattr(main.httpx, "AsyncClient", lambda **kwargs: real_client(transport=httpx.MockTransport(handle), **kwargs))


def test_vision_proxy_strips_raw_ocr_and_requires_confirmation(monkeypatch, request_data):
    setup_vision_stub(monkeypatch)
    response = client.post("/api/analyze-home", files={"meter_file": ("m.jpg", b"photo"), "bill_file": ("b.jpg", b"photo")})
    assert response.status_code == 200
    data = response.json()
    assert data["kdsye_dogrudan_aktarilabilir"] is False
    assert "PRIVATE DOCUMENT" not in response.text and "server-test-key" not in response.text
    request_data.update(home=data["home"], input_source="ocr", analysis_token=data["analysis_token"], home_confirmed=False)
    assert client.post("/api/recommend", json=request_data).status_code == 422
    request_data["home_confirmed"] = True
    assert client.post("/api/recommend", json=request_data).status_code == 200


@pytest.mark.parametrize("status,expected", [(400,400),(413,413),(500,503),(401,503)])
def test_upstream_errors_are_not_success(monkeypatch, status, expected):
    setup_vision_stub(monkeypatch, status)
    response = client.post("/api/analyze-home", files={"meter_file": ("m.jpg", b"photo"), "bill_file": ("b.jpg", b"photo")})
    assert response.status_code == expected


def test_empty_and_large_upload_rejected(monkeypatch):
    setup_vision_stub(monkeypatch)
    for content, status in [(b"",422), (b"12345",413)]:
        monkeypatch.setattr(main, "MAX_UPLOAD_BYTES", 4)
        response = client.post("/api/analyze-home", files={"meter_file": ("m.jpg", content), "bill_file": ("b.jpg", b"x")})
        assert response.status_code == status
