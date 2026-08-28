# -*- coding: utf-8 -*-
"""
analiz_cop_kutusu_fp.py  —  WP01 Yanlış Alarm (FP) Kök Neden Analizi
======================================================================
Soru: Çöp kutusu sahnedeyken MOG2 neden çöp kutusunun DIŞINDA
      üç ayrı nesne tespit ediyor ve IoU=0.094 veriyor?

Metod: Referans vs test kare farkını 6 ayrı boyutta ölçer,
       her boyut için kanıt görselini outputs/analiz_fp/ altına kaydeder.
"""

import sys, io
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8','utf-16'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import json
from pathlib import Path
import cv2
import numpy as np

# ── Yollar ─────────────────────────────────────────────────────────────
ROOT     = Path(__file__).resolve().parent.parent
REF_IMG  = ROOT / "data/waypoints/referans_kareler/WP01.jpg"
TEST_IMG = ROOT / "data/ip8_test/WP01_degisik.jpg"
GT_JSON  = ROOT / "data/ip8_test/etiketler.json"
OUT_DIR  = ROOT / "outputs/analiz_fp"
OUT_DIR.mkdir(parents=True, exist_ok=True)

ref  = cv2.imread(str(REF_IMG))
test = cv2.imread(str(TEST_IMG))
assert ref  is not None, f"Referans okunamadı: {REF_IMG}"
assert test is not None, f"Test okunamadı: {TEST_IMG}"

H, W = ref.shape[:2]
test = cv2.resize(test, (W, H))

with open(GT_JSON, encoding="utf-8") as f:
    gt_data = json.load(f)
gt = next(c for c in gt_data["test_ciftleri"] if c["waypoint_id"] == "WP01")["gt_bbox"]

def yazdir(baslik):
    print(f"\n{'='*60}")
    print(f"  {baslik}")
    print('='*60)

def kaydet(isim, img):
    p = OUT_DIR / isim
    cv2.imwrite(str(p), img)
    print(f"  → {p.name}")

# ══════════════════════════════════════════════════════════════════════
# 1. GÖRSEL FARK — Referans vs Test yan yana + fark kanalı
# ══════════════════════════════════════════════════════════════════════
yazdir("1. Referans vs Test — Görsel Fark")

diff_abs = cv2.absdiff(ref, test)
diff_gray = cv2.cvtColor(diff_abs, cv2.COLOR_BGR2GRAY)
print(f"  Tüm piksel fark ortalaması : {diff_gray.mean():.2f}")
print(f"  Tüm piksel fark std dev    : {diff_gray.std():.2f}")
print(f"  Maks fark pikseli          : {diff_gray.max()}")

# GT kutu bölgesindeki fark
gx,gy,gw,gh = gt["x"],gt["y"],gt["w"],gt["h"]
roi_gt   = diff_gray[gy:gy+gh, gx:gx+gw]
roi_disi = diff_gray.copy()
roi_disi[gy:gy+gh, gx:gx+gw] = 0   # GT dışı
print(f"\n  GT kutusu (çöp kutusu bölgesi) fark ort : {roi_gt.mean():.2f}")
print(f"  GT DIŞI fark ortalaması                  : {roi_disi[roi_disi>0].mean():.2f} (sadece >0 pikseller)")

side = np.hstack([ref, test, cv2.cvtColor(diff_gray, cv2.COLOR_GRAY2BGR) * 3])
cv2.rectangle(side, (gx, gy), (gx+gw, gy+gh), (0,255,0), 2)
cv2.rectangle(side, (W+gx, gy), (W+gx+gw, gy+gh), (0,255,0), 2)
cv2.putText(side, "REF", (10,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,200,255), 2)
cv2.putText(side, "TEST (cop+sise)", (W+10,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,200,255), 2)
cv2.putText(side, "FARK x3", (2*W+10,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,200,255), 2)
kaydet("1_ref_test_fark.png", side)

# ══════════════════════════════════════════════════════════════════════
# 2. IŞIK DEĞİŞİKLİĞİ — Parlaklık haritası
# ══════════════════════════════════════════════════════════════════════
yazdir("2. Işık Değişikliği Analizi")

