# EVCSDS Model API

Bu servis yalnızca elektrik sayacı ve elektrik faturası görsel analizini sunar.

## Çalıştırma

CUDA destekli PyTorch bu makinede ayrıca kuruludur. API'yi proje kökünde tek
worker ile başlatın:

```powershell
cd C:\EVCSDS
python -m pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

Servisi ve komut satırı analiz betiklerini normal giriş noktalarından başlatın;
Windows'ta CUDA DLL yükleme sırasını değiştirecek şekilde önce `paddle`, sonra
`torch` import eden özel bir başlatıcı kullanmayın.

YOLO modelleri GPU belleğinde tutulduğu için birden fazla Uvicorn worker
kullanmayın. Ölçekleme gerekiyorsa her GPU için ayrı servis örneği çalıştırın.
PaddleOCR, Windows'ta kararlılık için CPU kullanır. Aynı anda yalnızca bir analiz
çalıştırılır; diğer istekler servis içindeki semaforda sıraya alınır.

## Endpoint'ler

- `GET /health`: model ve CUDA hazır olma durumu
- `POST /analyze/meter`: sayaç tespiti, OCR ve faz çıkarımı
- `POST /analyze/bill`: fatura tespiti ve OCR
- `POST /analyze/home`: sayaç ve faturadan KDS `home` girdisi; ham OCR metni içermez
- `POST /analyze`: geriye uyumlu sayaç endpoint'i

Tüm analiz endpoint'leri `X-API-Key` header'ı ister. Ayrı sayaç/fatura
endpoint'leri `file` multipart alanını, birleşik ev endpoint'i ise
`meter_file` ve `bill_file` alanlarını ister.

```powershell
$headers = @{ "X-API-Key" = "API_KEY" }
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/analyze/bill" `
  -Headers $headers `
  -Form @{ file = Get-Item "C:\faturalar\ornek.jpg" }
```

OpenAPI arayüzü servis çalışırken `http://127.0.0.1:8000/docs` adresindedir.

## KDS'ye ev girdisi

`/analyze/home` iki dosya alanı ister: `meter_file` ve `bill_file`. Yanıtın
`home` nesnesi `faz`, `sozlesme_gucu_kw`, `donem_tuketimi_kwh`,
`gunluk_ortalama_kwh` ve `tarife` alanlarını taşır. Eksik veya düşük güvenli
alanlar `null`/`belirsiz` olur. `manuel_dogrulama_alanlari` teknik ön
değerlendirme için gerekli faz veya sözleşme gücü eksikse doldurulur; dönem
tüketimi ve tarife KDS V1.1'de opsiyoneldir. Bulunan otomatik değerler
`onay_bekleyen_alanlar` içinde listelenir. Hiçbir OCR alanı kullanıcı onayı
olmadan kesin KDS verisi sayılamaz: `kdsye_dogrudan_aktarilabilir=false` ve
`durum=kullanici_onayi_gerekli` (gerekli alan eksikse
`manuel_dogrulama_gerekli`) döner. Site/KDS sunucusu bu onay adımını ayrıca
uygulamalıdır. API yanıtı ham OCR metinlerini içermez.
Ham fatura yanıtında `manuel_giris_alanlari` yalnız zorunlu sözleşme gücünü,
`opsiyonel_dogrulama_alanlari` ise eksik/düşük güvenli tüketim ve tarifeyi
gösterir.

```powershell
$headers = @{ "X-API-Key" = "API_KEY" }
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/analyze/home" `
  -Headers $headers `
  -Form @{
    meter_file = Get-Item "C:\gorseller\sayac.jpg"
    bill_file = Get-Item "C:\gorseller\fatura.jpg"
  }
```

Web arayüzü API anahtarını tarayıcı koduna koymamalıdır; bu uç nokta site
sunucusundan çağrılmalıdır. Eski `/analyze/meter` ve `/analyze/bill` uçları
ayrıntılı OCR metinleri içerdiğinden yalnız yetkili sunucu tarafında
kullanılmalıdır.

