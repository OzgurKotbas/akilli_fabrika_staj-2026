# İP3 Tekrar — Adım Adım Rehber

## 📁 Klasör Yapısı

```
ip3_tekrar/
├── scripts/
│   ├── 1_video_to_frames.py     ← Yerel: video → kareler
│   ├── 2_waypoint_sec.py        ← Yerel: waypoint karelerini seç
│   └── 3_ply_gorsellestir.py    ← Yerel: PLY dosyasını görüntüle
├── kaggle/
│   └── ip3_lingbotmap_notebook.py  ← Kaggle'a kopyalayacağın kodlar
├── frames/                      ← Script sonrası oluşur (kareler burada)
└── outputs/
    ├── waypoints/               ← Waypoint görüntüleri
    ├── altin_tur_v2.ply         ← Kaggle'dan indirilecek 3D harita
    └── pointcloud_screenshot.png
```

---

## 🗺️ Adımlar

### ADIM 1 — Video Kaydet (Yeni Altın Tur)
- Koridorda sabit, yavaş, duraklamalı çekim yap
- En az 5 waypoint (durak noktası) olsun
- Her durakta **2 saniye dur** → referans kare net olsun
- Kaydet: `data/raw_videos/altin_tur_v2.mp4`

---

### ADIM 2 — Yerel: Video → Kareler
```powershell
cd d:\STAJ\akilli_fabrika_staj-2026
python ip3_tekrar/scripts/1_video_to_frames.py data/raw_videos/altin_tur_v2.mp4
```
Çıktı: `ip3_tekrar/frames/` klasörü (~570-5000 .jpg dosyası)

---

### ADIM 3 — Yerel: ZIP Oluştur
```powershell
cd d:\STAJ\akilli_fabrika_staj-2026
Compress-Archive -Path ip3_tekrar\frames -DestinationPath ip3_tekrar\frames.zip
```
> frames.zip boyutu ne kadar olacak?
> 30fps, 19 sn video = ~570 kare × ~50KB = ~28 MB → sorunsuz yüklenir

---

### ADIM 4 — Kaggle: Dataset Yükle
1. [kaggle.com/datasets](https://www.kaggle.com/datasets) → **New Dataset**
2. Dataset adı: `altin-tur-v2`
3. `frames.zip` dosyasını yükle
4. **Public** veya **Private** seç → **Create**

---

### ADIM 5 — Kaggle: Yeni Notebook Aç
1. [kaggle.com/code](https://www.kaggle.com/code) → **New Notebook**
2. Sağ panel → **Accelerator: GPU T4 x2** seç
3. `ip3_tekrar/kaggle/ip3_lingbotmap_notebook.py` dosyasını aç
4. Her `"""..."""` bloğu = 1 Kaggle hücresi

**Hücreleri Kaggle'a yapıştırma sırası:**
| Kaggle Hücre | Dosyadaki Bölüm |
|---|---|
| Hücre 1 | `HÜCRE 1` — GPU kontrolü |
| Hücre 2 | `HÜCRE 2` — Kurulum (%%bash) |
| Hücre 3 | `HÜCRE 3` — Model indir |
| Hücre 4 | `HÜCRE 4` — Dataset yükle |
| Hücre 5 | `HÜCRE 5` — **LingBot-Map çalıştır** |
| Hücre 6 | `HÜCRE 6` — PLY doğrula |
| Hücre 7 | `HÜCRE 7` — Dosyaları indir |

> ⚠️ **ÖNEMLİ:** Hücre 4'te `DATASET_PATH` satırını kendi dataset adınla güncelle:
> ```python
> DATASET_PATH = "/kaggle/input/altin-tur-v2"  # ← senin dataset adın
> ```

---

### ADIM 6 — Kaggle: Çalıştır
- **"Run All"** yerine her hücreyi sırayla çalıştır
- Hücre 2 (kurulum) ~5-7 dk sürer
- Hücre 5 (inference) kare sayısına göre ~3-10 dk sürer

**1034 Frame Sorunu Nasıl Çözüldü?**
> Eski denemende `batch_demo.py` kullanıldı ve `frustum_cull_ext` modülü eksikti.
> Bu sefer:
> - ✅ `demo.py` kullanıyoruz (frustum_cull_ext gerektirmez)
> - ✅ `--use_sdpa` → her GPU'da çalışır, VRAM patlamaz
> - ✅ `--keyframe_interval` → windowed inference, sonsuz uzunlukta video işler

---

### ADIM 7 — PLY İndir ve Görselleştir
1. Kaggle Output paneli → `altin_tur_v2.ply` → ↓ indir
2. `ip3_tekrar/outputs/altin_tur_v2.ply` olarak kaydet
3. Görselleştir:
```powershell
pip install open3d
python ip3_tekrar/scripts/3_ply_gorsellestir.py ip3_tekrar/outputs/altin_tur_v2.ply
```

---

### ADIM 8 — Waypoint Karelerini Seç
```powershell
python ip3_tekrar/scripts/2_waypoint_sec.py
```
> Waypoint zamanlarını `2_waypoint_sec.py` içindeki `WAYPOINTS` listesinden düzenle.

---

## ✅ İP3 Bitti Kriterleri

- [ ] `ip3_tekrar/frames/` klasöründe kareler mevcut
- [ ] `ip3_tekrar/outputs/waypoints/WP01.jpg` ... `WP05.jpg` mevcut
- [ ] `ip3_tekrar/outputs/altin_tur_v2.ply` mevcut (3D harita)
- [ ] `ip3_tekrar/outputs/pointcloud_screenshot.png` repoya commit edildi
