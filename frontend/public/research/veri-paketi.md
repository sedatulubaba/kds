# KDS Veri Paketi V1 Raporu

**Hazırlanma tarihi:** 2026-09-27

## 1. Paket ve veri tanesi

Paket dört girdi nesnesi (`home`, `vehicle`, `user`, `charger`), iki çekirdek katalog, bir alan rol matrisi ve üç açıklayıcı sözlük/sözleşme içerir. Araçta bir satır tek bir araç varyantı, wallboxta bir satır tek bir ürün + güç + bağlantı + pazar varyantıdır. Paket karar algoritması, ağırlık, puan, sıralama veya ürün önerisi içermez.

## 2. Kontroller

- Kayıt sayısı, alan sırası ve benzersiz kimlikler.
- Kaynak veri ile çekirdek dosyaya taşınan alanların birebir eşitliği.
- `null`, `Bilinmiyor`, `Hayır` ve boş string ayrımı.
- Faz desteği ile koşullu güç/akım alanlarının tutarlılığı.
- KDS kullanılabilirlik bayrağının belgelenmiş minimum alan kuralıyla uyumu.
- Wallbox fiyatı varsa fiyat tarihinin bulunması.
- Renault Twingo ve MG MGS5 genel/faza özel güç çelişkisinin uyarı olarak korunması.
- Kaynak JSON dosyalarının SHA-256 özetiyle değiştirilmediğinin doğrulanması.

## 3. Ev tarafı

### Hazır otomatik alanlar

- `faz`: sayaç OCR'ından `monofaz`, `trifaz` veya `belirsiz`.
- `sozlesme_gucu_kw`: faturadan; sözleşmesel güçtür, güvenli azami şarj gücü değildir.
- `donem_tuketimi_kwh`: faturada basılı dönem tüketimidir, anlık boş güç değildir.
- `gunluk_ortalama_kwh`: faturada basılıysa alınır, anlık boş güç değildir.
- `tarife`: tüketici grubu metninden normalize edilir.

### Henüz eksik veya yapılandırılmamış alanlar

- Sayaç `gerilim_v` ve `azami_akim_a`: OCR'da görülebilir fakat otomatik standart alan değildir.
- `ana_sigorta_a`, `pano_uygunluk_durumu`, `ayrilmis_sarj_hatti_var_mi`, `kablo_kesiti_mm2`, `hat_uzunlugu_m`, `rcd_koruma_durumu`, `topraklama_uygunluk_durumu`: mevcut sistem üretmez; kullanıcı/elektrikçi girdisi ve saha incelemesi gerekir.

## 4. Araç çekirdek veri seti

- Kayıt: **100**.
- Teknik AC eşleşmesine hazır: **100/100**.
- WLTP tüketimi eksik: **24/100**; bu kayıtlar teknik eşleşmeye devam edebilir, günlük enerji ihtiyacı hesaplanamaz.
- Belgelenmiş genel/faza özel AC güç çelişkisi: **2** kayıt.
- `ac_azami_guc_kw` çekirdeğe taşınmadı. Faz eşleşmesinde yalnız faza özel güç/akım alanları taşındı.
- Twingo ve MGS5 kaynak değerleri değiştirilmedi; çelişki `kds_veri_uyarilari` içinde görünürdür.

## 5. Wallbox çekirdek veri seti

- Kayıt: **10**.
- En az bir doğrulanmış faz yoluyla temel teknik eşleşmeye hazır: **10/10**.
- Bu kullanılabilirlik kurulum onayı değildir; ABB Terra AC kaydında tek faz desteği Bilinmiyor olduğundan monofaz eşleşme ayrıca doğrulanmalıdır.
- IEC/CE/OCPP/Wi-Fi/Bluetooth/RFID/V2X alanları çekirdek dosyaya taşınmadı.

### En yoğun eksik wallbox çekirdek alanları

Bu tablo koşullu olarak uygulanmayan `null` alanları (örneğin soketli üründe kablo uzunluğu) eksik saymaz; `kds_eksik_alanlar` listelerindeki eyleme dönük eksikleri sayar.

