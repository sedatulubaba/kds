# KDS Girdi Sözleşmesi V1.1

**Sürüm tarihi:** 2026-09-27

Bu belge karar algoritması değildir. KDS geliştiricisinin kullanacağı ham ve kalite kontrollü girdilerin anlamını, kaynağını ve mevcut durumunu tanımlar. Girdi zarfı dört nesneden oluşur:

```json
{
  "home": {},
  "vehicle": {},
  "user": {},
  "charger": {}
}
```

## Genel veri kuralları

- Sayısal veya serbest metin veri yoksa `null` kullanılır; eksik veri sıfır yapılmaz.
- Araştırılmış kategorik alan açıkça doğrulanamamışsa `Bilinmiyor` kullanılır.
- `Hayır` yalnız açık olumsuz kaynak kanıtıyla kullanılır.
- Koşullu alan uygulanmıyorsa `null` kabul edilir; örneğin üç faz desteği `Hayır` olan araçta üç faz güç/akım alanları.
- Sözleşme gücü güvenli kurulum gücü değildir. Dönem veya günlük tüketim anlık boş kapasite değildir.
- Sayaç azami akımı ana sigorta değeri olarak yorumlanmaz; pano, kablo, RCD ve topraklama saha incelemesi gerektirir.

## V1.1 faz ve eşleşme semantiği

### Araç faz desteği

`vehicle.ac_tek_faz_destegi` ve `vehicle.ac_uc_faz_destegi`, aracın **onboard AC charger** donanımının sırasıyla tek veya üç faz üzerinden enerji kabul edebilmesini ifade eder. Faza özel güç/akım alanları araç girişinin üst sınırıdır; konut veya wallbox kapasitesi değildir.

### Wallbox besleme/çalışma faz desteği

`charger.tek_faz_destegi` ve `charger.uc_faz_destegi`, wallboxın elektrik tesisatından sırasıyla tek veya üç faz beslenerek çalışabilmesini ifade eder. Faza özel güç/akım alanları wallboxın ilgili besleme düzenindeki üst sınırıdır; aracın kaç faz kabul ettiğini tanımlamaz.

Bu iki kavram aynı değildir. Özellikle `charger.tek_faz_destegi=Hayır`, "tek faz AC kabul eden araç bu cihazla şarj edilemez" demek değildir. Bu değer öncelikle wallbox varyantının **tek faz şebeke beslemesiyle çalışmasının kaynakta desteklenmediğini** gösterir. Üç faz beslenen bir wallboxın tek fazlı onboard charger taşıyan araçla davranışı ürün/kurulum özelinde ayrıca doğrulanır.

### İki ayrı eşleşme ilişkisi

1. **Ev → Wallbox:** Wallboxın mevcut konut beslemesinde çalışıp çalışamayacağı. Bu ilişki `home.faz` ile wallbox besleme desteğini karşılaştırır.
2. **Wallbox → Araç:** Konektör uyumu ve aracın onboard charger kapasitesinin wallbox çıkışını nasıl sınırlandırdığı. Bu ilişki araç ile wallbox alanlarını karşılaştırır.

Bir ilişkinin olumlu olması diğerini otomatik olumlu yapmaz. Nihai teknik durum yalnız `uygun`, `uygun_degil` veya `dogrulama_gerekli` semantik durumlarından biriyle ifade edilir. Bunlar ürün önerisi, sıralama veya kurulum onayı değildir.

### `kds_veri_kullanilabilir` sınırı

Bu kalite bayrağı yalnız kaydın en az bir teknik bağlamda değerlendirilebilecek minimum alana sahip olduğunu gösterir. Belirli bir ev–araç–wallbox üçlüsünün `uygun` olduğu anlamına gelmez.

### Sözleşme gücü ve DLM

`home.sozlesme_gucu_kw` yalnız **sözleşmesel/bağlantısal kapasite bağlamıdır**. Güvenli tesisat azami gücü, ana sigorta gücü veya wallboxa doğrudan ayrılabilir güç değildir. İleride DLM, güç artışı veya kapasite incelemesine bağlam sağlayabilir; güvenli wallbox gücü formülüne doğrudan konmaz.

