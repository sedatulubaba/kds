from __future__ import annotations

import os
import threading
from pathlib import Path

import cv2
import numpy as np


BASE_DIR = Path(__file__).resolve().parent
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
os.environ["PADDLE_PDX_CACHE_HOME"] = str(BASE_DIR / ".paddlex_cache")

from paddleocr import PaddleOCR


OCR_TILE_SIZE = 1800
OCR_TILE_OVERLAP = 120
OCR_MIN_SCORE = 0.25

ocr = PaddleOCR(
    text_detection_model_name="PP-OCRv5_mobile_det",
    text_recognition_model_name="latin_PP-OCRv5_mobile_rec",
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    device="cpu",
    enable_mkldnn=False,
    text_det_limit_side_len=OCR_TILE_SIZE,
    text_det_limit_type="max",
    text_det_thresh=0.3,
    text_det_box_thresh=0.4,
)

_ocr_lock = threading.Lock()


def _baslangic_noktalari(uzunluk: int) -> list[int]:
    if uzunluk <= OCR_TILE_SIZE:
        return [0]
    adim = OCR_TILE_SIZE - OCR_TILE_OVERLAP
    noktalar = list(range(0, uzunluk - OCR_TILE_SIZE + 1, adim))
    son = uzunluk - OCR_TILE_SIZE
    if noktalar[-1] != son:
        noktalar.append(son)
    return noktalar


def _ocr_parcalari(gorsel: np.ndarray) -> list[tuple[np.ndarray, int, int]]:
    yukseklik, genislik = gorsel.shape[:2]
    y_noktalari = _baslangic_noktalari(yukseklik)
    x_noktalari = _baslangic_noktalari(genislik)
    return [
        (
            gorsel[
                y : min(yukseklik, y + OCR_TILE_SIZE),
                x : min(genislik, x + OCR_TILE_SIZE),
            ],
            x,
            y,
        )
        for y in y_noktalari
        for x in x_noktalari
    ]


def _kutu_iou(a: dict, b: dict) -> float:
    ortak_x1 = max(a["x1"], b["x1"])
    ortak_y1 = max(a["y1"], b["y1"])
    ortak_x2 = min(a["x2"], b["x2"])
    ortak_y2 = min(a["y2"], b["y2"])
    ortak = max(0, ortak_x2 - ortak_x1) * max(0, ortak_y2 - ortak_y1)
    if ortak == 0:
        return 0.0
    alan_a = max(1, a["x2"] - a["x1"]) * max(1, a["y2"] - a["y1"])
    alan_b = max(1, b["x2"] - b["x1"]) * max(1, b["y2"] - b["y1"])
    return ortak / (alan_a + alan_b - ortak)


def _uzamsal_tekrarlari_temizle(metinler: list[dict]) -> list[dict]:
    """Örtüşen OCR parçalarının aynı konumdaki tekrarlarını kaldırır."""
    benzersiz: list[dict] = []
    for metin in sorted(metinler, key=lambda x: x["score"], reverse=True):
        tekrar = any(
            metin["text"].casefold() == mevcut["text"].casefold()
            and _kutu_iou(metin["bbox"], mevcut["bbox"]) >= 0.35
            for mevcut in benzersiz
        )
        if not tekrar:
            benzersiz.append(metin)
    return sorted(
        benzersiz,
        key=lambda x: (x["bbox"]["y1"], x["bbox"]["x1"]),
    )


def ocr_calistir(gorsel: np.ndarray) -> list[dict]:
    if gorsel is None or gorsel.size == 0:
        return []

    parcalar = _ocr_parcalari(gorsel)
    metinler: list[dict] = []
    with _ocr_lock:
        for parca, x_ofset, y_ofset in parcalar:
            metinler.extend(
                ocr_metinleri_topla(
                    list(ocr.predict(parca)),
                    x_ofset=x_ofset,
                    y_ofset=y_ofset,
                )
            )

    return _uzamsal_tekrarlari_temizle(metinler)


def ocr_metinleri_topla(
    ocr_result: list,
    min_score: float = OCR_MIN_SCORE,
    x_ofset: int = 0,
    y_ofset: int = 0,
) -> list[dict]:
    metinler: list[dict] = []
    for item in ocr_result or []:
        texts = item.get("rec_texts", [])
        scores = item.get("rec_scores", [])
        boxes = item.get("rec_boxes", [])
        for sira, (text, score) in enumerate(zip(texts, scores)):
            temiz_metin = str(text).strip()
            guven = float(score)
            if guven >= min_score and len(temiz_metin) > 1:
                if sira < len(boxes):
                    x1, y1, x2, y2 = (int(v) for v in boxes[sira])
                else:
                    x1 = y1 = x2 = y2 = 0
                metinler.append(
                    {
                        "text": temiz_metin,
                        "score": round(guven, 2),
                        "bbox": {
                            "x1": x1 + x_ofset,
                            "y1": y1 + y_ofset,
                            "x2": x2 + x_ofset,
                            "y2": y2 + y_ofset,
                        },
                    }
                )
    return metinler
