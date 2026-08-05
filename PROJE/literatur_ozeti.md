# Mini Literatür Özeti — Anomali Tespiti
**Tarih:** Temmuz 2026 · **İş Paketi:** İP4 · **Özgür Kotbaş**

Kaynak: [awesome-industrial-anomaly-detection](https://github.com/M-3LAB/awesome-industrial-anomaly-detection)

## Temel Makaleler

| # | Makale | Yıl | Yöntem | Neden Önemli |
|---|--------|-----|--------|--------------|
| 1 | PatchCore — "Towards Total Recall in Industrial Anomaly Detection" | CVPR 2022 | Memory bank + kNN | **Birincil model seçimimiz** — MVTec'te AUROC=1.0 |
| 2 | PaDiM — "Patch Distribution Modeling Framework" | 2020 | Multivariate Gaussian | Hafif, edge'e uygun; ikincil aday |
| 3 | MVTec AD Dataset | CVPR 2019 | Benchmark | Standart veri seti — kendi çalışmamızın referansı |
| 4 | EfficientAD | WACV 2024 | Knowledge distillation | Hız odaklı — edge robot için |
| 5 | FastFlow | 2021 | Normalizing flow | Gerçek zamanlı inference |
| 6 | SSCDNet (Sakurada) | 2015 | CNN fark analizi | Street-scene change detection — "altın tur"un akademik karşılığı |
| 7 | VisA Dataset | ECCV 2022 | Benchmark | 12 ürün, 9621 görüntü — alternatif veri seti |
| 8 | WinCLIP | CVPR 2023 | Zero-shot + CLIP | Az veriyle çalışır; waypoint senaryosu için ilginç |
| 9 | RD4AD | CVPR 2022 | Reverse distillation | Hafif lokalizasyon |
| 10 | SimpleNet | CVPR 2023 | Basit MLP üstü | Hız/doğruluk dengesi |

## Proje İçin Çıkarımlar

1. **PatchCore seçimi doğrulandı** — staj süresinde az veriyle çalışması kritik
2. **"Altın tur" fikrinin akademik karşılığı var** — SSCDNet ve change detection literatürü
3. **Yanlış alarm (false positive) ana sorun** — hemen hemen tüm makalelerde bahsediliyor; alarm yorgunluğu tasarım ilkemiz doğru
4. **Waypoint bazlı kıyas orijinal** — sürekli hizalama yerine duraklı kıyas literatürde az işlenmiş → bu yenilikçi bir açı