Dinamik yük yönetimi (DLM), Wi-Fi veya mobil uygulama gibi sıradan bir kullanıcı özelliği değil; ölçülen ev yüküne ve tanımlı sınırlara göre şarj akımını değiştiren kurulum/enerji yönetimi özelliğidir. `dinamik_yuk_yonetimi_destegi=Evet`, tek başına 22 kW veya başka bir gücün ilgili evde güvenli olduğunu kanıtlamaz. Üreticiye göre harici sayaç/modül, ölçüm noktası ve yetkili kurulum ayarı gerekebilir.

## `home` nesnesi

| Alan adı | Açıklama | Veri tipi | Birim | Zorunlu / opsiyonel | Verinin kaynağı | Şu an mevcut mu? | Eksikse ileride nereden alınacak? | KDS'deki rol |
|---|---|---|---|---|---|---|---|---|
| faz | Konut beslemesinin sayaç görselinden sınıflandırılan faz tipi. | String enum: monofaz \| trifaz \| belirsiz | — | Teknik eşleşme için zorunlu; belirsizse manuel doğrulama | Sayaç görseli OCR + faz kuralı | Evet; yapılandırılmış otomatik çıktı | Kullanıcı veya elektrikçi doğrulaması | Teknik uygunluk girdisi |
| sozlesme_gucu_kw | Dağıtım/perakende sözleşmesindeki sözleşmesel/bağlantısal kapasite bağlamı. Evin güvenli azami şarj gücü, ana sigorta gücü veya wallboxa ayrılabilir güç değildir. | Ondalık sayı | kW | Ön kapasite değerlendirmesi için gerekli | Elektrik faturası OCR/alan çıkarma | Evet; bulunursa yapılandırılmış | Faturadan manuel giriş/doğrulama | Koşullu kurulum bilgisi |
| donem_tuketimi_kwh | Faturada basılı dönem enerji tüketimi; anlık kullanılabilir güç değildir. | Ondalık sayı | kWh | Opsiyonel | Elektrik faturası OCR/alan çıkarma | Evet; bulunursa yapılandırılmış | Faturadan manuel giriş | Yardımcı bağlamsal veri |
| gunluk_ortalama_kwh | Faturada basılı günlük ortalama tüketim; anlık ev yükü değildir. | Ondalık sayı | kWh/gün | Opsiyonel | Elektrik faturası OCR/alan çıkarma | Evet; şablonda basılıysa | Faturadan manuel giriş veya ileride tarihsel tüketim sistemi | Yardımcı bağlamsal veri |
| tarife | Tüketici grubundan türetilen mesken/zaman/gerilim sınıfı. | String | — | Opsiyonel | Elektrik faturası OCR/alan çıkarma | Evet; bulunursa yapılandırılmış | Faturadan manuel giriş/doğrulama | Yardımcı bağlamsal veri |
| gerilim_v | Sayaç/tesisat gerilim bilgisi. Ham OCR'da görülebilse de standart alan değildir. | Ondalık sayı veya yapılandırılmış gerilim nesnesi | V | Opsiyonel; ileride teknik doğrulama için | Sayaç etiketi / elektrikçi ölçümü | Hayır; şu anda otomatik standart girdi değil | Sayaç parser'ı ve elektrikçi doğrulaması | Koşullu kurulum bilgisi |
| azami_akim_a | Sayaç etiketindeki akım ifadesinden ayrıştırılacak azami değer; ana sigorta değeri olarak yorumlanamaz. | Ondalık sayı | A | Opsiyonel; ileride | Sayaç etiketi / elektrikçi | Hayır; şu anda otomatik standart girdi değil | Sayaç parser'ı ve elektrikçi doğrulaması | Koşullu kurulum bilgisi |
| ana_sigorta_a | Konut ana koruma elemanının elektrikçi tarafından doğrulanan anma akımı. | Ondalık sayı | A | Güvenli kurulum değerlendirmesi için ileride gerekli olabilir | Kullanıcı belgesi + yetkili elektrikçi | Hayır | Yerinde elektrikçi incelemesi | Koşullu kurulum bilgisi |
| pano_uygunluk_durumu | Panonun yeni şarj devresine alan ve kapasite bakımından uygunluğu. | String enum: Uygun \| Uygun değil \| İnceleme gerekli | — | İleride koşullu | Yetkili elektrikçi | Hayır | Yerinde pano incelemesi | Koşullu kurulum bilgisi |
| ayrilmis_sarj_hatti_var_mi | Wallbox için ayrı ve uygun korumalı hat bulunup bulunmadığı. | String enum: Evet \| Hayır \| Bilinmiyor | — | İleride koşullu | Kullanıcı + yetkili elektrikçi | Hayır | Yerinde tesisat incelemesi | Koşullu kurulum bilgisi |
| kablo_kesiti_mm2 | Şarj hattının elektrikçi tarafından doğrulanan iletken kesiti. | Ondalık sayı | mm² | İleride koşullu | Yetkili elektrikçi | Hayır | Yerinde kablo/hat incelemesi | Koşullu kurulum bilgisi |
| hat_uzunlugu_m | Pano ile wallbox arasındaki yaklaşık kablo güzergâhı uzunluğu. | Ondalık sayı | m | İleride koşullu | Kullanıcı + elektrikçi keşfi | Hayır | Kurulum keşfi | Koşullu kurulum bilgisi |
| rcd_koruma_durumu | Mevcut/planlanan RCD veya RDC-DD korumasının tipi ve uygunluğu. | String | — | İleride koşullu | Yetkili elektrikçi ve ürün kılavuzu | Hayır | Yerinde inceleme ve ürün kurulum talimatı | Koşullu kurulum bilgisi |
| topraklama_uygunluk_durumu | Topraklama tesisatının ölçümle doğrulanan uygunluk durumu. | String enum: Uygun \| Uygun değil \| İnceleme gerekli | — | İleride koşullu | Yetkili elektrikçi ölçümü | Hayır | Yerinde ölçüm | Koşullu kurulum bilgisi |

