# Gösterge Okuma — İş Paketleri (Reşit Asrav)

**Çatı proje:** [pan_tilt_robot_projesi.md](../../pan_tilt_robot_projesi.md) · **Proje dosyası:** [Resit_Asrav_proje.md](Resit_Asrav_proje.md) · **Tarih:** 27.07.2026

Proje 16 iş paketine bölünmüştür. Her iş paketi 0,5-2 günlüktür ve **ölçülebilir bir "bitti" kriteri** vardır. Günlük commit'lerde iş paketi numarasını yaz (örn. `İP6: Hough ibre okuma calisiyor`).

> **Altın kural:** Takıldığın iş paketi 1 günü aşarsa not düş, danışmana sor, mümkünse sonrakine geç (2 saat kuralı).

---

## H1 — Isınma + Envanter (27-31 Tem)

| # | İş paketi | Ne yapılır | ✅ Bitti kriteri |
|---|-------|-----------|------------------|
| İP1 | Veri taraması | Roboflow/Kaggle "gauge" setlerinden 2-3 tanesini indir, incele | Setler indirildi; kısa değerlendirme notu repoda |
| İP2 | **Gösterge envanteri** | Test göstergelerinin config'i: `gauge_id, tip, birim, min/max değer, açı aralığı` (YAML/JSON) | Config dosyası repoda — okuma zincirinin temeli |
| İP3 | Sentetik üreteci v0 | Programatik gösterge çizimi: bilinen açıda ibre → görüntü + **otomatik etiket** (açı = ground truth) | 100 sentetik gösterge + etiket üretildi |
| İP4 | Mini literatür | ~10 makale (automatic gauge reading, industrial OCR) | Özet tablosu repoda |

## H2 — Analog Okuma Zinciri (3-7 Ağu)

| # | İş paketi | Ne yapılır | ✅ Bitti kriteri |
|---|-------|-----------|------------------|
| İP5 | Gösterge tespiti | YOLO ile gauge yüzü tespiti (açık set + sentetik) | Test görüntülerinde kutu; tespit doğruluğu raporlu |
| İP6 | Klasik ibre okuma | Hough/çizgi uydurma ile ibre açısı (önce sentetik sette — ground truth bedava) | Sentetik sette **ortalama açı hatası** ölçülü |
| İP7 | Açı→değer kalibrasyonu | Config'teki min/max ile açıdan değere dönüşüm | Sentetik sette **okuma hatası %** raporu |

## H3 — Gerçek Görüntü + Yayın (10-14 Ağu)

| # | İş paketi | Ne yapılır | ✅ Bitti kriteri |
|---|-------|-----------|------------------|
| İP8 | Uçtan uca gerçek test | Tespit→kırp→açı→değer zinciri gerçek gauge fotoğraflarında | Gerçek sette okuma hatası tablosu (hedef: <%5'e yaklaş) |
| İP9 | CNN alternatifi | [GaugereaderProject](https://github.com/Guydada/GaugereaderProject) tarzı regresyon; klasikle kıyas | İki yöntem yan yana hata tablosu |
| İP10 | MQTT yayını | `inspect/reading` mesajları (`gauge_id, value, unit, conf`) | Broker'da şema uyumlu mesajlar akıyor |

## H4 — Dijital + Canlı (17-21 Ağu)

| # | İş paketi | Ne yapılır | ✅ Bitti kriteri |
|---|-------|-----------|------------------|
| İP11 | 7-segment/dijital OCR | PaddleOCR + Tesseract `letsgodigital` ile panel okuma | Dijital örneklerde karakter doğruluğu raporlu |
| İP12 | Lamba/vana durumu | Aç/kapalı + renk durumu sınıflandırma | Durum doğruluğu raporlu |
| İP13 | 🎉 Canlı masa üstü test | Duvara gösterge as / ekranda göster → pan-tilt kamerasıyla canlı oku | Canlı okuma videosu (değer ekranda güncelleniyor) |

## H5 — Dayanıklılık (24-28 Ağu)

| # | İş paketi | Ne yapılır | ✅ Bitti kriteri |
|---|-------|-----------|------------------|
| İP14 | Zor koşullar | Eğik açı, parlama/yansıma, düşük ışık — hata analizi | Koşul bazlı hata tablosu |
| İP15 | Güven eşiği + entegrasyon | Düşük conf'ta `unreadable` bayrağı ("yanlış okumaktansa okuyamadım de"); ekip demosu hazırlığı | Eşik davranışı testli; dashboard'da okumalar görünüyor |

## H6 — Kapanış (31 Ağu-4 Eyl)

| # | İş paketi | Ne yapılır | ✅ Bitti kriteri |
|---|-------|-----------|------------------|
| İP16 | Final ölçüm + teslim | Okuma hatası dağılımı, yöntem kıyası, demo, rapor | **4 Eyl ekip demosu hazır** |

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

> Tasarım notları: **Sentetik-önce stratejisi** (İP3→İP6→İP7) bilinçli — sentetik göstergede ground truth bedava, yöntem orada otururken gerçek veriye geçilir. **İP15'teki `unreadable` davranışı ürün kalitesidir**: endüstride yanlış okuma, okuyamamaktan çok daha tehlikelidir. Geride kalırsan İP9 (alternatif yöntem) ve İP12 kırpılabilir; **İP7-İP8 (kalibrasyonlu okuma zinciri) feda edilemez**.
