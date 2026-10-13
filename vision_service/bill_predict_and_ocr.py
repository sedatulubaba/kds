from __future__ import annotations

import json
import re
import sys
import threading
import unicodedata
from pathlib import Path

import cv2
import torch
from ultralytics import YOLO

from bill_field_extractor import fatura_alanlarini_cikar
from ocr_engine import ocr_calistir


BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = (
    BASE_DIR
    / "runs"
    / "detect"
    / "electricity_bill_detection_v2"
    / "weights"
    / "best.pt"
)
DETECTION_CONFIDENCE = 0.25
TRUSTED_DETECTION_CONFIDENCE = 0.50
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
INFERENCE_DEVICE: int | str = 0 if torch.cuda.is_available() else "cpu"


if not MODEL_PATH.is_file():
    raise FileNotFoundError(f"Fatura modeli bulunamadı: {MODEL_PATH}")

model = YOLO(str(MODEL_PATH))
_model_lock = threading.Lock()


def _metni_normalize_et(metin: str) -> str:
    metin = metin.upper().replace("İ", "I").replace("Ş", "S")
    metin = metin.replace("Ü", "U").replace("Ö", "O").replace("Ç", "C")
    return "".join(
        karakter
        for karakter in unicodedata.normalize("NFKD", metin)
        if not unicodedata.combining(karakter)
    )


def _fatura_ocr_dogrulama_skoru(metinler: list[dict]) -> int:
    tam_metin = _metni_normalize_et(" ".join(m["text"] for m in metinler))
    anahtarlar = (
        "FATURA",
        "SOZLESME",
        "TESISAT",
        "MUSTERI",
        "TUKETIM",
        "ODENECEK",
        "KWH",
        "SON ODEME",
    )
    return sum(anahtar in tam_metin for anahtar in anahtarlar)


def _alan_cikarma_sonucu(metinler: list[dict], img) -> dict:
    yukseklik, genislik = img.shape[:2]
    try:
        sonuc = fatura_alanlarini_cikar(metinler, genislik, yukseklik)
        guc = (sonuc.get("alanlar") or {}).get("sozlesme_gucu_kw")
        if guc is None or guc.get("guven", 0) < 0.70:
            ek_metinler = _hedefli_guc_ocr(metinler, img)
            if ek_metinler:
                ikinci = fatura_alanlarini_cikar(
                    metinler + ek_metinler, genislik, yukseklik
                )
                ikinci_guc = (ikinci.get("alanlar") or {}).get("sozlesme_gucu_kw")
                if ikinci_guc and ikinci_guc.get("guven", 0) >= 0.70:
                    ikinci["yontem"] += "+hedefli_guc_ocr"
                    return ikinci
        return sonuc
    except Exception:
        return {
            "sirket": {"deger": "bilinmiyor", "guven": 0.0},
            "ozet": {},
            "alanlar": {},
            "eksik_kritik_alanlar": [
                "sozlesme_gucu_kw",
            ],
            "eksik_opsiyonel_alanlar": ["donem_tuketimi_kwh", "tarife"],
            "dusuk_guvenli_alanlar": [],
            "manuel_giris_gerekli": True,
            "manuel_giris_alanlari": [
                "sozlesme_gucu_kw",
            ],
            "opsiyonel_dogrulama_alanlari": ["donem_tuketimi_kwh", "tarife"],
            "yontem": "alan_cikarma_hatasi",
        }


def _hedefli_guc_ocr(metinler: list[dict], img) -> list[dict]:
    """Bozuk üçlü güç satırını, yalnız görülen etiket çevresinde bir kez büyütür."""
    yukseklik, genislik = img.shape[:2]
    if genislik > 2200:
        return []
    etiketler = []
    for metin in metinler:
        bbox = metin.get("bbox")
        if not bbox:
            continue
        normal = re.sub(r"[^A-Z]", "", _metni_normalize_et(metin["text"]))
        if "ARPAN" in normal and "DEMAND" in normal and "GUC" in normal:
            etiketler.append(metin)
    if not etiketler:
        return []
    etiket = max(etiketler, key=lambda m: m.get("score", 0))
    kutu = etiket["bbox"]
    satir_yuksekligi = kutu["y2"] - kutu["y1"]
    if satir_yuksekligi <= 0 or satir_yuksekligi > 80:
        return []
    ust_pay = max(20, min(29, round(satir_yuksekligi * 0.63)))
    kenar_pay = max(8, round(genislik * 0.023))
    x1 = max(0, kutu["x1"] - min(26, ust_pay))
    x2 = min(genislik, max(kutu["x2"] + 20, genislik - kenar_pay))
    y1 = max(0, kutu["y1"] - ust_pay)
    # Eğik yazıda OCR kutusu gerçek satırın altına taşabilir. Üçlü değerin
    # altındaki seri numarası satırını almamak için üst kenarı esas al.
    y2 = min(yukseklik, kutu["y1"] + min(34, satir_yuksekligi + 10))
    if y2 <= y1 or x1 >= x2:
        return []
    kirp = img[y1:y2, x1:x2]
    buyutulmus = cv2.resize(
        kirp, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC
    )
    try:
        yeniden_okunan = ocr_calistir(buyutulmus)
    except Exception:
        return []
    for metin in yeniden_okunan:
        metin["bbox"] = {
            "x1": x1 + round(metin["bbox"]["x1"] / 3),
            "y1": y1 + round(metin["bbox"]["y1"] / 3),
            "x2": x1 + round(metin["bbox"]["x2"] / 3),
            "y2": y1 + round(metin["bbox"]["y2"] / 3),
        }
    return yeniden_okunan