ref_gray  = cv2.cvtColor(ref,  cv2.COLOR_BGR2GRAY)
test_gray = cv2.cvtColor(test, cv2.COLOR_BGR2GRAY)
bright_diff = test_gray.astype(np.int16) - ref_gray.astype(np.int16)

print(f"  Test - Ref parlaklık farkı ort : {bright_diff.mean():.2f}  (+ = test daha parlak)")
print(f"  Std dev                        : {bright_diff.std():.2f}")

# Bölge bazlı parlaklık farkı
thirds = H // 3
for i, (y1,y2,etiket) in enumerate([(0,thirds,"ÜST (tavan)"),
                                      (thirds,2*thirds,"ORTA (duvarlar)"),
                                      (2*thirds,H,"ALT (zemin)")]):
    bölge = bright_diff[y1:y2,:]
    print(f"  {etiket:20s}: ort={bölge.mean():+.2f}  std={bölge.std():.2f}")

bright_vis = np.clip(bright_diff + 128, 0, 255).astype(np.uint8)
bright_colored = cv2.applyColorMap(bright_vis, cv2.COLORMAP_RdYlGn if hasattr(cv2,'COLORMAP_RdYlGn') else cv2.COLORMAP_JET)
cv2.putText(bright_colored, "Mavi=Test daha karanlik  Sari=daha parlak", (5,25),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255,255,255), 1)
kaydet("2_isik_degisimi.png", bright_colored)

# ══════════════════════════════════════════════════════════════════════
# 3. MOG2 SOĞUK BAŞLAÇ (Cold Start) SİMÜLASYONU
# ══════════════════════════════════════════════════════════════════════
yazdir("3. MOG2 Cold-Start — Tek Görüntü Çifti Sorunu")

print("  MOG2 ensemble scripti SADECE 2 kare görüyor:")
print("  Kare-1: referans.jpg (arka plan olarak öğrenilir)")
print("  Kare-2: test.jpg    (her şey 'ön plan' sayılır)")
print()
print("  Sonuç: MOG2 200 karelik history DOLMADAN (history=200)")
print("  arka planı tam öğrenemez. İki kare yeterli değil.")
print("  Bu yüzden çöp kutusu + tavan + duvar değişimleri hep ön plan.")

# MOG2 tek kare simülasyonu
mog2_tek = cv2.createBackgroundSubtractorMOG2(history=200, varThreshold=20, detectShadows=True)
fg_tek_1 = mog2_tek.apply(ref)   # Kare-1: arka plan
fg_tek_2 = mog2_tek.apply(test)  # Kare-2: ön plan maskelenir

fg_tek_2[fg_tek_2 == 127] = 0
fg_clean = cv2.morphologyEx(fg_tek_2, cv2.MORPH_OPEN,  cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(5,5)))
fg_clean = cv2.morphologyEx(fg_clean, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(9,9)))

# GT kutusu içinde ne kadar FG var?
fg_in_gt  = fg_clean[gy:gy+gh, gx:gx+gw]
fg_out_gt = fg_clean.copy(); fg_out_gt[gy:gy+gh, gx:gx+gw] = 0

pct_in  = 100 * np.sum(fg_in_gt  > 0) / max(gw*gh, 1)
pct_out = 100 * np.sum(fg_out_gt > 0) / max((H*W - gw*gh), 1)
print(f"\n  GT kutusu içi FG oranı  : %{pct_in:.1f}")
print(f"  GT kutusu DIŞI FG oranı : %{pct_out:.1f}")
print(f"  → Gürültü (FG dışı/içi) oranı: {pct_out/max(pct_in,0.01):.2f}x")

fg_vis = cv2.cvtColor(fg_clean, cv2.COLOR_GRAY2BGR)
cv2.rectangle(fg_vis, (gx,gy),(gx+gw,gy+gh), (0,255,0), 2)
cv2.putText(fg_vis,"GT kutusu",(gx,max(gy-5,12)),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,255,0),1)
kaydet("3_mog2_cold_start_fg.png", fg_vis)

