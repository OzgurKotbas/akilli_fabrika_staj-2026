# 📓 Günlük İlerleme Kaydı — Özgür Kotbaş

> Repo: `akilli_fabrika_staj-2026` · Başlangıç: 27.07.2026 · Bitiş: 04.09.2026
> Commit formatı: `İPx: kısa açıklama`

---

## Hafta 1 — 27–31 Temmuz 2026

### 📅 27–28 Temmuz 2026 (Pazartesi–Salı)

**Aktif İş Paketi:** İP1 — anomalib ilk çalıştırma

**Bugün yapılanlar:**
- [x] Proje ortamı kuruldu, anomalib kütüphanesi yüklendi
- [x] MVTec-AD veri seti araştırıldı; Kaggle üzerinden (`ipythonx/mvtec-ad`) erişim yolu belirlendi
- [x] `anomali_test.py` scripti yazıldı: anomalib Engine API kullanılarak PaDiM modeli ayarlandı
- [x] `bottle` kategorisinde ilk eğitim çalıştırıldı (Hugging Face'den ResNet18 ağırlıkları otomatik indirildi)
- [x] Sonuçlar alındı ve `RAPORLAR/rapor.md` dosyasına kaydedildi

**Sonuçlar (PaDiM — bottle):**
- Eğitim süresi: ~40.35 sn · Test süresi: ~15.41 sn
- `image_AUROC`: **0.9952** · `image_F1Score`: **0.9687**
- `pixel_AUROC`: 0.9799 · `pixel_F1Score`: 0.6944

**✅ İP1 bitti kriteri karşılandı:** Anomali heatmap çıktısı alındı.

---

### 📅 29–30 Temmuz 2026 (Çarşamba–Perşembe)

**Aktif İş Paketi:** İP4 — Mini literatür taraması

**Bugün yapılanlar:**
- [x] [awesome-industrial-anomaly-detection](https://github.com/M-3LAB/awesome-industrial-anomaly-detection) deposu tarandı
- [x] 10 makale seçildi ve her biri için detaylı notlar çıkarıldı (`PROJE/h1/30.07/Notlar.md`)
- [x] Ek olarak 9 makale daha özeti yazıldı (`PROJE/h1/30.07/Makaleler.md`)

**İncelenen makaleler (özet):**

| # | Makale | Önem |
|---|--------|------|
| 1 | FastFlow (arxiv 2111.07677) | Gerçek zamanlı inference |
| 2 | MVTec AD Dataset (CVPR 2019) | Temel benchmark |
| 3 | PaDiM (arxiv 2011.08785) | **Birincil model adayı** |
| 4 | SimpleNet (CVPR 2023) | Hız/doğruluk dengesi |
| 5 | Zero-Shot Scene Change Detection | Altın tur kıyasının akademik karşılığı |
| 6 | RMMDet — Sensor Fusion | Çok modelli algılama |
| 7 | ChangeFormer (Siamese Transformer) | Değişiklik tespiti |
| 8 | DUSt3R — 3D Reconstruction | Stretch hedef (LingBot-Map bağlantısı) |
| 9 | WinCLIP — Zero/Few-Shot | Az veriyle çalışma |
| 10 | LingBot-Map (GCT) | **Stretch hedef** — 3D altın tur |

**Commit:** `makaleler özetlendi` (2026-07-31 10:45)

**✅ İP4 bitti kriteri karşılandı:** Özet tablosu repoda.

---

### 📅 31 Temmuz 2026 (Cuma)

**Aktif İş Paketi:** İP3 — İlk altın tur kaydı + LingBot-Map keşfi

**Bugün yapılanlar:**
- [x] **Altın tur video kaydı yapıldı:** Koridorda sabit rotalı video çekildi (`31.07/koridor_992.mp4`, ~10.8 MB)
- [x] Google Colab T4 GPU üzerinde [LingBot-Map](https://github.com/robbyant/lingbot-map) pretrained modeli çalıştırıldı
- [x] Koridor videosundan 3D nokta bulutu çıkartıldı → `31.07/koridor_992_pointcloud.mp4`
- [x] Çıktı kareleri Google Drive'a yüklendi (`31.07/Frames_linki.txt` — Drive linki)
- [x] Nokta bulutu JSON çıktısı elde edildi (`31.07/batch_results.json`)

**Commit:** `Altın Tur. JSON çıktısı ve frames linki` (2026-07-31 21:03)

**✅ İP3 bitti kriteri karşılandı:** Referans video + 3D nokta bulutu çıktısı repoda.

> **Not:** LingBot-Map çıkarımı başarıyla çalıştı — bu stretch hedef (İP15) için erken bir prova niteliğinde. Ana hat olan 2D waypoint kıyası hâlâ öncelikli.

---

## Hafta 2 — 1–7 Ağustos 2026

### 📅 1 Ağustos 2026 (Cumartesi)

**Aktif İş Paketi:** İP3 tamamlama — Renderer kodu + video organizasyonu

**Bugün yapılanlar:**
- [x] Nokta bulutu render scripti geliştirildi (`31.07/Renderer_kodu.md`): ORB renderer, dünya koordinat dönüşümü, FFmpeg video çıktısı
- [x] Dosyalar `31.07/` klasörü altında düzenlendi (rename commit'leri)

**Commit'ler:**
- `Altın tur video kaydı - renderer kodu` (21:56)
- `Rename Renderer_kodu.md to 31.07/Renderer_kodu.md` (21:57)

---

### 📅 1–2 Ağustos 2026 (Cumartesi–Pazar)

**Aktif İş Paketi:** İP5 — MVTec baseline (F1/AUROC tablosu)

**Bugün yapılanlar:**
- [x] Google Colab T4 GPU üzerinde **PatchCore** modeli eğitildi ve test edildi (bottle kategorisi)
- [x] **PaDiM** modeli de eğitildi; PatchCore ile karşılaştırıldı
- [x] İki modelin F1 ve AUROC metrikleri karşılaştırmalı tabloya yazıldı
- [x] Her anomali türü için çıktı görüntüleri elde edildi (4 panel: ham görüntü / GT mask / ısı haritası / tahmin maskesi)
- [x] Detaylı rapor yazıldı (`01-02.08/ip5_model_ciktilari/rapor.md`)

**Sonuçlar (bottle kategorisi):**

| Model | Image F1 | Image AUROC | Pixel F1 | Pixel AUROC |
|-------|----------|-------------|----------|-------------|
| **PatchCore** | **0.9920** | **1.0000** | 0.7268 | 0.9856 |
| PaDiM | 0.9841 | 0.9968 | — | — |

**Yorumlar:**
- PatchCore `bottle` kategorisinde AUROC=1.0 → **birincil model seçildi**
- PaDiM daha hafif, edge cihaz için ikincil aday
- Normal görüntülerde yanlış alarm yok → alarm yorgunluğu riski düşük ✅
- Pixel F1 (0.727) lokalizasyon hassasiyetinde iyileştirme alanı var → İP6-İP7'de ele alınacak

**✅ İP5 bitti kriteri karşılandı:** F1/AUROC tablosu commit'lendi.

---

### 📅 4 Ağustos 2026 (Salı)

**Aktif İş Paketleri:** İP5 dosyaları düzenlendi, repoya eklendi

**Bugün yapılanlar:**
- [x] İP5 model çıktıları ve raporlar `01-02.08/ip5_model_ciktilari/` klasörüne taşındı
- [x] Model ağırlıkları (büyük dosya) `.gitignore`'a alındı; yalnızca çıktı görselleri ve raporlar commit edildi
- [x] `ip5_mvtec_baseline.md` özet metrik dosyası eklendi
- [x] Fazlalık klasörler temizlendi

**Commit'ler (4 Ağustos, 15:31–19:17 arası):**
- `İP5: MVTec baseline sonuçları ve rapor eklendi`
- `ip5 rapor ve sonuç çıktısı`
- `İP5: Fazlalık klasör silindi`
- `İP5: Ağırlıklar hariç, sadece PatchCore ve PaDiM çıktı resimleri eklendi`
- `İP5 Tamamlandı: MVTec Baseline çıktıları ana dizine taşındı`
- `Görseller temizlendi: Sadece raporlar ve kodlar bırakıldı`

---

### 📅 5–6 Ağustos 2026 (Çarşamba–Perşembe)

**Aktif İş Paketi:** İP2 — Senaryo listesi + İP6 hazırlığı

**Bugün yapılanlar:**
- [ ] İP2: Senaryo listesi yazılacak → `PROJE/senaryo_listesi.md`
- [ ] İP6 için kendi veri klasörü hazırlanacak
- [ ] daily_log.md oluşturuldu (bu dosya)

**Notlar:**
- H1 fiilen tamamlandı: İP1 ✅ · İP3 ✅ · İP4 ✅ · İP5 ✅
- İP2 (senaryo listesi) yazıya dökülmedi ama kapsam zihinsel olarak netleşti — bugün commit edilecek
- Sıradaki adım: İP6 — waypoint karelerini anomali modeline öğretmek

---

## Hafta 3 — 10–14 Ağustos 2026 *(Planlanan)*

| İş Paketi | Hedef |
|---|---|
| İP6 — Kendi verisiyle anomali | Waypoint'ten normal öğren → değiştirilmiş sahnede heatmap |
| İP7 — Waypoint kıyası v0 | ORB hizalama + fark maskesi |
| İP8 — Değişiklik enjekteli tur | 2. tur kaydı: nesne bırak, kapı kapat |

---

> **Genel durum (6 Ağu itibarıyla):** İP1 + İP3 + İP4 + İP5 tamamlandı. İP2 bugün yazılacak. İP6'ya geçmeye hazır.
