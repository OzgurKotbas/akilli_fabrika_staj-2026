# Devriye Tur Raporu
**Olusturan:** Ozgur Kotbas - Anomali + Devriye Raporu Modulu  
**Tarih:** 2026-08-17  
**Tur No:** TUR-20260817-0244  
**Proje:** Gorsel Anomali Tespiti + Otomatik Devriye Raporu - Grup 03_Gama - BTU - 2026

---

## Ozet

| Metrik | Deger |
|--------|-------|
| Toplam Waypoint | 3 |
| Anomali Tespit Edilen | 3 |
| Normal | 0 |
| Uyari Orani | 100.0% |
| TP | 2 |
| FP | 1 |
| FN | 1 |
| Precision | 0.667 |
| Recall | 0.667 |
| **F1** | **0.667** |
| PatchCore Aktif | Evet (esik=0.40) |
| Ensemble Mimarisi | MOG2 + PatchCore |

> **3 waypoint'te anomali tespit edildi.** Asagidaki tespitler oncelik sirasina gore (HIGH > MEDIUM > LOW) listelenmistir.

---

## Uyarilar (Oncelik Sirasina Gore)

### WP01 - Yerde Birakilan Cisim

| Alan | Deger |
|------|-------|
| **Severity** | HIGH |
| **MOG2 Nesne** | 3 adet |
| **MOG2 FG Orani** | 0.0255 |
| **PatchCore Skoru** | 0.3803 |
| **Karar** | MOG2: 3 nesne |
| **TP/FP Degerlendirme** | TP=0 FP=1 IoU=0.094 |

**Test Goruntüsü:** `data/ip8_test/WP01_degisik.jpg`  
**Ensemble Analiz:** `data/ip9_ensemble/WP01_ensemble_analiz.png`  
![WP01 Ensemble Analiz](data/ip9_ensemble/WP01_ensemble_analiz.png)

### WP02 - Yol Engeli

| Alan | Deger |
|------|-------|
| **Severity** | HIGH |
| **MOG2 Nesne** | 4 adet |
| **MOG2 FG Orani** | 0.2112 |
| **PatchCore Skoru** | 0.3198 |
| **Karar** | MOG2: 4 nesne |
| **TP/FP Degerlendirme** | TP=1 FP=0 IoU=0.493 |

**Test Goruntüsü:** `data/ip8_test/WP02_degisik.jpg`  
**Ensemble Analiz:** `data/ip9_ensemble/WP02_ensemble_analiz.png`  
![WP02 Ensemble Analiz](data/ip9_ensemble/WP02_ensemble_analiz.png)

### WP03 - Kapi Anomalisi

| Alan | Deger |
|------|-------|
| **Severity** | HIGH |
| **MOG2 Nesne** | 2 adet |
| **MOG2 FG Orani** | 0.1636 |
| **PatchCore Skoru** | 0.5150 |
| **Karar** | MOG2: 2 nesne + PatchCore: 0.515 > 0.4 |
| **TP/FP Degerlendirme** | TP=1 FP=0 IoU=0.692 |

**Test Goruntüsü:** `data/ip8_test/WP03_degisik.jpg`  
**Ensemble Analiz:** `data/ip9_ensemble/WP03_ensemble_analiz.png`  
![WP03 Ensemble Analiz](data/ip9_ensemble/WP03_ensemble_analiz.png)

---

## Normal Waypointler

| Waypoint | Tip | MOG2 Nesne | PatchCore Skoru |
|----------|-----|-----------|----------------|

---

## Ensemble Mimarisi

```
KATMAN 1 - MOG2 Arka Plan Cikarma  (aci bagimsiz)
           history=200 kare, learningRate=0 (son 30 kare donduruldu)

KATMAN 2 - PatchCore Anomali Skoru (~40 derece toleransli)
           ResNet18[:-2] => spatial 7x7=49 patch
           Memory bank: 3 referans kare x 49 patch = 147 vektor
           Skor: max nearest-neighbor mesafesi (cosine)

KARAR KURALI:
  is_alert = (MOG2_nesne_sayisi > 0) OR (PatchCore_score > 0.40)
```

---

*Bu rapor ip11_rapor_uret.py tarafindan otomatik uretilmistir.*  
*Kaynak: `data/ip9_ensemble/ensemble_ozet.json`*