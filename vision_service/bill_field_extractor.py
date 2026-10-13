from __future__ import annotations

import re
import unicodedata
from statistics import median
from typing import Callable

from rapidfuzz import fuzz


SIRKET_IPUCLARI = {
    "enerjisa": ("ENERJISA", "BASKENT EPSAS", "TOROSLAR EPSAS"),
    "ck_enerji": ("CK ENERJI", "CK BOGAZICI", "CK AKDENIZ", "CK CAMLIBEL"),
    "gediz": ("GEDIZ ELEKTRIK", "GEDIZ PERAKENDE"),
    "aydem": ("AYDEM",),
    "sepas": ("SEPAS",),
    "uludag": ("ULUDAG ELEKTRIK", "LIMAK ENERJI"),
    "dicle": ("DICLE ELEKTRIK",),
    "akedas": ("AKEDAS",),
}

ETIKETLER = {
    "sozlesme_gucu_kw": (
        "SOZLESME GUCU",
        "ANLASMA GUCU",
        "ANL GUCU",
        "ABONELIK GUCU",
        "SOZ GUCU",
    ),
    "odenecek_tutar_tl": ("ODENECEK TUTAR", "ODENECEK"),
    "gunluk_ortalama_kwh": (
        "FATURA ORT TUKETIM",
        "GUNLUK ORTALAMA",
        "ORTALAMA TUKETIM",
    ),
    "donem_tuketimi_kwh": (
        "DONEM TUKETIMI",
        "FATURA TUKETIMI",
        "TOPLAM TUKETIM",
        "AKTIF TUKETIM",
        "TEK ZAMAN ENDEKS",
    ),
    "tuketici_grubu": ("TUKETICI GRUBU", "ABONE GRUBU", "TARIFE GRUBU"),
    "fatura_donemi": ("FATURA DONEMI",),
    "son_odeme_tarihi": ("SON ODEME TARIHI", "SON ODEME"),
    "sayac_seri_no": ("SAYAC SERI", "SYC MRK SERI", "SAYAC MARKA SERI"),
    "sayac_tipi": ("SAYAC TIPI",),
}

SAYI_DESENI = (
    r"[-+]?(?:\d{1,3}(?:[. ]\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?)(?![\d.,])"
)


def metni_normalize_et(metin: str) -> str:
    metin = metin.upper().replace("İ", "I").replace("Ş", "S")
    metin = metin.replace("Ü", "U").replace("Ö", "O").replace("Ç", "C")
    metin = metin.replace("Ğ", "G")
    metin = "".join(
        karakter
        for karakter in unicodedata.normalize("NFKD", metin)
        if not unicodedata.combining(karakter)
    )
    return re.sub(r"\s+", " ", metin).strip()


def turkce_sayiyi_cevir(metin: str) -> float | None:
    eslesme = re.search(SAYI_DESENI, metin.replace("₺", ""))
    if not eslesme:
        return None
    deger = eslesme.group(0).replace(" ", "")
    if "," in deger:
        deger = deger.replace(".", "").replace(",", ".")
    elif deger.count(".") > 1:
        deger = deger.replace(".", "")
    try:
        return float(deger)
    except ValueError:
        return None


def _merkez(kutu: dict) -> tuple[float, float]:
    return ((kutu["x1"] + kutu["x2"]) / 2, (kutu["y1"] + kutu["y2"]) / 2)


def _kutu_birlestir(kutular: list[dict]) -> dict:
    return {
        "x1": min(k["x1"] for k in kutular),
        "y1": min(k["y1"] for k in kutular),
        "x2": max(k["x2"] for k in kutular),
        "y2": max(k["y2"] for k in kutular),
    }


