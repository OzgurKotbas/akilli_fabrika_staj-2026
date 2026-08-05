# Görsel Anomali Tespiti ve Otomatik Devriye Raporu

Bu proje, devriye sırasında normal durumdan sapmaları (yerde bırakılmış nesne, kapatılmış acil çıkış, sızıntı vb.) tespit etmeyi ve tur sonunda otomatik olarak kanıtlı raporlar (Markdown/PDF) üretmeyi amaçlamaktadır. Özgür Kotbaş'ın staj projesinin bir parçasıdır.

## Klasör Yapısı ve İçerik (Mevcut Çalışma Dizini)

* **`AI.md`**: Projenin geliştirilmesi sırasında alınan notları veya sistem kayıtlarını barındıran doküman.
* **`anomali_test.py`**: `anomalib` kütüphanesini (PaDiM modeli) kullanarak MVTec-AD veri seti üzerinde anomali tespiti yapan, model eğitimini ve test görüntüleri üzerinden anomali ısı haritası (heatmap) çıktısı almayı sağlayan örnek Python kodu.
* **`RAPORLAR/`**: Sistem tarafından oluşturulan çıktıların ve devriye raporlarının saklandığı dizin. (Örn: `rapor.md`)
* **`results/`**: Çalıştırılan anomali tespiti modellerinin (şu an için `Padim`) ağırlık, değerlendirme ve çıktı sonuçlarının kaydedildiği dizin.

## Başlangıç ve Kullanım

Projede anomali tespiti işlemleri için [Anomalib](https://github.com/open-edge-platform/anomalib) kütüphanesinden faydalanılmaktadır.

Anomali tespiti temel örneğini çalıştırmak için:
```bash
python anomali_test.py
```
*(Not: İlk çalıştırmada MVTec-AD veri seti otomatik olarak indirilecektir.)*

Daha fazla detay ve hedeflenen iş paketleri için lütfen `DOKUMANLAR\Ozgur_Kotbas_proje.md` dosyasını inceleyin.