# ══════════════════════════════════════════════════════════════════════
# 4. SARI MASKE ETKİSİ — Sarı yüzey bastırma analizi
# ══════════════════════════════════════════════════════════════════════
yazdir("4. Sarı Zemin Çizgisi Maskesi Analizi")

hsv  = cv2.cvtColor(test, cv2.COLOR_BGR2HSV)
ym   = cv2.inRange(hsv, np.array([18,80,80]), np.array([38,255,255]))
k    = cv2.getStructuringElement(cv2.MORPH_RECT,(15,15))
ym_d = cv2.dilate(ym, k, iterations=1)

print(f"  Sarı piksel oranı (test) : %{100*np.sum(ym>0)/ym.size:.2f}")
print(f"  Sarı+dilate oranı        : %{100*np.sum(ym_d>0)/ym_d.size:.2f}")

# Çöp kutusu rengi analizi
cop_roi_hsv = hsv[gy:gy+gh, gx:gx+gw]
cop_ym      = ym[gy:gy+gh, gx:gx+gw]
print(f"\n  Çöp kutusu bölgesinde sarı piksel: %{100*np.sum(cop_ym>0)/max(gw*gh,1):.1f}")
print(f"  (Çöp kutusu MAVI — sarı maskeden kaçmaz, bu doğru)")

# Çöp kutusunun gerçek renk dağılımı
cop_roi_bgr = test[gy:gy+gh, gx:gx+gw]
mean_bgr = cop_roi_bgr.reshape(-1,3).mean(axis=0)
print(f"  Çöp kutusu ortalama BGR  : B={mean_bgr[0]:.0f} G={mean_bgr[1]:.0f} R={mean_bgr[2]:.0f}")
print(f"  → Mavi tonlarda ({mean_bgr[0]:.0f}B > {mean_bgr[2]:.0f}R) — sarı bastırma etkisiz, doğru")

ym_vis = test.copy()
ym_vis[ym_d > 0] = (ym_vis[ym_d > 0].astype(int) // 2 + np.array([0,100,100])//2).clip(0,255).astype(np.uint8)
cv2.rectangle(ym_vis, (gx,gy),(gx+gw,gy+gh),(0,255,0),2)
cv2.putText(ym_vis,"GT kutu",(gx,max(gy-5,12)),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,255,0),1)
kaydet("4_sari_maske.png", ym_vis)

# ══════════════════════════════════════════════════════════════════════
# 5. TAVAN / YÜKSEK BÖLGE GÜRÜLTÜSÜ ANALİZİ
# ══════════════════════════════════════════════════════════════════════
yazdir("5. Tavan / Üst Bölge Gürültüsü — FP Nesnelerin Konumu")

# MOG2 tespit edilen 3 nesnenin konumu (ensemble_ozet.json'dan)
mog2_nesneler = [
    {"x":282,"y":0,  "w":104,"h":114,"etiket":"Nesne-1 (tavan sol)"},
    {"x":209,"y":275,"w":49, "h":118,"etiket":"Nesne-2 (orta sol)"},
    {"x":117,"y":110,"w":41, "h":107,"etiket":"Nesne-3 (sol duvar)"},
]

print("  MOG2 tespit edilen 3 nesnenin konumları:")
for n in mog2_nesneler:
    cy_n = n["y"] + n["h"]//2
    bölge = "TAVAN" if cy_n < H//4 else ("ÜST" if cy_n < H//2 else "ALT")
    print(f"    {n['etiket']:25s}: y={n['y']:3d}, cy={cy_n:3d}, bölge={bölge}")
    in_gt = (n["x"] < gx+gw and n["x"]+n["w"] > gx and
             n["y"] < gy+gh and n["y"]+n["h"] > gy)
    print(f"      GT kutusunla örtüşüyor mu? {'EVET' if in_gt else 'HAYIR — YANLIH ALARM'}")

