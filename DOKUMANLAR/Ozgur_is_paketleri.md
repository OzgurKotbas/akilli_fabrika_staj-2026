# Anomali + Devriye Raporu — İş Paketleri (Özgür Kotbaş)

**Çatı proje:** [pan_tilt_robot_projesi.md](../../pan_tilt_robot_projesi.md) · **Proje dosyası:** [Ozgur_Kotbas_proje.md](Ozgur_Kotbas_proje.md) · **Tarih:** 27.07.2026

Proje 16 iş paketine bölünmüştür (İP15 = LingBot-Map stretch). Her iş paketi 0,5-2 günlüktür ve **ölçülebilir bir "bitti" kriteri** vardır. Günlük commit'lerde iş paketi numarasını yaz (örn. `İP7: waypoint kiyas hatti calisiyor`).

> **Altın kural:** Takıldığın iş paketi 1 günü aşarsa not düş, danışmana sor, mümkünse sonrakine geç (2 saat kuralı).

---

## H1 — Isınma + Referans Veri (27-31 Tem)

| # | İş paketi | Ne yapılır | ✅ Bitti kriteri |
|---|-------|-----------|------------------|
| İP1 | anomalib ilk çalıştırma | [anomalib](https://github.com/open-edge-platform/anomalib) kur; MVTec-AD'de hazır örnek (PaDiM, 1 kategori) | Anomali heatmap çıktısı alındı |
| İP2 | Senaryo listesi | Hangi anormallikler tespit edilecek: bırakılmış nesne, kapatılmış çıkış, sızıntı izi... (öncelik sıralı) | Senaryo dokümanı repoda |
| İP3 | **İlk altın tur kaydı** | Koridorda tripod + **waypoint listesi**: her durakta aynı açıdan referans kare | Referans video + waypoint kareleri repoda (veri linki) |
| İP4 | Mini literatür | ~10 makale (industrial anomaly detection, change detection) — [awesome-IAD](https://github.com/M-3LAB/awesome-industrial-anomaly-detection)'dan başla | Özet tablosu repoda |

## H2 — Anomali Baseline (3-7 Ağu)

| # | İş paketi | Ne yapılır | ✅ Bitti kriteri |
|---|-------|-----------|------------------|
| İP5 | MVTec baseline | PatchCore/PaDiM 2-3 kategoride eğit/değerlendir | **F1/AUROC tablosu** commit'li |
| İP6 | Kendi verisiyle anomali | Waypoint karelerinden "normal"i öğren; değiştirilmiş sahnede dene | Değişiklik heatmap örneği (kendi verisiyle) |

## H3 — Altın Tur Kıyas Hattı (10-14 Ağu)

| # | İş paketi | Ne yapılır | ✅ Bitti kriteri |
|---|-------|-----------|------------------|
| İP7 | Waypoint kıyası v0 | Referans vs güncel kare: ORB/homografi hizalama + fark analizi | Kontrollü senaryoda değişiklik maskesi çıkıyor |
| İP8 | Değişiklik enjekteli tur | İkinci tur kaydı: nesne bırak, kapı kapat, işaret değiştir | **Etiketli test çifti seti** (referans + değişmiş + ne değişti listesi) |
| İP9 | Karar birleşimi | Anomali skoru + fark maskesi → uyarı kararı + eşik | Senaryo setinde **TP/FP sayımı** raporlu |

## H4 — Uyarı + Rapor (17-21 Ağu)

| # | İş paketi | Ne yapılır | ✅ Bitti kriteri |
|---|-------|-----------|------------------|
| İP10 | MQTT yayını | `patrol/alert` mesajları (`type, severity, waypoint, img_ref, ts`) | Broker'da şema uyumlu mesajlar |
| İP11 | **Devriye raporu v1** | Jinja2 → MD: uyarılar + görüntü kanıtı + waypoint + şiddet sırası | Örnek tur raporu repoda |
| İP12 | Yanlış alarm ayarı | Işık/gölge değişimi testleri (klasik tuzaklar); eşik çalışması | **Alarm/tur** ölçümü — ayar öncesi/sonrası |

## H5 — Cila + Entegrasyon + Stretch (24-28 Ağu)

| # | İş paketi | Ne yapılır | ✅ Bitti kriteri |
|---|-------|-----------|------------------|
| İP13 | PDF rapor | MD → PDF; şiddet sıralı, kanıt görüntülü | PDF tur raporu üretiliyor |
| İP14 | 🎉 Canlı tur | Pan-tilt kamerayla canlı waypoint turu → uyarı → rapor | Uçtan uca canlı demo videosu |
| İP15 | 🚀 **Stretch: LingBot-Map** | Pretrained modelle rota 3D haritası; uyarıları haritaya konumla (çekirdek bitmediyse **atla**) | Harita görüntüsü raporda + dashboard aktarım denemesi |

## H6 — Kapanış (31 Ağu-4 Eyl)

| # | İş paketi | Ne yapılır | ✅ Bitti kriteri |
|---|-------|-----------|------------------|
| İP16 | Final ölçüm + teslim | F1/AUROC + alarm/tur final tablosu; demo; rapor | **4 Eyl ekip demosu hazır** |

---

## İlerleme Takibi
| İş paketi | Durum | Tarih | Not |
|:---:|:---:|---|-----|
| İP1 | ⬜ | | |
| İP2 | ✅ | 10.08.2026 | 7 senaryo öncelik sıralı: S1-S3 test edildi, S4-S7 ileriki aşama. docs/senaryolar.md oluşturuldu. |
| İP3 | ✅ | 10.08.2026 | altin_tur_v2.mp4 çekildi, PLY haritası Lingbot-Map (1034 frame limiti aşılarak) Kaggle'da üretildi, Drive'a yüklendi. |
| İP4 | ⬜ | | |
| İP5 | ⬜ | | |
| İP6 | ✅ | 08.08.2026 | Heatmap outputs/ip6_heatmap.png olarak alındı |
| İP7 | ✅ | 08.08.2026 | ORB ile hizalama yapıldı, maske outputs/ip7_degisiklik_maskesi.png olarak alındı |
| İP8 | ✅ | 10.08.2026 | engel.mp4 çekildi, otomatik çift eşleştirici yazıldı, maskeler çıkarıldı. |
| İP9 | ⬜ | | |
| İP10 | ⬜ | | |
| İP11 | ⬜ | | |
| İP12 | ⬜ | | |
| İP13 | ⬜ | | |
| İP14 | ⬜ | | |
| İP15 | ⬜ | | (stretch — atlanabilir) |
| İP16 | ⬜ | | |

> Tasarım notları: **İP3 ilk haftada** — referans veri her şeyin temeli, geç kalması tüm zinciri geciktirir. **İP12 (yanlış alarm) bu projenin kalite kapısıdır**: alarm yorgunluğu ürünü öldürür; "az ama isabetli uyarı" hedefi. Geride kalırsan İP13 ve İP15 kırpılabilir; **İP7-İP9 (kıyas hattı + karar) ve İP11 (rapor) feda edilemez** — devriye raporu modülün varlık sebebi.
