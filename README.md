# Ev tipi AC wallbox karar destek motoru

Motor teknik kurallarla adayları ayırır ve uygun adaylarda M01–M06 metriklerini hesaplar. Ürün sıralaması veya kurulum güvenliği onayı üretmez.

## Birleşik uygulama

Next.js arayüzü, KDS API'si ve ayrı YOLO/OCR servisi eklendi. Fotoğrafla ya da manuel girilen ev bilgileri kullanıcı tarafından doğrulandıktan sonra gerçek araç/ürün kataloğuyla mevcut motor çalışır. Motorun HR01–HR08 ve M01–M06 kodu değiştirilmedi.

Python 3.13 ve Node.js 24 LTS ile proje kökünde:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
cd frontend
npm ci
cd ..
powershell -ExecutionPolicy Bypass -File scripts/start_app.ps1
```

Arayüz: http://127.0.0.1:3000 · KDS API: http://127.0.0.1:8000/docs

Fotoğraf analizi için ayrıca:

```powershell
.venv\Scripts\python -m pip install -r vision_service/requirements-cpu.txt
.venv\Scripts\python scripts/setup_vision.py
powershell -ExecutionPolicy Bypass -File scripts/start_app.ps1 -WithVision
```

`setup_vision.py` özgün iki modelin hash'lerini kontrol eder ve Git dışında kalan `.env` içine yerel anahtarları üretir. `.env` güncellendiyse çalışan sunucuları yeniden başlatın. CUDA isteyen özgün kurulum seçeneği `vision_service/requirements.txt` dosyasındadır. OCR modelleri ilk açılışta ayrıca indirilir; fotoğraf servisi başlatılmadan manuel giriş kullanılabilir.

Servislerin elle çalıştırılması:

```powershell
.venv\Scripts\python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
# İkinci terminal: görsel servis (tek worker)
.venv\Scripts\python -m uvicorn main:app --app-dir vision_service --host 127.0.0.1 --port 8001 --workers 1
# Üçüncü terminal: frontend klasöründe
npm run dev -- --hostname 127.0.0.1
```

Birleşik uygulamanın veri akışı ve kaynak sürümleri [ENTEGRASYON_V1.md](docs/ENTEGRASYON_V1.md) dosyasında açıklanmıştır.

## Entegrasyon testleri

```powershell
.venv\Scripts\python -m pytest tests vision_service/test_home_input.py vision_service/test_bill_field_extractor.py -q
# Arayüz ve KDS API çalışırken, frontend klasöründe:
npx playwright test
npm run lint
npm run build
```

Tarayıcı testleri Microsoft Edge kullanır. Başka sistemlerde `frontend/playwright.config.ts` içindeki kanal ayarı değiştirilebilir. HTTP görsel servis testleri ağ sözleşmesini sahte yanıtlarla sınar; YOLO/OCR saha doğruluğu değildir.

## Klasörler

- `kds_engine/`: dört Python kaynak dosyası.
- `data/`: gerçek araç/wallbox kayıtları, ev profilleri, 85 senaryo ve teknik testler.
- `data/kaynaklar/`: geniş wallbox tablosu ve alan kaynakları.
- `docs/`: kural, metrik ve yöntem belgeleri; gelecekte kullanılabilecek MCDM şablonları.
- `results/`: benchmark CSV, özet ve adayların kural/metrik izleri.
- `reports/`: sunum için PDF raporu ve düzenlenebilir HTML kaynağı.

## Çalıştırma

Proje kök klasöründen, Python kuruluysa:

```powershell
python -B -m kds_engine.run_benchmark
```

Bu bilgisayarda kullanılan taşınabilir Python ile:

```powershell
& "$env:LOCALAPPDATA\Codex\kds-python-3.13.7\python.exe" -B -m kds_engine.run_benchmark
```

Haricî Python paketi gerektirmez. `-B` geçici `__pycache__` dosyalarını oluşturmaz.

## Veriler

- `ARAC_KDS_CEKIRDEK_100.json`: 100 gerçek araç kaydı.
- `WALLBOX_KDS_CEKIRDEK_30_V1_1.json`: 30 wallbox kaydı.
- `KDS_EV_PROFILLERI_V1.json`: 15 kontrollü ev profili.
- `KDS_BENCHMARK_D1_D4.json`: D1–D4 için 85 senaryo; kullanıcı girdileri bu kayıtlarda bulunur.
- `KDS_TEKNIK_ESLESME_TEST_VAKALARI.xlsx`: kaynak teknik test tablosu.
- `KDS_ADAY_HAVUZLARI_V1.json`: runner'ın kullandığı 10 özgün havuz.
- `KDS_ADAY_HAVUZLARI.json`: ayrıca istenen üç havuzun `V1_REBUILT` çıktısı.

Teslim paketindeki yanlış adlar ve uzantılar içeriklerine göre düzeltilmiştir. `docs/` altındaki özgün belgeler tarihsel paket referansları içerebilir. `ORIJINAL_PAKET_VERIFY_MANIFEST.txt`, ilk teslim paketinin hash kaydıdır; mevcut klasör yollarının manifesti değildir.

## Doğrulanan sonuç

85 senaryo, 2.153 alternatif değerlendirmesi; 842 DEGERLENDIR, 142 ELE, 1.160 DOGRULAMA_GEREKLI, 9 VERI_YETERSIZ. 2.683 otomatik kontrol geçti; açık beklenen statülü 19 D4 testi eşleşti. D4-020 ayrıca HR06 semantik kontrolünden geçti. Bu sonuçlar mevcut kontrollü deney paketine aittir.