### Ev verisinin mevcut sınırı

Otomatik standart alanlar `faz`, `sozlesme_gucu_kw`, `donem_tuketimi_kwh`, `gunluk_ortalama_kwh` ve `tarife`dir. `gerilim_v` ve `azami_akim_a` bazı sayaçlarda OCR metninde görülebilir, ancak şu anda otomatik standart girdi değildir. Ana sigorta, pano kapasitesi, ayrılmış şarj hattı, kablo kesiti/güzergâhı, RCD ve topraklama çalışan sistem tarafından üretilmez.

## `vehicle` nesnesi

| Alan adı | Açıklama | Veri tipi | Birim | Zorunlu / opsiyonel | Verinin kaynağı | Şu an mevcut mu? | Eksikse ileride nereden alınacak? | KDS'deki rol |
|---|---|---|---|---|---|---|---|---|
| vehicle_id | Araç varyantının benzersiz kimliği. | String | — | Zorunlu | Araç çekirdek veri seti | Evet; 100/100 kayıtta değer var | Üretici Türkiye/Avrupa teknik kaynağı ve alan düzeyi provenans | Metadata / provenans |
| marka | Araç üreticisi. | String | — | Zorunlu | Araç çekirdek veri seti | Evet; 100/100 kayıtta değer var | Üretici Türkiye/Avrupa teknik kaynağı ve alan düzeyi provenans | Yardımcı bağlamsal veri |
| model | Araç model adı. | String | — | Zorunlu | Araç çekirdek veri seti | Evet; 100/100 kayıtta değer var | Üretici Türkiye/Avrupa teknik kaynağı ve alan düzeyi provenans | Yardımcı bağlamsal veri |
| versiyon | Batarya/çekiş/donanım ayrımını koruyan tam varyant. | String | — | Zorunlu | Araç çekirdek veri seti | Evet; 100/100 kayıtta değer var | Üretici Türkiye/Avrupa teknik kaynağı ve alan düzeyi provenans | Yardımcı bağlamsal veri |
| ac_konnektor_tipi | Araç AC giriş standardı. | String | — | Zorunlu | Araç çekirdek veri seti | Evet; 100/100 kayıtta değer var | Üretici Türkiye/Avrupa teknik kaynağı ve alan düzeyi provenans | Teknik uygunluk girdisi |
| ac_tek_faz_destegi | Aracın tek faz AC şarjı kabul edip etmediği. | Evet/Hayır/Bilinmiyor | — | Zorunlu | Araç çekirdek veri seti | Evet; 100/100 kayıtta değer var | Üretici Türkiye/Avrupa teknik kaynağı ve alan düzeyi provenans | Teknik uygunluk girdisi |
| ac_tek_faz_azami_guc_kw | Tek fazda araç üzeri şarj cihazının kabul ettiği üst güç. | Ondalık sayı | kW | Tek faz desteği Evet ise zorunlu | Araç çekirdek veri seti | Evet; 100/100 kayıtta değer var | Üretici Türkiye/Avrupa teknik kaynağı ve alan düzeyi provenans | Teknik uygunluk girdisi |
| ac_tek_faz_azami_akim_a | Tek fazda araç girişinin azami akımı. | Ondalık sayı | A | Tek faz desteği Evet ise zorunlu | Araç çekirdek veri seti | Evet; 100/100 kayıtta değer var | Üretici Türkiye/Avrupa teknik kaynağı ve alan düzeyi provenans | Teknik uygunluk girdisi |
| ac_uc_faz_destegi | Aracın üç faz AC şarjı kabul edip etmediği. | Evet/Hayır/Bilinmiyor | — | Zorunlu | Araç çekirdek veri seti | Evet; 100/100 kayıtta değer var | Üretici Türkiye/Avrupa teknik kaynağı ve alan düzeyi provenans | Teknik uygunluk girdisi |
| ac_uc_faz_azami_guc_kw | Üç fazda aracın kabul ettiği toplam üst güç. | Ondalık sayı | kW | Üç faz desteği Evet ise zorunlu | Araç çekirdek veri seti | Evet; 90/100 kayıtta değer var | Üretici Türkiye/Avrupa teknik kaynağı ve alan düzeyi provenans | Teknik uygunluk girdisi |
| ac_uc_faz_faz_basina_akim_a | Üç fazda araç girişinin faz başına azami akımı. | Ondalık sayı | A/faz | Üç faz desteği Evet ise zorunlu | Araç çekirdek veri seti | Evet; 90/100 kayıtta değer var | Üretici Türkiye/Avrupa teknik kaynağı ve alan düzeyi provenans | Teknik uygunluk girdisi |
| batarya_kullanilabilir_kwh | Normal kullanımda erişilebilen net batarya enerjisi. | Ondalık sayı | kWh | Opsiyonel | Araç çekirdek veri seti | Evet; 100/100 kayıtta değer var | Üretici Türkiye/Avrupa teknik kaynağı ve alan düzeyi provenans | Kullanıcı ihtiyacı hesabı girdisi |
| wltp_tuketim_kwh_100km | WLTP birleşik enerji tüketimi. | Ondalık sayı | kWh/100 km | Günlük enerji hesabı için gerekli; teknik eşleşme için opsiyonel | Araç çekirdek veri seti | Evet; 76/100 kayıtta değer var | Üretici Türkiye/Avrupa teknik kaynağı ve alan düzeyi provenans | Kullanıcı ihtiyacı hesabı girdisi |
| wltp_menzil_km | WLTP birleşik menzil. | Ondalık sayı | km | Opsiyonel | Araç çekirdek veri seti | Evet; 76/100 kayıtta değer var | Üretici Türkiye/Avrupa teknik kaynağı ve alan düzeyi provenans | Yardımcı bağlamsal veri |
| kaynak_url | Araç kaydının temel kaynak bağlantısı. | URL string | — | Zorunlu | Araç çekirdek veri seti | Evet; 100/100 kayıtta değer var | Üretici Türkiye/Avrupa teknik kaynağı ve alan düzeyi provenans | Metadata / provenans |
| dogrulama_durumu | Kaydın kaynak doğrulama durumu. | String | — | Zorunlu | Araç çekirdek veri seti | Evet; 100/100 kayıtta değer var | Üretici Türkiye/Avrupa teknik kaynağı ve alan düzeyi provenans | Metadata / provenans |
| veri_guven_duzeyi | Kaydın nitel veri güven sınıfı. | String | — | Zorunlu | Araç çekirdek veri seti | Evet; 100/100 kayıtta değer var | Üretici Türkiye/Avrupa teknik kaynağı ve alan düzeyi provenans | Metadata / provenans |
| kds_veri_kullanilabilir | Minimum teknik AC eşleşme alanlarının yeterli olup olmadığı. | Evet/Hayır | — | Zorunlu | Araç çekirdek veri seti | Evet; 100/100 kayıtta değer var | Üretici Türkiye/Avrupa teknik kaynağı ve alan düzeyi provenans | Metadata / provenans |
| kds_eksik_alanlar | Eksik fakat koşullu olarak uygulanmayan alanlar hariç alan adları. | String listesi | — | Zorunlu | Araç çekirdek veri seti | Evet; bu paketle üretildi | Üretici Türkiye/Avrupa teknik kaynağı ve alan düzeyi provenans | Metadata / provenans |
| kds_veri_uyarilari | Çelişki, doğrulama ve kısmi hesaplama uyarıları. | String listesi | — | Zorunlu | Araç çekirdek veri seti | Evet; bu paketle üretildi | Üretici Türkiye/Avrupa teknik kaynağı ve alan düzeyi provenans | Metadata / provenans |