def _satirlari_olustur(metinler: list[dict]) -> list[dict]:
    koordinatli = [m for m in metinler if m.get("bbox")]
    if not koordinatli:
        return []
    yukseklikler = [
        max(1, m["bbox"]["y2"] - m["bbox"]["y1"]) for m in koordinatli
    ]
    tolerans = max(8.0, median(yukseklikler) * 0.65)
    gruplar: list[list[dict]] = []
    for metin in sorted(koordinatli, key=lambda m: _merkez(m["bbox"])[1]):
        cy = _merkez(metin["bbox"])[1]
        uygun = None
        en_kisa = float("inf")
        for grup in gruplar:
            grup_y = median(_merkez(x["bbox"])[1] for x in grup)
            fark = abs(cy - grup_y)
            if fark <= tolerans and fark < en_kisa:
                uygun, en_kisa = grup, fark
        if uygun is None:
            gruplar.append([metin])
        else:
            uygun.append(metin)

    satirlar = []
    for grup in gruplar:
        sirali = sorted(grup, key=lambda m: m["bbox"]["x1"])
        satirlar.append(
            {
                "text": " ".join(m["text"] for m in sirali),
                "score": round(sum(m["score"] for m in sirali) / len(sirali), 2),
                "bbox": _kutu_birlestir([m["bbox"] for m in sirali]),
                "kaynaklar": sirali,
            }
        )
    return satirlar


def _etiket_skoru(metin: str, etiketler: tuple[str, ...]) -> float:
    normal = metni_normalize_et(metin)
    return max(fuzz.partial_ratio(etiket, normal) for etiket in etiketler) / 100


def _yakinlik_skoru(etiket: dict, aday: dict, genislik: int, yukseklik: int) -> float:
    ex, ey = _merkez(etiket["bbox"])
    ax, ay = _merkez(aday["bbox"])
    satir_yuksekligi = max(
        1,
        etiket["bbox"]["y2"] - etiket["bbox"]["y1"],
        aday["bbox"]["y2"] - aday["bbox"]["y1"],
    )
    y_farki = abs(ay - ey)
    x_farki = abs(ax - ex)

    if y_farki <= satir_yuksekligi * 1.2:
        yon_bonus = 1.0 if ax >= ex else 0.72
        return max(0.0, yon_bonus * (1 - x_farki / max(1, genislik * 0.45)))
    if ay > ey and y_farki <= yukseklik * 0.10:
        return max(0.0, 0.78 - x_farki / max(1, genislik * 0.55))
    return 0.0


def _alan_sonucu(
    deger,
    birim: str | None,
    guven: float,
    etiket: str,
    ham_deger: str,
    yontem: str,
    bbox: dict | None,
) -> dict:
    return {
        "deger": deger,
        "birim": birim,
        "guven": round(min(1.0, max(0.0, guven)), 2),
        "etiket": etiket,
        "ham_deger": ham_deger,
        "yontem": yontem,
        "bbox": bbox,
    }


def _en_iyi_etiket_deger(
    metinler: list[dict],
    etiketler: tuple[str, ...],
    genislik: int,
    yukseklik: int,
    deger_cozucu: Callable[[str], object | None],
    deger_filtresi: Callable[[str], bool] | None = None,
    etiket_filtresi: Callable[[str], bool] | None = None,
) -> tuple[dict, dict, object, float] | None:
    etiket_adaylari = [
        (m, _etiket_skoru(m["text"], etiketler))
        for m in metinler
        if _etiket_skoru(m["text"], etiketler) >= 0.72
        and (etiket_filtresi is None or etiket_filtresi(m["text"]))
    ]
    en_iyi = None
    en_iyi_skor = 0.0
    for etiket, eslesme_skoru in etiket_adaylari:
        for aday in metinler:
            if aday is etiket or not aday.get("bbox"):
                continue
            if deger_filtresi and not deger_filtresi(aday["text"]):
                continue
            deger = deger_cozucu(aday["text"])
            if deger is None:
                continue
            yakinlik = _yakinlik_skoru(etiket, aday, genislik, yukseklik)
            if yakinlik <= 0:
                continue
            skor = eslesme_skoru * 0.42 + yakinlik * 0.38 + aday["score"] * 0.20
            if skor > en_iyi_skor:
                en_iyi = (etiket, aday, deger, skor)
                en_iyi_skor = skor
    return en_iyi