def _tam_gorsel_ocr_ile_dogrula(
    img, yolo_guveni: float, aday_var: bool
) -> dict:
    try:
        metinler = ocr_calistir(img)
    except Exception:
        return {
            "fatura_bulundu": False,
            "yolo_guveni": yolo_guveni,
            "bbox": None,
            "tespit_yontemi": "dogrulanamadi",
            "ocr_dogrulama_skoru": 0,
            "ocr_metinleri": [],
            "inceleme_gerekli": aday_var,
            "hata": "OCR işlemi tamamlanamadı.",
        }

    skor = _fatura_ocr_dogrulama_skoru(metinler)
    dogrulandi = skor >= 2
    return {
        "fatura_bulundu": dogrulandi,
        "yolo_guveni": yolo_guveni,
        "bbox": None,
        "tespit_yontemi": "tam_gorsel_ocr" if dogrulandi else "dogrulanamadi",
        "ocr_dogrulama_skoru": skor,
        "ocr_metinleri": metinler if dogrulandi else [],
        "inceleme_gerekli": not dogrulandi and aday_var,
        "performans_uyarisi": "dusuk_guvenli_geri_donus" if dogrulandi else None,
        "fatura_bilgileri": (
            _alan_cikarma_sonucu(metinler, img) if dogrulandi else None
        ),
    }


def fatura_analiz_et(gorsel_yolu: str | Path) -> dict:
    gorsel_yolu = Path(gorsel_yolu)
    img = cv2.imread(str(gorsel_yolu))
    if img is None:
        return {"hata": "Görsel okunamadı."}

    with _model_lock:
        results = model.predict(
            source=str(gorsel_yolu),
            conf=DETECTION_CONFIDENCE,
            device=INFERENCE_DEVICE,
            verbose=False,
        )

    adaylar = [
        box
        for result in results
        if result.boxes is not None
        for box in result.boxes
    ]
    if not adaylar:
        return _tam_gorsel_ocr_ile_dogrula(img, 0.0, False)

    en_iyi_box = max(adaylar, key=lambda box: float(box.conf[0]))
    yolo_guveni = round(float(en_iyi_box.conf[0]), 2)
    x1, y1, x2, y2 = map(int, en_iyi_box.xyxy[0])

    if yolo_guveni < TRUSTED_DETECTION_CONFIDENCE:
        return _tam_gorsel_ocr_ile_dogrula(img, yolo_guveni, True)

    margin = 30
    h, w = img.shape[:2]
    crop = img[
        max(0, y1 - margin) : min(h, y2 + margin),
        max(0, x1 - margin) : min(w, x2 + margin),
    ]

    try:
        ocr_metinleri = ocr_calistir(crop)
    except Exception:
        return {
            "fatura_bulundu": True,
            "yolo_guveni": yolo_guveni,
            "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
            "tespit_yontemi": "yolo",
            "ocr_dogrulama_skoru": 0,
            "ocr_metinleri": [],
            "hata": "OCR işlemi tamamlanamadı.",
        }

    dogrulama_skoru = _fatura_ocr_dogrulama_skoru(ocr_metinleri)
    if dogrulama_skoru < 2:
        return _tam_gorsel_ocr_ile_dogrula(img, yolo_guveni, True)

    return {
        "fatura_bulundu": True,
        "yolo_guveni": yolo_guveni,
        "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
        "tespit_yontemi": "yolo_ocr_dogrulama",
        "ocr_dogrulama_skoru": dogrulama_skoru,
        "ocr_metinleri": ocr_metinleri,
        "inceleme_gerekli": False,
        "fatura_bilgileri": _alan_cikarma_sonucu(ocr_metinleri, crop),
    }


def _gorselleri_bul(hedef: Path) -> list[Path]:
    if hedef.is_dir():
        images_dir = hedef / "images"
        klasor = images_dir if images_dir.is_dir() else hedef
        return sorted(
            path
            for path in klasor.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        )
    return [hedef]


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 2:
        print("Kullanım: python bill_predict_and_ocr.py <görsel veya klasör yolu>")
        raise SystemExit(1)
    for gorsel in _gorselleri_bul(Path(sys.argv[1])):
        print(f"\n=== {gorsel.name} ===")
        print(json.dumps(fatura_analiz_et(gorsel), ensure_ascii=False, indent=2))