### Araç kullanılabilirlik kuralı

`kds_veri_kullanilabilir=Evet` için konektör tipi, tek/üç faz destek bayrakları ve açıkça desteklenen her faz yolu için faza özel azami güç ile akım bulunmalıdır. WLTP tüketimi bu teknik bayrağı `Hayır` yapmaz; eksikse günlük enerji ihtiyacı hesabı için uyarı üretilir. Genel `ac_azami_guc_kw` V1 çekirdeğine taşınmamıştır.

## `user` nesnesi

| Alan adı | Açıklama | Veri tipi | Birim | Zorunlu / opsiyonel | Verinin kaynağı | Şu an mevcut mu? | Eksikse ileride nereden alınacak? | KDS'deki rol |
|---|---|---|---|---|---|---|---|---|
| gunluk_ortalama_km | Kullanıcının tipik bir günde araçla katettiği ortalama mesafe. | Ondalık sayı | km/gün | Günlük enerji ihtiyacı için zorunlu | Kullanıcı girişi | Hayır; V1 şeması hazır, gerçek değer yok | Kullanıcıdan form ile | Kullanıcı ihtiyacı hesabı girdisi |
| evde_sarj_icin_uygun_sure_saat | Aracın evde şarja bağlı kalabileceği tipik süre. | Ondalık sayı | saat/gün | İhtiyaç karşılama süresi için zorunlu | Kullanıcı girişi | Hayır; V1 şeması hazır, gerçek değer yok | Kullanıcıdan form ile | Kullanıcı ihtiyacı hesabı girdisi |
| butce_tl | Wallbox ürün bedeli için kullanıcının yaklaşık üst bütçesi; kurulum kapsamı ayrı ele alınır. | Ondalık sayı | TL | Opsiyonel | Kullanıcı girişi | Hayır; V1 şeması hazır, gerçek değer yok | Kullanıcıdan form ile | Sıralama kriteri adayı |
| kurulum_yeri | Wallbox kurulumunun iç veya dış mekânda olacağı bilgisi. | String enum: İç mekan \| Dış mekan | — | Teknik çevresel eşleşme için zorunlu | Kullanıcı girişi | Hayır; V1 şeması hazır, gerçek değer yok | Kullanıcıdan form ile | Teknik uygunluk girdisi |

