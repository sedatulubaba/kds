# Araştırma arayüzü — 13 Ekim 2026

2209-A araştırması için arayüz; özet, yöntem, kontrollü deney, sınırlılıklar ve kaynak bölümleriyle yeniden düzenlendi. Kullanıcının verdiği tasarım referansına uygun beyaz kartlar, lacivert başlıklar, yeşil/mavi vurgular ve solda adım menüsü kullanıldı. Araç ve ürün fotoğrafları sonraki çalışmaya bırakıldı.

21 açıklama konusu; giriş verilerinin rolü, HR01–HR08, M01–M06, YOLO/PaddleOCR, kullanıcı onayı, aday grupları ve deney tasarımını kapsar. Pencereler istek üzerine açılır; Escape, kapatma düğmesi ve devam düğmesiyle kapanır. Klavye odağı pencere içinde tutulur ve kapanışta açan düğmeye döner.

Deney tablosu `frontend/public/research/benchmark-ozeti.json` içindeki gerçek kayıtlı özeti kullanır. Bu dosya `results/summary.json` ile aynıdır. Veri paketi, senaryo ve entegrasyon raporlarının kopyaları aynı public dizininden indirilebilir. Benchmark yeniden üretildiğinde bu yayın kopyaları da güncellenmelidir.

Araç/ürün katalogları ve karar motoru değiştirilmedi. Mevcut gruplama ve teorik metrikler korunur. Gerçek kullanıcı örneklemi, saha doğruluk oranı veya ürün sıralaması iddia edilmez. Görsel servisin canlı yayında bağlı olmadığı gösterilir.

Doğrulama: ESLint, üretim derlemesi ve sekiz tarayıcı testi; mevcut beş karar akışı testi ile üç açıklama/benchmark/mobil testi. Canlı yayın sonrasında aynı testler üretim adresinde çalıştırılır.
