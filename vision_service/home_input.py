"""Sayaç ve fatura analizlerinden KDS için veri-minimum ev girdisi üretir."""

from __future__ import annotations

import math
from typing import Any


KRITIK_FATURA_ALANLARI = ("sozlesme_gucu_kw",)
HOME_ALANLARI = (
    "sozlesme_gucu_kw",
    "donem_tuketimi_kwh",
    "gunluk_ortalama_kwh",
    "tarife",
)
MIN_ALAN_GUVENI = 0.70
SAYISAL_ALAN_ARALIKLARI = {
    "sozlesme_gucu_kw": (0.5, 100.0),
    "donem_tuketimi_kwh": (0.0, 1_000_000.0),
    "gunluk_ortalama_kwh": (0.0, 10_000.0),
}


def _kanitli_fatura_adayi(bilgiler: dict[str, Any], alan: str) -> Any:
    """OCR kanıtı yetersizse değeri taşıma; dönen değer kullanıcı onayı değildir."""
    if alan in bilgiler.get("manuel_giris_alanlari", []):
        return None
    kanit = bilgiler.get("alanlar", {}).get(alan)
    if not isinstance(kanit, dict):
        return None
    if kanit.get("deger") is None:
        return None
    try:
        guven = float(kanit.get("guven", 0))
    except (TypeError, ValueError):
        return None
    if not math.isfinite(guven) or guven < MIN_ALAN_GUVENI:
        return None
    deger = kanit["deger"]
    if alan in SAYISAL_ALAN_ARALIKLARI:
        if isinstance(deger, bool) or not isinstance(deger, (int, float)):
            return None
        alt, ust = SAYISAL_ALAN_ARALIKLARI[alan]
        if not math.isfinite(deger) or not alt <= deger <= ust:
            return None
    elif alan == "tarife" and (not isinstance(deger, str) or not deger.strip()):
        return None
    return deger


def kds_ev_girdisi_olustur(sayac: dict[str, Any], fatura: dict[str, Any]) -> dict:
    """Ham OCR veya kişisel fatura metinlerini yanıtın içine koymaz."""
    sayac_bulundu = sayac.get("sayac_bulundu") is True
    faz = sayac.get("faz") if sayac_bulundu else None
    if faz not in {"monofaz", "trifaz"}:
        faz = "belirsiz"

    fatura_bulundu = fatura.get("fatura_bulundu") is True
    bilgiler = fatura.get("fatura_bilgileri") if fatura_bulundu else None
    if not isinstance(bilgiler, dict):
        bilgiler = {}

    home = {"faz": faz}
    for alan in HOME_ALANLARI:
        home[alan] = _kanitli_fatura_adayi(bilgiler, alan)

    dogrulanacak = []
    if faz == "belirsiz":
        dogrulanacak.append("faz")
    dogrulanacak.extend(
        alan for alan in KRITIK_FATURA_ALANLARI if home[alan] is None
    )
    onay_bekleyen = [
        alan
        for alan, deger in home.items()
        if deger is not None and deger != "belirsiz"
    ]

    return {
        "home": home,
        "durum": "manuel_dogrulama_gerekli" if dogrulanacak else "kullanici_onayi_gerekli",
        "manuel_dogrulama_alanlari": dogrulanacak,
        "onay_bekleyen_alanlar": onay_bekleyen,
        "kdsye_dogrudan_aktarilabilir": False,
        "kaynak_durumu": {
            "sayac_bulundu": sayac_bulundu,
            "fatura_bulundu": fatura_bulundu,
            "fatura_tespit_yontemi": fatura.get("tespit_yontemi"),
        },
        "uyari": (
            "Otomatik değerler kullanıcı tarafından doğrulanmadan KDS'ye kesin girdi olarak aktarılmamalıdır. Sözleşme gücü tesisatın güvenli şarj gücünü veya kurulum uygunluğunu kanıtlamaz."
        ),
    }
