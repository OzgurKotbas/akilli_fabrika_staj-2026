# Akıllı Fabrika Staj 2026 — Teknik Sunum Raporu

## Pan-Tilt Devriye Robotu: Üç Stajyer, Üç Görüntü İşleme Modülü

> **Tarih:** 7 Eylül 2026
> **Kapsam:** Üç GitHub reposunun derinlemesine (kod + döküman + bağımlılık) incelemesi
> **Repolar:**
> - [Bedirhangok/Akilli_Fabrika_Staj-2026](https://github.com/Bedirhangok/Akilli_Fabrika_Staj-2026) — Bedirhan Gök — VİZYON/ALGILAMA modülü
> - [resitasrav/rasrav-gauge-vision-2026](https://github.com/resitasrav/rasrav-gauge-vision-2026) — Reşit Asrav — GÖSTERGE/PANEL OKUMA modülü
> - [OzgurKotbas/akilli_fabrika_staj-2026](https://github.com/OzgurKotbas/akilli_fabrika_staj-2026) — Özgür Kotbaş — ANOMALİ TESPİTİ + DEVRİYE RAPORU modülü

> **Analiz yöntemi:** Her repo `git clone --depth 1` ile indirilmiş; tüm README, günlük log, literatür özeti, iş paketi, config ve kod dosyaları satır satır okunmuş; bağımlılık dosyaları (`requirements.txt`, `pyproject.toml`, `.gitignore`) ve çıktı JSON'ları doğrulanmıştır. Aşağıdaki dosya yolu ve satır numarası referansları doğrudan bu incelemelerden alınmıştır.

---

## İçindekiler

1. [Yönetici Özeti](#1-yönetici-özeti)
2. [Çatı Proje ve Ortak Mimari](#2-çatı-proje-ve-ortak-mimari)
3. [Repo 1 — Bedirhan Gök (VİZYON / ALGILAMA)](#3-repo-1--bedirhan-gök-vizyon--algılama)
4. [Repo 2 — Reşit Asrav (GÖSTERGE / PANEL OKUMA)](#4-repo-2--reşit-asrav-gösterge--panel-okuma)
5. [Repo 3 — Özgür Kotbaş (ANOMALİ + DEVRİYE RAPORU)](#5-repo-3--özgür-kotbaş-anomali--devriye-raporu)
6. [Teknoloji Karar Matrisi](#6-teknoloji-karar-matrisi)
7. [Karşılaştırmalı Mimari Tablosu](#7-karşılaştırmalı-mimari-tablosu)
8. [Çıktıya Etki Analizi](#8-çıktıya-etki-analizi)
9. [Benzerlikler ve Farklılıklar](#9-benzerlikler-ve-farklılıklar)
10. [Riskler, Sınırlamalar ve Açık Konular](#10-riskler-sınırlamalar-ve-açık-konular)
11. [Sunum Konuşma Notları](#11-sunum-konuşma-notları)
12. [Ek: Kanıt Dosya Yolları](#12-ek-kanıt-dosya-yolları)

---

### 1. Yönetici Özeti

Üç repo, BTÜ 03_Gama Grubu'nun 2026 yaz stajı (27 Temmuz – 4 Eylül 2026) kapsamında geliştirilen **pan-tilt kameralı akıllı fabrika devriye robotu**nun görüntü işleme katmanını oluşturur.Robot bir köpek formunda mobil platformdur; üzerindeki pan-tilt kamera fabrika ortamını tarar. Her stajyer, robotun "görme" yeteneğinin farklı bir boyutundan sorumludur ve modüller birbirleriyle **MQTT pub/sub** mimarisi üzerinden, donmuş JSON şemaları üzerinden haberleşir.

| Stajyer | Modül | MQTT Topic'i | Birincil Görev | Çekirdek Teknoloji |
|---|---|---|---|---|
| **Bedirhan Gök** | VİZYON (ALGILAMA) | `vision/target_offset` | İnsan/forklift/KKD tespiti + aktif hedef takibi | YOLOv8 + ByteTrack |
| **Reşit Asrav** | GÖSTERGE | `inspect/reading` | Analog/dijital gösterge, ikaz lambası, vana, keypad okuma | OpenCV + NumPy (torch'suz çekirdek) + YOLOv8 tespit |
| **Özgür Kotbaş** | ANOMALİ | `patrol/alert` | "Altın tur" referansıyla anomali tespiti + otomatik rapor | MOG2 + PatchCore ensemble + anomalib |

Üç modül de **tek bir fiziksel akışın** parçalarıdır: kamera görüntüsü → VİZYON tehlikeleri/insanları bulur ve pan-tilt'i takibe yönlendirir → GÖSTERGE çevredeki ölçüm cihazlarını okur → ANOMALİ sahneyle referans arasındaki farkları (yabancı nesne, kapanan çıkış, sızıntı) tespit edip kanıtlı rapor üretir. Her modül farklı bir bilgisayarlı görü paradigması kullanır: **nesne tespiti (detection + tracking)**, **gösterge okuma (geometric/OCR)**, **anomali tespiti (unsupervised / reconstruction)**.

Üç stajyer de **Python** ortak dilinde, **OpenCV** ortak görüntü işleme katmanında ve **paho-mqtt + Mosquitto** ortak haberleşme katmanında birleşir. Ancak her biri görevinin doğasına uygun farklı yapay zeka omurgası seçmiştir: Bedirhan **YOLOv8** (denetimli, gerçek zamanlı tespit), Reşit **YOLOv8 + klasik görüntü işleme** (gömülü taşınabilir, torch'suz çekirdek), Özgür **PatchCore/PaDiM** (denetimsiz, "sadece normali görerek" öğrenme). Bu seçimler çıktıyı doğrudan şekillendirmiştir: ≥20 FPS canlı takip, %0.19 analog okuma hatası, AUROC=1.0 anomali doğruluğu ve otomatik PDF devriye raporu.

Üç repo da staj dönemi içinde "akademik prototip"ten "production-ready"yaklaşımına evrilmiştir: config-driven yapılandırma, modüler paket yapısı, hata toleransı (retry/offline mod) ve ölçüm odaklı eşik seçimi öne çıkan ortak disiplinlerdir.

---

### 2. Çatı Proje ve Ortak Mimari

#### 2.1. Robot ve Görev

Pan-tilt kameralı devriye robotu, fabrika koridorlarında otonom tur atan bir platformdur. Robotun üç temel "göz" yeteneği vardır:

1. **Tehlike ve insan tespiti** — kimlerin/neyin sahede olduğunu bulmak ve en kritik hedefi kadrajda tutmak (Bedirhan).
2. **Saha ölçüm cihazlarını okumak** — operatörün elle yaptığı gösterge okuma turunu otomatikleştirmek (Reşit).
3. **"Bir şeyler yolunda değil" deme yeteneği** — altın (referans) tur ile canlı tur arasındaki farkları bulmak (Özgür).

#### 2.2. Üç Modülün MQTT Üzerindeki Sözleşmesi

Modüller birbirlerinin koduna değil, **donmuş MQTT JSON şemalarına** bağlıdır. Bu, üç stajyerin paralel ve bağımsız geliştirebilmesini sağlayan mimari karar:

| Topic | Yayıncı | Abone | Payload | Frekans / Hedef |
|---|---|---|---|---|
| `camera/frame` | publisher (Bedirhan'ın altyapısı) | tüm modüller | `{ts, frame_w, frame_h, seq, frame:<base64 JPEG>}` | canlı akış |
| `vision/target_offset` | Bedirhan (VİZYON) | KONTROL modülü | `{ts, track_id, class, conf, dx, dy, frame_w, frame_h}` | ≥15 Hz (gerçekte ~20 FPS) |
| `inspect/reading` | Reşit (GÖSTERGE) | operatör paneli | `{ts, schema:1, source, img_ref, gauge_id, type, value, unit, conf, status, raw_angle}` | tur bazlı |
| `patrol/alert` | Özgür (ANOMALİ) | operatör/rapor | `{type, severity, waypoint, score, det_count, fg_ratio, img_ref, ts, ...}` | tur bazlı |

Bedirhan'ın `docs/target_offset_schema.md`'i **"Durum: Donduruldu (Frozen) ❄️"** notuyla bir şema sözleşmesi tanımlar; `vision/target_offset` QoS 0, ≥15 Hz (hedef 30 Hz) yayınlar. Koordinat ekseni kadraj merkezidir: `dx<0` nesne solda (pan sola), `dx>0` sağda. Hedef yoksa `track_id: -1` gönderilir; KONTROL modülü 1 sn'den fazla mesaj almazsa hedefi kayıp kabul eder. Bu şema, "İP10 ve İP12 feda edilemez" kuralıyla koruma altına alınmıştır.

Reşit'in `publish/reading.py`'i **broker yoksa otomatik dosya moduna** düşer (JSONL `outputs/mqtt/`), böylece broker bağımlılığı yayının doğruluğunu ölçmeyi engellemez. Özgür'ün `ip10_mqtt_yayini.py`'si de aynı `--offline` disiplini uygular. Yani üç modül de "broker her zaman ayakta değil" gerçeğini tasarımın içine yedirmiştir.

#### 2.3. Ekip İçi Bağlar ve Uyuşmazlık Yönetimi

Üç modül, ortak üst proje `pan_tilt_robot_projesi.md` etrafında senkronize çalışır. Özgür'ün reposu, Bedirhan ve Reşit'in proje tanımlarını ve iş paketlerini (`DOKUMANLAR/Bedirhan_Gok_proje.md`, `DOKUMANLAR/Resit_Asrav_proje.md` vb.) barındırır — yani Özgür'ün reposu bir bakıma ekibin **doküman merkezi** işlevini de görmüştür. Reşit'in reposundaki `demo/uyusmazliklar/RAPOR.md` (220 satır), üç modülün "ortak sözleşme öncülü" ile gerçek proje arasındaki uyuşmazlıkları tarar: örneğin ALGILAMA/ANOMALİ modüllerinde başlangıçta kare-bazlı `f(kare)→sonuç` fonksiyonu yoktu (🔴 kızıl işaret). 27 Ağustos güncellemesiyle ANOMALİ, Özgür'ün kendi `AlgilayiciMOG2` sınıfıyla çalışmaya başlamış, PaDiM yedek konuma çekilmiştir. Reşit'in `waypoint_gosterge_sozlugu.yaml`'ı Özgür'ün waypoint'leri (WP01-03) ile Reşit'in gauge kimliklerini (PT-101, TI-205 vb.) eşler — bu, modüller arası köprüdür. Hazırlayan olarak "Özgür Kotbaş, 2026-08-17" imzası vardır.

#### 2.4. Ortak Geliştirme Disiplinleri

Üç repo da şu disiplinleri paylaşır:

- **Fabrika görüntüsü repoya giremez.** Üç repo da public/PRIVATE karışımı kuralla, fabrika görsellerini `.gitignore` ile korur (Bedirhan `*.pt`, Reşit `data/real/*` ve `*.mp4`, Özgür `data/raw_videos/` harici).
- **İP (iş paketi) bazlı yönetim.** Her repo 16 iş paketinden (İP1–İP16) oluşur, her birinin ölçülebilir "bitti kriteri" vardır.
- **Literatür öncülü.** Her stajyer 9–13 makalelik mini literatür taraması yapmış ve kararlarını akademik referanslarla gerekçelendirmiştir.
- **Haftalık plan + günlük log.** 6 haftalık staj planı ve ters kronolojik `daily_log.md` / `devam_notu.md` tutulmuştur.
- **Ekip demosu 4 Eylül'de.** Üç modül de bu tarihe yetiştirilmiştir (Bedirhan ve Reşit tamam, Özgür'de İP16 final bekliyor).

---

### 3. Repo 1 — Bedirhan Gök (VİZYON / ALGILAMA)

#### 3.1. Repo Kimliği ve Proje Amacı

| Alan | Değer |
|---|---|
| Repo | [Bedirhangok/Akilli_Fabrika_Staj-2026](https://github.com/Bedirhangok/Akilli_Fabrika_Staj-2026) |
| İçerideki proje adı | `bgok-patrol-vision-2026` |
| Sahip | Bedirhan Gök |
| Kurum/Grup | BTÜ · 03_Gama Grubu |
| Staj dönemi | 27.07.2026 – 04.09.2026 |
| Modül | VİZYON (Algılama) → `vision/target_offset` |
| Kaynak | [GitHub repo](https://github.com/Bedirhangok/Akilli_Fabrika_Staj-2026) |
| Tek commit | `25c15f9` "Proje Kapanışı: İP15 ve İP16 logları girildi, proje başarıyla tamamlandı" (tüm geçmiş squash'lanmış) |

Bedirhan'ın modülü, robot köpeğin üzerindeki pan-tilt kameranın "gözü" görevini görür. Fabrika ortamındaki kritik nesneleri (insan, forklift, KKD/baret-yelek, engel) gerçek zamanlı tespit eder; seçilen hedefi izleyip kadraj merkezinden sapmayı `(dx, dy)` piksel ofseti olarak **KONTROL modülünün PID döngüsüne** besler (kapalı çevrim aktif takip). Geleneksel güvenlik kameralarının aksine pasif izleme yerine, tehlikeyi (baret/yelek takmayanlar, yere düşen işçiler) tespit edip pan-tilt motorlarına anlık ofset verileri göndererek aktif takip sağlar.

#### 3.2. Dosya Yapısı

Repo toplam **1707 satır** (kod + döküman), 10 Python scripti + 3 markdown dökümanı + `requirements.txt` + `.gitignore`'dan oluşur. Dört klasör: `infra/` (publisher, subscriber, recorder, replayer), `vision/` (detector, live_detector, evaluate_tracker, train), `scripts/` (calculate_metrics, simulate_harsh_conditions), `docs/` (final_report, literature_summary, target_offset_schema).

Ana modül **`vision/live_detector.py`** (282 satır) — tespit, takip, ofset hesaplama, MQTT yayını, Lock-on ve Priority mantığını tek dosyada birleştirir.

#### 3.3. Kullanılan Yazılımlar ve Neden Seçildiği

Bedirhan'ın teknoloji yığını **"gerçek zamanlı aktif takip"** gereksinimi etrafında şekillenmiştir. Her seçim, dökümanlarda gerekçelendirilmiştir:

##### Yapay Zeka / Bilgisayarlı Gör

| Teknoloji | Kanıt | Kullanım Nedeni |
|---|---|---|
| **YOLOv8 (Ultralytics)** | `requirements.txt:5` (`ultralytics>=8.0.0`); `live_detector.py:19`; `literature_summary.md:14` | Gerçek zamanlı tespit için omurga model. Literatür özetinde "tek-aşama anchor-free detektör" olarak gerekçelendirildi. **Dokümanda açıklanmış.** |
| **ByteTrack** | `live_detector.py:137` (`model.track(...persist=True)`); `literature_summary.md:15` (Zhang ECCV 2022) | Low-score tespitleri takibe katarak ID tutarlılığı sağlar. Occlusion'da hedef kaybını önler. **Dokümanda açıklanmış.** |
| **PyTorch (torch)** | `train.py:106-107` (`torch.cuda.is_available()`) | YOLO fine-tune için GPU (CUDA) backend. **Çıkarım: GPU erişimi için.** |
| **kagglehub** | `train.py:26-29` | Kaggle'dan PPE veri setini programatik indirme. |
| **OpenCV** | `requirements.txt:6`; `publisher.py:12`, `live_detector.py:13` | Webcam/video açma, görüntü işleme, JPEG encode/decode, çizim, HSV dönüşümü. Literatürde STAPLE/KCF/CSRT hibrit tracker omurgası olarak referans alındı. **Dokümanda açıklanmış.** |
| **NumPy** | `requirements.txt:7` | Dizi/matris işlemleri, frame buffer, warpAffine transform matrix. |
| **MOTMetrics** | `requirements.txt:13`; `calculate_metrics.py:14` | İP11: MOTA/IDF1 takip metrikleri hesaplama (`mm.MOTAccumulator`, `mm.distances.iou_matrix`). |
| **Pandas** | `requirements.txt:14`; `calculate_metrics.py:15` | MOT16 formatındaki GT/prediction TXT'lerini CSV olarak okuma. |
| **PyYAML** | `train.py:12,88,95` | YOLO `dataset.yaml` okuma/yazma, yolları mutlak hale getirme. |
| **SAHI** (referans) | `literature_summary.md:17` (Akyon 2022) | Küçük nesneler için dilimleme çıkarım — **"gerekirse entegre edilecek"**, kodda değil, sadece literatür referansı. |

##### Haberleşme

| Teknoloji | Kanıt | Neden |
|---|---|---|
| **paho-mqtt** | `requirements.txt:10`; `live_detector.py:18`, `publisher.py:13` | Modüller arası hafif, düşük gecikmeli mesajlaşma. |
| **Mosquitto Broker** | `README.md:114`, `daily_log.md:120` | Yerel MQTT broker (localhost:1883). |
| **base64 + JSON** | `publisher.py:14-15`, `live_detector.py:17` | Binary JPEG frame'leri MQTT üzerinden text olarak taşımak için. |

##### Eğitim / Geliştirme Ortamı

| Teknoloji | Kanıt | Neden |
|---|---|---|
| **Google Colab / Kaggle (T4 GPU)** | `README.md:28`, `train.py:5-6`, `daily_log.md:65` | GPU erişimi için bulut notebook ortamı. README Colab der ama kod Kaggle uyumlu yazılmış. |
| **Conda** | `README.md:109` | Python sanal ortam yönetimi (`conda create -n patrol-vision python=3.10`). |
| **argparse** | tüm scriptlerde | Standart CLI arayüz. |

##### Veri Setleri

| Veri Seti | Kanıt | Neden |
|---|---|---|
| **COCO** | `README.md:38`, `detector.py:20` | İnsan tespiti için pretrained YOLO ağırlıkları. |
| **SH17** (planlanan) | `README.md:39` (8099 görüntü, 17 sınıf) | KKD tespiti için — **ama Kaggle'dan kaldırıldığı için alternatife geçildi.** |
| **shlokraval/ppe-dataset-yolov8** (gerçek) | `train.py:69`, `daily_log.md:65` | SH17 alternatifi PPE veri seti. README güncellenmemiş, gerçek eğitimde bu kullanıldı. |
| **LOCO** (referans) | `README.md:40`, `literature_summary.md:23` | Fabrika forklift/engel — **kodda kullanılmamış**, sadece referans. |

##### Algoritmalar / Yöntemler

| Yöntem | Kanıt | Neden |
|---|---|---|
| **NMS (Non-Maximum Suppression)** | `live_detector.py:55` (`--iou 0.45`), `final_report.md:9` | Yan yana hedeflerin mükerrer sayımını önleme. |
| **Confidence thresholding** | `live_detector.py:54` (`--conf 0.6`) | Hatalı kilitlenme önleme; confidence 0.4→0.6 yükseltildi. |
| **Lock-on (Hedef Kilitlenme)** | `live_detector.py:109,151-164` | Hedefin kadrajdan çıkana kadar `track_id` korunması, ID-Switch azaltma. |
| **Sınıf Öncelik (Priority) Puanlama** | `live_detector.py:25-46`, `final_report.md:24-28` | Aciliyet sırasına göre hedef seçimi: Düşen işçi=100, KKD ihlali=90, Person=50. |
| **PID Kontrol (KONTROL modülü)** | `README.md:15`, `target_offset_schema.md:51` | `(dx,dy)` ofsetini pan-tilt motor kontrolüne besleme — VİZYON üretir, KONTROL tüketir. |
| **Retry / Hata Toleransı** | `live_detector.py:98-130` | Kamera kopması ve Wi-Fi kesintilerine karşı dayanıklılık. |
| **HSV parlaklık düşürme + Affine titreşim** | `simulate_harsh_conditions.py:27-42` | İP14 zor koşul test verisi üretme (karanlık `%60`, `±15px` kaydırma). |

#### 3.4. Çıktı ve Teknoloji Seçiminin Çıktıya Etkisi

**Ana çıktı**, `vision/target_offset` topic'ine ≥15 Hz (gerçekte ~20 FPS) ile yayınlanan JSON mesajlarıdır:

```json
{"ts": ..., "track_id": 1, "class": "person", "conf": 0.92, "dx": -45, "dy": 12, "frame_w": 640, "frame_h": 480}
```

Bu mesaj KONTROL modülü tarafından pan-tilt motor PID döngüsüne beslenir. Hedef yoksa `track_id: -1` gönderilir.

Teknoloji seçimlerinin çıktıya etkisi:

- **YOLOv8 + ByteTrack** seçimi gerçek zamanlı (~30 FPS canlı, ~20 FPS MQTT yayın) çıkarım sağladı; ≥15 Hz ve ≥10 FPS bitti kriterleri aşıldı. ByteTrack sayesinde occlusion'da ID korunması ve pürüzsüz pan-tilt kontrolü mümkün oldu.
- **Edge + hafif model (yolov8n/best.pt)** düşük gecikmeli çıkarım; QoS 0 ile en düşük gecikme hedeflendi.
- **MQTT + base64 JPEG** modüler mimari (VİZYON, KONTROL, GÖSTERGE, ANOMALİ ayrı süreçler) ve ekip içi paralel geliştirmeyi mümkün kıldı.
- **Sınıf Öncelik Mimarisi** kalabalık sahnede "ilk bulduğunu takip et" yerine aciliyet sıralı hedef seçimi sağladı → acil durum (düşen işçi) önceliği.
- **NMS/Confidence tuning (conf=0.6, iou=0.45)** yanlış alarm azaltma ve hatalı kilitlenme önleme → pan-tilt titreme çözüldü.
- **Retry mekanizmaları** kamera/MQTT kopmalarında çökme önledi → sistem dayanıklılığı.

Eğitilmiş `best.pt` modeli (Kaggle'da `shlokraval/ppe-dataset-yolov8` ile fine-tune) 14 sınıf tanır: Fall-Detected, NO-Hardhat, NO-Safety Vest, NO-Gloves, NO-Goggles, NO-Mask, Person, Ladder, Safety Cone, Hardhat, Safety Vest, Gloves, Goggles, Mask. Model dosyası repoda yok (`.gitignore` `*.pt` engeller).

#### 3.5. Mimari ve Çalışma Akışı

Sistem, MQTT broker etrafında modüler bir publish/subscribe mimarisidir. Kapalı çevrim akış:

```
[Görüntü Kaynağı] → publisher.py → MQTT(camera/frame, base64 JPEG)
                                                        ↓
                                     live_detector.py (YOLO + ByteTrack)
                                                        ↓
                              vision/target_offset (dx,dy,track_id) → [KONTROL modülü]
                                                                            ↓
                                                          Pan-Tilt PID kontrol → kamera açısı değişir
```

Önemli not: README'de publisher'ın frame yayıncı, live_detector'ın abone olduğu izlenimi var; ama gerçekte `live_detector.py` MQTT'ten frame almıyor, doğrudan `cv2.VideoCapture` ile kameradan okuyor. `camera/frame` topic'ini sadece `subscriber.py` (test aracı) tüketiyor. Yani publisher→live_detector MQTT zinciri kullanılmıyor.

#### 3.6. Sınıf Öncelik Mimarisi

```python
PRIORITY_SCORES = {
    "Fall-Detected": 100,       # Acil durum
    "NO-Hardhat": 90, "NO-Safety Vest": 90,  # KKD ihlali
    "NO-Gloves": 80, "NO-Goggles": 80, "NO-Mask": 80,
    "Person": 50,               # Normal insan
    "Ladder": 40, "Safety Cone": 40,  # Engel
    "Hardhat": 10, "Safety Vest": 10, ...  # Giyilmiş KKD (düşük)
}
# Hedef seçimi: max(base_priority + confidence)
```

#### 3.7. Eksiklikler ve Tutarsızlıklar

Bedirhan'ın reposunda, README ile gerçek kod arasında bir dizi tutarsızlık ve eksiklik vardır:

- **Ölü linkler / olmayan dosyalar:** README `docs/is_paketleri.md`, `vision/tracker.py`, `vision/offset_publisher.py`'ı linkliyor ama bunlar repoda yok. Tracker ve ofset yayını `live_detector.py` içine gömülü.
- **`best.pt` ve veri setleri repoda değil** (`.gitignore` `*.pt`, `data/`, `models/`).
- **README teknoloji tablosu "YOLOv8/YOLOv11"** diyor ama kodda sadece YOLOv8 var; YOLOv11 kullanım kanıtı yok.
- **"Hybrid-SORT (CSRT/KCF + periyodik YOLO re-init)"** README'de var ama kodda OpenCV KCF/CSRT tracker kullanılmamış; sadece Ultralytics'in yerleşik ByteTrack'i var. STAPLE/OC-SORT sadece literatür referansı.
- **Veri seti değişti:** README SH17 der, gerçek eğitimde `shlokraval/ppe-dataset-yolov8` kullanıldı (README güncellenmemiş).
- **Kurulum tutarsızlığı:** README sadece `ultralytics opencv-python paho-mqtt` kuruyor; `motmetrics`, `pandas`, `kagglehub`, `numpy`, `torch` eksik.
- **Sayısal metrik yok:** MOTA/IDF1 hesaplama kodu hazır ama manuel ground truth etiketleme atlandı; final raporda "yüksek IDF1, düşük ID-Switch" deniyor ama **somut sayısal değer verilmemiş**.
- **Edge cihaz spesifik değil:** hangi donanım (Jetson, Raspberry Pi) belirtilmemiş.
- **Test/CI/Docker yok**, LICENSE yok.
- **Kod kokuları:** `frame_w in locals()` kontrolü, bare `except:` (hata maskeleniyor).

#### 3.8. Bedirhan Özeti

Bedirhan'ın modülü, tek bir `live_detector.py` etrafında örgülenmiş, YOLOv8 + ByteTrack ile nesne tespit/takip, sınıf öncelik puanlama ile akıllı hedef seçimi, `(dx,dy)` ofset hesaplama ve MQTT üzerinden KONTROL modülüne ≥15 Hz yayın yapan kapalı çevrim aktif takip sistemidir. Tüm 16 iş paketi tamamlanmış, 4 Eylül Ekip Demosuna hazır. README ile gerçek kod arasında tutarsızlıklar ve sayısal metrik eksikliği mevcut. Temel teknik karar: **gerçek zamanlılık için YOLOv8 + ByteTrack**, **güvenlik önceliği için sınıf bazlı puanlama**, **dayanıklılık için retry mekanizmaları**.

```text
    ┌─────────────────────────────────────────────────┐
    │           BEDİRHAN'IN MEVCUT MİMARİSİ           │
    │                                                 │
    │  KATMAN 1: YOLOv8 Nesne Tespiti                │
    │  • Önceden eğitilmiş model (14 sınıf)           │
    │  • Confidence ve NMS filtreleri                 │
    │                                                 │
    │  KATMAN 2: ByteTrack Takip Algoritması         │
    │  • Hedef ID koruma (Lock-on)                    │
    │  • Kaybolan nesneyi telafi etme                │
    │                                                 │
    │  KARAR: Hedef Sınıf Önceliği (Priority Puanı)   │
    │                                                 │
    │  ÇIKTI: (dx, dy) Pan-Tilt Motor Ofsetleri       │
    │  • MQTT üzerinden ≥15 Hz yayın                  │
    └─────────────────────────────────────────────────┘
```

---

### 4. Repo 2 — Reşit Asrav (GÖSTERGE / PANEL OKUMA)

#### 4.1. Repo Kimliği ve Proje Amacı

| Alan | Değer |
|---|---|
| Repo | [resitasrav/rasrav-gauge-vision-2026](https://github.com/resitasrav/rasrav-gauge-vision-2026) |
| Paket adı | `gauge-vision` v0.1.0 (`pyproject.toml:6`) |
| Sahip | Reşit Asrav |
| Kurum/Grup | BTÜ · 03_Gama Grubu · 27.07–04.09.2026 |
| Modül | GÖSTERGE → `inspect/reading` |
| Kaynak | [GitHub repo](https://github.com/resitasrav/rasrav-gauge-vision-2026) |
| Hedef donanım | Orange Pi 5 (RK3588) + NPU |
| Tek commit | `5a0dd8d` "Demo ciktilari artik baskasina gonderilebiliyor: H.264 + boyut" |

Reşit'in modülü, pan-tilt kameralı devriye platformunun görüntüsünden **analog göstergeleri, dijital panelleri, ikaz lambalarını, vana pozisyonlarını ve buton panellerini** otomatik okuyup sayıya/duruma çevirir. Bugün bu işi bir operatör tur atıp elle yapıyor; proje bunu otomatikleştirir. Boru hattı: görüntü → tespit (YOLO, İP5) → kırp → okuma (analog: ibre açısı İP6, dijital: OCR İP11, lamba/vana İP12) → kalibrasyon (açı→değer İP7) → MQTT yayını (İP10). Hedef: analog okuma ortalama hatası **< %5**.

#### 4.2. Dosya Yapısı

Repo, toplam **6297 satır src kodu**, 40 script, 18 test, 19 kaynak modül, 2 konfig YAML, 6+ markdown dokümanı, 6 demo dosyası. `pyproject.toml` ile `pip install -e .` her yerden import sağlar. `pytest` ile 18 birim testi vardır.
Çekirdek paket `src/gauge_vision/` altında modüler: `config.py` (619 satır, Gauge/Scale dataclass'ları), `pipeline.py` (521 satır, uçtan uca zincir), `temporal.py` (323 satır, kareler-arası karar sabitleyici), `waypoints.py` (166 satır). Alt paketler: `detect/` (dataset, perspective, refine), `read/` (calibrate, needle, digital, state, keypad, roll, evaluate), `publish/` (reading), `synth/` (generate, dial, digital, keypad, panel, state, degrade).

#### 4.3. Beş Gösterge Tipi

Reşit'in modülü beş farklı gösterge tipini okur — her biri farklı bir algoritma gerektirir:

| Tip | Gösterge | Algoritma | Kanıt |
|---|---|---|---|
| **Analog** | PT-101 (bar), TI-205 (°C), FI-310 (m³/h), EM-501 (MW) | İbre açısı: polar tarama + Hough | `read/needle.py` (454 satır) |
| **Digital** | DP-401 (kPa) | 7-segment segment geometrisi (OCR değil) | `read/digital.py` (510 satır) |
| **Lamp** | LM-501 (off/green/red) | HSV renk + yanıp sönme oylama | `read/state.py` (304 satır) |
| **Valve** | VL-601 (open/closed) | PCA kol açısı | `read/state.py` |
| **Keypad** | CP-701 (4 buton + selector) | Buton bileşimi → makine durumu | `read/keypad.py` (286 satır) |

Önemli tasarım kararı: **dijital panel için OCR (PaddleOCR/Tesseract) kullanılmadı**, bunun yerine 7-segment segment geometrisi yöntemi seçildi. Bu nedenle `paddleocr` ve `pytesseract` `requirements.txt`'te yorum satırı (pasif).

#### 4.4. Kullanılan Yazılımlar ve Neden Seçildiği

Reşit'in teknoloji yığını, **gömülü taşınabilirlik** (Orange Pi 5 + NPU hedefi) ve **"ölçüm odaklı" disiplin** etrafında şekillenmiştir. En çarpıcı özellik: **çekirdek paket tamamen torch'suz** — `src/gauge_vision/` içinde tek bir torch/ultralytics/cuda importu yoktur. YOLOv8 sadece tespit (İP5) için kullanılır ve kart üstünde gerekmez.

##### Aktif Bağımlılıklar

| Kütüphane | Sürüm | Kullanım Nedeni (kanıt) |
|---|---|---|
| **numpy** | >=1.26 | Temel sayısal işlemler. Gömülü hedefte ana bağımlılık. |
| **PyYAML** | >=6.0 | `configs/gauges.yaml` envanter yükleme (`config.py:23`). **Envanter tek doğru kaynak** ilkesi. |
| **opencv-python** | >=4.10 | Sentetik kadran çizimi + görüntü işleme. `read/needle.py` (Otsu, Canny, HoughLinesP), `detect/refine.py` (Scharr, GaussianBlur), `read/digital.py` (connectedComponents), `read/state.py` (HSV). |
| **pillow** | >=10.0 | HF parquet'ten görüntü açma (`detect/dataset.py:128`). |
| **matplotlib** | >=3.8 | Hata grafikleri, rapor figürleri. |
| **pytest** | >=8.0 | 18 birim testi — envanter ve okuma doğrulaması. |
| **torch** | >=2.0 | YOLOv8 tespit modeli eğitimi/çıkarımı. CUDA 12.6, RTX 4050 6GB. **Sadece İP5 için; kart üstünde gerekmez.** |
| **torchvision** | >=0.15 | PaDiM sarmalayıcıda ResNet18 (`demo/anomali_demo.py`). |
| **ultralytics** | >=8.3 | YOLOv8 gösterge tespiti. Arayüz minimal: `sonuc.boxes.{xyxy,conf,cls}` + `.names`. |
| **gdown** | >=6.0 | Google Drive'dan açık veri seti indirme (A1/A2, 404 verdi). |
| **pyarrow** | >=15.0 | HF parquet setleri okuma (A9 Roboflow aynası). |
| **onnx** | >=1.16 | Tespit modelini ONNX'e aktarma — Hailo (.hef) ve RKNN (.rknn) derleyicilerinin girdisi. |
| **onnxruntime** | >=1.18 | ONNX çıktısını bu makinede koşturma/doğrulama. |
| **imageio-ffmpeg** | (yorumlu) | Demo çıktılarını paylaşılabilir hâle getirme. Kendi ffmpeg ikilisini taşır (mp4v 577MB → avc1 796MB → x264 CRF23 48MB). |

##### Pasif Bağımlılıklar

| Kütüphane | Neden Pasif |
|---|---|
| **paho-mqtt** | İP10 MQTT yayını. Broker yoksa dosya moduna düşer. Yorumda çünkü broker her zaman ayakta değil. |
| **paddleocr** | İP11 dijital OCR — 7-segment segment geometrisi seçildiği için gerek kalmadı. |
| **pytesseract** | İP11 alternatif OCR — aynı şekilde pasif. |

##### Python Sürümü ve Donanım

**Python 3.13** kullanıldı — gerekçe: ultralytics/torch daha yeni sürümlerde tekerlek sorunu çıkarabiliyor. Geliştirme: RTX 4050 (6 GB VRAM, compute 8.9), CUDA 12.6. Hedef: **Orange Pi 5 (RK3588) + NPU** hızlandırıcı.

##### Veri Setleri

- **A9 (Roboflow HF aynası `Francesco/gauge-u2lwv`)** — 235 gerçek endüstriyel fotoğraf, 640×640, COCO kutu. K1 kararı (sentetik+gerçek karışık eğitim).
- **Synanthropic/reading-analog-gauge (HF)** — ~2,8 GB, 8.072 corners + 34.370 keypoint. Bağımsız doğruluk ölçümü.
- **A4 (Endava Kaggle)** — DS5.0/DS6.0, Houdini + Stable Diffusion.
- **A1/A2 (Cambridge)** — erişilemiyor (Google Drive 404).
- **Kendi sentetik üreteci** (`synth/`) — tohumlu, tekrar üretilebilir.

#### 4.5. Teknoloji Seçimlerinin Çıktıya Etkisi

Reşit'in tasarım prensipleri, çıktı kalitesini doğrudan belirleyen **dört temel kural** etrafında örgülüdür:

1. **"Yanlış okumaktansa okumamak" (3. kural).** Hiçbir koşulda hata yükseltmez; sorunlar `status: unreadable` + `value: None` ile bildirilir. Belirsiz desen uydurulmaz (`read/digital.py:29-31`, `read/keypad.py:19-22`). Bu, güvenlik açısından kritik: yanlış basınç okuması kazaya yol açabilir.

2. **"Kanıt, cevap makul mü değil."** Kapılar (eşikler) körlemesine konmaz; **iki dağılım ölçülerek** seçilir. `MIN_TESPIT_GUVENI=0.30`, `MIN_IBRE_KANITI=0.10` (`pipeline.py:249-250`). Bu kural sayesinde sahte okumalar **383'ten 39'a** düştü (%89.8 azalma).

3. **Tek doğru kaynak (envanter).** Gösterge bilgisi `gauges.yaml`'da, koda gömülmez. Üç yer bakar: sentetik üreteç (İP3), açı→değer (İP7), MQTT yayını (İP10). Yeni gösterge = YAML satırı, kod değişmez. Doğrulama katı — bozuk envanter erken patlar.

4. **Modüller birbirinin koduna değil MQTT şemalarına bağlıdır.**

##### Ölçüm Sonuçları

- **İP6 ibre açı hatası: 0.123°** (synth+gerçek), bağımsız sette medyan 0.20°, p95 0.56°.
- **İP7 değer hatası: %0.129** (zincir %0.19) — hedef <%5'in çok altında.
- **ONNX aktarım doğrulandı:** 1.38 px sapma (sınır 2 px).
- **ROI kırpması:** 1080p'de 18.13ms → 3.25ms.
- **Tespit gerçek zeminde mAP50:** 0.3925 → 0.9950 (ama videolarda iyileşme yok, kısmen gerileme — alan aşırı uyumu).
- **320 test geçiyor.**

##### Tasarım Güçlü Yönleri

- **Sentetik-önce stratejisi + OpenCV çizim:** Ground truth bedava gelir (ibreyi biz o açıya koyduğumuz için), ölçüm tekrar üretilebilir (tohumlu). Etiketleme maliyeti sıfır.
- **OpenCV (matplotlib değil) çizim:** Pikselin nereye düştüğü birebir kontrol ediliyor, sentetik ile gerçek arası tutarlı (`synth/dial.py:13-15`).
- **NumPy+OpenCV çekirdek (torch yok):** Kart üstünde yalnız numpy+opencv+PyYAML; maliyet kamera çözünürlüğünden bağımsız.
- **YAML-driven envanter:** Yeni gösterge = YAML satırı. Sessiz hata sınıflarına karşı doğrulama katı (pivot, kol açıları, buton çakışması).
- **Zamansal tutarlılık:** 180° ters okuma (sessiz hata) tek karede ayrılamaz ama kare dizisinde fizik yasağıyla yakalanır (`temporal.py`).
- **Ablasyon anahtarları:** `refine`, `perspektif`, `roll_deg` parametre olarak kapatılabilir — kazanç ölçülebilir.

#### 4.6. Mimari ve Çalışma Akışı

Analog okuma zinciri:

```
görüntü ──► model.predict (YOLO, İP5) ──► _tipe_uyan_kutular (sınıf filtresi)
   ──► dial_from_box (merkez/yarıçap, envanter face geometrisi)
   ──► [perspektif düzeltme (İP8/K2)] ──► [refine_dial (merkez rafinesi)]
   ──► [estimate_roll (yatıklık, çizgi korelasyonu)]
   ──► read_needle_angle (kutupsal tarama, polar/hough)
   ──► read_value (açı→değer, alarm, güven eşiği İP15)
   ──► GaugeReading ──► ReadingPublisher.yayinla ──► inspect/reading MQTT
```

#### 4.7. Eksiklikler ve Açık Konular

1. **Gösterge kimliği görüntüden çıkarılamıyor.** Tip filtresi var, kimlik yok. Kimlik robotun durağından (waypoint) gelmeli ama `waypoint_gosterge_sozlugu.yaml`'da `gauges: []` placeholder — sahada doğrulanmamış.
2. **180° ters okuma (sessiz hata).** Merkez etiketten gelirse %1.0, `refine_dial` kestiriminde %8.1 ters. Kök sebep merkez doğruluğu; çözüm zamansal tutarlılık ama İP8/bağımsız ölçümlerde henüz kullanılmıyor.
3. **Dijital panel gerçek fotoğrafta 0/5→1/5.** Sorun hane kutusu bulma; yansıma gradyanı altında `_segment_maskesi` zemin sabit varsayımı bozuluyor.
4. **Keypad tespit sınıfı yok.** Okuyucu hazır ama YOLO `keypad` tanımıyor; şimdilik kırpılmış görüntüde okunuyor (`--tespitsiz`). Gerçek pano fotoğrafı gelmeden sınıf eklenmez (alan aşırı uyumu riski).
5. **Tespit yeniden eğitimi videolarda işe yaramadı.** mAP 0.3925→0.9950 ama videolarda gerileme (alan aşırı uyumu). Üretim ağırlığı `cok_sinif` olarak kaldı.
6. **A1/A2 (Cambridge) erişilemiyor** (404). İP8'in gerçek-görüntü ground truth ihtiyacı karşılanamadı.
7. **Kapı eşikleri eski ağırlığın dağılımından.** Yeni modelle yeniden ölçülmeli.
8. **Vana kolu renkleri varsayılan kapalı.** Eksik olan renk değil şekil/bağlam; k-means sentetikte 40/40 ama gerçek fotoğrafta sessiz hata üretti.
9. **Pano metresi yatıklık kestirimi atlanıyor** (çember halkası yok).
10. **Selector + yatıklık:** Kamera yatınca kol açısı dönüyor ama envanter beyan sabit. 25° eğikte kapsama 0.
11. **Gerçek pano fotoğrafı (S8/S10) eksik.** Keypad eşikleri, dijital perspektif, birim kimliği hep buna bağlı.
12. **MQTT şema format uyuşmazlığı:** "WP-04" (tireli) vs "WP01" (tiresiz) — dondurma toplantısında karara bağlanmamış.

#### 4.8. Reşit Özeti

Reşit'in modülü, 6297 satır modüler src kodu, 40 script, 18 test, pyproject.toml ile kurulabilir paket, ölçüm odaklı kültür (her eşik iki dağılım ölçülerek seçilir), "yanlış okumaktansa okumamak" prensibi, torch'suz çekirdek ile gömülü taşınabilirlik. Temel teknik karar: **gömülü hedef için torch'suz NumPy+OpenCV çekirdek**, **ground truth bedava olduğu için sentetik-önce stratejisi**, **OCR yerine segment geometrisi**, **ölçülen eşiklerle kanıt kapıları**. Çıktı: %0.19 analog okuma hatası (hedef <%5'in çok altında), 1.38 px ONNX sapması, 320 geçen test.

```text
    ┌─────────────────────────────────────────────────┐
    │             REŞİT'İN MEVCUT MİMARİSİ            │
    │                                                 │
    │  KATMAN 1: YOLOv8 Nesne Tespiti                 │
    │  • 5 tip gösterge + kırpma (ROI)                │
    │                                                 │
    │  KATMAN 2: Torch'suz NumPy+OpenCV Çekirdek      │
    │  • Segment geometrisi (Dijital)                 │
    │  • Polar tarama + Hough (Analog)                │
    │  • HSV + Oylama (Lamba)                         │
    │  • PCA (Vana) & Buton bileşimi (Keypad)         │
    │                                                 │
    │  KARAR: Kanıt Kapıları ve Zamansal Tutarlılık   │
    │                                                 │
    │  ÇIKTI: Okuma Değeri, Birim, Durum              │
    │  • Yanlış okumaktansa okumama prensibi          │
    └─────────────────────────────────────────────────┘
```

---

### 5. Repo 3 — Özgür Kotbaş (ANOMALİ + DEVRİYE RAPORU)

#### 5.1. Repo Kimliği ve Proje Amacı

| Alan | Değer |
|---|---|
| Repo | [OzgurKotbas/akilli_fabrika_staj-2026](https://github.com/OzgurKotbas/akilli_fabrika_staj-2026) |
| Sahip | Özgür Kotbaş |
| Kurum/Grup | BTÜ · 03_Gama Grubu · 27.07–04.09.2026 |
| Modül | ANOMALİ → `patrol/alert` |
| Kaynak | [GitHub repo](https://github.com/OzgurKotbas/akilli_fabrika_staj-2026) |
| Toplam dosya | 214 adet (.git hariç) |
| Durum | İP1–İP15 tamamlandı, İP16 final bekliyor |

Özgür'ün modülü, kameranın elde ettiği görüntüleri **"normal (altın tur)" referanslarla** karşılaştırarak devriye sırasında oluşmuş olağandışı durumları (anomalileri) yapay zeka ile otomatik tespit eder. Tur sonunda kanıtlı bir **Markdown/PDF Devriye Raporu** üretir. Örnek anomali senaryoları: yerde bırakılmış yabancı nesneler, acil çıkış kapılarının önünün kapanması, fabrika zeminindeki su/yağ sızıntıları.

Özgür'ün reposunda `DOKUMANLAR/` altında Bedirhan ve Reşit'in proje tanımları ve iş paketleri de mevcuttur. `AI.md` (657 satır), staj boyunca yapay zeka ile yapılan teknik diyalogların tam kaydıdır.

#### 5.2. Dosya Yapısı

Repo modüler ve sürdürülebilir bir yapıya sahiptir. Modüler paket yapısı `scripts/` altında: `core/` (config_okuyucu, kaynak_adaptoru, anomali_motor), `data_prep/` (video→kare, waypoint seçimi, augmentation, PLY görselleştirme), `vision/` (anomali_test, ip7 kıyas, ip8 tespit, ip9 ensemble, model+heatmap), `comms/` (mqtt_yayini, rapor_uret, pdf_rapor, mqtt_test_abone). Import yolları standart Python paket yapısına uygun: `from scripts.core import config_okuyucu`.

Önemli dosyalar: `demo_anomali.py` (1196 satır, gerçek zamanlı demo UI), `ip14_canli_tur.py` (662 satır, uçtan uca canlı devriye turu), `ip15_harita_konumlandir.py` (718 satır, 3D harita + uyarı konumlandırma), `vision/ip9_ensemble_analiz.py` (ana pipeline).
Yeni eklenen dosyalar: `core/anomali_hizalamali.py` (ORB+RANSAC hizalamalı hareketli kamera anomali motoru) ve `olc_karsilastir.py` (yeni motorun eskisine karşı performans kıyaslaması).

#### 5.3. Kullanılan Yazılımlar ve Neden Seçildiği

Özgür'ün teknoloji yığını, **denetimsiz anomali tespiti** ("sadece normali görerek öğrenme") ve **otomatik raporlama** gereksinimi etrafında şekillenmiştir.

##### Python Kütüphaneleri (requirements.txt)

| Kütüphane | Sürüm | Kullanım Nedeni |
|---|---|---|
| **opencv-python** | >=4.8.0 | Görüntü okuma, MOG2 arka plan çıkarma, ORB hizalama, morfolojik işlemler, contour tespiti. Tüm vision pipeline'ın bel kemiği. |
| **numpy** | >=1.24.0 | Matris işlemleri, patch vektör hesaplama, cosine similarity matrisi, IoU hesaplama. |
| **scikit-image** | >=0.21.0 | **SSIM** (Yapısal Benzerlik) — İP8 değişiklik tespiti. `skimage.metrics.structural_similarity`. |
| **python-dotenv** | >=1.0.0 | `.env` dosyalarından ortam değişkenleri yükleme — `config_okuyucu.py`. |
| **fpdf2** | >=2.7.4 | PDF rapor üretimi (İP13). Saf Python, Windows uyumlu. |
| **paho-mqtt** | >=1.6.1 | MQTT istemcisi — `patrol/alert` topic'e anomali uyarıları (İP10). Offline mod desteği. |
| **Jinja2** | >=3.1.2 | Şablon motoru — `docs/rapor_sablonu.md.j2` ile devriye raporu (İP11). |
| **PyYAML** | >=6.0 | `config.yaml` ve `waypoint_listesi.yaml` okuma. |

##### Derin Öğrenme (yorum satırı — opsiyonel)

| Kütüphane | Sürüm | Kullanım Nedeni |
|---|---|---|
| **anomalib** | v2.x | PatchCore/PaDiM/FastFlow anomali modelleri. MVTec-AD entegre. İP1, İP5, İP6'da kullanıldı. |
| **torch** | >=2.0.0 | anomalib'in altyapısı. İP9'da PatchCore scorer (ResNet18 backbone, spatial patch). |
| **torchvision** | >=0.15.0 | ResNet18 pretrained ağırlıkları, transforms, veri artırma. |

> **Önemli:** `anomalib`, `torch`, `torchvision` `requirements.txt`'te **yorum satırı**. Sebep: GPU gerektiriyor ve lightweight demo için opsiyonel. İP9 ensemble scripti `try/except ImportError` ile PyTorch yoksa sadece MOG2 katmanını çalıştırır (`--no-patchcore` flag). Bu, "ağır bağımlılık olmadan da çalışabilen" tasarımın göstergesidir.

##### Ek Kütüphaneler (kod içinde, requirements.txt'te olmayan)

| Kütüphane | Nerede | Neden |
|---|---|---|
| **matplotlib** | `anomali_test.py` | anomalib heatmap görselleştirme. |
| **open3d** | `ip3_3_ply_gorsellestir.py` | PLY 3D nokta bulutu görselleştirme (İP3). |
| **Pillow (PIL)** | `ip9_ensemble_analiz.py`, `ip6_veri_artirma.py` | ResNet18 preprocessing. |
| **markdown2 / mistune** | `ip11_rapor_uret.py` | MD → HTML dönüşümü (alternatif). |
| **WeasyPrint** | `ip13_pdf_rapor.py` (yedek) | HTML → PDF (fpdf2 yoksa). Sistem bağımlılıkları gerektirir (GTK, Pango). |
| **huggingface_hub** | `ip3_lingbotmap_notebook.py` | LingBot-Map model indirme. |
| **einops, timm, viser, trimesh, onnxruntime, flashinfer** | LingBot-Map bağımlılıkları | 3D haritalama modeli. |

##### Harici Modeller ve Veri Setleri

| Bileşen | Kaynak | Neden |
|---|---|---|
| **anomalib** | github.com/open-edge-platform/anomalib | PatchCore/PaDiM/FastFlow/EfficientAD. MVTec AD entegre. Projenin bel kemiği. |
| **MVTec-AD** | Kaggle/anomalib | Endüstriyel anomali benchmark. `bottle` kategorisi. 15 kategori. |
| **VisA** | amazon-science/spot-diff | Alternatif anomali seti (12 ürün, 9621 görüntü). |
| **ResNet18** | torchvision (IMAGENET1K_V1) | PatchCore ve PaDiM için özellik çıkarıcı. İP9'da spatial patch için `[:-2]`. |
| **LingBot-Map** | robbyant/lingbot-map | Pretrained 3D sahne haritalama modeli. İP3/İP15 stretch hedef. Kaggle T4 GPU. |
| **PatchCore** | anomalib | "Towards Total Recall" (CVPR 2022). Memory bank + kNN. Birincil model. |
| **PaDiM** | anomalib | "Patch Distribution Modeling" (2020). İkincil/edge aday. |

#### 5.4. Her Teknoloji için Kullanım Nedeni (Dokümanlardan)

##### anomalib (PatchCore / PaDiM)
- **Dokümandan:** "Sistemdeki kameranın elde ettiği görüntüleri 'normal (altın tur)' referanslarla karşılaştırarak... yapay zeka ile otomatik olarak tespit etmektir." "anomalib kütüphanesinin sağladığı son teknoloji (SOTA) makine öğrenmesi modelleriyle (Özellikle PatchCore ve PaDiM) sistemin sadece 'normali' görerek eğitilmesi."
- **Seçim gerekçesi:** PatchCore, MVTec-AD'de AUROC=1.0 başarısı nedeniyle birincil seçildi; staj süresinde az veriyle çalışması kritik. PaDiM ikincil (hafif, edge'e uygun).

##### OpenCV
- Tüm görüntü işleme pipeline'ının temeli. MOG2, ORB, homografi, contour, morfoloji, HSV, optical flow, video okuma/yazma, görsel kompozisyon.
- **Seçim:** OpenCV standart görüntü işleme kütüphanesidir, Python ile entegredir, MOG2 gibi klasik algoritmaları içerir.

##### MOG2 (Arka Plan Çıkarma)
- **Dokümandan:** "Engel videosunu kendi içinde tarayarak durağan yeni nesneleri tespit eder. Farklı açıyla çekilmiş ikinci videoyla kıyaslama yapmaz — bu yüzden açıya tamamen bağımsızdır."
- **Seçim (daily_log, 15.08):** "mevcut SSIM/ORB pipeline'ı robot köpek senaryosunda yapısal olarak yetersiz. ORB homografisi ~20° açı toleransı sonrası kırılır; robot köpek her turda aynı açıyı tutamaz." MOG2 açı-bağımsız katman olarak eklendi.

##### SSIM (scikit-image)
- **Dokümandan:** "SSIM, absdiff'e göre ışık ve ufak kaymalara ÇOK daha dayanıklıdır." Piksel bazlı fark ışık değişimlerine aşırı duyarlı; SSIM yapısal benzerliği ölçtüğü için daha robust.

##### ORB
- **Dokümandan (daily_log, 08.08):** "AKAZE algoritması kullanılması denendi ancak mevcut OpenCV sürümündeki modül eksikliği (AKAZE_create bulunamaması) sebebiyle daha hızlı ve projeye daha uygun olan ORB algoritmasına geçiş yapıldı."

##### Jinja2
- **Dokümandan:** "Uyarıları önceliğe göre (HIGH > MEDIUM > LOW) dizen scripts/ip11_rapor_uret.py yazıldı. Sistem hem Markdown hem HTML formatında devriye raporları üretir."

##### fpdf2
- **Dokümandan:** "fpdf2 kütüphanesi birincil backend; WeasyPrint yedek."
- **Seçim (AI.md):** "fpdf2 saf Python, Windows geliştirme ortamında sistem bağımlılığı olmadan çalışıyor. WeasyPrint fallback olarak kodda mevcut ama şu anda kurulu değil."

##### paho-mqtt
- **Dokümandan:** "İstenen JSON şeması tam olarak uygulandı (severity, waypoint, score, det_count, img_ref, vs.). MQTT broker yokken veya ulaşılamadığında verileri yerel JSON dosyasına yazan (--offline) mod eklendi."
- **Seçim:** Python için standart MQTT istemcisi. Bedirhan'ın kurduğu Mosquitto broker ile uyumlu.

##### PyYAML ve python-dotenv
- **Dokümandan:** "Sistem tamamen config.yaml dosyası üzerinden yönetilmektedir. Kodu değiştirmenize gerek yoktur." "Tüm Python scriptleri artık Python dosyasının içinden değil doğrudan bu config.yaml dosyasından okuyor." Production-ready yazılım için.

##### LingBot-Map
- **Dokümandan:** "LingBot-Map, tek kameradan video alarak 3D nokta bulutu oluşturan bir modeldir." Stretch hedef (İP15): "Devriye rotası kaydından pretrained modelle 3D harita çıkar. Uyarıları harita üzerine konumla."
- **Seçim:** "pretrained çıkarım Colab T4'te çalışır" — ek eğitim gerektirmeden pretrained modelle 3D harita üretebilir.

#### 5.5. Çıktı Ürünleri ve Teknoloji Seçiminin Çıktıya Etkisi

Özgür'ün modülü on çıktı ürünü üretir:

1. **Anomali Heatmap'leri (İP1/İP5/İP6):** anomalib + PatchCore/PaDiM + ResNet18. PatchCore AUROC=1.0 ile neredeyse mükemmel görüntü seviyesi tespit.
2. **Değişiklik Maskeleri (İP7):** ORB hizalama + mutlak fark.
3. **Etiketli Test Çifti Seti (İP8):** 3 waypoint için referans + değiştirilmiş kare çiftleri, GT bbox ile.
4. **Ensemble Analiz Sonuçları (İP9):** MOG2 + PatchCore ensemble çıktıları. Her WP için 4 panelli görsel.
5. **MQTT patrol/alert Mesajları (İP10):** JSON formatında anomali uyarıları.
6. **Devriye Raporu (İP11):** Jinja2 ile MD ve HTML.
7. **PDF Devriye Raporu (İP13):** fpdf2 ile kapak + özet + uyarı kartları + metrikler.
8. **Canlı Devriye Turu (İP14):** Evrensel kaynak adaptörü ile uçtan uca tur.
9. **3D Harita + Uyarı Konumlandırma (İP15):** LingBot-Map + optik akış.
10. **Gerçek Zamanlı Demo:** 3 modlu interaktif OpenCV UI.

##### Teknoloji Seçimlerinin Çıktıya Etkisi

- **PatchCore seçimi (AUROC=1.0):** Yüksek doğruluk, az veriyle çalışma (3 referans kare yeterli). Spatial patch (49 adet 7×7) düzeltmesi küçük anomalilerin kaybolmasını engelledi → WP03 kapı anomalisi doğru tespit edildi (PC=0.515 > 0.40).
- **MOG2 seçimi (açı-bağımsız):** Robot köpek açı tutarsızlığı sorununu çözdü. ORB homografisi ~20° tolerans sonrası kırılıyordu; MOG2 video içinde kendi analiz yaptığı için açıya tamamen bağımsız.
- **Ensemble (MOG2 OR PatchCore):** İki katman birbirini tamamlar. MOG2 sabit yeni nesneleri yakalar, PatchCore embedding bazlı anomalileri (kapı, yüzey değişimi) yakalar. F1'i 0.333'ten 0.667'ye çıkardı (+%100).
- **Jinja2 + fpdf2 raporlama:** Otomatik, kanıtlı, öncelik sıralı rapor üretimi. İnsan müdahalesi gerektirmeden tur sonu raporu.
- **Evrensel Kaynak Adaptörü (Adapter Pattern):** Video/RTSP/webcam/statik görüntü desteği. Gerçek pan-tilt kameraya bağlandığında kod değişikliği gerektirmiyor.
- **Multi-deployment desteği:** Birden fazla hat/fabrika aynı broker'a bağlandığında topic collision'ı önler. `deployment-id` ile izole çıktılar.
- **config.yaml merkezi yapılandırma:** Hardcoded parametrelerden kurtuldu. Production-ready.

##### PatchCore Scorer Teknik Detayı (İP12 düzeltmesi)

`PatchCoreScorer` sınıfı:
- Backbone: `torchvision.models.resnet18(weights="IMAGENET1K_V1")`, `[:-2]` (AveragePool çıkarıldı).
- Çıktı: (512, 7, 7) → 49 adet 512-boyutlu L2-normalize patch vektörü.
- Memory bank: 3 referans kare × 49 patch = 147 patch vektörü.
- Skor: `sim_matrix = test_patches @ all_ref.T` → `max_sims = sim_matrix.max(axis=1)` → `patch_scores = 1.0 - max_sims` → `anomali_score = patch_scores.max()` (en kötü patch karar verir).
- Karar: `is_alert = (mog2_nesne > 0) OR (patchcore_score > 0.40)`.

İP12'de iki kritik düzeltme yapıldı: (1) MOG2 sabit zaman bug'ı — `cap.set()` ile geriye sarma kaldırıldı, tek geçiş (single-pass); (2) PatchCore global embedding — `ResNet18[:-1]` → `[:-2]` (49 spatial patch). Bu düzeltmeler F1'i 0.333'ten 0.667'ye çıkardı.

##### Anomali Motoru (anomali_motor.py)

`AlgilayiciMOG2` sınıfı:
- `cv2.createBackgroundSubtractorMOG2(history=200, varThreshold=20, detectShadows=True)`.
- **Tavan Crop:** Resmin üst %18'i (tavan) parallax hatası için sıfırlanır.
- **Rotation Guard:** Optik akış ile dönme tespiti. Dönme sırasında `learningRate=0` (arka plan modelini bozmamak için). Dönme anında tespitler sıfırlanır.
- **Sarı Maske:** HSV renk uzayında sarı zemin çizgileri bastırılır (FP azaltmak için).
- **Warmup:** Referans kareyi N kez (40) MOG2'ye besleyerek arka planı hızlıca öğrenir.

##### Hizalamalı Anomali Motoru (anomali_hizalamali.py)

Yeni eklenen `AkisAlgilayici` sınıfı, kameranın hareketli olduğu senaryolar için geliştirilmiştir:
- **ORB+RANSAC Hizalama:** Ardışık iki kareyi birbirine geometrik olarak hizalayarak kamera hareketini (parallax etkisine kadar) sönümler.
- **Adaptif MAD Eşiği:** Geçerli (örtüşen) bölgenin medyan ve MAD (Median Absolute Deviation) değerine göre eşik belirleyerek aydınlatma değişimlerine dinamik adapte olur.
- **Zamansal Onay:** Bir adayın gerçek nesne sayılabilmesi için `onay_kare` (örn. 3) boyunca aynı konumda görülmesini şart koşarak FP (yanlış pozitif) oranını düşürür.

#### 5.6. Mimari ve Çalışma Akışı

Sistem, **"Altın Tur" (Golden Tour)** konsepti üzerine kuruludur:

```
Altın Tur Video → referans_kareler_cikart.py → WP01/02/03.jpg
                                                    ↓
                                            ip6_veri_artirma.py (augmentation → normal/)
                                                    ↓
                    model_ve_heapMap.py (anomalib Folder → PatchCore eğitimi)
                                                    ↓
engel.mp4 (değiştirilmiş sahne) → ip8_video_frame_al.py → WP0x_degisik.jpg
                                                    ↓
                    ip9_ensemble_analiz.py (MOG2 + PatchCore ensemble)
                         ↓                              ↓
              data/ip9_ensemble/*.json     data/ip9_ensemble/*.png
                         ↓
              ip10_mqtt_yayini.py (patrol/alert JSON → MQTT broker / offline)
                         ↓
              ip11_rapor_uret.py (Jinja2 → MD/HTML) → ip13_pdf_rapor.py (fpdf2 → PDF)
                                                    ↓
                                    outputs/devriye_raporu/son_devriye_raporu.pdf
```

#### 5.7. Eksiklikler ve Açık Konular

1. **İP16 (Final Teslim) tamamlanmadı.** 4 Eylül tarihi geçmiş olmasına rağmen final teslim durumu belirsiz.
2. **anomalib/PyTorch yorum satırı.** `pip install -r requirements.txt` çalıştırıldığında kurulmaz. İP9 gracefully degrade eder ama `anomali_test.py` ve `model_ve_heapMap.py` çalışmaz.
3. **Hardcoded Windows yolları (eski scriptler).** `model_ve_heapMap.py:8` (`root="D:/STAJ/..."`), `referans_kareler_cikart.py:6`, `test_verisi_olusturma.py:3`. Ana scriptler temizlendi ama data_prep altındaki bazı eski scriptler hardcoded.
4. **Eski/duplike dosyalar.** `outputs/model_results/01-02.08_eski/`, `docs/literatur_ozet.md` ile `docs/proje_tanimi/literatur_ozeti.md` aynı içerik, `DOKUMANLAR/Makaleler.md` ile `docs/proje_tanimi/makaleler/Makaleler.md` aynı.
5. **F1=0.667 hala düşük.** WP01'de FP (IoU=0.094 < 0.30) — nesne doğru bulunuyor ama konumlandırma hassasiyeti yetersiz. GT bbox'lar MOG2 tespitlerinden türetildiği için dairesel bir değerlendirme var.
6. **Türkçe karakter sorunu (fpdf2).** Built-in Helvetica fontu Latin-1; Türkçe karakterler sorunlu. ASCII karşılıkları veya DejaVu TTF önerilmiş.
7. **MQTT broker bağlantısı test edilmemiş.** Tüm MQTT işlemleri `--offline` modda çalıştırıldı.
8. **S4-S7 senaryoları test edilmedi.** S1-S3 (yerde cisim, yol engeli, kapı anomalisi) test edildi; S4 (sızıntı), S5 (yangın tüpü), S6 (levha), S7 (kablo) test edilmedi.
9. **İP3'te klasör yapısı uyumsuzluğu.** Rehber `ip3_tekrar/scripts/...` yolları referans veriyor ama gerçek scriptler `scripts/data_prep/...`'da.
10. **Sınırlı test verisi.** Sadece 3 waypoint ve tek `engel.mp4` videosu. Farklı ışık/açı/anomali tipleri eksik.
11. **`rasrav_gauge_repo` klasörü.** Reşit'in gauge demo scripti Özgür'ün reposunda — neden olduğu belirsiz (muhtemelen ortak testing).
12. **İP15 PLY dosyası repo'da yok.** Google Drive'da; yoksa 2D fallback mod çalışır.
13. **Veri seti ve model ağırlıkları repo'da yok.** MVTec-AD, PatchCore ağırlıkları, LingBot-Map modeli (500MB) hep harici.

#### 5.8. Özgür Özeti

Özgür'ün modülü, "altın tur" konseptiyle çalışan, MOG2 + PatchCore ensemble ile açı-bağımsız anomali tespiti yapan ve tur sonunda otomatik kanıtlı PDF devriye raporu üreten sistemdir. 16 iş paketinden 15'i tamamlandı. Temel teknik karar: **denetimsiz öğrenme (sadece normali görerek)**, **açık-bağımsızlık için MOG2 + PatchCore ensemble**, **production-ready için config.yaml + Adapter Pattern + multi-deployment**, **raporlama için Jinja2 + fpdf2**. Stretch hedef: LingBot-Map ile 3D harita. Çıktı: F1=0.667, AUROC=1.0, otomatik PDF rapor. Repo, akademik prototipten production-ready yaklaşımına evrilmiş; tüm teknik kararlar `daily_log.md` ve `AI.md`'de gerekçeleriyle dokümante edilmiş.

```text
    ┌─────────────────────────────────────────────────┐
    │           ÖZGÜR'ÜN MEVCUT MİMARİSİ              │
    │                                                 │
    │  KATMAN 1: MOG2 Arka Plan Çıkarma               │
    │  • Tavan crop (%18)                             │
    │  • Sarı çizgi maskesi                           │
    │  • Optik akış ile dönme koruması                │
    │  • Warmup (40 kare)                             │
    │                                                 │
    │  KATMAN 2: PatchCore (ResNet18 backbone)        │
    │  • Memory bank: 3 ref × 49 patch = 147 vektör   │
    │  • Cosine similarity → anomali skoru            │
    │                                                 │
    │  KARAR: MOG2 nesne VAR  OR  PatchCore > 0.50    │
    │                                                 │
    │  EK: AkisAlgilayici (ORB+RANSAC, yeni eklendi)  │
    │  • Ardışık kare farkı                           │
    │  • MAD-tabanlı adaptif eşik                     │
    │  • Zamansal onay (3 kare)                       │
    └─────────────────────────────────────────────────┘
```

---

### 6. Teknoloji Karar Matrisi

Aşağıdaki tablo, üç stajyerin teknoloji seçimlerini ve bu seçimlerin **görev doğasından nasıl kaynaklandığını** gösterir:

| Karar Boyutu | Bedirhan (VİZYON) | Reşit (GÖSTERGE) | Özgür (ANOMALİ) |
|---|---|---|---|
| **Öğrenme paradigması** | Denetimli (supervised) | Denetimli tespit + kural tabanlı okuma | Denetimsiz (unsupervised, "sadece normali görerek") |
| **AI omurgası** | YOLOv8 (Ultralytics) | YOLOv8 (sadece tespit) + klasik görüntü işleme | PatchCore/PaDiM (anomalib) + ResNet18 |
| **Takip/tracking** | ByteTrack (Ultralytics yerleşik) | — (tur bazlı, kareler-arası temporal stabilizer) | — (MOG2 arka plan çıkarma) |
| **Görüntü işleme** | OpenCV (çizim, HSV, JPEG) | OpenCV (Otsu, Canny, Hough, connectedComponents, HSV, PCA) — **en yoğun kullanım** | OpenCV (MOG2, ORB, homografi, optical flow, morfoloji) |
| **Haberleşme** | paho-mqtt + Mosquitto (QoS 0) | paho-mqtt (broker→dosya fallback) | paho-mqtt (--offline mod) |
| **Gömülü hedef** | "Edge cihaz" (belirsiz) | Orange Pi 5 (RK3588) + NPU (net, torch'suz çekirdek) | Windows geliştirme, GPU opsiyonel (`--no-patchcore`) |
| **Veri etiketleme** | Kaggle PPE veri seti (hazır etiketli) | Sentetik-önce (ground truth bedava, tohumlu) | "Altın tur" referans + sentetik anomali |
| **Eğitim ortamı** | Google Colab/Kaggle (T4) | RTX 4050 6GB CUDA 12.6 + Colab/Kaggle | Google Colab/Kaggle (T4) |
| **Raporlama** | Markdown dökümanlar | Ölçüm JSON'ları + matplotlib figürleri | Jinja2 (MD/HTML) + fpdf2 (PDF) + otomatik devriye raporu |
| **Test/CI** | Yok | 18 pytest birim testi | Sınırlı (FP test scriptleri) |
| **Config yönetimi** | README'de conda komutu | YAML envanter + pyproject.toml | config.yaml + .env + python-dotenv |
| **Hata toleransı** | Retry (kamera/MQTT) | Broker→dosya modu | `try/except ImportError` + `--offline` |
| **Python sürümü** | 3.10+ | 3.13 (tekerlek sorunu) | (standart, opsiyonel GPU) |
| **Paket yapısı** | Klasör bazlı (infra/vision/scripts) | `pyproject.toml` + src/ düzeni (`pip install -e .`) | Modüler paket (core/data_prep/vision/comms) |

#### 6.1. Neden Bu Kararlar Alındı?

Her stajyerin teknoloji seçimi, **çözdüğü problemin doğası** tarafından belirlendi:

- **Bedirhan** "gerçek zamanlı aktif takip" sorunu çözüyordu → bu, **denetimli nesne tespiti + tracking** gerektirir (YOLOv8 + ByteTrack). Çıktı bir ofset akışı olduğundan, frekans (≥15 Hz) ve gecikme kritiktir → QoS 0, hafif model, retry mekanizmaları. Öncelik mantığı (düşen işçi=100) güvenlik gereksiniminden doğdu.

- **Reşit** "gömülü cihazda gösterge okuma" sorunu çözüyordu → bu, **NPU'da çalışacak hafif bir çekirdek** gerektirir → torch'suz NumPy+OpenCV çekirdeği. OCR yerine segment geometrisi seçilmesinin nedeni: gömülü ortamda OCR ağır ve hata yapar; segment geometrisi deterministiktir. "Yanlış okumaktansa okumamak" kuralı güvenlik endişesinden (yanlış basınç okuması kazaya yol açar). Sentetik-önce stratejisi etiketleme maliyetini sıfırladı.

- **Özgür** "az veriyle anomali tespiti" sorunu çözüyordu → bu, **denetimsiz öğrenme** gerektirir (anomali örnekleri toplanamaz, "normal" toplanır) → PatchCore/PaDiM. MOG2'nin eklenmesi, robot köpeğin açı tutarsızlığı sorunu nedeniyle (ORB ~20° tolerans sonrası kırılıyor). Ensemble (MOG2 OR PatchCore) iki farklı anomali tipini yakalar. Raporlama otomasyonu, operatörün tur sonunda rapor yazma yükünü kaldırdı.

---

### 7. Karşılaştırmalı Mimari Tablosu

| Mimari Boyut | Bedirhan (VİZYON) | Reşit (GÖSTERGE) | Özgür (ANOMALİ) |
|---|---|---|---|
| **Çıktı frekansı** | ≥15 Hz (gerçekte ~20 FPS) | Tur bazlı (her gösterge için bir okuma) | Tur bazlı (her waypoint için bir uyarı) |
| **Gecikme kritikliği** | Çok yüksek (kapalı çevrim PID) | Düşük (operatör turu) | Orta (tur sonu rapor) |
| **Modülerlik** | Tek dosyada birleşmiş (`live_detector.py`) | En modüler (19 kaynak modül, 6297 satır) | Modüler paket (4 alt paket) |
| **Kod büyüklüğü** | 1707 satır (en küçük) | 6297 satır src + 40 script + 18 test (en büyük) | 214 dosya (en geniş) |
| **Test disiplini** | Yok | 18 pytest (en sıkı) | FP test scriptleri |
| **Dökümantasyon** | 3 markdown (README, daily_log, final_report) | 6+ markdown (en kapsamlı `devam_notu.md` 533 satır) | En zengin: README, daily_log, AI.md (657 satır), KULLANIM_KILAVUZU, senaryolar, literatür, makaleler, örnek rapor |
| **Production-ready** | Orta (retry var ama test/CI yok) | Yüksek (test, pyproject, gömülü tasarım) | Yüksek (config-driven, Adapter Pattern, multi-deployment) |
| **Akademik temel** | 10 makale literatür özeti | 13 makale + 12 veri seti derlemesi | 9-10 makale + awesome-industrial-anomaly-detection |
| **Gizlilik disiplini** | `*.pt`, `data/`, `models/` yasaklı | `data/real/*`, `*.mp4` yasaklı (PUBLIC repo koruması) | `data/raw_videos/` harici, model ağırlıkları yasaklı |
| **Ekip katkısı** | MQTT altyapı (publisher/subscriber/recorder/replayer) — ekibin haberleşme omurgasını kurdu | waypoint-gauge köprüsü, demo entegrasyon uyuşmazlık raporu | Ekibin doküman merkezi (Bedirhan ve Reşit'in proje/iş paketleri Özgür'ün reposunda) |

---

### 8. Çıktıya Etki Analizi

#### 8.1. Bedirhan — Çıktı: Aktif Takip Akışı

Bedirhan'ın çıktısı, robotun pan-tilt motorlarını gerçek zamanlı yönlendiren bir ofset akışıdır. Teknoloji seçimleri bu çıktıyı şu şekilde şekillendirdi:

- **YOLOv8 + ByteTrack** → gerçek zamanlılık (~30 FPS canlı, ~20 FPS MQTT) sağlandı; ≥15 Hz hedefi aşıldı. ByteTrack olmadan occlusion'da ID kaybı ve pan-tilt titremesi olurdu.
- **Sınıf Öncelik Mimarisi** → "ilk gördüğünü takip et" yerine "düşen işçiyi öncele" davranışı. Bu, güvenlik açısından çıktının niteliğini değiştirdi: robot artık sadece takip etmiyor, tehlike önceliği belirliyor.
- **NMS/Confidence tuning (conf=0.6)** → yanlış alarm ve hatalı kilitlenme azaldı; pan-tilt titremesi çözüldü.
- **Retry mekanizmaları** → kamera/MQTT kopmalarında sistem çökmedi; dayanıklılık arttı.

**Çıktının zayıf noktası:** Sayısal MOTA/IDF1 değerleri hesaplanmadı (manuel GT etiketleme atlandı). Yani "yüksek IDF1, düşük ID-Switch" iddiası nitel; somut kanıt yok. Ayrıca README ile kod arasındaki tutarsızlıklar (olmayan dosyalar, güncellenmemiş İP durumları, SH17→PPE değişikliği) çıktının tekrar üretilebilirliğini zorlaştırıyor.

#### 8.2. Reşit — Çıktı: Gösterge Okuma Değerleri

Reşit'in çıktısı, her gösterge için `{gauge_id, type, value, unit, conf, status, raw_angle}` JSON mesajıdır. Teknoloji seçimleri bu çıktıyı şu şekilde şekillendirdi:

- **Sentetik-önce stratejisi + OpenCV çizim** → ground truth bedava, ölçüm tekrar üretilebilir (tohumlu). İP6 açı hatası **0.123°**, İP7 değer hatası **%0.129** (zincir %0.19) — hedef <%5'in çok altında.
- **OCR yerine segment geometrisi** → dijital panelde deterministik okuma; OCR'ın belirsizliğinden kurtuldu. Ama gerçek fotoğrafta 0/5→1/5 — yani sentetik başarı gerçek sahaya tam taşınmadı.
- **"Yanlış okumaktansa okumamak" kuralı + kanıt kapıları** → sahte okuma 383'ten 39'a düştü (%89.8 azalma). Bu, güvenlik açısından çıktının güvenilirliğini dramatik biçimde artırdı: yanlış basınç okuması kazaya yol açabilirdi.
- **torch'suz çekirdek** → gömülü hedefte (Orange Pi 5) çalışabilir; maliyet kamera çözünürlüğünden bağımsız. ONNX aktarım doğrulandı (1.38 px sapma).
- **YAML-driven envanter** → yeni gösterge eklemek kod değişikliği gerektirmiyor; ölçeklenebilirlik.

**Çıktının zayıf noktası:** Gösterge kimliği görüntüden çıkarılamıyor (waypoint'ten gelmeli ama placeholder); 180° ters okuma sessiz hata; dijital panel gerçek görüntüde 0/5; keypad tespit sınıfı yok; tespit yeniden eğitimi videolarda işe yaramadı (alan aşırı uyumu).

#### 8.3. Özgür — Çıktı: Devriye Raporu

Özgür'ün çıktısı, tur sonunda otomatik üretilen kanıtlı PDF devriye raporudur (kapak + özet metrikler + öncelik sıralı uyarı kartları + normal WP tablosu + mimari detay). Teknoloji seçimleri bu çıktıyı şu şekilde şekillendirdi:

- **PatchCore (AUROC=1.0)** → az veriyle (3 referans kare) yüksek doğruluk. Spatial patch düzeltmesi küçük anomalilerin kaybolmasını engelledi.
- **MOG2 (açık-bağımsız)** → robot köpek açı tutarsızlığı sorununu çözdü. ORB homografisi ~20° tolerans sonrası kırılıyordu.
- **Ensemble (MOG2 OR PatchCore)** → iki farklı anomali tipi yakalandı; F1 0.333'ten 0.667'ye (+%100).
- **Jinja2 + fpdf2** → otomatik, kanıtlı, öncelik sıralı rapor. Operatörün tur sonunda rapor yazma yükü kalktı.
- **Evrensel Kaynak Adaptörü + multi-deployment** → gerçek pan-tilt kameraya ve birden fazla fabrikaya ölçeklenebilir.
- **config.yaml** → production-ready; başka makineye taşındığında kod değişikliği gerekmiyor.

**Çıktının zayıf noktası:** F1=0.667 hala düşük (WP01'de FP, IoU=0.094); GT bbox'lar tespitlerden türetildi (dairesel değerlendirme); MQTT broker gerçekten test edilmedi (sadece offline); S4-S7 senaryoları test edilmedi; Türkçe karakter sorunu fpdf2'de; anomalib/torch opsiyonel (yorum satırı) → kurulum belirsizliği.

---

### 9. Benzerlikler ve Farklılıklar

#### 9.1. Ortak Noktalar (Benzerlikler)

- **Aynı çatı proje:** Üçü de pan-tilt kameralı devriye robotunun görüntü işleme katmanı; aynı staj dönemi (27.07–04.09.2026), aynı grup (03_Gama).
- **Python + OpenCV + paho-mqtt + Mosquitto:** Üçü de bu ortak teknoloji yığınında birleşir.
- **MQTT pub/sub mimarisi:** Üçü de modüller arası haberleşmede donmuş JSON şemaları kullanır; broker bağımlılığını tasarımın içine yedirir (offline/fallback mod).
- **İP bazlı yönetim:** Her repo 16 iş paketinden oluşur, ölçülebilir "bitti kriteri" ile.
- **Literatür öncülü:** Her stajyer 9-13 makalelik mini literatür taraması yapmış, kararlarını akademik referanslarla gerekçelendirmiş.
- **Haftalık plan + günlük log:** 6 haftalık plan ve ters kronolojik günlük log.
- **Ekip demosu 4 Eylül:** Üç modül de bu tarihe yetiştirildi.
- **Gizlilik disiplini:** Fabrika görüntüleri üç repoda da yasaklı (`.gitignore`).
- **Bulut GPU erişimi:** Üçü de GPU erişimi için Google Colab ve/veya Kaggle T4 kullandı; Reşit ayrıca yerel RTX 4050 (6 GB, CUDA 12.6) ile geliştirdi.
- **PyYAML:** Üçü de YAML okudu — Reşit ve Özgür config/envanter için, Bedirhan ise YOLO `dataset.yaml` için kullandı (config-driven yapı Reşit ve Özgür'de daha belirgin).
- **NumPy:** Üçü de sayısal işlemler için NumPy kullandı.
- **Kalman/filtering/tracking kavramları:** Bedirhan ByteTrack, Reşit temporal stabilizer (EMA + oylama), Özgür MOG2 (Gaussian mixture) — üçü de "zamansal tutarlılık" kavramıyla farklı şekillerde uğraştı.

#### 9.2. Farklılıklar

| Boyut | Bedirhan | Reşit | Özgür |
|---|---|---|---|
| **Öğrenme paradigması** | Denetimli | Denetimli + kural | Denetimsiz |
| **AI omurgası** | YOLOv8 | YOLOv8 + klasik CV | PatchCore/PaDiM |
| **Çıktı tipi** | Akış (ofset) | Değer (okuma) | Rapor (kanıt) |
| **Frekans** | Yüksek (≥15 Hz) | Düşük (tur) | Düşük (tur) |
| **Kod büyüklüğü** | 1707 satır | 6297 satır | 214 dosya |
| **Test disiplini** | Yok | 18 pytest | FP testleri |
| **Gömülü hedef** | Belirsiz | Orange Pi 5 (net) | Windows (opsiyonel GPU) |
| **Veri etiketleme** | Hazır veri seti | Sentetik-önce (bedava GT) | Altın tur referans |
| **Production olgunluğu** | Orta | Yüksek | Yüksek |
| **Dökümantasyon zenginliği** | 3 dosya | 6+ dosya | En zengin (AI.md dahil) |
| **Ekip katkısı** | MQTT altyapı | demo uyuşmazlık raporu | doküman merkezi |
| **OCR kullanımı** | Yok | Yok (segment geometrisi seçti) | Yok |
| **Tracking** | ByteTrack | temporal stabilizer | MOG2 |
| **Raporlama** | Markdown | JSON + matplotlib | Jinja2 + fpdf2 PDF |

---

### 10. Riskler, Sınırlamalar ve Açık Konular

#### 10.1. Üç Repoda Ortak Riskler

- **Model ağırlıkları ve veri setleri repoda yok.** Üçü de `*.pt`, veri setlerini `.gitignore` ile dışlıyor. Bu, tekrar üretilebilirliği zorlaştırıyor; yeni bir geliştiricinin `best.pt`'yi veya MVTec-AD'yi sıfırdan üretmesi/indirmesi gerekiyor.
- **Shallow clone / squash'lanmış commit geçmişi.** Bedirhan ve Reşit'in reposunda tek commit var; günlük commit geçmişi görünmüyor. Geliştirme aşamaları sadece `daily_log.md`'den takip edilebiliyor.
- **Gerçek MQTT broker testi eksik.** Üçü de broker'ı tam olarak test etmedi (Bedirhan Mosquitto kurulum durumu belirsiz, Reşit dosya moduna düştü, Özgür `--offline` çalıştı).
- **Edge/üretim donanımı doğrulanmamış.** Bedirhan "Edge cihaz" belirsiz, Reşit Orange Pi 5 hedefi ama gerçek cihazda test edilmedi, Özgür Windows'ta geliştirdi.
- **LICENSE yok** (üçü de).
- **CI/CD yok** (üçü de).

#### 10.2. Bedirhan'a Özel Riskler

- Sayısal MOTA/IDF1 değerleri yok (manuel GT atlandı) → "yüksek IDF1" iddiası kanıtsız.
- README ile kod arasında 6 tutarsızlık (olmayan dosyalar, YOLOv11 kullanılmamış, SH17→PPE değişikliği, publisher→live_detector zinciri kırık).
- Kod kokuları: `frame_w in locals()`, bare `except:`.
- Edge cihaz spesifik değil.
- Test/CI/Docker yok.

#### 10.3. Reşit'e Özel Riskler

- Gösterge kimliği görüntüden çıkarılamıyor (waypoint placeholder).
- 180° ters okuma sessiz hata (%8.1 `refine_dial` kestiriminde).
- Dijital panel gerçek fotoğrafta 0/5→1/5.
- Keypad tespit sınıfı yok.
- Tespit yeniden eğitimi videolarda işe yaramadı (alan aşırı uyumu).
- A1/A2 Cambridge veri setleri erişilemiyor (404).
- Kapı eşikleri eski ağırlığın dağılımından.
- MQTT şema format uyuşmazlığı ("WP-04" vs "WP01").

#### 10.4. Özgür'e Özel Riskler

- İP16 final teslim tamamlanmadı (4 Eylül geçti).
- anomalib/PyTorch yorum satırı → kurulum belirsizliği.
- Hardcoded Windows yolları (eski scriptler).
- F1=0.667 düşük; GT bbox'lar tespitlerden türetildi (dairesel değerlendirme).
- Türkçe karakter sorunu fpdf2'de.
- MQTT broker gerçekten test edilmedi.
- S4-S7 senaryoları test edilmedi.
- Duplike/eski dosyalar.
- `rasrav_gauge_repo` klasörünün neden orada olduğu belirsiz.

---

### 11. Sunum Konuşma Notları

Bu bölüm, raporu bir sunum olarak anlatacak kişi için hazır konuşma notlarıdır.

#### 11.1. Açılış (2 dakika)

"Bugün size BTÜ 03_Gama Grubu'nun 2026 yaz stajında geliştirilen akıllı fabrika devriye robotunun görüntü işleme katmanını sunacağım. Bu robot, fabrika koridorlarında otonom tur atan pan-tilt kameralı bir platform. Üç stajyer — Bedirhan Gök, Reşit Asrav ve Özgür Kotbaş — robotun 'görme' yeteneğinin üç farklı boyutundan sorumluydu. Her biri farklı bir bilgisayarlı görü paradigması seçti: nesne tespiti, gösterge okuma ve anomali tespiti. Modüller MQTT pub/sub mimarisi üzerinden, donmuş JSON şemalarıyla haberleşiyor. Amacım, her stajyerin hangi teknolojiyi neden seçtiğini ve bu seçimin çıktıyı nasıl etkilediğini göstermek."

#### 11.2. Çatı Mimari (3 dakika)

"Üç modül tek bir fiziksel akışın parçaları. Kamera görüntüsü alınıyor: Bedirhan tehlikeleri ve insanları bulup pan-tilt'i takibe yönlendiriyor, Reşit çevredeki ölçüm cihazlarını okuyor, Özgür sahneyle referans arasındaki farkları tespit edip rapor üretiyor. Üçü de birbirinin koduna değil, MQTT şemalarına bağlı. Bedirhan'ın `target_offset_schema.md`'i 'donduruldu' olarak işaretli — yani bir kez sözleşme yapıldı, değişmedi. Bu, üç stajyerin paralel geliştirebilmesini sağlayan anahtar mimari karar."

#### 11.3. Bedirhan — VİZYON (5 dakika)

"Bedirhan'ın modülü robotun 'gözü'. YOLOv8 ile nesne tespiti, ByteTrack ile takip yapıyor. Neden YOLOv8? Çünkü gerçek zamanlı — ~30 FPS canlı, ~20 FPS MQTT yayın. Hedef ≥15 Hz'di, aştı. Neden ByteTrack? Occlusion'da, yani nesne kısmen kapandığında ID kaybını önler. Bu kritik çünkü çıktı bir ofset akışı — pan-tilt motorları bu ofseti PID ile takip ediyor. ID kaybı olursa robot hedefi kaybeder ve titrer. Bedirhan ayrıca bir sınıf öncelik sistemi kurdu: düşen işçi 100 puan, KKD ihlali 90, normal insan 50. Yani robot 'ilk gördüğünü' değil, 'en tehlikeli olanı' takip ediyor. Bu, güvenlik odaklı bir tasarım kararı. Confidence'ı 0.4'ten 0.6'ya yükseltti — yanlış kilitlenmeyi önlemek için. Retry mekanizmaları var — kamera koparsa sistem çökmesin diye. Zayıf nokta: MOTA/IDF1 sayısal değerleri hesaplanmadı, çünkü manuel ground truth etiketleme atlandı. Yani 'yüksek IDF1' iddiası nitel."

#### 11.4. Reşit — GÖSTERGE (5 dakika)

"Reşit'in modülü, operatörün elle yaptığı gösterge okuma turunu otomatikleştiriyor. Beş gösterge tipini okuyor: analog ibre, dijital 7-segment, ikaz lambası, vana, keypad. En çarpıcı karar: dijital panel için OCR kullanmadı. PaddleOCR ve Tesseract requirements.txt'te ama yorum satırı. Neden? Çünkü 7-segment segment geometrisi deterministik — OCR ise gömülü ortamda ağır ve hata yapar. Reşit'in çekirdeği tamamen torch'suz — Orange Pi 5 + NPU hedefi için tasarlandı. YOLOv8 sadece tespit için kullanılıyor, kart üstünde değil. Üç temel tasarım kuralı var: Birincisi, 'yanlış okumaktansa okumamak' — yanlış basınç okuması kazaya yol açabilir, bu yüzden belirsizse `status: unreadable` diyor. İkincisi, 'kanıt, cevap makul mü değil' — her eşik iki dağılım ölçülerek seçiliyor, körlemesine konmuyor. Bu kural sayesinde sahte okuma 383'ten 39'a düştü. Üçüncüsü, tek doğru kaynak — gösterge envanteri YAML'da, koda gömülmez. Yeni gösterge eklemek için YAML'a bir satır yazman yeterli. Sonuç: analog okuma hatası %0.19 — hedef <%5'in çok altında. 320 test geçiyor. Zayıf nokta: gösterge kimliği görüntüden çıkarılamıyor, dijital panel gerçek fotoğrafta 0/5, keypad tespit sınıfı yok."

#### 11.5. Özgür — ANOMALİ (5 dakika)

"Özgür'ün modülü robotun 'bir şeyler yolunda değil' deme yeteneği. 'Altın tur' konsepti: önce normal bir devriye turu kaydediliyor (referans), sonra canlı tur bununla karşılaştırılıyor. İki katmanlı ensemble var: MOG2 arka plan çıkarma ve PatchCore. Neden MOG2? Çünkü açı-bağımsız. Robot köpek her turda aynı açıyı tutamıyor; ORB homografisi ~20° tolerans sonrası kırılıyor. MOG2 videoyu kendi içinde taradığı için açıya tamamen bağımsız. Neden PatchCore? Çünkü denetimsiz — anomali örnekleri toplanamaz, sadece 'normal' toplanır. PatchCore MVTec-AD'de AUROC=1.0 başardı. İP12'de iki kritik düzeltme yaptı: MOG2'de `cap.set()` geri sarma bug'ını kaldırdı, PatchCore'da `ResNet18[:-1]` yerine `[:-2]` kullanarak 49 spatial patch çıkardı — küçük anomaliler kayboluyordu. Bu düzeltmeler F1'i 0.333'ten 0.667'ye çıkardı, yüzde 100 iyileşme. Tur sonunda otomatik rapor üretiyor — Jinja2 ile Markdown, fpdf2 ile PDF. Kapak, özet metrikler, öncelik sıralı uyarı kartları (HIGH kırmızı, MEDIUM turuncu, LOW mavi), görüntü kanıtları. Evrensel kaynak adaptörü var — video, RTSP, webcam, statik görüntü hepsi çalışıyor. Multi-deployment desteği — birden fazla fabrika aynı broker'a bağlanınca topic collision'ı önleniyor. Zayıf nokta: F1 hala düşük, GT bbox'lar tespitlerden türetildiği için dairesel değerlendirme var, MQTT broker gerçekten test edilmedi, S4-S7 senaryoları eksik. Özgür'ün reposu ayrıca ekibin doküman merkezi — AI.md 657 satır, Bedirhan ve Reşit'in proje tanımları da orada."

#### 11.6. Karşılaştırma ve Kapanış (3 dakika)

"Üç stajyeri karşılaştıralım. Bedirhan denetimli öğrenme ile gerçek zamanlı aktif takip çözüyor — çıktı bir ofset akışı. Reşit gömülü taşınabilirlik için torch'suz çekirdek ve sentetik-önce strateji ile gösterge okuyor — çıktı değer. Özgür denetimsiz öğrenme ile anomali tespit ediyor ve otomatik rapor üretiyor — çıktı kanıt. Üçü de Python, OpenCV, paho-mqtt ve Mosquitto ortak teknolojisinde birleşiyor. Ama her biri görevinin doğasına uygun farklı AI omurgası seçti. Ortak disiplinler: hata toleransı (retry/offline), ölçüm odaklı eşik seçimi, literatür öncülü kararlar. Reşit ve Özgür config-driven yapıyla production-ready'a yaklaştı; Bedirhan daha kompakt ve MQTT şema odaklı bir yapı kurdu. Bedirhan ve Reşit tamam, Özgür'de İP16 final bekliyor. Teşekkürler."

---

### 12. Ek: Kanıt Dosya Yolları

#### 12.1. Bedirhan (Repo 1) — Kanıt Dosya Yolları ve Satır Numaraları

**Teknoloji kullanım kanıtları:**
- ultralytics (YOLOv8): `vision/detector.py:17`, `vision/live_detector.py:19`, `vision/evaluate_tracker.py:13`, `vision/train.py:30`; `requirements.txt:5`
- OpenCV: `infra/publisher.py:12`, `infra/subscriber.py:20`, `vision/live_detector.py:13`, `vision/evaluate_tracker.py:9`, `scripts/simulate_harsh_conditions.py:1`; `requirements.txt:6`
- paho-mqtt: `infra/publisher.py:13`, `infra/subscriber.py:11`, `infra/recorder.py:9`, `infra/replayer.py:10`, `vision/live_detector.py:18`; `requirements.txt:10`
- numpy: `infra/subscriber.py:17`, `scripts/simulate_harsh_conditions.py:2`; `requirements.txt:7`
- motmetrics: `scripts/calculate_metrics.py:14`; `requirements.txt:13`
- pandas: `scripts/calculate_metrics.py:15`; `requirements.txt:14`
- torch: `vision/train.py:106-107`; `requirements.txt:16`
- kagglehub: `vision/train.py:26-29`, `vision/train.py:69`
- PyYAML: `vision/train.py:12,88,95`

**Önemli kod kanıtları:**
- ByteTrack aktif: `vision/live_detector.py:137` — `model.track(source=frame, conf=args.conf, iou=args.iou, persist=True, verbose=False)`
- Lock-on mantığı: `vision/live_detector.py:109`, `151-164`, `167-184`
- dx/dy ofset hesaplama: `vision/live_detector.py:205-214`
- MQTT ofset yayını: `vision/live_detector.py:222-236`
- Bekleme modu (track_id:-1): `vision/live_detector.py:237-249`
- Priority skorları: `vision/live_detector.py:25-40`
- NMS/conf eşikleri: `vision/live_detector.py:54-55`
- Kamera retry: `vision/live_detector.py:121-130`
- MOT16 format çıktısı: `vision/evaluate_tracker.py:73`
- MOTA/IDF1 hesaplama: `scripts/calculate_metrics.py:84`
- Karanlık simülasyonu: `scripts/simulate_harsh_conditions.py:27-34`
- Titreşim simülasyonu: `scripts/simulate_harsh_conditions.py:38-42`
- GPU algılama: `vision/train.py:107`
- MQTT broker ayarları: `infra/publisher.py:21-23`
- JPEG kalitesi: `infra/publisher.py:24`
- Şema dondurma: `docs/target_offset_schema.md:4`

#### 12.2. Reşit (Repo 2) — Kanıt Dosya Yolları ve Satır Numaraları

- Açı konvansiyonu şeması: `configs/gauges.yaml:16-37`
- 8 gösterge tanımı: `configs/gauges.yaml:56-311` (PT-101:56, TI-205:77, FI-310:96, EM-501:126, DP-401:156, LM-501:181, VL-601:197, CP-701:234)
- `value_for_angle` (İP7 çekirdeği): `src/gauge_vision/config.py:141-154`
- `GAUGE_TYPES`: `config.py:29`
- Kanıt kapıları `MIN_TESPIT_GUVENI=0.30`, `MIN_IBRE_KANITI=0.10`: `pipeline.py:249-250`
- `read_all_analog`: `pipeline.py:253-308`
- `read_gauge` tip dallanması: `pipeline.py:337-366`
- `read_frame` zincir sırası: `pipeline.py:456-521`
- Polar tarama `_read_polar` + `_polarity_mask` (Otsu): `needle.py:238-324`
- Hough `_read_hough` (Canny+HoughLinesP): `needle.py:380-436`
- `refine_dial` gradyan doğrusu kesişimi: `refine.py:153-179`, `182-297`
- `duzlestir` elips→daire afin: `perspective.py:140-210`
- `estimate_roll` FFT korelasyon: `roll.py:225-234`, kapılar `MIN_UYUM=0.40`, `MIN_AYRIKLIK=0.10`: `roll.py:82,108`
- `read_value` (İP7): `calibrate.py:85-133`
- 7-segment `DESEN_RAKAM` tablosu: `digital.py:98-103`
- `_segment_maskesi` iki kademeli Otsu: `digital.py:118-161`
- `_aydinlatma_bantlari` (8 band): `digital.py:332-362`
- `_lamba_durumu` HSV: `state.py:111-162`
- `_kol_acisi` PCA: `state.py:165-206`
- `read_keypad` buton→machine_state: `keypad.py:223-285`
- `TemporalStabilizer` EMA + oylama: `temporal.py:57-323`
- `generate_dataset` (tohumlu): `synth/generate.py:111-173`
- `mesaj_dogrula` (şema kuralı): `publish/reading.py:71-105`
- `ReadingPublisher.baglan` (broker→dosya modu): `publish/reading.py:141-163`
- config doğrulama: `_dogrula_butonlar`: `config.py:335-440`, `_dogrula_kol_acilari`: `config.py:442-488`

#### 12.3. Özgür (Repo 3) — Kanıt Dosya Yolları ve Satır Numaraları

**requirements.txt:**
- `opencv-python>=4.8.0` (satır 2), `numpy>=1.24.0` (satır 3), `scikit-image>=0.21.0` (satır 4), `python-dotenv>=1.0.0` (satır 5), `fpdf2>=2.7.4` (satır 6), `paho-mqtt>=1.6.1` (satır 9), `Jinja2>=3.1.2` (satır 10), `PyYAML>=6.0` (satır 11)
- `# anomalib`, `# torch>=2.0.0`, `# torchvision>=0.15.0` (satır 13-15, yorum)

**config.yaml:**
- `broker: "${MQTT_BROKER:-localhost}"` (satır 6), `patchcore_thresh: 0.50` (satır 11), `mog2_history: 200` (satır 14), `mog2_thresh: 20` (satır 15), `yellow_hsv_lower/upper` (satır 21-22), `tavan_crop_oran: 0.18` (satır 28), `rotation_flow_thresh: 3.5` (satır 29), `mog2_warmup_n: 40` (satır 31)

**scripts/vision/ip9_ensemble_analiz.py:**
- Mimari karar docstring: satır 3-46
- KATMAN 1 MOG2: satır 36-39
- KATMAN 2 PatchCore spatial: satır 41-47
- `is_alert` kararı: satır 55-58
- `PatchCoreScorer.__init__` ResNet18 `[:-2]`: satır 144-152
- `_extract_patches` (512,7,7)→(49,512): satır 168-179
- `score` cosine similarity: satır 204-222
- `mog2_detect` warmup: satır 249-257
- Video modu single-pass: satır 287-305

**scripts/core/anomali_motor.py:**
- `class AlgilayiciMOG2`: satır 15
- `cv2.createBackgroundSubtractorMOG2`: satır 27-28
- warmup: satır 37-38
- Optical Flow `cv2.calcOpticalFlowFarneback`: satır 43-46
- `learning_rate = 0.0 if is_rotation else -1.0`: satır 53
- gölge kaldırma `fg[fg==127]=0`: satır 57
- Tavan crop: satır 60
- Sarı maske: satır 62-65

**scripts/vision/ip8_degisiklik_tespiti.py:**
- Sarı çizgi FP docstring: satır 10-16
- `cv2.ORB_create`: satır 88-90
- Lowe ratio test 0.80: satır 95
- Zemin homografi: satır 114-117
- `cv2.findHomography` RANSAC: satır 133
- SSIM `structural_similarity`: satır 146

**scripts/vision/anomali_test.py:**
- `from anomalib.data import MVTecAD`: satır 5
- `from anomalib.engine import Engine`: satır 6
- `from anomalib.models import Padim`: satır 7
- MVTecAD bottle datamodule: satır 11-15
- `model = Padim()`: satır 18
- `engine.fit`: satır 22

**scripts/vision/model_ve_heapMap.py:**
- `from anomalib.data import Folder`: satır 1
- `from anomalib.models import Patchcore`: satır 2
- `from anomalib.engine import Engine`: satır 3
- Folder datamodule (hardcoded `D:/STAJ/...`): satır 5-11
- `Patchcore(backbone="resnet18", coreset_sampling_ratio=0.1)`: satır 13-15

**scripts/comms/ip10_mqtt_yayini.py:**
- MQTT şema docstring: satır 27-39
- `mesaj_dogrula`: satır 86-100
- deployment-id topic: satır 140-143
- eşsiz client ID: satır 143

**scripts/comms/ip11_rapor_uret.py:**
- uyarıları severity sıralama: satır 127-146
- Jinja2 render: satır 150-155
- `son_devriye_raporu.md`: satır 195

**scripts/comms/ip13_pdf_rapor.py:**
- `class DevriyeRaporuPDF(FPDF)`: satır 80
- `SEV_RENK` HIGH=(220,50,50), MEDIUM, LOW, NONE: satır 82-87
- `uyari_karti`: satır 128-161
- `kapak`: satır 220-256
- `ozet_sayfasi`: satır 258-285

**scripts/ip14_canli_tur.py:**
- `class WaypointAnalizci`: satır 120-179
- warmup referans kareden docstring: satır 148-153
- `_ssim_analiz`: satır 181-246
- `class TurYonetici`: satır 446-519

**scripts/ip15_harita_konumlandir.py:**
- `ip14_uyari_yukle`: satır 73-119
- `waypoint_rota_yukle`: satır 122-158

**scripts/core/kaynak_adaptoru.py:**
- Adapter Pattern docstring: satır 8-19
- `_kaynak_tipini_belirle`: satır 61-87
- `kare_al` video seek: satır 89-130

**.env.example:**
- `DEPLOYMENT_ID=fabrika_a_hat_1` (satır 6), `MQTT_BROKER=192.168.10.100` (satır 9), `MQTT_PORT=1883` (satır 10), `MQTT_TOPIC_BASE=patrol/alert` (satır 11), `CAMERA_SOURCE=rtsp://...` (satır 14), `REF_DIR=data/waypoints/referans_kareler/` (satır 17)

**Çıktı JSON'ları:**
- `data/ip9_ensemble/ensemble_ozet.json`: TP=2, FP=1, FN=1, F1=0.667 (satır 7-13); WP01 PC=0.3803 FP IoU=0.094; WP02 PC=0.3198 TP IoU=0.493; WP03 PC=0.515 TP IoU=0.692
- `outputs/model_results/ip5_patchcore_padim/rapor.md`: PatchCore Image F1=0.9920, AUROC=1.0000; PaDiM F1=0.9841, AUROC=0.9968
- `docs/raporlar/rapor.md`: PaDiM bottle image_AUROC=0.9952, F1=0.9687; eğitim 40.35sn, test 15.41sn, throughput 5.38 FPS; PadimModel 2.8M params

---

### 12.5. Mimari Analiz: Hareketli Kamera ve Yanlış Pozitif Problemi (Sistem Entegrasyonu)

Bu bölümde, modüllerin (GÖSTERGE, ALGILAMA, ANOMALİ) birleştirildiği demo ortamındaki uyumsuzluklar ve robot hareket halindeyken ortaya çıkan yapısal sorunlar analiz edilmiştir.

#### 1. Demo Ortamının Çalışma Yapısı
Demo dosyası (`rasrav_gauge_repo/demo/run_demo.py`), üç farklı repoyu MQTT üzerinden değil, doğrudan kod (import) seviyesinde birleştiren bir sarmalayıcıdır (wrapper):
- **GÖSTERGE (Reşit):** Kendi `gauge_vision` paketi standart olarak import edilip çalıştırılır.
- **ALGILAMA (Bedirhan):** Bedirhan'ın kodu modüler (tek-karelik bir fonskiyon) olmadığı için, demo kendi içinde YOLO çağrılarını tekrar yazar.
- **ANOMALİ (Özgür):** Başlangıçta test için kullanılan `MVTec-AD` indiren eğitim scriptlerine bağlıydı. Güncelleme sonrası `_AnomalDurumu` adında bağımsız bir sarmalayıcı sınıf yazılarak `anomali_hizalamali.py` (MOG2 + RANSAC) kodları doğrudan kare-bazlı çağrılabilir hale getirilmiştir. 

#### 2. Yanlış Pozitif (False Positive) Uyarıların Nedeni: 3D Parallax Problemi
`kontrol_et` klasöründeki testlerde karşılaşılan devasa yanlış anomali uyarılarının (özellikle koridor videosunda) sebebi kod hatası değil, **algoritmik bir mimari uyumsuzluktur**:
- **Sorun:** Pan-tilt kameralı robot köpek hareket halindeyken (waypointler arası geçiş yaparken) sahnedeki derinlik (depth) değişir. 
- **Parallax Etkisi:** Kameraya yakın nesneler, uzak nesnelere göre daha hızlı yer değiştirir. `anomali_hizalamali.py` içindeki ORB+RANSAC hizalaması **2 boyutlu (2D) bir homografi** matrisi hesaplar. Bu yöntem, kameranın sadece olduğu yerde sağa-sola dönmesi (pan) durumunda kusursuz çalışır, ancak robot ileri doğru yürüdüğünde oluşan 3D perspektif kaymasını (parallax) düzeltemez.
- **Sonuç:** Hizalanamayan derinlik farkları, MOG2 tarafından "hareket eden yeni bir anomali" olarak algılanır ve tüm ekran kırmızı kutularla dolar.

#### 3. Robot Köpek İçin En Mantıklı Anomali Tespiti Mimarisi
Mevcut mimari (MOG2 + PatchCore), **robotun tamamen durduğu (sabitlendiği)** waypoint noktalarında anomali aramak için harikadır. Ancak hareket halindeyken (transit geçiş) başarısız olmaya mahkumdur. 

Robot köpek için en optimal mimari **İki Fazlı (Hibrit) Sistem** olmalıdır:
1. **Hareket Halindeyken (Transit):** Arka plan çıkarma (MOG2) ve homografi kullanılmamalıdır. Bunun yerine sadece Bedirhan'ın **YOLO (Nesne Tespiti)** modeli aktif olmalı, "Düşen İşçi", "Baret Yok", "Forklift Yolu Tıkıyor" gibi bilinen tehlikeler aranmalıdır. Ayrıca basit bir renk uzayı (HSV) veya semantik segmentasyon ile zemindeki sıvı sızıntıları aranabilir.
2. **Duraklama Anında (Waypoint):** Robot hedefe varıp durduğunda kamera sabitlenir. Bu anda **MOG2** çalışarak ortama sonradan bırakılmış yabancı cisimleri tespit ederken, **PatchCore** (yapısal anomali) ile borulardaki bükülme, kırılma veya kapı durumları analiz edilir.

*(Not: Bu analiz sonrası, robotun hareket durumunu tespit edip hareket anında MOG2'yi durduran Öncelik 1 ve 2 düzeltmeleri sisteme başarıyla entegre edilmiştir.)*

---

### 13. Sonuç

Bu rapor, BTÜ 03_Gama Grubu'nun 2026 yaz stajında geliştirilen akıllı fabrika devriye robotunun görüntü işleme katmanını oluşturan üç GitHub reposunun derinlemesine analizidir.Tüm dökümanlar, kod dosyaları, bağımlılık dosyaları ve çıktı JSON'ları satır satır incelenmiştir.

Üç stajyer — Bedirhan Gök (VİZYON/ALGILAMA), Reşit Asrav (GÖSTERGE), Özgür Kotbaş (ANOMALİ) — pan-tilt kameralı devriye robotunun "görme" yeteneğinin üç farklı boyutundan sorumluydu. Her biri, çözdüğü problemin doğasından kaynaklanan teknoloji seçimleri yaptı:

- **Bedirhan**, gerçek zamanlı aktif takip için **denetimli nesne tespiti + tracking** (YOLOv8 + ByteTrack) seçti. Çıktısı bir ofset akışıydı (`vision/target_offset`, ≥15 Hz). Güvenlik önceliği için sınıf bazlı puanlama (düşen işçi=100) kurdu. Zayıf nokta: sayısal MOTA/IDF1 değerleri hesaplanmadı.

- **Reşit**, gömülü cihazda (Orange Pi 5 + NPU) gösterge okuma için **torch'suz NumPy+OpenCV çekirdeği** ve **sentetik-önce strateji** seçti. OCR yerine segment geometrisi. "Yanlış okumaktansa okumamak" ve "kanıt, cevap makul mü değil" kurallarıyla sahte okuma %89.8 azaldı. Çıktı: %0.19 analog okuma hatası (hedef <%5'in çok altında). Zayıf nokta: gösterge kimliği, 180° ters okuma, dijital panel gerçek fotoğrafta 0/5.

- **Özgür**, az veriyle anomali tespiti için **denetimsiz öğrenme** (PatchCore/PaDiM) ve açı-bağımsızlık için **MOG2 + PatchCore ensemble** seçti. Çıktısı otomatik kanıtlı PDF devriye raporu. F1 0.333'ten 0.667'ye çıktı (%100 iyileşme). Production-ready: config-driven, Adapter Pattern, multi-deployment. Zayıf nokta: F1 hala düşük, GT dairesel, MQTT test edilmemiş, S4-S7 eksik.

Üçü de Python, OpenCV, paho-mqtt, Mosquitto, PyYAML ve NumPy ortak teknolojisinde birleşti. Reşit ve Özgür'de config-driven yapılandırma (`config.yaml`/`pyproject.toml`) güçlüdür; Bedirhan'da ise yapılandırma daha çok CLI (`argparse`) + donmuş MQTT şema sözleşmesi üzerinden yürür. Üçü de hata toleransı (retry/offline mod) ve ölçüm odaklı eşik seçimi disiplinini paylaştı.

Her teknik iddia, repo-relative dosya yolu ve satır numarasıyla kanıtlanmıştır (Bölüm 12). Üç repo da, staj döneminin kısalığına (30 iş günü) rağmen, endüstriyel kalitede görüntü işleme sistemleri ortaya koymuş; her stajyer kendi modülünün gereksinimlerine uygun, gerekçelendirilmiş teknik kararlar almıştır.

---

