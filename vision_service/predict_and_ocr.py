from __future__ import annotations

import json
import re
import sys
import threading
import unicodedata
from pathlib import Path

import cv2
import torch
from rapidfuzz import fuzz
from ultralytics import YOLO

from ocr_engine import ocr_calistir


BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = (
    BASE_DIR
    / "runs"
    / "detect"
    / "runs"
    / "electric_meter_detection3"
    / "weights"
    / "best.pt"
)
INFERENCE_DEVICE: int | str = 0 if torch.cuda.is_available() else "cpu"

if not MODEL_PATH.is_file():
    raise FileNotFoundError(f"Sayaç modeli bulunamadı: {MODEL_PATH}")

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


def faz_tespit_et(metinler: list[dict]) -> dict:
    tam_metin = _metni_normalize_et(" ".join(m["text"] for m in metinler))

    trifaz_ifadeleri = (
        r"\b3\s*FAZ",
        r"\bTRI\s*FAZ",
        r"\b3\s*[XP]\s*(?:220|230|240|380|400)",
        r"\b3P(?:\+N)?\b",
    )
    monofaz_ifadeleri = (
        r"\b1\s*FAZ",
        r"\bMONO\s*FAZ",
        r"\b1P(?:\+N)?\b",
    )

    if any(re.search(ifade, tam_metin) for ifade in trifaz_ifadeleri):
        return {"faz": "trifaz", "guvenskor": 100, "yontem": "kural"}
    if any(re.search(ifade, tam_metin) for ifade in monofaz_ifadeleri):
        return {"faz": "monofaz", "guvenskor": 100, "yontem": "kural"}

    monofaz_skoru = fuzz.partial_ratio("1 FAZLI", tam_metin)
    trifaz_skoru = fuzz.partial_ratio("3 FAZLI", tam_metin)
    en_yuksek = max(monofaz_skoru, trifaz_skoru)
    if en_yuksek >= 75 and abs(monofaz_skoru - trifaz_skoru) >= 8:
        faz = "monofaz" if monofaz_skoru > trifaz_skoru else "trifaz"
        return {
            "faz": faz,
            "guvenskor": round(en_yuksek, 2),
            "yontem": "benzerlik",
        }
    return {"faz": "belirsiz", "guvenskor": 0, "yontem": "eslesme_yok"}


def sayac_analiz_et(gorsel_yolu: str | Path) -> dict:
    gorsel_yolu = Path(gorsel_yolu)
    img = cv2.imread(str(gorsel_yolu))
    if img is None:
        return {"hata": "Görsel okunamadı."}

    with _model_lock:
        results = model.predict(
            source=str(gorsel_yolu),
            conf=0.5,
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
        return {
            "sayac_bulundu": False,
            "yolo_guveni": 0.0,
            "bbox": None,
            "faz": "belirsiz",
            "faz_guvenskor": 0,
            "faz_tespit_yontemi": "eslesme_yok",
            "ocr_metinleri": [],
        }

    en_iyi_box = max(adaylar, key=lambda box: float(box.conf[0]))
    yolo_guveni = round(float(en_iyi_box.conf[0]), 2)
    x1, y1, x2, y2 = map(int, en_iyi_box.xyxy[0])
    margin = 60
    h, w = img.shape[:2]
    crop = img[
        max(0, y1 - margin) : min(h, y2 + margin),
        max(0, x1 - margin) : min(w, x2 + margin),
    ]

    try:
        ocr_metinleri = ocr_calistir(crop)
    except Exception:
        return {
            "sayac_bulundu": True,
            "yolo_guveni": yolo_guveni,
            "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
            "faz": "belirsiz",
            "faz_guvenskor": 0,
            "faz_tespit_yontemi": "ocr_hatasi",
            "ocr_metinleri": [],
            "hata": "OCR işlemi tamamlanamadı.",
        }

    faz_sonucu = faz_tespit_et(ocr_metinleri)
    return {
        "sayac_bulundu": True,
        "yolo_guveni": yolo_guveni,
        "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
        "faz": faz_sonucu["faz"],
        "faz_guvenskor": faz_sonucu["guvenskor"],
        "faz_tespit_yontemi": faz_sonucu["yontem"],
        "ocr_metinleri": ocr_metinleri,
    }


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) != 2:
        print("Kullanım: python predict_and_ocr.py <görsel_yolu>")
        raise SystemExit(1)
    print(json.dumps(sayac_analiz_et(sys.argv[1]), ensure_ascii=False, indent=2))
