# Özgür Kotbaş — Staj Projesi

## Künye
| Alan | Bilgi |
|------|-------|
| Ad Soyad | Özgür Kotbaş |
| Grup | 03_Gama |
| Danışman | — |
| Üniversite | BTÜ |
| Sınıf | — |
| Başlangıç | **2026-07-27** (belge geldi ✅) |
| Staj süresi | 30 iş günü → tahmini bitiş 2026-09-04 |
| Çatı proje | [pan_tilt_robot_projesi.md](../../pan_tilt_robot_projesi.md) |
| İş paketleri | [Ozgur_is_paketleri.md](Ozgur_is_paketleri.md) — 16 iş paketi, ölçülebilir bitti kriterleriyle |

> 🔄 26.07 kararı: modül ataması güncellendi — anomali+rapor modülü (ANOMALİ) bu projeye verildi.

## Proje Tanımı
**Görsel Anomali Tespiti + Otomatik Devriye Raporu** — robotun "bir şeyler yolunda değil" deme yeteneği: normal durumu bilen sistem, devriye sırasında sapmaları yakalar ve tur sonunda kanıtlı rapor üretir.

**Amaç:** (1) "Altın tur" (normal durum referans kaydı) ile güncel devriye görüntüsünü kıyaslayarak **sahne değişikliği** tespiti — yerde bırakılmış nesne, kapatılmış acil çıkış, sızıntı/duman izi; (2) makine/yüzey seviyesinde **görsel anomali** modeli; (3) tur sonunda uyarıları toplayan **otomatik devriye raporu** (konum + görüntü kanıtı + önem derecesi).

**Kapsam:** Referans-kıyas hattı (görüntü hizalama + fark analizi), MVTec-AD tarzı anomali modeli (PatchCore/PaDiM gibi embedding tabanlı — az veriyle çalışır), rapor üretimi (Markdown/PDF; uyarı şiddeti sıralı). Yanlış alarm oranı ana kalite ölçütü — alarm yorgunluğu ürünü öldürür.

**Altın tur pratiği (robot beklenmez):** referans kayıt, koridorda tripod/elde çekilmiş **sabit rotalı video**dur. Kıyas **waypoint bazlı** yapılır: sürekli kare-kare hizalama yerine belirli duraklarda aynı açıdan kare alınıp karşılaştırılır — pan-tilt tekrarlanabilir açıya dönebildiği için bu, sistemin doğal avantajı. (Sürekli hizalama denemesi stretch; ana hat waypoint.)

**Kullanılacak teknolojiler:** Python, OpenCV (hizalama/fark), anomalib kütüphanesi (PatchCore/PaDiM/FastFlow), MQTT, rapor şablonu (Jinja2 → MD/PDF).

**Veri setleri:** MVTec-AD, VisA (anomali), kendi çekilmiş "altın tur" + değiştirilmiş sahne kayıtları (kontrollü senaryo: nesne bırak, kapı kapat, vb.).

## Hedefler
- [ ] Anomalib ile baseline anomali modeli — **F1/AUROC raporlu** (MVTec-AD)
- [ ] Altın-tur kıyas hattı: hizalama + değişiklik tespiti, kontrollü senaryolarda test
- [ ] **Yanlış alarm oranı ölçümü** (alarm/tur) + eşik ayar çalışması
- [ ] `patrol/alert` MQTT yayını + tur sonu otomatik rapor (MD/PDF, görüntü kanıtlı)
- [ ] Mini literatür (~10 makale: industrial anomaly detection, change detection)

## 🚀 Stretch Hedef — LingBot-Map ile 3D Altın Tur (çekirdek tamamsa, H4-5)
[LingBot-Map](https://github.com/robbyant/lingbot-map) — feed-forward 3D sahne haritalama; **pretrained çıkarım Colab T4'te çalışır** (bkz. [P14-P19](../../projeler.md) analizi):
- [ ] Devriye rotası kaydından pretrained modelle **3D harita** çıkar
- [ ] Uyarıları harita üzerine konumla — rapor "şu karede" değil **"fabrikanın şu noktasında"** der
- [ ] Rapora harita görünümü ekle; şirket içi 3D dashboard çalışmasına aktarım denemesi (danışman koordine eder)
- Vizyon (staj sonrası, rapora "gelecek iş" notu): iki tur arası 3D fark analizi

> Kural: çekirdek teslimat (2D altın-tur + anomalib + rapor) tamamlanmadan stretch'e geçilmez.

## Haftalık Plan
| Hafta | Tarih | İş |
|:---:|---|---|
| 1 | 27-31 Tem | Kurulum, MVTec-AD/anomalib tanışma, ~10 makale, senaryo listesi (hangi anormallikler?); **ilk altın tur kaydı** (koridor, tripod, waypoint listesiyle) |
| 2-3 | 3-14 Ağu | Colab: anomali baseline (F1/AUROC) + altın-tur fark hattı ilk sürüm |
| 4 | 17-21 Ağu | Pan-tilt kayıtlarıyla masa üstü test: kontrollü değişiklik senaryoları; rapor üretimi v1 |
| 5 | 24-28 Ağu | Saha-benzeri test; yanlış alarm ayarı (ışık, gölge — klasik tuzaklar); *(stretch: LingBot-Map 3D harita)* |
| 6 | 31 Ağu-4 Eyl | Ölçüm, uçtan uca demo (devriye → uyarı → rapor), final rapor |

## Başlangıç Kaynakları
**Çekirdek repolar:**
- [anomalib](https://github.com/open-edge-platform/anomalib) — PatchCore/PaDiM/FastFlow/EfficientAD tek kütüphanede, MVTec AD entegre; projenin bel kemiği (repo `open-edge-platform`'a taşındı — güncel link bu)
- [awesome-industrial-anomaly-detection](https://github.com/M-3LAB/awesome-industrial-anomaly-detection) — sürekli güncellenen makale+veri seti kütüphanesi; H1 literatür taraması buradan yürür
- [patchcore-inspection](https://github.com/amazon-science/patchcore-inspection) — PatchCore resmî kodu
- [LingBot-Map](https://github.com/robbyant/lingbot-map) — stretch hedef için (3D haritalama)

**Makaleler:** PatchCore — "Towards Total Recall..." (CVPR 2022) · PaDiM (2020) · **EfficientAD** (WACV 2024 — hızlı, edge'e uygun; robot senaryosu için önemli) · MVTec AD (CVPR 2019) · Sakurada SSCDNet — street-scene change detection ("altın tur" kıyasının akademik karşılığı)

**Veri setleri:** MVTec AD (mvtec.com, akademik ücretsiz) · VisA (`github.com/amazon-science/spot-diff`)

## GitHub & Takip
- [ ] Repo aç (öneri: `okotbas-patrol-anomaly-2026`) — **fabrika görüntüsü paylaşılmaz**, açık veri serbest
- [ ] Sık commit + `daily_log.md` · [Çalışma ilkeleri](../../calisma_ilkeleri.md)

## Haftalık İlerleme
| Hafta | Tarih | Yapılanlar | Durum | Notlar |
|-------|-------|------------|-------|--------|
| 1 | | | | |

## Notlar / Geri Bildirim
-
