import unittest

from home_input import kds_ev_girdisi_olustur


def fatura_alanlari(guven=0.91):
    return {
        "fatura_bulundu": True,
        "tespit_yontemi": "tam_gorsel_ocr",
        "ocr_metinleri": [{"text": "Kişisel veri"}],
        "fatura_bilgileri": {
            "alanlar": {
                "sozlesme_gucu_kw": {"deger": 3.0, "guven": guven},
                "donem_tuketimi_kwh": {"deger": 246.186, "guven": 1.0},
                "gunluk_ortalama_kwh": {"deger": 8.206, "guven": 0.94},
                "tarife": {
                    "deger": "mesken_tek_zamanli_alcak_gerilim",
                    "guven": 0.96,
                },
            },
            "manuel_giris_alanlari": [],
        },
    }


class KdsEvGirdisiTesti(unittest.TestCase):
    def test_dogrulanmis_alanlar_ve_kisisel_veri_yok(self):
        sonuc = kds_ev_girdisi_olustur(
            {"sayac_bulundu": True, "faz": "trifaz", "ocr_metinleri": []},
            fatura_alanlari(),
        )
        self.assertEqual(sonuc["home"]["faz"], "trifaz")
        self.assertEqual(sonuc["home"]["sozlesme_gucu_kw"], 3.0)
        self.assertEqual(sonuc["durum"], "kullanici_onayi_gerekli")
        self.assertFalse(sonuc["kdsye_dogrudan_aktarilabilir"])
        self.assertIn("sozlesme_gucu_kw", sonuc["onay_bekleyen_alanlar"])
        self.assertNotIn("Kişisel veri", str(sonuc))

    def test_dusuk_guvenli_deger_kdsye_tasinmaz(self):
        sonuc = kds_ev_girdisi_olustur(
            {"sayac_bulundu": True, "faz": "monofaz"}, fatura_alanlari(0.6)
        )
        self.assertIsNone(sonuc["home"]["sozlesme_gucu_kw"])
        self.assertIn("sozlesme_gucu_kw", sonuc["manuel_dogrulama_alanlari"])

    def test_belirsiz_gorseller_manuel_dogrulamaya_gider(self):
        sonuc = kds_ev_girdisi_olustur(
            {"sayac_bulundu": False}, {"fatura_bulundu": False}
        )
        self.assertEqual(sonuc["home"]["faz"], "belirsiz")
        self.assertEqual(
            sonuc["manuel_dogrulama_alanlari"], ["faz", "sozlesme_gucu_kw"]
        )
        self.assertEqual(sonuc["durum"], "manuel_dogrulama_gerekli")

    def test_opsiyonel_fatura_alanlari_eksikse_zorunlu_manuel_giris_yok(self):
        fatura = fatura_alanlari()
        for alan in ("donem_tuketimi_kwh", "gunluk_ortalama_kwh", "tarife"):
            fatura["fatura_bilgileri"]["alanlar"].pop(alan)
        sonuc = kds_ev_girdisi_olustur(
            {"sayac_bulundu": True, "faz": "trifaz"}, fatura
        )
        self.assertEqual(sonuc["manuel_dogrulama_alanlari"], [])
        self.assertEqual(sonuc["durum"], "kullanici_onayi_gerekli")
        self.assertIsNone(sonuc["home"]["donem_tuketimi_kwh"])

    def test_sayisal_olmayan_ve_sonsuz_guvenli_degerler_tasinmaz(self):
        fatura = fatura_alanlari()
        fatura["fatura_bilgileri"]["alanlar"]["sozlesme_gucu_kw"]["deger"] = "40Z000"
        fatura["fatura_bilgileri"]["alanlar"]["donem_tuketimi_kwh"]["guven"] = float("nan")
        sonuc = kds_ev_girdisi_olustur(
            {"sayac_bulundu": True, "faz": "trifaz"}, fatura
        )
        self.assertIsNone(sonuc["home"]["sozlesme_gucu_kw"])
        self.assertIsNone(sonuc["home"]["donem_tuketimi_kwh"])
        self.assertEqual(sonuc["manuel_dogrulama_alanlari"], ["sozlesme_gucu_kw"])


if __name__ == "__main__":
    unittest.main()