## `charger` nesnesi

| Alan adı | Açıklama | Veri tipi | Birim | Zorunlu / opsiyonel | Verinin kaynağı | Şu an mevcut mu? | Eksikse ileride nereden alınacak? | KDS'deki rol |
|---|---|---|---|---|---|---|---|---|
| charger_id | Wallbox ürün/varyant benzersiz kimliği. | String | — | Zorunlu | Wallbox çekirdek veri seti | Evet; 10/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Metadata / provenans |
| marka | Üretici marka. | String | — | Zorunlu | Wallbox çekirdek veri seti | Evet; 10/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Yardımcı bağlamsal veri |
| model | Ürün modeli. | String | — | Zorunlu | Wallbox çekirdek veri seti | Evet; 10/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Yardımcı bağlamsal veri |
| versiyon | Güç, bağlantı ve pazar ayrımını taşıyan tam varyant. | String | — | Zorunlu | Wallbox çekirdek veri seti | Evet; 10/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Yardımcı bağlamsal veri |
| pazar | Teknik özelliklerin geçerli olduğu satış pazarı. | String | — | Zorunlu | Wallbox çekirdek veri seti | Evet; 10/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Yardımcı bağlamsal veri |
| nominal_azami_guc_kw | Ürünün ilan edilen toplam azami AC gücü. | Ondalık sayı | kW | Zorunlu | Wallbox çekirdek veri seti | Evet; 10/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Teknik uygunluk girdisi |
| nominal_gerilim | Üretici kaynağında yayımlanan ham wallbox besleme gerilimi ifadesi. Akımdan güç değerlendirmesinde kanıt bağlamıdır; otomatik sayısal gerilime dönüştürülmez. | String | V (ham metin) | Çapraz faz/akım değerlendirmesinde koşullu | Wallbox V1.1 çekirdek veri seti | Evet; 10/10 kayıtta kaynaklı değer var | Üretici teknik föyü/kurulum kılavuzu; ileride yapılandırılmış gerilim alanları | Koşullu kurulum bilgisi |
| tek_faz_destegi | Tek faz çalışma desteği. | Evet/Hayır/Bilinmiyor | — | Zorunlu | Wallbox çekirdek veri seti | Evet; 9/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Teknik uygunluk girdisi |
| tek_faz_azami_guc_kw | Tek faz bağlantıda ürün üst gücü. | Ondalık sayı | kW | Tek faz desteği Evet ise zorunlu | Wallbox çekirdek veri seti | Evet; 7/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Teknik uygunluk girdisi |
| tek_faz_azami_akim_a | Tek faz bağlantıda ürün üst akımı. | Ondalık sayı | A | Tek faz desteği Evet ise zorunlu | Wallbox çekirdek veri seti | Evet; 7/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Teknik uygunluk girdisi |
| uc_faz_destegi | Üç faz çalışma desteği. | Evet/Hayır/Bilinmiyor | — | Zorunlu | Wallbox çekirdek veri seti | Evet; 10/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Teknik uygunluk girdisi |
| uc_faz_azami_guc_kw | Üç faz bağlantıda toplam üst güç. | Ondalık sayı | kW | Üç faz desteği Evet ise zorunlu | Wallbox çekirdek veri seti | Evet; 8/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Teknik uygunluk girdisi |
| uc_faz_faz_basina_akim_a | Üç faz bağlantıda faz başına üst akım. | Ondalık sayı | A/faz | Üç faz desteği Evet ise zorunlu | Wallbox çekirdek veri seti | Evet; 8/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Teknik uygunluk girdisi |
| ac_konnektor_tipi | Araç tarafı AC bağlantı standardı. | String | — | Zorunlu | Wallbox çekirdek veri seti | Evet; 10/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Teknik uygunluk girdisi |
| ayarlanabilir_akim_destegi | Cihaz akım sınırının ayarlanabilmesi. | Evet/Hayır/Bilinmiyor | — | Opsiyonel | Wallbox çekirdek veri seti | Evet; 8/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Koşullu kurulum bilgisi |
| minimum_ayarlanabilir_akim_a | Açıkça belirtilen en düşük ayar akımı. | Ondalık sayı | A | Opsiyonel | Wallbox çekirdek veri seti | Evet; 4/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Koşullu kurulum bilgisi |
| maksimum_ayarlanabilir_akim_a | Açıkça belirtilen en yüksek ayar akımı. | Ondalık sayı | A | Opsiyonel | Wallbox çekirdek veri seti | Evet; 8/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Koşullu kurulum bilgisi |
| dinamik_yuk_yonetimi_destegi | Ev yüküne göre şarj akımını dinamik ayarlama desteği. | Evet/Hayır/Bilinmiyor | — | Opsiyonel | Wallbox çekirdek veri seti | Evet; 7/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Koşullu kurulum bilgisi |
| harici_enerji_sayaci_gerekli_mi | Dinamik yük yönetimi için harici sayaç gereksinimi. | Evet/Hayır/Bilinmiyor | — | DLM kullanılacaksa koşullu | Wallbox çekirdek veri seti | Evet; 7/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Koşullu kurulum bilgisi |
| uyumlu_yuk_yonetim_modulu | Üreticinin belirttiği uyumlu sayaç/modül. | String | — | DLM kullanılacaksa koşullu | Wallbox çekirdek veri seti | Evet; 7/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Koşullu kurulum bilgisi |
| statik_guc_sinirlandirma_destegi | Kurulumda sabit akım/güç üst sınırı ayarlama desteği. | Evet/Hayır/Bilinmiyor | — | Opsiyonel | Wallbox çekirdek veri seti | Evet; 8/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Koşullu kurulum bilgisi |
| dc_kacak_akim_algilama_6ma | Açıkça belirtilmiş 6 mA DC kaçak akım algılama. | Evet/Hayır/Bilinmiyor | — | Kurulum tasarımı için koşullu | Wallbox çekirdek veri seti | Evet; 7/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Koşullu kurulum bilgisi |
| rdc_dd_destegi | Açıkça beyan edilen RDC-DD işlevi. | Evet/Hayır/Bilinmiyor | — | Kurulum tasarımı için koşullu | Wallbox çekirdek veri seti | Evet; 4/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Koşullu kurulum bilgisi |
| dahili_rcd_tipi | Ürün içinde açıkça belirtilen RCD tipi. | String | — | Kurulum tasarımı için koşullu | Wallbox çekirdek veri seti | Evet; 5/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Koşullu kurulum bilgisi |
| gerekli_harici_rcd_tipi | Üreticinin kurulumda istediği harici RCD tipi. | String | — | Kurulum tasarımı için koşullu | Wallbox çekirdek veri seti | Evet; 2/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Koşullu kurulum bilgisi |
| ip_sinifi | Muhafazanın giriş koruma sınıfı. | String | — | Kurulum yerine göre koşullu | Wallbox çekirdek veri seti | Evet; 10/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Teknik uygunluk girdisi |
| ic_mekan_uygun | İç mekân kurulum uygunluğu. | Evet/Hayır/Bilinmiyor | — | Kurulum yerine göre koşullu | Wallbox çekirdek veri seti | Evet; 10/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Teknik uygunluk girdisi |
| dis_mekan_uygun | Dış mekân kurulum uygunluğu. | Evet/Hayır/Bilinmiyor | — | Kurulum yerine göre koşullu | Wallbox çekirdek veri seti | Evet; 10/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Teknik uygunluk girdisi |
| baglanti_tipi | Soketli veya sabit kablolu yapı. | String enum | — | Zorunlu | Wallbox çekirdek veri seti | Evet; 10/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Sıralama kriteri adayı |
| kablo_uzunlugu_m | Sabit kablolu varyantta kablo uzunluğu. | Ondalık sayı | m | Sabit kabloluysa opsiyonel | Wallbox çekirdek veri seti | Evet; 5/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Sıralama kriteri adayı |
| zamanlanmis_sarj | Ürünün programlı başlatma/zamanlama desteği. | Evet/Hayır/Bilinmiyor | — | Opsiyonel | Wallbox çekirdek veri seti | Evet; 7/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Sıralama kriteri adayı |
| enerji_olcumu | Şarj enerjisini ölçme/raporlama desteği. | Evet/Hayır/Bilinmiyor | — | Opsiyonel | Wallbox çekirdek veri seti | Evet; 8/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Sıralama kriteri adayı |
| fiyat_tl | Tarih ve kapsamıyla birlikte kayıtlı Türkiye fiyatı. | Ondalık sayı | TL | Ekonomik değerlendirme için opsiyonel | Wallbox çekirdek veri seti | Evet; 6/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Sıralama kriteri adayı |
| fiyat_tarihi | Fiyatın gözlendiği tarih. | Tarih | YYYY-AA-GG | Fiyat varsa zorunlu | Wallbox çekirdek veri seti | Evet; 6/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Metadata / provenans |
| kurulum_dahil_mi | Fiyata standart kurulumun dâhil olup olmadığı. | Evet/Hayır/Bilinmiyor | — | Fiyat yorumunda opsiyonel | Wallbox çekirdek veri seti | Evet; 3/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Sıralama kriteri adayı |
| garanti_yil | Açıkça belirtilen garanti süresi. | Ondalık sayı | yıl | Opsiyonel | Wallbox çekirdek veri seti | Evet; 7/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Sıralama kriteri adayı |
| dogrulama_durumu | Ürün kaydının kaynak doğrulama durumu. | String | — | Zorunlu | Wallbox çekirdek veri seti | Evet; 10/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Metadata / provenans |
| veri_guven_duzeyi | Nitel veri güven sınıfı. | String | — | Zorunlu | Wallbox çekirdek veri seti | Evet; 10/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Metadata / provenans |
| kaynak_url | Kaydın temel üretici/teknik kaynak bağlantısı. | URL string | — | Zorunlu | Wallbox çekirdek veri seti | Evet; 10/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Metadata / provenans |
| kds_veri_kullanilabilir | En az bir faz yolu için teknik eşleşme verisinin yeterli olması. | Evet/Hayır | — | Zorunlu | Wallbox çekirdek veri seti | Evet; 10/10 kayıtta değer var | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Metadata / provenans |
| kds_eksik_alanlar | Koşullu uygulanmayanlar hariç eksik çekirdek alan adları. | String listesi | — | Zorunlu | Wallbox çekirdek veri seti | Evet; bu paketle üretildi | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Metadata / provenans |
| kds_veri_uyarilari | Koşullu eşleşme, fiyat, kaynak ve çelişki uyarıları. | String listesi | — | Zorunlu | Wallbox çekirdek veri seti | Evet; bu paketle üretildi | Üretici teknik kaynağı, distribütör veya alan düzeyi provenans | Metadata / provenans |