## Yayın öncesi fatura değerlendirmesi

`planning/FATURA_SAHA_DOGRULAMA_SABLONU.csv` dosyasında her örnek için
`fatura_var`, kaynağın bağımsızlığı ve üç alanın gerçek değerleri işaretlenir.
Manifestteki `testimagelast/` görselleri kişisel belge içerebildiği için Git'e
eklenmez. Değerlendirme komutları yalnız bu görseller yerel makinede mevcutsa
çalışır; yeni kurulumda önce izinli ve anonimleştirilmiş test görselleriyle
manifest yolları güncellenmelidir.
Mevcut pilotta bazı alanlar yalnız kullanıcı görsel okumasıyla etiketlenmiştir;
ikinci kişiyle doğrulama henüz tamamlanmamıştır. `dogrulanmadi` doğruluk hesabına girmez;
`belgede_yok` alanın gerçekten basılı olmadığını belirtir. Sayısal değerleri
ondalık noktayla girin (`6.408` gibi). Ad, adres, tesisat numarası veya ham OCR
metni bu tabloya eklenmemelidir.

```powershell
python bill_release_eval.py --validate-only
python bill_release_eval.py
```

Değerlendirme aracı API ile aynı görüntü hazırlama adımını kullanır; OCR
çıktısını veya görsel kopyalarını kalıcı olarak saklamaz. Doğru dolu, yanlış
dolu ve kaçırılan alanları ayrı sayar; bağımsız örneklerin sonuçlarını ayrıca
raporlar. Şablonda sekiz fatura ve mevcut veri setinden dört fatura olmayan
görsel vardır. Altı güç ve dört tarife etiketi girilmiştir; faturaların
bağımsızlığı henüz bilinmediği ve dört negatif geliştirme verisi olduğu için yalnız bu şablonla
yayın kararı verilemez.

## Görsel sınırları

- JPEG, PNG ve WebP
- En fazla 25 MB
- En fazla 80 megapiksel
- EXIF yönü otomatik düzeltilir
- Uzun kenarda 6000 piksele kadar ayrıntı korunur
- Tespit edilen belge, OCR için örtüşmeli 1800 piksellik parçalara ayrılır
- Geçici normalize edilmiş dosya analizden sonra silinir

Fatura YOLO güveni `0.50` altındaysa yanlış kutu başarılı sayılmaz. Servis tüm
görsel OCR doğrulamasına geçer ve yanıtta `tespit_yontemi: tam_gorsel_ocr` ile
`performans_uyarisi: dusuk_guvenli_geri_donus` alanlarını döndürür. Bu güvenli
geri dönüş normal yoldan daha uzun sürebilir.

## Fatura modeliyle ilgili önemli sınır

Mevcut Roboflow fatura veri setindeki kutuların neredeyse tamamı görselin tamamını
kaplıyor. Bu nedenle yüksek test metriğine rağmen YOLO modeli, kullanıcının uzaktan
çektiği gerçek sahne fotoğraflarında faturanın sınırını güvenilir biçimde bulamıyor.
API yanlış kutuyu sonuç olarak vermemek için OCR doğrulaması ve tam-görsel geri
dönüşü uygular; fakat bu yol CPU üzerinde yavaştır.

Fatura tespitini üretim seviyesine getirmek için gerçek telefon fotoğraflarıyla yeni
bir veri seti hazırlanmalı, kutular yalnızca faturanın dört kenarını sıkıca kapsamalı
ve fatura içermeyen negatif görseller eklenmelidir. Yeni ağırlık gerçek sahne testini
geçmeden `bill_predict_and_ocr.py` içindeki etkin model yolu değiştirilmemelidir.

## API key üretimi

`/keys/generate` yalnızca sunucuda `EVCSDS_ADMIN_KEY` tanımlandığında çalışır.

```powershell
$env:EVCSDS_ADMIN_KEY = "uzun-rastgele-yonetici-anahtari"
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```
