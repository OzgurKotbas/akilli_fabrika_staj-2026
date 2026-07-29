# Bedirhan Gök — Staj Projesi

## Künye
| Alan | Bilgi |
|------|-------|
| Ad Soyad | Bedirhan Gök |
| Grup | 03_Gama |
| Danışman | — |
| Üniversite | BTÜ |
| Sınıf | — |
| Başlangıç | **2026-07-27** (belge geldi ✅) |
| Staj süresi | 30 iş günü → tahmini bitiş 2026-09-04 |
| Çatı proje | [pan_tilt_robot_projesi.md](../../pan_tilt_robot_projesi.md) |
| İş paketleri | [Bedirhan_is_paketleri.md](Bedirhan_is_paketleri.md) — 16 iş paketi, ölçülebilir bitti kriterleriyle |

## Proje Tanımı
**Fabrika Nesne Algılama + Aktif Hedef Takibi** — robot köpek üstündeki pan-tilt kameranın "gözü": sahnedeki kritik nesneleri tespit eder ve seçilen hedefi kadrajda tutmak için pan-tilt kontrolüne yön sinyali üretir.

**Amaç:** Fabrika ortamı nesnelerini (insan, forklift, KKD/baret-yelek, engel) gerçek zamanlı tespit etmek; tespit edilen hedefi izleyip kadraj merkezinden sapmayı `(dx, dy)` piksel ofseti olarak KONTROL modülünün PID döngüsüne beslemek (kapalı çevrim aktif takip).

**Kapsam:** YOLO tabanlı tespit + hafif tracker (hibrit yaklaşım — [P20](../../projeler.md) deseni: korelasyon tracker'ı + periyodik YOLO düzeltmesi). Çıktı ≥15 Hz `vision/target_offset` mesajı (MQTT).

**Hedef seçim kuralı (v1 — net olsun):** sahnede birden çok tespit varsa **en yüksek güven skorlu "insan"** izlenir; manuel seçim `track_id` parametresiyle mümkün. Gelişmiş seçim stratejileri (en yakın, bölgeye giren) sonraki sürüm.

**Kullanılacak teknolojiler:** Python, YOLOv8/v11, OpenCV (CSRT/KCF), ByteTrack/Hybrid-SORT, MQTT, Colab (eğitim) → edge cihaz (çıkarım).

**Veri setleri:** COCO (person), SH17/CHV (KKD-baret/yelek), LOCO (forklift/palet — lojistik ortam), kendi pan-tilt kamera kayıtları.

## Hedefler
- [ ] **Önce tek sınıfla (insan) uçtan uca zincir** — çalıştıktan sonra forklift/KKD/engel eklenir
- [ ] **Ortak altyapı (H1, ekip için — senin öncülüğünde):** Mosquitto broker + `camera/frame` yayınlayıcı + kayıt/replay scripti
- [ ] Fabrika sınıfları için tespit modeli — **mAP@50 raporlu**
- [ ] Hibrit takip: tracker + periyodik YOLO re-init — **IDF1 + FPS raporlu**
- [ ] `(dx, dy)` ofset yayını ≥15 Hz, uçtan uca gecikme **< 100 ms** hedefi
- [ ] Masa üstü kapalı çevrim demo: pan-tilt hedefi kadrajda tutuyor (KONTROL modülüyle — seansı danışman ayarlar)
- [ ] Mini literatür (~10 makale: tracking-by-detection, aktif görüş)

## Haftalık Plan
| Hafta | Tarih | İş |
|:---:|---|---|
| 1 | 27-31 Tem | Kurulum, veri seti indirme, ~10 makale; **`target_offset` formatını kendisi dondurup dokümante et** (KONTROL modülü 03.08'de okuyarak başlar — bekleme); **ortak altyapı kurulumu** (Mosquitto + frame yayınlayıcı + kayıt/replay) |
| 2-3 | 3-14 Ağu | Colab: YOLO fine-tune + tracker entegrasyonu, baseline metrikler (mAP, IDF1, FPS) |
| 4 | 17-21 Ağu | Pan-tilt RTSP görüntüsüyle masa üstü test; MQTT yayını; PID ile ilk kapalı çevrim |
| 5 | 24-28 Ağu | Robot üstü / saha-benzeri test; ışık/titreşim dayanıklılığı (şirket içi stabilizasyon çıktısıyla dene — danışmandan iste) |
| 6 | 31 Ağu-4 Eyl | Ölçüm, ablation (tracker'lı vs tracker'sız), demo + rapor |

## Başlangıç Kaynakları
**Veri setleri:**
- [SH17](https://github.com/ahmadmughees/SH17dataset) — imalatta KKD tespiti: 8.099 görüntü, 17 sınıf; YOLO v8/v9/v10 eğitilmiş ağırlıklar repoda ([makale](https://www.sciencedirect.com/science/article/pii/S266644962400077X), 2024)
- LOCO (`github.com/tum-fml/loco`) — lojistik: forklift, palet, transpalet
- Roboflow Universe — ek KKD/fabrika setleri

**Repolar:**
- [ultralytics](https://github.com/ultralytics/ultralytics) (YOLOv8/11) + [SAHI](https://github.com/obss/sahi) (küçük nesne dilimleme)
- [ByteTrack](https://github.com/ifzhang/ByteTrack) (ECCV 2022), OC-SORT — tracking-by-detection referansları
- [PPE-Detection-YOLO-Deep_SORT](https://github.com/AnshulSood11/PPE-Detection-YOLO-Deep_SORT) — tespit+takip birleşim örneği

**Makale tohumları (H1 taraması için):** SH17 (2024), ByteTrack (2022), OC-SORT (2023), SAHI (2022), STAPLE (2016 — [P20](../../projeler.md))

> 💡 Hybrid-SORT konusunda şirket içi hazır deneyim var — ilk hafta danışmandan kısa bir bilgi aktarımı iste.

## GitHub & Takip
- [ ] Repo aç (öneri: `bgok-patrol-vision-2026`) — **fabrika görüntüsü paylaşılmaz**, açık veri setleri serbest
- [ ] Sık commit + `daily_log.md` · [Çalışma ilkeleri](../../calisma_ilkeleri.md)

## Haftalık İlerleme
| Hafta | Tarih | Yapılanlar | Durum | Notlar |
|-------|-------|------------|-------|--------|
| 1 | | | | |

## Notlar / Geri Bildirim
-