def _birlesik_guc_alanini_bul(
    metinler: list[dict], satirlar: list[dict], genislik: int, yukseklik: int
) -> dict | None:
    uc_deger = re.compile(
        rf"({SAYI_DESENI})\s*/\s*(-|{SAYI_DESENI})\s*/\s*({SAYI_DESENI})"
    )
    etiketler = [
        m
        for m in metinler + satirlar
        # OCR bazen "Çarpan" sözcüğünün ilk harfini düşürüyor ("'arpan").
        # Bu tolerans yalnızca Demand ve Güç kanıtı da aynı etiketteyse geçerli.
        # Dar OCR kutularında "ÇarpanDemand" birleşebilir; başlangıç ve
        # Demand/Güç kanıtı aranır, yalnız komşu sayıdan güç türetilmez.
        if re.search(r"(?:^|[^A-Z])C?ARPAN", metni_normalize_et(m["text"]))
        and "DEMAND" in re.sub(r"[^A-Z]", "", metni_normalize_et(m["text"]))
        and "GUC" in re.sub(r"[^A-Z]", "", metni_normalize_et(m["text"]))
    ]
    for etiket in sorted(etiketler, key=lambda x: x["score"], reverse=True):
        adaylar = []
        for aday in metinler + satirlar:
            eslesme = uc_deger.search(aday["text"])
            if not eslesme:
                continue
            yakinlik = (
                1.0
                if aday is etiket
                else _yakinlik_skoru(etiket, aday, genislik, yukseklik)
            )
            if yakinlik > 0:
                adaylar.append((aday, eslesme, yakinlik))
        if not adaylar:
            continue
        aday, eslesme, yakinlik = max(
            adaylar, key=lambda x: x[2] * 0.7 + x[0]["score"] * 0.3
        )
        carpan = turkce_sayiyi_cevir(eslesme.group(1))
        demand = (
            None
            if eslesme.group(2) == "-"
            else turkce_sayiyi_cevir(eslesme.group(2))
        )
        guc = turkce_sayiyi_cevir(eslesme.group(3))
        if guc is None or not 0.5 <= guc <= 100:
            continue
        guven = etiket["score"] * 0.35 + aday["score"] * 0.30 + yakinlik * 0.35
        return {
            "sozlesme_gucu_kw": _alan_sonucu(
                guc,
                "kW",
                guven,
                etiket["text"],
                eslesme.group(0),
                "carpan_demand_anlasma_gucu",
                aday["bbox"],
            ),
            "carpan": _alan_sonucu(
                carpan,
                None,
                guven,
                etiket["text"],
                eslesme.group(0),
                "carpan_demand_anlasma_gucu",
                aday["bbox"],
            ),
            "demand_kw": _alan_sonucu(
                demand,
                "kW",
                guven,
                etiket["text"],
                eslesme.group(0),
                "carpan_demand_anlasma_gucu",
                aday["bbox"],
            ),
        }
    return None


def _basit_sayisal_alani_bul(
    alan: str,
    metinler: list[dict],
    genislik: int,
    yukseklik: int,
    birim: str,
    alt: float,
    ust: float,
    yasak_birimler: tuple[str, ...] = (),
) -> dict | None:
    def filtre(metin: str) -> bool:
        normal = metni_normalize_et(metin)
        if alan in ("sozlesme_gucu_kw", "donem_tuketimi_kwh") and not re.fullmatch(
            rf"\s*(?:{SAYI_DESENI})\s*(?:KW|KWH)?\s*", normal
        ):
            return False
        return not any(yasak in normal for yasak in yasak_birimler)

    def etiket_filtresi(metin: str) -> bool:
        normal = metni_normalize_et(metin)
        if alan == "gunluk_ortalama_kwh":
            return "GUNLUK" in normal or "ORT" in normal
        if alan == "donem_tuketimi_kwh":
            return (
                any(
                    kosul
                    for kosul in (
                        "DONEM" in normal and "TUKETIM" in normal,
                        "TOPLAM" in normal and "TUKETIM" in normal,
                        "AKTIF" in normal and "TUKETIM" in normal,
                        "TEK ZAMAN" in normal and "ENDEKS" in normal,
                        "FATURA" in normal and "TUKETIM" in normal,
                    )
                )
                and "GUNLUK" not in normal
                and "ORT" not in normal
                and "REAKTIF" not in normal
                and "ENDUKTIF" not in normal
                and "KAPASITIF" not in normal
            )
        if alan == "sozlesme_gucu_kw":
            # Çarpan/Demand/Anl. Gücü üçlü alandır. Yakınındaki tek bir
            # sayı güç kabul edilemez; üçlü değer okunamıyorsa alan boş kalır.
            return "GUC" in normal and "DEMAND" not in normal
        if alan == "odenecek_tutar_tl":
            return "ODENECEK" in normal
        return True

    bulunan = _en_iyi_etiket_deger(
        metinler,
        ETIKETLER[alan],
        genislik,
        yukseklik,
        turkce_sayiyi_cevir,
        filtre,
        etiket_filtresi,
    )
    if not bulunan:
        return None
    etiket, aday, deger, skor = bulunan
    if not alt <= float(deger) <= ust:
        return None
    return _alan_sonucu(
        deger,
        birim,
        skor,
        etiket["text"],
        aday["text"],
        "etiket_konum_birim",
        aday["bbox"],
    )


