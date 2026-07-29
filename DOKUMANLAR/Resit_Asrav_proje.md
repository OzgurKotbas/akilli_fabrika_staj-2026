# Reşit Asrav — Staj Projesi

## Künye
| Alan | Bilgi |
|------|-------|
| Ad Soyad | Reşit Asrav |
| Grup | 03_Gama |
| Danışman | — |
| Üniversite | BTÜ |
| Sınıf | — |
| Başlangıç | **2026-07-27** (belge geldi ✅) |
| Staj süresi | 30 iş günü → tahmini bitiş 2026-09-04 |
| Çatı proje | [pan_tilt_robot_projesi.md](../../pan_tilt_robot_projesi.md) |
| İş paketleri | [Resit_is_paketleri.md](Resit_is_paketleri.md) — 16 iş paketi, ölçülebilir bitti kriterleriyle |

> 🔄 26.07 kararı: modül ataması güncellendi — gösterge okuma modülü (GÖSTERGE) bu projeye verildi.

## Proje Tanımı
**Görsel Denetim Zekâsı — Gösterge ve Panel Okuma** — devriye robotunun fabrikadaki analog/dijital göstergeleri "okuyup" sayıya çevirmesi. Fabrika devriyesinin asıl ticari değeri: insan operatörün tur atıp not aldığı ölçümleri robot otomatik toplar.

**Amaç:** RGB kamera görüntüsünden analog gösterge (ibre açısı → değer), dijital panel / 7-segment ekran, vana pozisyonu ve ikaz lambası durumunu otomatik okumak; `{gauge_id, value, unit, conf}` olarak yayınlamak.

**Kapsam:** İki aşamalı boru hattı: (1) gösterge tespiti (YOLO/detektör), (2) okuma — analog için ibre açısı geometrisi (keypoint/Hough), dijital için OCR (PaddleOCR/Tesseract + 7-segment özel model). Sentetik gösterge üretimiyle veri artırma ([D1-D9](../../projeler.md) deseni).

**Kullanılacak teknolojiler:** Python, OpenCV, YOLOv8 (gösterge tespiti), PaddleOCR, keypoint regresyonu, programatik sentetik gösterge üretimi, MQTT.

**Veri setleri:** Açık analog gauge veri setleri (Kaggle/Roboflow gauge datasets), 7-segment OCR setleri, kendi ürettiği sentetik göstergeler + pan-tilt kamera kayıtları.

## Hedefler
- [ ] **Gösterge envanteri (H1):** test göstergelerinin config dosyası — `gauge_id, tip, birim, min/max değer, açı aralığı`. Okuma **manuel kalibrasyonla** başlar (endüstride de standart yaklaşım budur); otomatik kalibrasyon kapsam dışı
- [ ] Gösterge tespit modeli — doğruluk raporlu
- [ ] Analog ibre okuma — **ortalama okuma hatası < %5** hedefi (açı→değer kalibrasyonlu)
- [ ] Dijital panel/7-segment OCR — karakter doğruluğu raporlu
- [ ] İkaz lambası / vana pozisyonu sınıflandırma (aç/kapalı, renk durumu)
- [ ] `inspect/reading` MQTT yayını + dashboard'da görünürlük
- [ ] Mini literatür (~10 makale: automatic gauge reading, industrial OCR)

## Haftalık Plan
| Hafta | Tarih | İş |
|:---:|---|---|
| 1 | 27-31 Tem | Kurulum, veri seti tarama + sentetik gösterge üreteci ilk sürüm, ~10 makale; **gösterge envanteri config'i** (hangi göstergeler test edilecek + kalibrasyon değerleri) |
| 2-3 | 3-14 Ağu | Colab: tespit + analog okuma baseline; farklı açı/ışıkta hata analizi |
| 4 | 17-21 Ağu | Dijital OCR + lamba/vana sınıflandırma; pan-tilt RTSP ile masa üstü test (duvara gösterge as) |
| 5 | 24-28 Ağu | Saha-benzeri test: eğik açıdan okuma, parlama/yansıma dayanıklılığı |
| 6 | 31 Ağu-4 Eyl | Ölçüm (okuma hatası dağılımı), demo + rapor |

## Başlangıç Kaynakları
**Makaleler (2024-25, alan taze):**
- [DialBench](https://arxiv.org/html/2511.21982v1) (2025) — ibre okumada foundation model benchmark'ı; literatürün güncel fotoğrafı
- [Pointer meters in the wild](https://www.nature.com/articles/s41598-024-81248-7) (Sci Reports 2024) — saha koşullarında okuma
- [PM-SwinUnet + YOLOX-DC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11723371/) (2025) — iki aşamalı modern boru hattı (tespit→segmentasyon→açı)
- [IoT gauge okuma çözümü](https://www.mdpi.com/2673-4001/3/4/32) — uçtan uca sistem örneği

**Repolar:**
- [Reading-Analog-Meter-Gauge-in-the-Wild](https://github.com/importrayhan/Reading-Analog-Meter-Gauge-in-the-Wild) — gerçek koşullara dayanıklı demo; başlangıç iskeleti olabilir
- [GaugereaderProject](https://github.com/Guydada/GaugereaderProject) — CNN regresyonla okuma (geometrik yaklaşımla kıyasla — güzel deney)
- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) — dijital panel okuma standardı; 7-segment için Tesseract `letsgodigital` modeli

**Veri:** Roboflow Universe "gauge" setleri (çok sayıda hazır etiketli) — H1 taraması buradan başlasın.

## GitHub & Takip
- [ ] Repo aç (öneri: `rasrav-gauge-vision-2026`) — **fabrika görüntüsü paylaşılmaz**, açık/sentetik veri serbest
- [ ] Sık commit + `daily_log.md` · [Çalışma ilkeleri](../../calisma_ilkeleri.md)

## Haftalık İlerleme
| Hafta | Tarih | Yapılanlar | Durum | Notlar |
|-------|-------|------------|-------|--------|
| 1 | | | | |

## Notlar / Geri Bildirim
-
