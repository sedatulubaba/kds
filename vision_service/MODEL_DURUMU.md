# Model durumu

## Elektrik sayacı

- YOLO tespiti, ortak OCR motoru ve faz çıkarımı API'ye bağlıdır.
- Model CUDA varsa GPU'da, OCR Windows kararlılığı için CPU'da çalışır.
- Düşük veya çelişkili faz kanıtında kesin sonuç uydurmak yerine `bilinmiyor` döner.

## Elektrik faturası

- Etkin ağırlık: `runs/detect/electricity_bill_detection_v2/weights/best.pt`
- YOLO güveni ve fatura anahtar kelimeleri birlikte doğrulanır.
- Güvenilir kutu bulunamazsa tüm görsel parçalara ayrılarak OCR uygulanır.
- Mevcut Roboflow etiketlerinin yaklaşık tamamı tam-kare olduğundan model gerçek
  sahnede fatura sınırı tespiti için henüz üretim seviyesinde değildir.
- Sentetik sahnelerle eğitilen v3 ağırlığı gerçek test görselini geçemediği için
  API'ye alınmamıştır.

## Yeni fatura veri seti kabul ölçütleri

1. Eğitim, doğrulama ve test kümeleri farklı gerçek telefon çekimlerinden oluşmalı.
2. Her kutu yalnızca faturanın dış kenarlarını sıkıca çevrelemeli.
3. Masa, kumaş, zemin, gölge, eğiklik, farklı ışık ve uzaklık örnekleri bulunmalı.
4. Fatura bulunmayan negatif görseller eklenmeli.
5. Ayrı tutulan gerçek saha testlerinde yanlış pozitifler ayrıca ölçülmeli.
6. Model, kullanıcı test görsellerinde kutu ve OCR doğrulamasını geçmeden etkin
   ağırlığın yerine konmamalı.