def _satir_ici_sozlesme_gucunu_bul(metinler: list[dict]) -> dict | None:
    desen = re.compile(
        rf"\b(?:SOZLESME|ANLASMA|ANL\.?|ABONELIK|SOZ)\s+GUC[U]?\s*[:=]?\s*"
        rf"({SAYI_DESENI})(?=\s|KW\b|$)"
    )
    en_iyi = None
    for metin in metinler:
        normal = metni_normalize_et(metin["text"])
        if "DEMAND" in normal:
            continue
        eslesme = desen.search(normal)
        if not eslesme:
            continue
        guc = turkce_sayiyi_cevir(eslesme.group(1))
        if guc is None or not 0.5 <= guc <= 100:
            continue
        sonuc = _alan_sonucu(
            guc,
            "kW",
            metin["score"],
            metin["text"],
            eslesme.group(1),
            "satir_ici_sozlesme_gucu",
            metin["bbox"],
        )
        if en_iyi is None or sonuc["guven"] > en_iyi["guven"]:
            en_iyi = sonuc
    return en_iyi


def _satir_ici_metni_bul(
    alan: str, satirlar: list[dict], deger_deseni: str | None = None
) -> dict | None:
    en_iyi = None
    for satir in satirlar:
        normal_satir = metni_normalize_et(satir["text"])
        if alan == "fatura_donemi" and "FATURA" not in normal_satir:
            continue
        if alan == "son_odeme_tarihi" and "SON" not in normal_satir:
            continue
        skor = _etiket_skoru(satir["text"], ETIKETLER[alan])
        if skor < 0.75:
            continue
        normal = metni_normalize_et(satir["text"])
        if deger_deseni:
            eslesme = re.search(deger_deseni, satir["text"])
            if not eslesme:
                continue
            deger = eslesme.group(0)
        elif ":" in satir["text"]:
            deger = satir["text"].split(":", 1)[1].strip()
        else:
            continue
        if not deger or metni_normalize_et(deger) == normal:
            continue
        aday = _alan_sonucu(
            deger,
            None,
            skor * satir["score"],
            satir["text"].split(":", 1)[0],
            deger,
            "satir_ici_etiket",
            satir["bbox"],
        )
        if en_iyi is None or aday["guven"] > en_iyi["guven"]:
            en_iyi = aday
    return en_iyi


def _donem_tuketimini_bul(
    metinler: list[dict], genislik: int, yukseklik: int
) -> dict | None:
    dogrudan = _basit_sayisal_alani_bul(
        "donem_tuketimi_kwh",
        metinler,
        genislik,
        yukseklik,
        "kWh",
        0.0,
        1_000_000.0,
        ("TL",),
    )
    if (
        dogrudan
        and "AKTIF TUKETIM" in metni_normalize_et(dogrudan["etiket"])
        and any("KADEME" in metni_normalize_et(m["text"]) for m in metinler)
    ):
        # Kademeli faturada tek bir Aktif Tüketim satırı toplam tüketim değildir.
        dogrudan = None
    if (
        dogrudan
        and "TOPLAM TUKETIM" in metni_normalize_et(dogrudan["etiket"])
        and "KWH" not in metni_normalize_et(dogrudan["ham_deger"])
        and any(
            kelime in metni_normalize_et(m["text"])
            for m in metinler
            for kelime in ("ENDEKS", "FARK")
        )
    ):
        # Çok sütunlu tabloda ilk veya son endeks fark değeri sanılabilir.
        dogrudan = None
    if dogrudan and "TEK ZAMAN" not in metni_normalize_et(dogrudan["etiket"]):
        return dogrudan

    for etiket in metinler:
        normal = metni_normalize_et(etiket["text"])
        if "TEK ZAMAN" not in normal or "ENDEKS" not in normal:
            continue
        _, ey = _merkez(etiket["bbox"])
        satir_yuksekligi = max(1, etiket["bbox"]["y2"] - etiket["bbox"]["y1"])
        adaylar = []
        for aday in metinler:
            ax, ay = _merkez(aday["bbox"])
            y_farki = abs(ay - ey)
            if ax <= etiket["bbox"]["x2"] or y_farki > satir_yuksekligi * 0.85:
                continue
            if re.search(r"\b\d{2}[./-]\d{2}[./-]20\d{2}\b", aday["text"]):
                continue
            deger = turkce_sayiyi_cevir(aday["text"])
            if deger is not None:
                adaylar.append((y_farki, ax, aday, deger))
        if adaylar:
            _, _, aday, deger = min(
                adaylar, key=lambda x: (x[0], -x[1])
            )
            return _alan_sonucu(
                deger,
                "kWh",
                etiket["score"] * 0.48 + aday["score"] * 0.52,
                etiket["text"],
                aday["text"],
                "tek_zaman_endeks_fark_sutunu",
                aday["bbox"],
            )
    return dogrudan