# Işıktaki değişiklik tavan bölgesinde ne kadar?
tavan_diff = diff_gray[0:H//4, :]
print(f"\n  Tavan bölgesi (üst 1/4) fark ort : {tavan_diff.mean():.2f}")
print(f"  Zemin bölgesi (alt 1/2) fark ort  : {diff_gray[H//2:,:].mean():.2f}")
print(f"  → Tavan farkı zeminden {tavan_diff.mean()/max(diff_gray[H//2:,:].mean(),0.01):.1f}x büyük")
print(f"  KÖK NEDEN 1: Farklı çekim açısı → tavan dokusu kaymış (tavan lambası, siyah panel)")

# Görsel: FP nesne kutularını test üzerinde göster
fp_vis = test.copy()
cv2.rectangle(fp_vis, (gx,gy),(gx+gw,gy+gh),(0,255,0),3)
cv2.putText(fp_vis,"GT (cop kutusu+sise)",(gx,max(gy-8,14)),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,255,0),1)
for i,n in enumerate(mog2_nesneler):
    renk = (0,0,220)
    cv2.rectangle(fp_vis,(n["x"],n["y"]),(n["x"]+n["w"],n["y"]+n["h"]),renk,2)
    cv2.putText(fp_vis,f"FP#{i+1}",(n["x"],max(n["y"]-4,12)),cv2.FONT_HERSHEY_SIMPLEX,0.45,renk,1)
kaydet("5_fp_nesne_konumlari.png", fp_vis)

# ══════════════════════════════════════════════════════════════════════
# 6. ÇEKİM AÇISI KAYMA ANALİZİ — ORB ile homografi
# ══════════════════════════════════════════════════════════════════════
yazdir("6. Kamera Açı Kayması — ORB Homografi")

orb    = cv2.ORB_create(nfeatures=1000)
kp1,d1 = orb.detectAndCompute(ref_gray, None)
kp2,d2 = orb.detectAndCompute(test_gray, None)

