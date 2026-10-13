# KDS D1–D4 Akademik Deney Senaryosu Veri Raporu

**Sürüm:** V1  
**Üretim tarihi:** 2026-09-27  
**Deney birimi:** `HOME + VEHICLE + USER + CANDIDATE WALLBOX POOL`

Bu paket gerçek kullanıcı nüfusunu temsil eden istatistiksel bir örneklem değildir. Ev ve kullanıcı profilleri düşük, orta, yüksek ve sınır koşullarını kontrollü biçimde test etmek için oluşturulmuş **sentetik deney profilleridir**. Araçlar gerçek 100 araçlık çekirdekten, wallboxlar gerçek 30 ürünlük katalogdan gelir; bu kaynak kayıtlar değiştirilmemiştir.

Paket karar algoritması, AHP/TOPSIS veya başka bir ÇKKV yöntemi, ürün puanı, sıralama, satın alma önerisi ya da kurulum onayı içermez.

## Deney üretim kuralları

1. Rastgele sayı kullanılmaz. Araç adayları her AC güç sınıfında `vehicle_id` ile sıralanır; seçim sınıf içi sayaç ve listenin uzunluğu üzerinden mod alma ile yapılır.
2. D1 sınıf planı sabittir: sırasıyla 8 adet 6,6/7,4 kW, 9 adet 11 kW ve 8 adet 22 kW. Belirli fazlı ev profilleri dosya sırasıyla `(senaryo_no-1) mod 12`; bütçesi dolu kullanıcı profilleri `(senaryo_no-1) mod N` kuralıyla seçilir.
3. D2 dört talep kombinasyonunun her birinden 5 senaryo içerir. Araç döngüsü her sınıfın `vehicle_id` ile sıralanmış ilk beş kaydından oluşur; kullanıcı kimlik listeleri üretim betiğinde ve çıktı satırlarında açıktır. Günlük enerji yalnız `km × WLTP / 100` ile hesaplanır; şarj verimi katsayısı kullanılmaz.
4. D3'ün ilk 10 kaydı D1-001…D1-010'un kontrollü bozulmuş karşılığıdır. Bozulmalar `scenario_override` içinde tutulur; gerçek araç/wallbox kayıtları değişmez.
5. D4'ün ilk 19 kaydı mevcut teknik test vakalarının TC-01…TC-19 semantiğini taşır; 20. kayıt dış mekân uygunluğu Bilinmiyor durumunu ekler.
6. `sozlesme_gucu_kw`, dönem tüketimi ve günlük ev tüketimi güvenli tesisat gücüne dönüştürülmez.

## Senaryo sayıları

| Veri seti | Senaryo |
|---|---:|
| D1 — Temiz ve tam | 25 |
| D2 — Talep stresi | 20 |
| D3 — Eksik/belirsiz | 20 |
| D4 — Teknik sınır | 20 |
| **Toplam benzersiz** | **85** |

- Ev profili: **15**
- Kullanıcı profili: **15**
- Kullanılan benzersiz araç: **26**
- D1 ile eşleştirilmiş bozulmuş D3 senaryosu: **10**

## Araç AC güç sınıfı dağılımı

Bu tablo senaryo düzeyindedir; aynı gerçek araç farklı kontrollü koşullarda tekrar kullanılabilir.

| Sınıf | Senaryo | Oran |
|---|---:|---:|
| 6,6/7,4 kW | 42 | %49.4 |
| 11 kW | 24 | %28.2 |
| 22 kW | 19 | %22.4 |

## Ev faz dağılımı

| Sınıf | Senaryo | Oran |
|---|---:|---:|
| trifaz | 41 | %48.2 |
| monofaz | 38 | %44.7 |
| belirsiz | 6 | %7.1 |

Sözleşme gücü hiçbir senaryoda güvenli wallbox gücü, ana sigorta kapasitesi veya doğrudan eleme sınırı olarak kullanılmamıştır.

## Günlük kilometre dağılımı

| Sınıf | Senaryo | Oran |
|---|---:|---:|
| Orta (51–120 km) | 30 | %35.3 |
| Düşük (≤50 km) | 23 | %27.1 |
| Yüksek (121–200 km) | 17 | %20.0 |
| Çok yüksek (>200 km) | 15 | %17.6 |

## Evde şarja uygun park süresi dağılımı

