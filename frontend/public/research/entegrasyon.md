# Uygulama entegrasyonu

## Akış

Sayaç ve fatura fotoğrafları → ayrı YOLO/PaddleOCR servisi → alanlara dönüştürülmüş `home` → kullanıcı kontrolü/düzeltmesi ve açık onay → gerçek katalogdan seçilen araç + kullanıcı girdileri → mevcut KDS motoru → dört aday listesi.

Fotoğraf yüklemeden manuel giriş de desteklenir. Boş alanlar tahmin edilmez. Faz belirsiz bırakılabilir; motor doğrulama gereken adayları ayırır. Sözleşme gücü kurulum kapasitesi olarak kullanılmaz. Fiyat ve bütçe teknik eleme ölçütü değildir.

## Parçalar

- `kds_engine/`: özgün karar motoru; kural ve metrik kodu değiştirilmedi.
- `backend/`: FastAPI katalog/karar uçları, istek doğrulama, imzalı OCR analiz kaydı ve görsel servis bağlantısı.
- `frontend/`: Next.js arayüzü; fotoğraf/manuel giriş, ev bilgisi onayı, araç ve kullanım formu, gerekçeli sonuç kartları.
- `vision_service/`: özgün sayaç/fatura çıkarım kodu ve kaynak testleri.

Tarayıcı yalnız `/api/...` uçlarını çağırır. Next.js bu istekleri KDS API'sine iletir. Görsel servisin anahtarı yalnız KDS sunucusunda kullanılır; tarayıcıya ve Git'e gönderilmez. Arayüze ham OCR metni aktarılmaz.

## API sözleşmesi

- `GET /api/catalog`: gerçek araç kayıtları.
- `GET /api/health`: katalog sayıları ve görsel servis yapılandırma bilgisi. Yapılandırılmış olması servisin çalıştığını veya OCR doğruluğunu kanıtlamaz.
- `POST /api/analyze-home`: multipart `meter_file` ve `bill_file`; doğrulanabilir ev alanları ve imzalı `analysis_token` döner. Otomatik aktarım bayrağı her zaman false.
- `POST /api/recommend`: `home`, `user`, `vehicle_id`, `home_confirmed`, `input_source`, isteğe bağlı `analysis_token`.

Onay false veya eksikse karar isteği reddedilir. Fotoğraf kaynaklı istekte geçerli ve bir saatten eski olmayan analiz kaydı gerekir. Kullanıcının OCR değerlerini düzeltmesi serbesttir; değişiklikler `home_changes` içinde izlenir. Arayüzde bir ev alanı değişince onay ve önceki sonuçlar geçersizleşir. Araç teknik değerleri istemciden alınmaz.

## Kaynak ve değişiklikler

Görsel kaynak: https://github.com/RounenRais/evcsds-app — `yolo` dalı, `ddae1f6ad19ffe9835e479a01bf1133180153b2d`.
Frontend başlangıç paket ayarları: aynı deponun `main` dalı, `213233fd50be6ffc74c7710ffc4e0b8db38a4866`.

Görsel servis algoritmaları korunmuştur. `main.py` proje `.env` dosyasını okur; `key_utils.py` yerel `EVCSDS_VISION_API_KEY` anahtarını destekler. Depodaki hazır `keys.json` kopyalanmamıştır. Ağır model ağırlıkları Git dışında tutulur; `scripts/setup_vision.py` özgün Git blob hash'lerini kontrol ederek iki etkin ağırlığı indirir. Saha testini geçmemiş v3 modeline geçiş yapılmaz.

`home_input.py` OCR güç alanını kritik sayabilir; motor HR08 gereği bu değeri güvenli güç sınırı veya otomatik eleme nedeni yapmaz. Manuel yolda sözleşme gücü opsiyoneldir.

## Test kapsamı

API testleri gerçek katalog ve KDS motorunu kullanır. Görsel HTTP servisi senaryoları sahte yanıtlarla ağ sözleşmesini sınar; bu testler YOLO veya OCR başarı oranı değildir. Kaynak alan çıkarım/onay testleri ayrıca çalıştırılır. 85 senaryolu özgün benchmark, motor davranışının korunması için tekrar çalıştırılır. Tarayıcı testleri gerçek yerel KDS API'si ile form, onay, sonuç grupları ve mobil taşmayı kontrol eder.

Fatura modelinin gerçek sahne fotoğraflarındaki sınırlamaları `vision_service/MODEL_DURUMU.md` içinde korunmuştur. Birim ve entegrasyon testlerinin geçmesi, saha doğruluğunun doğrulandığı anlamına gelmez.

## Bu entegrasyonda doğrulananlar — 13 Ekim 2026

- API ile kaynak alan çıkarım/onay testleri: 47 başarılı.
- Gerçek yerel API ile Edge tarayıcı testleri: 5 başarılı; mobil taşma kontrolü dahil.
- TypeScript kontrolü, ESLint ve üretim derlemesi başarılı.
- Motorun dört Python kaynağı ve özgün benchmark aday/CSV çıktıları önceki commit ile aynı.
- 85 senaryo ve 2.683 benchmark kontrolü başarılı; kaynakta açık statülü 19 D4 testi eşleşiyor.
- İki etkin YOLO ağırlığı kaynak Git blob hash'leriyle doğrulandı; servis CPU üzerinde açıldı.
- Sentetik sayaç/fatura görselleriyle gerçek Next.js → KDS API → YOLO/OCR → kullanıcı düzeltmesi/onayı → karar motoru akışı hem HTTP hem tarayıcı üzerinden çalıştı. Onaysız istek reddedildi; onaylı sonuç 27 adayın 14 değerlendirilebilir, 4 elenen ve 9 doğrulama gereken ürüne ayrılmasıydı. Bu sentetik smoke testi saha doğruluk ölçümü değildir.

CPU kurulumunda NumPy 2.2.6 ve pandas 2.3.3 sabitlendi. Bu kombinasyonla Windows/Python 3.13 üzerinde OCR servisi açılışı doğrulandı. CUDA seçeneği bu entegrasyon koşusunda denenmedi.
