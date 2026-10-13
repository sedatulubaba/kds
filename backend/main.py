"""KDS HTTP katmanı: katalog, onaylı karar isteği ve sunucudan görsel servis çağrısı."""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.models import HomeInput, RecommendationInput
from kds_engine.engine import recommend_candidates

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
MAX_UPLOAD_BYTES = 25 * 1024 * 1024
TOKEN_TTL_SECONDS = 3600
CONFIRMATION_SECRET = os.getenv("EVCSDS_CONFIRMATION_SECRET") or secrets.token_hex(32)
VISION_URL = os.getenv("EVCSDS_VISION_URL", "http://127.0.0.1:8001").rstrip("/")
VISION_KEY = os.getenv("EVCSDS_VISION_API_KEY", "")


def read_catalog(filename, id_field):
    records = json.loads((ROOT / "data" / filename).read_text(encoding="utf-8-sig"))
    result = {record[id_field]: record for record in records}
    if len(result) != len(records):
        raise ValueError(f"Tekrarlı katalog ID: {filename}")
    return result


VEHICLES = read_catalog("ARAC_KDS_CEKIRDEK_100.json", "vehicle_id")
WALLBOXES = read_catalog("WALLBOX_KDS_CEKIRDEK_30_V1_1.json", "charger_id")
POOLS = json.loads((ROOT / "data/KDS_ADAY_HAVUZLARI_V1.json").read_text(encoding="utf-8-sig"))["havuzlar"]
CANDIDATE_IDS = next(pool["charger_ids"] for pool in POOLS if pool["candidate_pool_id"] == "POOL_TEKNIK_27")
if len(CANDIDATE_IDS) != 27 or len(set(CANDIDATE_IDS)) != 27:
    raise ValueError("Teknik havuz 27 benzersiz ürün içermeli.")
if any(WALLBOXES[c]["kds_veri_kullanilabilir"] != "Evet" for c in CANDIDATE_IDS):
    raise ValueError("Teknik havuzda veri yetersiz kayıt var.")

app = FastAPI(title="EVCSDS Karar Destek Uygulaması", version="1.0.0")


@app.exception_handler(RequestValidationError)
async def validation_error(request, error):
    # İstemcinin NaN/Infinity veya kişisel girdisini hata yanıtına kopyalama.
    return JSONResponse(status_code=422, content={"detail": [
        {"loc": item["loc"], "msg": item["msg"], "type": item["type"]} for item in error.errors()]})


def sign_analysis(home):
    payload = json.dumps({"home": home, "issued_at": int(time.time())}, ensure_ascii=False, separators=(",", ":")).encode()
    encoded = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    signature = hmac.new(CONFIRMATION_SECRET.encode(), encoded.encode(), hashlib.sha256).hexdigest()
    return encoded + "." + signature