### Wallbox kullanılabilirlik kuralı

`kds_veri_kullanilabilir=Evet` için konektör ve nominal güç ile en az bir açıkça desteklenen wallbox **besleme** faz yolunda faza özel güç ve akım bulunmalıdır. `nominal_gerilim` V1.1'de ham kaynak ifadesi olarak taşınır. Başka bir besleme yolunun `Bilinmiyor` olması yalnız doğrulanmış bağlamda değerlendirmeye izin verir. Bu bayrak belirli araçla uyum veya kurulum onayı değildir; Ev → Wallbox ve Wallbox → Araç ilişkileri ayrı değerlendirilir.

## Kapsam dışı

Bu sözleşme puan, ağırlık, ürün sıralaması, satın alma önerisi veya elektrik tesisatı uygunluk onayı tanımlamaz.

## V1.1 değişiklik özeti

- Araç faz kabulü ile wallbox besleme/çalışma fazı ayrı kavramlar olarak tanımlandı.
- Ev → Wallbox ve Wallbox → Araç ilişkileri ayrıldı.
- `charger.nominal_gerilim` ham kaynak metni V1.1 wallbox çekirdeğine eklendi; sayısal gerilim türetilmedi.
- `kds_veri_kullanilabilir` bayrağının uyumluluk sonucu olmadığı açıklandı.
- Sözleşme gücü ve DLM'nin sınırları netleştirildi.
- V1 dosyası değiştirilmedi.
