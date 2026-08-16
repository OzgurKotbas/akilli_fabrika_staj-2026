# Anomali Tespiti Demo — README

**Proje:** Görsel Anomali Tespiti + Otomatik Devriye Raporu  
**Modül:** ANOMALİ → `patrol/alert`  
**Geliştirici:** Özgür Kotbaş · BTÜ · Grup 03_Gama · Staj 2026

---

## Hızlı Başlangıç

```
CALISTIR_DEMO.bat  ← Çift tıkla, çalışır
```

veya terminalde:
```powershell
cd D:\STAJ\akilli_fabrika_staj-2026
python scripts\demo_anomali.py
```

---

## Çalışma Modları

| Mod | Tetikleyici | Açıklama |
|---|---|---|
| **A — Waypoint Slayt** | `data/ip8_test/etiketler.json` varsa | WP01/WP02/WP03 referans–test çiftleri; İP8 (SSIM+ORB) pipeline |
| **B — Video Akışı** | `data/raw_videos/engel.mp4` varsa | MOG2 arka plan çıkarma ile canlı anomali tespiti |
| **C — Sentetik** | Her zaman | Veri yoksa otomatik fabrika sahnesi simülasyonu |

Mod seçimi **otomatiktir** (A → B → C önceliği).  
Elle seçmek için: `python scripts\demo_anomali.py --mod b`

---

## Ekran Düzeni

```
┌─────────────────────────────────────────────────────────┐
│  ▶ ANOMALİ TESPİT DEMO      >>> UYARI <<<      12:34:56 │  ← Başlık
├──────────────────────┬──────────────────────────────────┤
│   REFERANS           │   CANLI / TEST KARE              │
│   (Altın Tur)        │   [#1 tespit kutusu]  >>>UYARI<<<│
├──────────────────────┼──────────────────────────────────┤
│   FARK MASKESİ       │   MOG2 FG MASK                   │
│   (SSIM ikili harita)│   fg_ratio, nesne sayısı         │
├──────────────────────┴──────────────────────────────────┤
│   ▓▓▓▓░░░░░░▓▓▓▓▓▓▓▓▓▓▓░░    ← Anomali Skoru Grafiği   │
├─────────────────────────────────────────────────────────┤
│  MOG2: 2 nesne | Score: 0.72 | Kare: 145 | Uyarı: 3    │  ← Alt bilgi
└─────────────────────────────────────────────────────────┘
```

---

## Klavye Kısayolları

| Tuş | İşlev |
|---|---|
| `Q` / `ESC` | Demoyu kapat |
| `SPACE` | Duraklat / Devam |
| `N` | Sonraki waypoint (Mod A) |
| `+` / `-` | Anomali eşiğini artır / azalt |
| `S` | Ekran görüntüsü kaydet |

Ekran görüntüleri: `outputs/demo_ciktilari/`

---

## Teknik Altyapı

Bu demo **ip8_degisiklik_tespiti.py** ve **ip9_ensemble_analiz.py** dosyalarını
değiştirmez. Reşit Asrav'ın `demo/uyusmazliklar/RAPOR.md §1`'de tanımlanan
mimari sorunu çözer:

> *"ANOMALİ modülü `f(kare)→sonuç` biçiminde fonksiyon sunmuyordu"*

Demo içindeki sınıflar:
- `AlgilayiciIP8` — SSIM + ORB hizalama + contour tespiti (İP8 mantığı)
- `AlgilayiciMOG2` — Arka plan çıkarma + fg filtresi (İP9 mantığı)

### Bağımlılıklar
```
opencv-python
numpy
scikit-image   (SSIM için)
```

---

## MQTT Entegrasyonu (İP10 — sonraki aşama)

Demo şu an terminale yazar. İP10'da `patrol/alert` topic'e bağlanacak:
```json
{
  "type"     : "patrol_alert",
  "severity" : "HIGH",
  "waypoint" : "WP01",
  "score"    : 0.84,
  "det_count": 2,
  "ts"       : "2026-08-17T12:34:56"
}
```
