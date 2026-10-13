import unittest

from bill_field_extractor import fatura_alanlarini_cikar, turkce_sayiyi_cevir


def ocr(text, x1, y1, x2, y2, score=0.98):
    return {
        "text": text,
        "score": score,
        "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
    }


class FaturaAlanCikarmaTesti(unittest.TestCase):
    def test_bes_basamakli_endeks_ucte_kesilmez(self):
        self.assertEqual(turkce_sayiyi_cevir("20621,288"), 20621.288)

    def test_enerjisa_birlesik_guc_satiri(self):
        metinler = [
            ocr("ENERJISA", 10, 10, 120, 35),
            ocr("Çarpan/Demand/Anl. Gücü", 10, 100, 270, 130),
            ocr("1,000/-/3,000", 300, 100, 460, 130),
            ocr("Dönem Tüketimi", 10, 200, 190, 230),
            ocr("246,186 kWh", 300, 200, 440, 230),
            ocr(
                "Tüketici Grubu: Mesken Tek Zamanlı (Alçak Gerilim)",
                10,
                300,
                600,
                330,
            ),
        ]
        sonuc = fatura_alanlarini_cikar(metinler, 1000, 1400)
        self.assertEqual(sonuc["ozet"]["sozlesme_gucu_kw"], 3.0)
        self.assertEqual(sonuc["ozet"]["carpan"], 1.0)
        self.assertIsNone(sonuc["ozet"]["demand_kw"])
        self.assertEqual(sonuc["ozet"]["donem_tuketimi_kwh"], 246.186)
        self.assertEqual(
            sonuc["ozet"]["tarife"], "mesken_tek_zamanli_alcak_gerilim"
        )
        self.assertFalse(sonuc["manuel_giris_gerekli"])

    def test_ayri_yazilmis_sozlesme_gucu(self):
        metinler = [
            ocr("Sözleşme Gücü", 10, 100, 190, 130),
            ocr("5,00 kW", 230, 100, 330, 130),
            ocr("Toplam Tüketim", 10, 200, 190, 230),
            ocr("185,20 kWh", 230, 200, 360, 230),
            ocr("Abone Grubu: Mesken Çok Zamanlı", 10, 300, 450, 330),
        ]
        sonuc = fatura_alanlarini_cikar(metinler, 1000, 1400)
        self.assertEqual(sonuc["ozet"]["sozlesme_gucu_kw"], 5.0)
        self.assertEqual(sonuc["ozet"]["donem_tuketimi_kwh"], 185.2)
        self.assertEqual(sonuc["ozet"]["tarife"], "mesken_cok_zamanli")

    def test_ayri_ocr_kutularindaki_tuketici_grubu_ve_ag(self):
        metinler = [
            ocr("Tüketici Grubu", 50, 400, 190, 430),
            ocr("MESKEN A G Tek Terim Tek Zamanlı", 230, 400, 550, 430),
        ]
        sonuc = fatura_alanlarini_cikar(metinler, 640, 1300)
        self.assertEqual(
            sonuc["ozet"]["tarife"], "mesken_tek_zamanli_alcak_gerilim"
        )
        self.assertEqual(
            sonuc["alanlar"]["tuketici_grubu"]["yontem"], "etiket_sag_komsu"
        )

    def test_uzak_mesken_ifadesi_tuketici_grubuna_baglanmaz(self):
        metinler = [
            ocr("Tüketici Grubu", 50, 400, 190, 430),
            ocr("MESKEN A G Tek Terim Tek Zamanlı", 230, 700, 550, 730),
        ]
        sonuc = fatura_alanlarini_cikar(metinler, 640, 1300)
        self.assertNotIn("tarife", sonuc["ozet"])

    def test_okunamayan_birlesik_guc_alaninda_yakin_sayi_kullanilmaz(self):
        metinler = [
            ocr("'arpan/Demand/Anl.Gücü", 10, 100, 270, 130),
            ocr("024", 280, 100, 330, 130),
        ]
        sonuc = fatura_alanlarini_cikar(metinler, 1000, 1400)
        self.assertNotIn("sozlesme_gucu_kw", sonuc["ozet"])
        self.assertIn("sozlesme_gucu_kw", sonuc["manuel_giris_alanlari"])

    def test_ilk_harfi_dusen_carpan_etiketinden_anlasma_gucu(self):
        metinler = [
            ocr("'arpan/Demand/Anl.Gücü", 38, 1146, 205, 1171, 0.97),
            ocr("1,000/-/6,408", 746, 1150, 834, 1168, 0.97),
        ]
        sonuc = fatura_alanlarini_cikar(metinler, 900, 1400)
        self.assertEqual(sonuc["ozet"]["sozlesme_gucu_kw"], 6.408)
        self.assertEqual(sonuc["ozet"]["carpan"], 1.0)
        self.assertIsNone(sonuc["ozet"]["demand_kw"])
        self.assertEqual(
            sonuc["alanlar"]["sozlesme_gucu_kw"]["ham_deger"],
            "1,000/-/6,408",
        )
        self.assertFalse(sonuc["manuel_giris_gerekli"])
        self.assertIn("donem_tuketimi_kwh", sonuc["opsiyonel_dogrulama_alanlari"])

    def test_bitisik_carpan_demand_etiketi_ve_bosluklu_uclu_deger(self):
        metinler = [
            ocr("CarpanDemand,An Guco", 10, 100, 220, 125, 0.94),
            ocr("1.00/5 588/5.01", 230, 100, 385, 125, 0.94),
        ]
        sonuc = fatura_alanlarini_cikar(metinler, 600, 800)
        self.assertEqual(sonuc["ozet"]["sozlesme_gucu_kw"], 5.01)

    def test_demand_ocr_icinde_bolundugunde_uclu_deger(self):
        metinler = [
            ocr("Çarpan/Dem andiAnlaşma Gücü", 10, 100, 220, 125, 0.94),
            ocr("1.0/6.576/7.13", 230, 100, 385, 125, 0.94),
        ]
        sonuc = fatura_alanlarini_cikar(metinler, 600, 800)
        self.assertEqual(sonuc["ozet"]["sozlesme_gucu_kw"], 7.13)

    def test_yalniz_carpan_demand_etiketi_guc_sanilmaz(self):
        metinler = [
            ocr("CarpanDemand", 10, 100, 220, 125),
            ocr("1.00/5 588/5.01", 230, 100, 385, 125),
        ]
        sonuc = fatura_alanlarini_cikar(metinler, 600, 800)
        self.assertNotIn("sozlesme_gucu_kw", sonuc["ozet"])

    def test_etiket_kaniti_olmadan_uclu_sayi_guc_sanilmaz(self):
        metinler = [
            ocr("'arpan/Demand", 10, 100, 180, 130),
            ocr("1,000/-/6,408", 200, 100, 350, 130),
        ]
        sonuc = fatura_alanlarini_cikar(metinler, 1000, 1400)
        self.assertNotIn("sozlesme_gucu_kw", sonuc["ozet"])

    def test_sozlesme_gucu_ayni_ocr_kutusundaysa_seri_kodu_kullanilmaz(self):
        metinler = [
            ocr("Sözleşme Gücü : 6,09", 10, 100, 260, 130),
            ocr("EIC : 40Z000006029874K", 270, 100, 520, 130),
        ]
        sonuc = fatura_alanlarini_cikar(metinler, 1000, 1400)
        self.assertEqual(sonuc["ozet"]["sozlesme_gucu_kw"], 6.09)
        self.assertEqual(
            sonuc["alanlar"]["sozlesme_gucu_kw"]["yontem"],
            "satir_ici_sozlesme_gucu",
        )

    def test_sonraki_okuma_donemini_fatura_donemi_sanmaz(self):
        metinler = [
            ocr("Sonraki Okuma Dönemi", 10, 100, 240, 130),
            ocr("05.2026", 300, 100, 390, 130),
            ocr("Toplam", 10, 200, 100, 230),
            ocr("2.982,186 kWh", 230, 200, 390, 230),
        ]
        sonuc = fatura_alanlarini_cikar(metinler, 1000, 1400)
        self.assertNotIn("fatura_donemi", sonuc["ozet"])
        self.assertNotIn("donem_tuketimi_kwh", sonuc["ozet"])
        self.assertTrue(sonuc["manuel_giris_gerekli"])

    def test_endeks_farkini_okuma_gunuyle_karistirmaz(self):
        metinler = [
            ocr("Okuma (Gün)", 144, 351, 542, 456),
            ocr("30", 2092, 378, 2177, 456),
            ocr("Tek Zaman (Endeks)", 144, 438, 752, 549),
            ocr("246,186", 1930, 461, 2176, 546),
        ]
        sonuc = fatura_alanlarini_cikar(metinler, 2400, 1100)
        self.assertEqual(sonuc["ozet"]["donem_tuketimi_kwh"], 246.186)

    def test_fatura_ortalamasini_yillik_ortalamaya_tercih_eder(self):
        metinler = [
            ocr("Fatura Ort. Tüketim", 700, 100, 1000, 180),
            ocr("20.04.202", 300, 220, 550, 290),
            ocr("8,206", 780, 220, 930, 290),
            ocr("Günlük Ortalama", 700, 700, 1000, 780),
            ocr("7,706 (kWh)", 780, 820, 1000, 890),
        ]
        sonuc = fatura_alanlarini_cikar(metinler, 1400, 1200)
        self.assertEqual(sonuc["ozet"]["gunluk_ortalama_kwh"], 8.206)

    def test_reaktif_tuketim_ve_kademe_sayisi_donem_tuketimi_olmaz(self):
        metinler = [
            ocr("Endüktif Reaktif Tüketim", 10, 100, 220, 130),
            ocr("Tek Zamanlı (Kademe 1)", 230, 100, 450, 130),
        ]
        sonuc = fatura_alanlarini_cikar(metinler, 1000, 1400)
        self.assertNotIn("donem_tuketimi_kwh", sonuc["ozet"])

    def test_kademeli_faturada_tek_aktif_satiri_toplam_sanilmaz(self):
        metinler = [
            ocr("DÜŞÜK KADEME", 10, 60, 170, 90),
            ocr("Aktif Tüketim", 10, 100, 190, 130),
            ocr("232,000", 230, 100, 330, 130),
            ocr("YÜKSEK KADEME", 10, 160, 170, 190),
        ]
        sonuc = fatura_alanlarini_cikar(metinler, 1000, 1400)
        self.assertNotIn("donem_tuketimi_kwh", sonuc["ozet"])
        self.assertIn("donem_tuketimi_kwh", sonuc["opsiyonel_dogrulama_alanlari"])

    def test_endeks_tablosunda_ilk_endeks_tuketim_sanilmaz(self):
        metinler = [
            ocr("Endeks Bilgileri", 10, 50, 220, 80),
            ocr("Toplam Tüketim (kWh)", 10, 100, 220, 130),
            ocr("20621,288", 230, 100, 330, 130),
            ocr("21174,215", 350, 100, 450, 130),
            ocr("552,927", 470, 100, 560, 130),
        ]
        sonuc = fatura_alanlarini_cikar(metinler, 1000, 1400)
        self.assertNotIn("donem_tuketimi_kwh", sonuc["ozet"])
        self.assertIn("donem_tuketimi_kwh", sonuc["opsiyonel_dogrulama_alanlari"])


if __name__ == "__main__":
    unittest.main()
