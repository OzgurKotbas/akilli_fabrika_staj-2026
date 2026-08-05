# Görsel Anomali Tespiti ve Otomatik Devriye Raporu

Bu proje, devriye sırasında normal durumdan sapmaları (yerde bırakılmış nesne, kapatılmış acil çıkış, sızıntı vb.) tespit etmeyi ve tur sonunda otomatik olarak kanıtlı raporlar (Markdown/PDF) üretmeyi amaçlamaktadır. Özgür Kotbaş'ın staj projesinin bir parçasıdır.

## 📂 Klasör Yapısı ve İçerik

Proje daha modüler ve anlaşılır olması adına aşağıdaki yapıya göre organize edilmiştir:

* **`docs/`** 📚: Proje tanımı, literatür özetleri, akademik makaleler ve eski raporların bulunduğu dokümantasyon dizini.
* **`data/`** 🗃️: Model eğitiminde ve testinde kullanılan ham videolar (`raw_videos/`) ile çıkartılan referans karelerin (`waypoints/`) tutulduğu veri seti dizini.
* **`scripts/`** 💻: `anomalib` kullanılarak yazılmış model inferans/test kodları, referans kare çıkartma betikleri ve yapay zeka ile diyalogları barındıran `AI.md` dosyası.
* **`outputs/`** 📈: Eğitilen modellerin ürettiği sonuçlar, ısı haritaları (heatmaps) ve performans değerlendirme raporları (F1, AUROC).
* **`DOKUMANLAR/`**: Eski iş paketleri ve proje takip notlarının bulunduğu arşiv dizini.
* **`daily_log.md`**: Proje boyunca günlük ilerlemelerin kaydedildiği izleme dosyası.

## 🚀 Başlangıç ve Kullanım

Projede anomali tespiti işlemleri için [Anomalib](https://github.com/open-edge-platform/anomalib) kütüphanesinden faydalanılmaktadır. MVTec-AD üzerinde temel testi (PaDiM/PatchCore) başlatmak için:

```bash
# Scripts klasöründeki kodu çalıştırarak testi başlatın
python scripts/anomali_test.py
```
*(Not: İlk çalıştırmada MVTec-AD veri seti otomatik olarak indirilecektir.)*

Daha fazla detay ve anomali senaryoları için lütfen `docs/proje_tanimi/senaryo_listesi.md` dosyasını inceleyin.
