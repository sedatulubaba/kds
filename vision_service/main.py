from __future__ import annotations

import asyncio
import logging
import os
import secrets
import time
from pathlib import Path
from typing import Callable

import torch
from fastapi import FastAPI, File, Header, HTTPException, Query, UploadFile
from starlette.concurrency import run_in_threadpool
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

os.environ.setdefault("YOLO_AUTOINSTALL", "false")

from bill_predict_and_ocr import MODEL_PATH as BILL_MODEL_PATH
from bill_predict_and_ocr import fatura_analiz_et
from image_processing import (
    GorselDogrulamaHatasi,
    gorseli_hazirla,
    upload_verisini_oku,
)
from home_input import kds_ev_girdisi_olustur
from key_utils import key_gecerli_mi, key_sahibi, key_uret
from predict_and_ocr import MODEL_PATH as METER_MODEL_PATH
from predict_and_ocr import sayac_analiz_et


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "temp_uploads"
ADMIN_KEY = os.getenv("EVCSDS_ADMIN_KEY")
MAX_CONCURRENT_ANALYSES = 1

logging.basicConfig(
    level=os.getenv("EVCSDS_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("evcsds.api")
analiz_semaforu = asyncio.Semaphore(MAX_CONCURRENT_ANALYSES)

app = FastAPI(
    title="EVCSDS Görsel Analiz API",
    description="Elektrik sayacı ve elektrik faturası görsellerini analiz eder.",
    version="2.0.0",
)


def api_key_dogrula(api_key: str | None) -> str:
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="API key gerekli. X-API-Key header'ını gönderin.",
        )
    if not key_gecerli_mi(api_key):
        raise HTTPException(status_code=401, detail="Geçersiz API key.")
    return key_sahibi(api_key) or "bilinmeyen"


async def _gorsel_analiz_et(
    file: UploadFile,
    x_api_key: str | None,
    analiz_fonksiyonu: Callable[[str | Path], dict],
    analiz_turu: str,
) -> dict:
    kullanici = api_key_dogrula(x_api_key)
    gecici_yol: Path | None = None

    try:
        veri = await upload_verisini_oku(file)
        gecici_yol, gorsel_bilgisi = await run_in_threadpool(
            gorseli_hazirla, veri, UPLOAD_DIR
        )

        baslangic = time.perf_counter()
        async with analiz_semaforu:
            sonuc = await run_in_threadpool(analiz_fonksiyonu, gecici_yol)
        sure_ms = round((time.perf_counter() - baslangic) * 1000)

        sonuc["analiz_turu"] = analiz_turu
        sonuc["kullanici"] = kullanici
        sonuc["islem_suresi_ms"] = sure_ms
        sonuc["gorsel"] = gorsel_bilgisi.dict()
        return sonuc
    except GorselDogrulamaHatasi as exc:
        durum = 413 if "25 MB" in str(exc) else 400
        raise HTTPException(status_code=durum, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception:
        logger.exception("%s analizi sırasında beklenmeyen hata", analiz_turu)
        raise HTTPException(
            status_code=500,
            detail="Görsel analizi tamamlanamadı.",
        )
    finally:
        await file.close()
        if gecici_yol is not None:
            try:
                gecici_yol.unlink(missing_ok=True)
            except OSError:
                logger.warning("Geçici dosya silinemedi: %s", gecici_yol)


@app.get("/")
def root() -> dict:
    return {
        "mesaj": "EVCSDS API çalışıyor",
        "versiyon": "2.0.0",
        "endpointler": ["/analyze/meter", "/analyze/bill", "/analyze/home"],
    }


@app.get("/health")
def health() -> dict:
    modeller = {
        "sayac": METER_MODEL_PATH.is_file(),
        "fatura": BILL_MODEL_PATH.is_file(),
    }
    hazir = all(modeller.values())
    return {
        "durum": "ok" if hazir else "hazir_degil",
        "modeller": modeller,
        "cuda": torch.cuda.is_available(),
        "cihaz": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
    }


@app.post("/keys/generate")
def generate_key(
    kullanici_adi: str = Query(min_length=2, max_length=100),
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> dict:
    if not ADMIN_KEY:
        raise HTTPException(
            status_code=503,
            detail="API key üretimi sunucuda etkin değil.",
        )
    if not x_admin_key or not secrets.compare_digest(x_admin_key, ADMIN_KEY):
        raise HTTPException(status_code=403, detail="Geçersiz yönetici anahtarı.")

    yeni_key = key_uret(kullanici_adi)
    return {"kullanici": kullanici_adi, "api_key": yeni_key}


@app.post("/analyze")
@app.post("/analyze/meter")
async def analyze_meter(
    file: UploadFile = File(...),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> dict:
    return await _gorsel_analiz_et(
        file, x_api_key, sayac_analiz_et, "sayac"
    )


@app.post("/analyze/bill")
async def analyze_bill(
    file: UploadFile = File(...),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> dict:
    return await _gorsel_analiz_et(
        file, x_api_key, fatura_analiz_et, "fatura"
    )


@app.post("/analyze/home")
async def analyze_home(
    meter_file: UploadFile = File(...),
    bill_file: UploadFile = File(...),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> dict:
    """İki görselden KDS home girdisi üretir; ham OCR metinlerini döndürmez."""
    api_key_dogrula(x_api_key)
    baslangic = time.perf_counter()
    sayac_sonucu = await _gorsel_analiz_et(
        meter_file, x_api_key, sayac_analiz_et, "sayac"
    )
    fatura_sonucu = await _gorsel_analiz_et(
        bill_file, x_api_key, fatura_analiz_et, "fatura"
    )
    sonuc = kds_ev_girdisi_olustur(sayac_sonucu, fatura_sonucu)
    sonuc["islem_suresi_ms"] = round((time.perf_counter() - baslangic) * 1000)
    return sonuc
