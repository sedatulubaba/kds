# Vercel yayını

Vercel Services (beta) yapılandırması `vercel.json` içindedir. Proje kökü depo kökü olmalıdır; yalnız `frontend` seçilirse karar API'si yayınlanmaz.

- Next.js: `frontend` hizmeti, `/`.
- FastAPI ve değişmemiş Python KDS motoru: depo kökü, `backend.main:app`, `/api/*`.
- Gerçek kataloglar `data` içinde kalır. Yerel `.env`, YOLO modelleri ve OCR bağımlılıkları dağıtıma gönderilmez.

CLI ile depo kökünde `npx vercel login`, ardından `npx vercel --prod` çalıştırılır. GitHub ile import edilirse `feature/vision-kds-integration` dalı seçilir; root directory depo kökü olarak bırakılır.

`EVCSDS_CONFIRMATION_SECRET` Vercel ortam değişkenlerinde kalıcı, rastgele bir sunucu sırrı olmalıdır. OCR bağlanırken `EVCSDS_VISION_URL` erişilebilir HTTPS servis adresi ve `EVCSDS_VISION_API_KEY` sunucu anahtarı olarak eklenir. Bunları `NEXT_PUBLIC_` değişkenlerine koymayın. Yerel localhost adresleri bulutta çalışmaz.

Görsel servis bağlanmadan elle girişli karar akışı kullanılabilir. Arayüz görsel analizin yapılandırılmadığını gösterir ve analiz düğmesini kapatır. Vercel Functions istek gövdesi sınırı 4.5 MB olduğundan yereldeki 25 MB fotoğraf sınırı bulutta uygulanamaz; büyük görseller için doğrudan depolama yükleme akışı ayrıca gerekir. Görsel servisi bağlamak tek başına büyük dosya desteği sağlamaz.

Yayın sonrası `/api/health` (100 araç, 27 aday), `/api/catalog`, onaylı elle karar isteği ve mobil arayüz kontrol edilmelidir. Yerel build kontrolü, canlı yayın doğrulaması değildir.

Kaynaklar: https://vercel.com/docs/services, https://vercel.com/docs/services/routing, https://vercel.com/docs/functions/limitations

## 13 Ekim 2026 canlı yayın kontrolü

Site: https://kds-lac.vercel.app

CLI ile üretim yayını tamamlandı. Ana sayfa, `/api/health` ve `/api/catalog` herkese açık erişimde HTTP 200 döndü. 100 araç ve 27 aday doğrulandı. Canlı karar yanıtı yerel Python motorunun yanıtıyla birebir eşleşti (14 değerlendirilebilir, 4 elenen, 9 doğrulama gerekli); onaysız istek HTTP 422 ile reddedildi.

Beş Playwright testi canlı üretim adresinde geçti: karar/gerekçe/JSON indirme, düzenleme sonrası onayın sıfırlanması, bilinmeyen faz, analiz öncesi onay engeli ve mobil genişlik. Test adresi `EVCSDS_TEST_BASE_URL` ortam değişkeniyle değiştirilebilir.

Görsel servis bu yayında yapılandırılmadı (`vision_configured=false`). Elle giriş akışı çalışır; fotoğraf analizi ayrıca çevrimiçi servis bağlantısı gerektirir.