| Alan | Eksik ürün | Oran | Etki |
|---|---:|---:|---|
| `gerekli_harici_rcd_tipi` | 8/10 | %80 | Kurulum koruma tasarımı elektrikçi/kılavuz doğrulaması gerektirir. |
| `kurulum_dahil_mi` | 7/10 | %70 | Fiyatların ekonomik karşılaştırılabilirliği düşer. |
| `minimum_ayarlanabilir_akim_a` | 6/10 | %60 | Düşük güçte sınırlandırma kabiliyeti nicel karşılaştırılamaz. |
| `rdc_dd_destegi` | 6/10 | %60 | İlgili teknik/ekonomik karşılaştırma kısmi kalır. |
| `dahili_rcd_tipi` | 5/10 | %50 | İlgili teknik/ekonomik karşılaştırma kısmi kalır. |
| `fiyat_tl` | 4/10 | %40 | Ekonomik değerlendirme yapılamaz. |
| `dinamik_yuk_yonetimi_destegi` | 3/10 | %30 | İlgili teknik/ekonomik karşılaştırma kısmi kalır. |
| `harici_enerji_sayaci_gerekli_mi` | 3/10 | %30 | İlgili teknik/ekonomik karşılaştırma kısmi kalır. |
| `uyumlu_yuk_yonetim_modulu` | 3/10 | %30 | İlgili teknik/ekonomik karşılaştırma kısmi kalır. |
| `zamanlanmis_sarj` | 3/10 | %30 | İlgili teknik/ekonomik karşılaştırma kısmi kalır. |

## 6. Kullanıcıdan V1'de istenecek bilgiler

- `gunluk_ortalama_km`
- `evde_sarj_icin_uygun_sure_saat`
- `butce_tl` (opsiyonel)
- `kurulum_yeri`: `İç mekan` veya `Dış mekan`

Anlık SOC ve batarya yüzdesi temel wallbox seçimi için V1 zorunlu değildir.

## 7. İleride türetilecek değişkenler

- `gunluk_arac_enerji_ihtiyaci_kwh`: günlük km × WLTP tüketimi / 100.
- `arac_wallbox_etkin_guc_kw`: konut güvenli güç sınırı eklenmeden önce araç ve wallboxın faza özel ortak üst sınırı.
- `gunluk_ihtiyaci_karsilama_suresi_saat`: günlük enerji ihtiyacı, etkin güç ve ileride kaynaklandırılacak şarj verimiyle hesaplanacak süre.

## 8. KDS geliştiricisinin şu anda kullanabileceği veriler

- Sayaçtan yapılandırılmış faz ve faturadan güç/tüketim/tarife alanları.
- 100 araçta Type 2 ve faza özel araç AC sınırları.
- 10 wallboxta en az bir desteklenen faz için ürün güç/akım sınırı.
- Araçlarda WLTP tüketimi bulunan kayıtlar için günlük araç enerji ihtiyacı girdileri.
- Wallbox kurulum, yük yönetimi, koruma, bağlantı ve ekonomik alanları; eksik/uyarı listeleriyle birlikte.
- Rol matrisi ve açık girdi sözleşmesi.

## 9. KDS geliştirilmeden önce hâlâ çözülmesi gereken veri sorunları

- Konutun güvenli kullanılabilir şarj gücü için ana sigorta, eşzamanlı yük, pano, hat, RCD ve topraklama girdileri tanımlanıp elektrikçi sürecine bağlanmalıdır.
- Sayaç gerilimi ve azami akımı standartlaştırılmış otomatik alan değildir; azami sayaç akımı ana sigorta yerine kullanılamaz.
- 24 araçta WLTP tüketimi eksiktir; kaynak olmadan batarya/menzilden türetilmemelidir.
- Twingo ve MGS5 için genel/faza özel AC güç çelişkisi birinci üretici kaynağıyla doğrulanmalıdır.
- Araç veri setinin provenansı kayıt düzeyindedir ve çoğu kayıt ikinci üretici kaynağı doğrulaması beklemektedir.
- Wallbox RCD/RDC-DD, harici koruma ve fiyat kapsamı alanlarında yoğun eksik vardır; Bilinmiyor değerleri Hayır sayılmamalıdır.
- Kullanıcı V1 formu ve manuel ev/elektrikçi girdi akışı henüz çalışan API'ye bağlı değildir.
- Şarj verimi katsayısı kaynaklandırılmadan süre hesabı kesinleştirilmemelidir.

## 10. Kalite bulguları

- Kritik/yüksek doğrulama hatası: **0**.
- Kaynak JSON dosyaları değişmedi: **Evet**.
- Boş string yerine `null`/`Bilinmiyor` ayrımı korunmuştur.
- Araç ve wallbox kaynak alanları çekirdek dosyalara değiştirilmeden kopyalanmıştır.
- Bilinen kaynak çelişkileri uyarı alanında tutulmuş, sessiz düzeltme yapılmamıştır.

## 11. Varsayımlar ve sınırlar

- Wallbox `kds_veri_kullanilabilir=Evet`, en az bir faz bağlamında teknik eşleşme verisi bulunduğunu söyler; her konuta uygunluk veya güvenli kurulum anlamına gelmez.
- Araç teknik kullanılabilirliği WLTP'den bağımsızdır; WLTP yalnız ihtiyaç/süre hesabını etkiler.
- Fiyatlar kaynak dosyadaki tarih ve kapsamla taşınmıştır; güncellik garantisi değildir.
- Bu rapor veri kullanılabilirliğini değerlendirir; karar yöntemi veya ürün önerisi içermez.