def _gunluk_ortalamayi_bul(
    metinler: list[dict], satirlar: list[dict], genislik: int, yukseklik: int
) -> dict | None:
    birincil_tekil = [
        m
        for m in metinler
        if "FATURA" in metni_normalize_et(m["text"])
        and (
            "ORT" in metni_normalize_et(m["text"])
            or "TUKETIM" in metni_normalize_et(m["text"])
        )
    ]
    birincil_satir = [
        m
        for m in satirlar
        if "FATURA" in metni_normalize_et(m["text"])
        and (
            "ORT" in metni_normalize_et(m["text"])
            or "TUKETIM" in metni_normalize_et(m["text"])
        )
    ]
    birincil = birincil_tekil or birincil_satir
    ikincil = [
        m
        for m in metinler + satirlar
        if "GUNLUK" in metni_normalize_et(m["text"])
        and "ORT" in metni_normalize_et(m["text"])
    ]
    for etiketler, oncelik in ((birincil, 1.0), (ikincil, 0.88)):
        en_iyi = None
        en_iyi_skor = 0.0
        for etiket in etiketler:
            ex, ey = _merkez(etiket["bbox"])
            for aday in metinler:
                if re.search(
                    r"\b\d{1,2}[./-]\d{1,2}[./-](?:20)?\d{2,4}\b",
                    aday["text"],
                ):
                    continue
                deger = turkce_sayiyi_cevir(aday["text"])
                if deger is None or not 0 <= deger <= 10_000:
                    continue
                yakinlik = _yakinlik_skoru(
                    etiket, aday, genislik, yukseklik
                )
                ax, ay = _merkez(aday["bbox"])
                if (
                    yakinlik <= 0
                    and ay > ey
                    and ay - ey <= yukseklik * 0.55
                    and abs(ax - ex) <= genislik * 0.14
                ):
                    yakinlik = max(0.25, 1 - (ay - ey) / (yukseklik * 0.70))
                if yakinlik <= 0:
                    continue
                yatay_uyum = max(0.0, 1 - abs(ax - ex) / max(1, genislik * 0.25))
                skor = (
                    oncelik * 0.32
                    + yakinlik * 0.28
                    + yatay_uyum * 0.20
                    + aday["score"] * 0.20
                )
                if skor > en_iyi_skor:
                    en_iyi = (etiket, aday, deger, skor)
                    en_iyi_skor = skor
        if en_iyi:
            etiket, aday, deger, skor = en_iyi
            return _alan_sonucu(
                deger,
                "kWh/gün",
                skor,
                etiket["text"],
                aday["text"],
                "fatura_ortalama_tuketim_konum",
                aday["bbox"],
            )
    return None