| Sınıf | Senaryo | Oran |
|---|---:|---:|
| Uzun (≥8 saat) | 41 | %48.2 |
| Kısa (≤4 saat) | 33 | %38.8 |
| Orta (5–7 saat) | 11 | %12.9 |

## Kurulum yeri dağılımı

| Sınıf | Senaryo | Oran |
|---|---:|---:|
| Dış mekan | 45 | %52.9 |
| İç mekan | 40 | %47.1 |

## Veri kalitesi sınıfı

| Sınıf | Senaryo | Oran |
|---|---:|---:|
| Temiz | 57 | %67.1 |
| Belirsiz | 17 | %20.0 |
| Eksik | 11 | %12.9 |

`Eksik`, gerekli veya opsiyonel bir alanın `null` olduğu kontrollü durumu; `Belirsiz`, faz veya ürün özelliğinde `Bilinmiyor`/doğrulama gerektiren durumu ifade eder. Eksik değerler sıfırla veya ortalamayla doldurulmamıştır.

## Aday havuz büyüklükleri

| Havuz | Üye | Kullanım amacı |
|---|---:|---|
| `POOL_TUM_30` | 30 | Eksik-veri testleri dâhil bütün gerçek wallbox kataloğu |
| `POOL_TEKNIK_27` | 27 | Normal teknik değerlendirme havuzu |
| `POOL_FIYAT_BILINEN` | 7 | TL fiyatı kaynakta bulunan ürünler |
| `POOL_MONOFAZ_CALISABILEN` | 21 | Tek faz besleme desteği açık ve kullanılabilir ürünler |
| `POOL_UCFAZ_CALISABILEN` | 19 | Üç faz besleme desteği açık ve kullanılabilir ürünler |
| `POOL_DLM_BILINMIYOR` | 8 | DLM alanı Bilinmiyor olan kullanılabilir ürünler |
| `POOL_FIYAT_BILINMIYOR` | 20 | TL fiyatı bulunmayan kullanılabilir ürünler |
| `POOL_TEK_FAZ_BILINMIYOR` | 2 | Tek faz besleme desteği Bilinmiyor olan kullanılabilir ürünler |
| `POOL_DIS_MEKAN_BILINMIYOR` | 8 | Dış mekân uygunluğu Bilinmiyor olan kullanılabilir ürünler |
| `POOL_EKSIK_VERI_3` | 3 | Yalnız veri kalitesi testlerinde kullanılacak kayıtlar |

Normal D1/D2 havuzu yalnız `kds_veri_kullanilabilir=Evet` olan **27** ürünü içerir. Kullanılamaz üç kayıt sadece D3 eksik-veri test havuzundadır.

## Fiyat eksikliğinin deneylere etkisi

30 ürünün yalnız **7** tanesinde TL fiyat vardır; **23** kayıtta fiyat yoktur. Bu nedenle D1–D4 ana veri setleri fiyatı bilinen ürünlerle sınırlandırılmamıştır. Ekonomik bir alt deney gerektiğinde `POOL_FIYAT_BILINEN` kullanılabilir. Fiyatı olmayan ürüne ortalama değer, sınıf veya yabancı para dönüşümü atanmaz.

## Veri kalitesi kontrolleri

| Kontrol | Sonuç |
|---|---|
| `scenario_id` benzersizliği | 85/85 |
| Profil referans bütünlüğü | Hata yok |
| Araç ve wallbox referans bütünlüğü | Hata yok |
| D1 gerekli alanları | 25/25 tam |
| D2 günlük enerji formülü | 20/20 doğru; keyfi verim katsayısı yok |
| D3 temiz–bozulmuş eşleşmesi | 10/10 |
| Normal havuzda kullanılamaz wallbox | 0 |
| Eksik değerin sıfır/ortalama ile doldurulması | Yapılmadı |
| `Bilinmiyor` değerinin `Hayır` yapılması | Yapılmadı |
| Kaynak araç/wallbox dosyalarında değişiklik | Yok; SHA-256 doğrulandı |

## Kullanım sınırı

Beklenen sistem davranışları yalnız teknik eleme, değerlendirmeye devam, veri yetersizliği ve doğrulama ihtiyacı seviyesindedir. Hiçbir kayıt “doğru wallbox”, ürün sırası veya puanı tanımlamaz. Gerçek kurulum için pano, ana sigorta, kablo, koruma ve topraklama yetkili elektrikçi tarafından doğrulanmalıdır.