def verify_analysis(token):
    try:
        encoded, signature = token.rsplit(".", 1)
        expected = hmac.new(CONFIRMATION_SECRET.encode(), encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("signature")
        payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
        age = time.time() - payload["issued_at"]
        if not 0 <= age <= TOKEN_TTL_SECONDS:
            raise ValueError("expired")
        return HomeInput.model_validate(payload["home"]).model_dump()
    except (ValueError, TypeError, KeyError):
        raise HTTPException(422, "Görsel analiz kaydı geçersiz veya süresi dolmuş; yeniden analiz edin.")


@app.get("/api/health")
def health():
    return {"status": "ok", "vehicle_count": len(VEHICLES), "candidate_count": len(CANDIDATE_IDS),
            "vision_configured": bool(VISION_KEY)}


@app.get("/api/catalog")
def catalog():
    return {"vehicles": list(VEHICLES.values()), "candidate_count": len(CANDIDATE_IDS)}


@app.post("/api/recommend")
def recommend(request: RecommendationInput):
    vehicle = VEHICLES.get(request.vehicle_id)
    if vehicle is None:
        raise HTTPException(422, "Araç katalogda bulunamadı; listeden bir araç seçin.")
    home = request.home.model_dump()
    original_home = verify_analysis(request.analysis_token) if request.input_source == "ocr" else None
    candidates = recommend_candidates(home, vehicle, request.user.model_dump(), [WALLBOXES[c] for c in CANDIDATE_IDS])
    # Motorun sırası ve statüleri aynen korunur; arayüz için yalnız katalog bilgisi eklenir.
    for items in candidates.values():
        for item in items:
            charger = WALLBOXES[item["charger_id"]]
            item["product"] = {field: charger.get(field) for field in (
                "marka", "model", "versiyon", "nominal_azami_guc_kw", "fiyat_tl", "fiyat_tarihi", "kurulum_dahil_mi", "kaynak_url")}
    return {"vehicle": vehicle, "home": home, "user": request.user.model_dump(),
            "input_source": request.input_source, "home_confirmed": True,
            "home_changes": {} if original_home is None else {
                key: {"detected": original_home[key], "confirmed": value}
                for key, value in home.items() if original_home[key] != value},
            "counts": {group: len(items) for group, items in candidates.items()}, "candidates": candidates,
            "notice": "Bu sonuçlar ürün ön değerlendirmesidir. Güç ve süre teoriktir; sözleşme gücü güvenli tesisat gücü değildir."}


async def read_upload(upload):
    content = bytearray()
    try:
        while chunk := await upload.read(1024 * 1024):
            content.extend(chunk)
            if len(content) > MAX_UPLOAD_BYTES:
                raise HTTPException(413, "Her fotoğraf en fazla 25 MB olabilir.")
        if not content:
            raise HTTPException(422, "Boş fotoğraf yüklenemez.")
        return bytes(content)
    finally:
        await upload.close()


def sanitize_home_analysis(result):
    """Yalnız doğrulanabilir home alanları; ham OCR veya kişisel metin taşınmaz."""
    home = HomeInput.model_validate(result["home"]).model_dump()
    missing = [key for key in ("faz", "sozlesme_gucu_kw") if home[key] in (None, "belirsiz")]
    return {"home": home, "durum": "manuel_dogrulama_gerekli" if missing else "kullanici_onayi_gerekli",
            "manuel_dogrulama_alanlari": missing,
            "onay_bekleyen_alanlar": [key for key, value in home.items() if value is not None and value != "belirsiz"],
            "kdsye_dogrudan_aktarilabilir": False,
            "analysis_token": sign_analysis(home),
            "uyari": "Okunan değerleri kontrol edip onaylayın. Eksik değerler tahmin edilmedi; sözleşme gücü kurulum kapasitesi değildir."}


@app.post("/api/analyze-home")
async def analyze_home(meter_file: UploadFile = File(...), bill_file: UploadFile = File(...)):
    if not VISION_KEY:
        await meter_file.close()
        await bill_file.close()
        raise HTTPException(503, "Görsel analiz servisi yapılandırılmadı. Ev bilgilerini manuel girerek devam edebilirsiniz.")
    try:
        meter = await read_upload(meter_file)
        bill = await read_upload(bill_file)
        async with httpx.AsyncClient(timeout=httpx.Timeout(180, connect=5)) as client:
            response = await client.post(VISION_URL + "/analyze/home", headers={"X-API-Key": VISION_KEY}, files={
                "meter_file": ("meter.jpg", meter, "application/octet-stream"),
                "bill_file": ("bill.jpg", bill, "application/octet-stream")})
        if response.status_code in (400, 413, 422):
            raise HTTPException(response.status_code, "Fotoğraflar işlenemedi. JPEG, PNG veya WebP dosyalarını kontrol edin.")
        response.raise_for_status()
        return sanitize_home_analysis(response.json())
    except httpx.TimeoutException:
        raise HTTPException(504, "Görsel analizi zaman aşımına uğradı. Yeniden deneyin veya manuel devam edin.")
    except httpx.HTTPError:
        raise HTTPException(503, "Görsel analiz servisine ulaşılamadı. Manuel girişle devam edebilirsiniz.")
    except (ValueError, KeyError, TypeError):
        raise HTTPException(502, "Görsel servisinin çıktısı doğrulanamadı; değerler motora aktarılmadı.")
    finally:
        await meter_file.close()
        await bill_file.close()