def _tuketici_grubunu_bul(metinler: list[dict], satirlar: list[dict]) -> dict | None:
    temel = _satir_ici_metni_bul("tuketici_grubu", satirlar)
    if not temel:
        # Bazı faturalarda etiket ve değeri OCR iki ayrı kutu olarak döndürür;
        # aynı satırdaki sağ komşuyu açık tarife kanıtıyla eşleştir.
        adaylar = []
        for etiket in metinler:
            etiket_norm = metni_normalize_et(etiket["text"])
            if not any(
                ifade in etiket_norm
                for ifade in ("TUKETICI GRUBU", "ABONE GRUBU", "TARIFE GRUBU")
            ):
                continue
            ex, ey = _merkez(etiket["bbox"])
            for deger in metinler:
                if deger is etiket:
                    continue
                normal = metni_normalize_et(deger["text"])
                if not any(k in normal for k in ("MESKEN", "SANAYI", "TICARETHANE")):
                    continue
                dx, dy = _merkez(deger["bbox"])
                satir_yuksekligi = max(
                    1,
                    etiket["bbox"]["y2"] - etiket["bbox"]["y1"],
                    deger["bbox"]["y2"] - deger["bbox"]["y1"],
                )
                etiket_genisligi = max(
                    1, etiket["bbox"]["x2"] - etiket["bbox"]["x1"]
                )
                yatay_bosluk = max(0, deger["bbox"]["x1"] - etiket["bbox"]["x2"])
                if (
                    dx <= ex
                    or abs(dy - ey) > satir_yuksekligi * 1.2
                    or yatay_bosluk > max(50, etiket_genisligi * 3)
                ):
                    continue
                yakinlik = 1 - abs(dy - ey) / (satir_yuksekligi * 1.2)
                adaylar.append((yakinlik, deger["score"], etiket, deger))
        if not adaylar:
            return None
        yakinlik, _, etiket, deger = max(adaylar, key=lambda x: (x[0], x[1]))
        temel = _alan_sonucu(
            deger["text"],
            None,
            etiket["score"] * 0.35 + deger["score"] * 0.45 + yakinlik * 0.20,
            etiket["text"],
            deger["text"],
            "etiket_sag_komsu",
            _kutu_birlestir([etiket["bbox"], deger["bbox"]]),
        )
    kutu = temel["bbox"]
    _, temel_y = _merkez(kutu)
    yukseklik = max(1, kutu["y2"] - kutu["y1"])
    devamlar = []
    for satir in satirlar:
        if satir["bbox"] == kutu:
            continue
        sx, sy = _merkez(satir["bbox"])
        if not (temel_y < sy <= temel_y + yukseklik * 2.8):
            continue
        normal = metni_normalize_et(satir["text"])
        if any(
            ifade in normal
            for ifade in ("MESKEN", "ALCAK GERILIM", "SERBEST TUK", "ZAMANLI")
        ):
            devamlar.append((sy, satir["text"]))
    if devamlar:
        ek = " ".join(text for _, text in sorted(devamlar))
        temel["deger"] = f"{temel['deger']} {ek}".strip()
        temel["ham_deger"] = temel["deger"]
    return temel


def _tarifeyi_siniflandir(tuketici_grubu: dict | None) -> dict | None:
    if not tuketici_grubu:
        return None
    normal = metni_normalize_et(str(tuketici_grubu["deger"]))
    parcalar = []
    if "MESKEN" in normal:
        parcalar.append("mesken")
    if "SANAYI" in normal:
        parcalar.append("sanayi")
    if "TICARETHANE" in normal:
        parcalar.append("ticarethane")
    if "TEK ZAMAN" in normal:
        parcalar.append("tek_zamanli")
    elif "COK ZAMAN" in normal or "UC ZAMAN" in normal:
        parcalar.append("cok_zamanli")
    if "ALCAK GERILIM" in normal or re.search(r"\bA\s*G\b", normal):
        parcalar.append("alcak_gerilim")
    if not parcalar:
        return None
    return _alan_sonucu(
        "_".join(parcalar),
        None,
        tuketici_grubu["guven"],
        tuketici_grubu["etiket"],
        tuketici_grubu["ham_deger"],
        "tuketici_grubu_siniflandirma",
        tuketici_grubu["bbox"],
    )


