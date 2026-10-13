# KDS Kullanıcı Girdi Şeması V1

Bu belge gerçek kullanıcı kaydı içermez; yalnız V1 form sözleşmesini tanımlar.

## V1 alanları

| Alan | Açıklama | Veri tipi | Birim / izin verilen değer | Zorunluluk | Doğrulama kuralı |
|---|---|---|---|---|---|
| `gunluk_ortalama_km` | Tipik günlük sürüş mesafesi. | Pozitif ondalık sayı | km/gün | Günlük enerji ihtiyacı hesabı için zorunlu | `> 0`; makul olmayan değer kullanıcıya doğrulatılır, otomatik düzeltilmez. |
| `evde_sarj_icin_uygun_sure_saat` | Aracın evde şarja bağlı kalabileceği tipik süre. | Pozitif ondalık sayı | saat/gün | İhtiyaç karşılama süresi için zorunlu | `> 0` ve `<= 24`; sıfır eksik değer yerine kullanılmaz. |
| `butce_tl` | Ürün için yaklaşık üst bütçe; kurulumun dâhil olup olmadığı ayrıca dikkate alınır. | Pozitif ondalık sayı veya `null` | TL | Opsiyonel | `> 0`; fiyat tarihi ve kurulum kapsamı olmadan kesin karşılaştırma yapılmaz. |
| `kurulum_yeri` | Wallboxın kurulacağı çevre. | String enum | `İç mekan`, `Dış mekan` | Teknik çevresel eşleşme için zorunlu | Yalnız izin verilen iki değer. |

## Boş ve bilinmeyen değer kuralları

- Girilmemiş sayısal alan `null` olur; `0` eksik değer değildir ve bu alanlarda geçersizdir.
- `kurulum_yeri` boşsa teknik çevresel eşleşme bekletilir; sistem tahmin yapmaz.
- `butce_tl=null` teknik eşleşmeyi durdurmaz; yalnız ekonomik değerlendirme eksik kalır.

## V1 için zorunlu olmayan, ileride değerlendirilebilecek alanlar

- Kullanıcının sabit kablo/soket tercihi.
- Zamanlanmış şarj, enerji ölçümü veya uygulama tercihi.
- Güneş enerjisi entegrasyonu isteği.
- Birden fazla araç veya birden fazla şarj cihazı kullanımı.
- Gece/çok zamanlı tarife tercihleri.
- Erişilebilirlik, kablo güzergâhı ve montaj estetiği tercihleri.

Günlük batarya SOC'si, anlık batarya yüzdesi ve belirli bir şarj oturumunun hedef SOC'si temel wallbox seçimi için V1 zorunlu girdisi değildir. Bunlar ileride oturum planlaması ayrı bir kapsam olarak ele alınırsa eklenebilir.