if d1 is not None and d2 is not None and len(kp1)>10 and len(kp2)>10:
    bf   = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    raw  = bf.knnMatch(d1, d2, k=2)
    good = [m for m,n in raw if m.distance < 0.75*n.distance]
    print(f"  Toplam iyi eşleşme: {len(good)}")
    if len(good) >= 10:
        src = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1,1,2)
        dst = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1,1,2)
        M, inliers = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
        if M is not None:
            # Köşe noktaları ne kadar kaymış?
            corners = np.float32([[0,0],[W,0],[W,H],[0,H]]).reshape(-1,1,2)
            warped  = cv2.perspectiveTransform(corners, M).reshape(-1,2)
            orig    = corners.reshape(-1,2)
            sapmalar = np.linalg.norm(warped - orig, axis=1)
            print(f"  Köşe sapma (px): {sapmalar.round(1).tolist()}")
            print(f"  Ortalama köşe sapması: {sapmalar.mean():.1f} px")
            if sapmalar.mean() > 8:
                print(f"  ⚠️  >8px sapma — kamera açısı/pozisyon değişimi BÜYÜK")
                print(f"  KÖK NEDEN 2: Çekim açısı kayması tavan/duvar dokusunu farklı gösteriyor")
            else:
                print(f"  ✅ <8px sapma — çekim açısı kayması küçük, asıl sorun başka")

            # ORB eşleşmelerini çiz
            match_vis = cv2.drawMatches(ref, kp1, test, kp2,
                                         good[:40], None,
                                         flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
            kaydet("6_orb_eslesme.png", match_vis)
        else:
            print("  Homografi hesaplanamadı — eşleşmeler yetersiz")
    else:
        print(f"  Yetersiz eşleşme ({len(good)})")
else:
    print("  ORB özellik çıkarımı başarısız")

# ══════════════════════════════════════════════════════════════════════
# 7. ÖZET RAPOR
# ══════════════════════════════════════════════════════════════════════
yazdir("ÖZET — WP01 FP Kök Neden Analizi")

print("""
  SENARYO: S1 — Su şişesi + çöp kovası bırakıldı (yerde_birakilan_cisim)
  GT kutu : x=190, y=196, w=204, h=301 (nesne bölgesi, görüntü alt kısmı)
  MOG2 kararı: 3 FP nesne (tavan + sol duvar), IoU=0.094

  ──────────────────────────────────────────────────────────
  KÖK NEDEN 1 — MOG2 SOĞUK BAŞLAÇ (PRIMARY, ağırlık: YÜKSEK)
  ──────────────────────────────────────────────────────────
  MOG2 history=200 kare bekliyor. Ensemble scripti 2 kare veriyor:
    - Kare 1 (ref.jpg):  arka plan modeli başlatılıyor
    - Kare 2 (test.jpg): arka plan HENÜZ ÖĞRENİLMEDEN çalıştırılıyor
  → İlk karede tavan/duvar "henüz öğrenilmemiş" sayılıyor
  → Çok küçük parlaklık değişimleri bile ön plan olarak işaretleniyor
  → Nesne-1 (y=0-114): TAVAN bölgesi — zemin değişimi değil ışık/açı gürültüsü

  ──────────────────────────────────────────────────────────
  KÖK NEDEN 2 — KAMERA AÇISI/YÜKSEKLIK FARKI (ağırlık: ORTA)
  ──────────────────────────────────────────────────────────
  Referans kare: daha yüksek/dik çekilmiş (tavan siyah panel geniş görünüyor)
  Test kare   : biraz farklı açıdan/yükseklikten çekilmiş
  → Tavan lambası, siyah tavan paneli konumu kaymış
  → ORB eşleşmeleri yüksek köşe sapmasını ölçüyor
  → Nesne-3 (x=117, y=110): sol duvar bölgesi — ORB hizalamadan kaçmış gürültü

  ──────────────────────────────────────────────────────────
  KÖK NEDEN 3 — MİN ALAN EŞİĞİ ÇOĞU FP İÇİN YETERSİZ (ağırlık: ORTA)
  ──────────────────────────────────────────────────────────
  mog2_min_area = 1500 px²  (config'den)
  FP Nesne-2: 5782 px²  (1500'ün 3.8x üstünde — eşikten geçiyor)
  FP Nesne-3: 4387 px²  (1500'ün 2.9x üstünde — eşikten geçiyor)
  FP Nesne-1: 11856 px² (yüksek — tavan lambası/panel kayması büyük)
  → Eşik artırılsa da bu FP'leri durdurmaz (5782 >> 1500)

  ──────────────────────────────────────────────────────────
  KÖK NEDEN 4 — FLOOR_CROP EKSİK (ağırlık: DÜŞÜK-ORTA)
  ──────────────────────────────────────────────────────────
  Demo_anomali.py'de SSIM detektöründe floor_crop=0.20 var (üst %20 yoksay)
  Ama MOG2 (_AlgilayiciMOG2) bu floor_crop'u UYGULAMIYOR
  → y=0-114 tavan bölgesi FP'si bu yüzden MOG2'de kalıyor

  ──────────────────────────────────────────────────────────
  DÜZELTME ÖNERİLERİ (öncelik sırası)
  ──────────────────────────────────────────────────────────
  Ö1 [en etkili]: MOG2'ye warm-up kareleri ver — referans görüntüyü
     N=30-50 kare besle (learningRate=1.0), sonra test karesini uygula.
     İP12 notunda da aynı çözüm: "son 30 kare learningRate=0"

  Ö2 [orta etki]: ROI crop — tavan bölgesini (üst %15-20) MOG2'den hariç tut
     IP8'deki floor_crop mantığını MOG2 sarmalayıcısına taşı
     fg[0:int(H*0.15), :] = 0  →  tavan lambası gürültüsü kesilir

  Ö3 [kolay]: min_area'yı 1500→3000 px² yükselt (FP-2/3 için kısmen etkili,
     FP-1 (11856) durdurmaz — tek başına yetersiz)

  Ö4 [uzun vadeli]: PatchCore spatial embedding (İP12'de uygulandı)
     PatchCore=0.38 < eşik=0.40 — çok yakın, eşik 0.38'e düşürülse WP01'de
     ek kanıt olurdu. Ama asıl sorun MOG2 cold-start, PatchCore şu an
     yedek rol oynuyor.
""")

print(f"\n✅ Analiz görselleri: {OUT_DIR}")
print(f"   Toplam çıktı: {len(list(OUT_DIR.glob('*.png')))} dosya")