def fatura_alanlarini_cikar(
    ocr_metinleri: list[dict], gorsel_genisligi: int, gorsel_yuksekligi: int
) -> dict:
    metinler = [m for m in ocr_metinleri if m.get("bbox")]
    satirlar = _satirlari_olustur(metinler)
    tam_metin = metni_normalize_et(" ".join(m["text"] for m in metinler))

    sirket = "bilinmiyor"
    sirket_guveni = 0.0
    for ad, ipuclari in SIRKET_IPUCLARI.items():
        skor = max(fuzz.partial_ratio(ipucu, tam_metin) for ipucu in ipuclari) / 100
        if skor > sirket_guveni and skor >= 0.78:
            sirket, sirket_guveni = ad, skor

    alanlar: dict[str, dict] = {}
    birlesik = _birlesik_guc_alanini_bul(
        metinler, satirlar, gorsel_genisligi, gorsel_yuksekligi
    )
    if birlesik:
        alanlar.update(birlesik)
    else:
        guc = _satir_ici_sozlesme_gucunu_bul(metinler)
        if guc is None:
            guc = _basit_sayisal_alani_bul(
                "sozlesme_gucu_kw",
                metinler,
                gorsel_genisligi,
                gorsel_yuksekligi,
                "kW",
                0.5,
                100.0,
                ("KWH", "TL"),
            )
        if guc:
            alanlar["sozlesme_gucu_kw"] = guc

    for alan, birim, alt, ust, yasaklar in (
        ("odenecek_tutar_tl", "TL", 0.0, 1_000_000.0, ("KWH", "KW")),
    ):
        sonuc = _basit_sayisal_alani_bul(
            alan,
            metinler,
            gorsel_genisligi,
            gorsel_yuksekligi,
            birim,
            alt,
            ust,
            yasaklar,
        )
        if sonuc:
            alanlar[alan] = sonuc

    gunluk_ortalama = _gunluk_ortalamayi_bul(
        metinler, satirlar, gorsel_genisligi, gorsel_yuksekligi
    )
    if gunluk_ortalama:
        alanlar["gunluk_ortalama_kwh"] = gunluk_ortalama

    donem_tuketimi = _donem_tuketimini_bul(
        metinler, gorsel_genisligi, gorsel_yuksekligi
    )
    if donem_tuketimi:
        alanlar["donem_tuketimi_kwh"] = donem_tuketimi

    tuketici_grubu = _tuketici_grubunu_bul(metinler, satirlar)
    if tuketici_grubu:
        alanlar["tuketici_grubu"] = tuketici_grubu
        tarife = _tarifeyi_siniflandir(tuketici_grubu)
        if tarife:
            alanlar["tarife"] = tarife

    donem = _satir_ici_metni_bul(
        "fatura_donemi", satirlar, r"\b(?:0[1-9]|1[0-2])[/.-]20\d{2}\b"
    )
    if donem:
        alanlar["fatura_donemi"] = donem
    son_odeme = _satir_ici_metni_bul(
        "son_odeme_tarihi", satirlar, r"\b\d{2}[./-]\d{2}[./-]20\d{2}\b"
    )
    if son_odeme:
        alanlar["son_odeme_tarihi"] = son_odeme

    for alan in ("sayac_seri_no", "sayac_tipi"):
        sonuc = _satir_ici_metni_bul(alan, satirlar)
        if sonuc:
            alanlar[alan] = sonuc

    # KDS V1.1: tüketim ve tarife yardımcı alanlar; eksikleri teknik ön
    # değerlendirmeyi bloke etmez, fakat isteğe bağlı doğrulanabilir.
    kritik = ("sozlesme_gucu_kw",)
    opsiyonel = ("donem_tuketimi_kwh", "tarife")
    eksik = [alan for alan in kritik if alan not in alanlar]
    eksik_opsiyonel = [alan for alan in opsiyonel if alan not in alanlar]
    dusuk_guven = [
        alan for alan, sonuc in alanlar.items() if sonuc.get("guven", 0) < 0.70
    ]
    manuel_alanlar = sorted(set(eksik + [a for a in dusuk_guven if a in kritik]))
    opsiyonel_dogrulama = sorted(
        set(eksik_opsiyonel + [a for a in dusuk_guven if a in opsiyonel])
    )
    ozet = {alan: sonuc["deger"] for alan, sonuc in alanlar.items()}
    return {
        "sirket": {"deger": sirket, "guven": round(sirket_guveni, 2)},
        "ozet": ozet,
        "alanlar": alanlar,
        "eksik_kritik_alanlar": eksik,
        "eksik_opsiyonel_alanlar": eksik_opsiyonel,
        "dusuk_guvenli_alanlar": dusuk_guven,
        "manuel_giris_gerekli": bool(manuel_alanlar),
        "manuel_giris_alanlari": manuel_alanlar,
        "opsiyonel_dogrulama_alanlari": opsiyonel_dogrulama,
        "yontem": "koordinatli_ocr_etiket_konum_sablon_dogrulama",
    }
