# Algılama + Aktif Takip — İş Paketleri (Bedirhan Gök)

**Çatı proje:** [pan_tilt_robot_projesi.md](../../pan_tilt_robot_projesi.md) · **Proje dosyası:** [Bedirhan_Gok_proje.md](Bedirhan_Gok_proje.md) · **Tarih:** 27.07.2026

Proje 16 iş paketine bölünmüştür. Her iş paketi 0,5-2 günlüktür ve **ölçülebilir bir "bitti" kriteri** vardır — paket ya bitti ya bitmedi. Günlük commit'lerde iş paketi numarasını yaz (örn. `İP8: hibrit tracker calisiyor`).

> **Altın kural:** Takıldığın iş paketi 1 günü aşarsa not düş, danışmana sor, mümkünse sonrakine geç (2 saat kuralı).

---

## H1 — Altyapı + Isınma (27-31 Tem) *(İP1-İP2 tüm ekip için — sen kuruyorsun)*

| # | İş paketi | Ne yapılır | ✅ Bitti kriteri |
|---|-------|-----------|------------------|
| İP1 | **Ortak altyapı: broker + yayıncı** | Mosquitto kur; webcam/videodan `camera/frame` yayınlayan script | İkinci bir terminaldeki abone frame'leri alıyor |
| İP2 | **Kayıt/replay aracı** | Video + MQTT mesajlarını zaman damgalı kaydet, tekrar oynat | Kayıtlı akış yeniden oynatılınca aynı çıktı üretiliyor (ekip bununla cihazsız çalışacak) |
| İP3 | İlk tespit | SH17 + LOCO indir; hazır YOLOv8 ağırlığıyla örnek çıkarım | Örnek görüntüde kutulu çıktı |
| İP4 | **Sözleşme dondurma** | `vision/target_offset` şemasını yaz + örnek mesajlarla dokümante et (KONTROL modülü 03.08'de okuyarak başlayacak — bekleme) | Çatı dokümanda güncel şema + örnek mesaj commit'li |
| İP5 | Mini literatür | ~10 makale (tracking-by-detection, aktif görüş, KKD tespiti) | Özet tablosu repoda |

## H2 — Tek Sınıf Zinciri (3-7 Ağu)

| # | İş paketi | Ne yapılır | ✅ Bitti kriteri |
|---|-------|-----------|------------------|
| İP6 | Canlı insan tespiti | COCO hazır ağırlıkla "insan" sınıfı, webcam/pan-tilt canlı | Canlı videoda insan kutusu, **≥10 FPS** |
| İP7 | SH17 fine-tune | Colab'da KKD sınıfları (baret/yelek) eğitimi | **mAP@50 tablosu** (val set) commit'li |
| İP8 | Hibrit tracker | CSRT/KCF tek hedef + periyodik YOLO re-init ([P20](../../projeler.md) deseni) | Kesikli tespitte ID sabit kalan iz videosu |

## H3 — Ofset Zinciri + İlk Ölçüm (10-14 Ağu)

| # | İş paketi | Ne yapılır | ✅ Bitti kriteri |
|---|-------|-----------|------------------|
| İP9 | Hedef seçimi + (dx,dy) | Seçim kuralı v1 (en yüksek conf'lu insan); kadraj merkezinden sapma hesabı | Ekranda hedefe ofset oku çizili canlı görüntü |
| İP10 | Ofset yayını | MQTT `vision/target_offset` **≥15 Hz**; uçtan uca gecikme ölçümü | Gecikme (ms) raporlu; sahte-abone ile doğrulanmış |
| İP11 | İlk takip metriği | Kısa klip etiketle (CVAT/labelImg, ~200 kare) → py-motmetrics | **İlk MOTA/IDF1 tablosu** commit'li |

## H4 — Kapalı Çevrim (17-21 Ağu) *(KONTROL modülünün kalibrasyon haftasıyla hizalı)*

| # | İş paketi | Ne yapılır | ✅ Bitti kriteri |
|---|-------|-----------|------------------|
| İP12 | 🎉 **Kapalı çevrim** | KONTROL modülünün PID'ine canlı ofset besle (seansı danışman ayarlar) — masa üstü: kamera→AI→PID→servo | **Pan-tilt, yürüyen kişiyi kadrajda tutuyor** (video kanıtlı) |
| İP13 | Çoklu sınıf genişleme | Forklift + KKD + engel sınıfları aktif; sınıf öncelik mantığı | Güncellenmiş mAP tablosu + seçim kuralı çoklu sınıfla çalışıyor |

## H5 — Dayanıklılık (24-28 Ağu)

| # | İş paketi | Ne yapılır | ✅ Bitti kriteri |
|---|-------|-----------|------------------|
| İP14 | Zor koşullar | Düşük ışık, titreşim; şirket içi stabilizasyon ön-işlemesiyle kıyas (çıktıyı danışmandan iste) | Ön-işlemeli vs ön-işlemesiz metrik kıyası |
| İP15 | Yanlış alarm ayarı | Eşik/NMS ayarları; kaçırma-yanlış alarm dengesi | Ayar öncesi/sonrası tablo + seçilen çalışma noktası gerekçeli |

## H6 — Kapanış (31 Ağu-4 Eyl)

| # | İş paketi | Ne yapılır | ✅ Bitti kriteri |
|---|-------|-----------|------------------|
| İP16 | Ablation + teslim | Hibrit (tracker'lı) vs YOLO-only: FPS/IDF1 dengesi; final tablo; ekip demosuna katkı; rapor | **4 Eyl ekip demosu hazır** — kapalı çevrim + metrikler |

---

## İlerleme Takibi
| İş paketi | Durum | Tarih | Not |
|:---:|:---:|---|-----|
| İP1 | ⬜ | | |
| İP2 | ⬜ | | |
| İP3 | ⬜ | | |
| İP4 | ⬜ | | |
| İP5 | ⬜ | | |
| İP6 | ⬜ | | |
| İP7 | ⬜ | | |
| İP8 | ⬜ | | |
| İP9 | ⬜ | | |
| İP10 | ⬜ | | |
| İP11 | ⬜ | | |
| İP12 | ⬜ | | |
| İP13 | ⬜ | | |
| İP14 | ⬜ | | |
| İP15 | ⬜ | | |
| İP16 | ⬜ | | |

> Tasarım notları: **İP1-İP2 ekip hizmetidir** — ilk iki gün "başkaları için altyapı" kurmak sıkıcı gelebilir ama üç kişinin önünü açar (ve DevOps refleksi kazandırır). **İP12 projenin kalbi** — KONTROL modülüyle ortak an; danışman o haftayı iki tarafın takviminde işaretler. Geride kalırsan İP13 (çoklu sınıf) ve İP14 kırpılabilir; **İP10 ve İP12 feda edilemez** — ofset yayını + kapalı çevrim bu modülün varlık sebebi.
