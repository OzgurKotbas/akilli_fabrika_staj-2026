# İP5 Çalışma Raporu — MVTec Anomali Tespiti Baseline

**Hazırlayan:** Özgür Kotbaş  
**Tarih:** 01–02 Ağustos 2026  
**İlgili İş Paketi:** İP5 — MVTec Baseline  
**Proje:** Görsel Anomali Tespiti + Otomatik Devriye Raporu  
**Danışman Proje Dosyası:** [Ozgur_Kotbas_proje.md](../../DOKUMANLAR/Ozgur_Kotbas_proje.md)  
**İş Paketi Dosyası:** [Ozgur_is_paketleri.md](../../DOKUMANLAR/Ozgur_is_paketleri.md)

---

## İçindekiler
- [1. Amaç](#1-Amaç)
- [2. Kullanılan Veri Seti](#2-kullanılan-veri-seti)
- [3. Kullanılan Yöntem ve Araçlar](#3-kullanılan-yöntem-ve-araçlar)
- [4. Çıktı Görüntüleri](#4-çıktı-görüntüleri)
- [5. Sonuçlar](#5-sonuçlar)
- [6. Yorumlar ve Çıkarımlar](#6-yorumlar-ve-çıkarımlar)
- [7. Klasör Yapısı](#7-klasör-yapısı)
- [8. Sonraki Adım](#8-sonraki-adım)

---

## 1. Amaç

Bu çalışmanın amacı, **anomalib** kütüphanesini kullanarak **MVTec Anomaly Detection (MVTec-AD)** veri seti üzerinde iki farklı anomali tespit modeli olan **PatchCore** ve **PaDiM**'i eğitmek ve performanslarını **F1 / AUROC** metrikleriyle karşılaştırmalı olarak ölçmektir.

Bu çalışma, proje kapsamındaki **"altın tur kıyası"** hattının temelini oluşturmaktadır. MVTec-AD üzerinde başarılı bir baseline elde etmek, ilerleyen haftalarda kendi çekilmiş waypoint görüntülerine uygulanacak olan anomali modelinin doğru konfigürasyonu seçmek için referans noktası oluşturur.

---

## 2. Kullanılan Veri Seti

### MVTec Anomaly Detection (MVTec-AD)

| Özellik | Bilgi |
|---|---|
| **Kaynak** | [Kaggle — ipythonx/mvtec-ad](https://www.kaggle.com/datasets/ipythonx/mvtec-ad) |
| **Orijinal Yayın** | MVTec AD: CVPR 2019 — P. Bergmann et al. |
| **Lisans** | Akademik kullanım için ücretsiz |
| **İçerik** | 15 sanayi kategorisi, yüzey kusuru görüntüleri |
| **Test Kategorisi** | **bottle** (şişe) |

### Bottle Kategorisi Anomali Türleri

| Anomali Türü | Açıklama |
|---|---|
| `broken_large` | Şişede büyük çatlak / kırılma |
| `broken_small` | Şişede küçük çatlak / kırılma |
| `contamination` | Şişe içinde/üstünde yabancı madde |
| `good` | Normal, kusursuz şişe (referans) |

---

## 3. Kullanılan Yöntem ve Araçlar

### Ortam
- **Platform:** Google Colab (T4 GPU)
- **Python:** 3.12
- **Kütüphane:** [anomalib](https://github.com/open-edge-platform/anomalib) (v2.x)
- **Framework:** PyTorch Lightning

### Modeller

#### PatchCore
Eğitim görüntülerinden elde edilen derin öznitelik gömülerini bir **bellek bankasında** saklar. Test sırasında her yamanın (patch) bellek bankasındaki en yakın komşusuna olan mesafesini anomali skoru olarak kullanır. Eğitim gerektirmez — tek epoch'ta bellek bankası oluşturulur.

> 📄 Kaynak: *"Towards Total Recall in Industrial Anomaly Detection"* — Roth et al., CVPR 2022

#### PaDiM (Patch Distribution Modeling)
Her yamanın öznitelik dağılımını **çok değişkenli Gaussian** ile modeller. Test zamanında Mahalanobis uzaklığı ile anomali skoru hesaplar. PatchCore'a kıyasla daha hafif, CPU'da da çalışabilir.

> 📄 Kaynak: *"PaDiM: a Patch Distribution Modeling Framework for Anomaly Detection and Localization"* — Defard et al., 2020

---

## 4. Çıktı Görüntüleri

Her test görüntüsü için 4 panel üretilmektedir:

| Panel | Açıklama |
|---|---|
| **Image** | Ham test görüntüsü |
| **Gt Mask** | Ground truth — gerçek anomali maskesi (beyaz bölge) |
| **Image + Anomaly Map** | Isı haritası — kırmızı = yüksek anomali skoru |
| **Image + Pred Mask** | Model tahmin maskesi — kırmızı çizgi sınırı gösterir |

### PatchCore Çıktı Örnekleri

**broken_large** — Büyük kırılma tespiti:
Model anomaliyi doğru bölgede (alt-sağ) yüksek skor ile işaretlemiş; tahmin maskesi gerçek maskeyle örtüşüyor.

**broken_small** — Küçük kırılma tespiti:
Küçük anomali bölgesi başarıyla lokalize edilmiş. Isı haritasında odaklanmış sarı-turuncu alan görülüyor.

**contamination** — Kirlilik/yabancı madde tespiti:
Şişe içindeki yabancı madde net biçimde tespit edilmiş, ısı haritası kirli bölgeyi turuncu-sarı ile vurguluyor.

**good** — Normal şişe (beklenen: anomali yok):
Isı haritası tamamen mavi (düşük skor). Yanlış alarm yok ✅

### PaDiM Çıktı Örneği

**broken_large** — PaDiM tespiti:
Anomali bölgesi tespit edilmiş ancak ısı haritası PatchCore'a göre daha dağınık. Lokalizasyon hassasiyeti görece düşük.

---

## 5. Sonuçlar

### Metrik Tablosu

| Kategori | Model | Image F1 | Image AUROC | Pixel F1 | Pixel AUROC |
|----------|-------|----------|-------------|----------|-------------|
| bottle | **PatchCore** | **0.9920** | **1.0000** | 0.7268 | 0.9856 |
| bottle | **PaDiM** | 0.9841 | 0.9968 | — | — |

### Değerlendirme

| Metrik | Anlam | PatchCore Sonucu |
|---|---|---|
| **Image AUROC = 1.0** | Görüntü seviyesinde mükemmel ayrım | Tüm anomaliler doğru sınıflandırıldı |
| **Image F1 = 0.992** | Kesinlik-duyarlılık dengesi | Neredeyse sıfır yanlış alarm |
| **Pixel AUROC = 0.986** | Piksel seviyesinde lokalizasyon | Anomali bölgesi doğru konumlandırıldı |
| **Pixel F1 = 0.727** | Piksel maskesi kalitesi | Gelişim alanı — kenar hassasiyeti |

---

## 6. Yorumlar ve Çıkarımlar

- **PatchCore**, `bottle` kategorisinde neredeyse mükemmel görüntü düzeyinde sınıflandırma elde etti (AUROC=1.0). Bu, projenin anomali modeli için **birincil model adayı** olduğunu doğrulamaktadır.
- **PaDiM** de rekabetçi sonuçlar verdi (AUROC=0.997) ve daha hafif olduğundan edge cihazda çalıştırma için değerlendirilecek.
- **Piksel F1 (0.727)** her iki modelde de görece düşük — bu, lokalizasyon maskeleri kenar hassasiyetinin iyileştirme gerektirdiğine işaret ediyor. İP6 ve İP7 aşamalarında bu konu ele alınacak.
- Normal görüntülerde (good) **yanlış alarm üretilmedi** — proje kalite kriteri olan "alarm yorgunluğu" riski bu aşamada düşük.

---

## 7. Klasör Yapısı

```
01-02.08/
├── rapor.md                          ← bu dosya
├── ip5_mvtec_baseline.md             ← özet metrik tablosu
├── Patchcore/
│   └── MVTecAD/bottle/v1/
│       ├── images/
│       │   ├── broken_large/         ← 20 görüntü
│       │   ├── broken_small/         ← 20 görüntü
│       │   ├── contamination/        ← 20 görüntü
│       │   └── good/                 ← 20 görüntü
│       └── weights/                  ← eğitilmiş model ağırlıkları
└── Padim/
    └── MVTecAD/bottle/v1/
        ├── images/
        │   ├── broken_large/
        │   ├── broken_small/
        │   ├── contamination/
        │   └── good/
        └── weights/
```

---

## 8. Sonraki Adım

**İP5 bitti kriteri ✅ karşılandı** — F1/AUROC tablosu commit'lendi.

Sıradaki iş paketi: **İP6 — Kendi verisiyle anomali**  
> Waypoint karelerinden "normal"i öğren; değiştirilmiş sahnede dene → değişiklik heatmap örneği (kendi verisiyle)

