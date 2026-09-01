# -*- coding: utf-8 -*-
"""
İP8: Değişiklik Enjekteli Tur — Gelişmiş Değişiklik Tespiti
============================================================
Bitti kriteri: data/ip8_test/ klasöründe etiketli test çifti seti commit'li

Çözülen sorunlar (v2):
  1. Sarı zemin çizgileri FP olarak tespit ediliyordu
     → HSV renk maskesiyle sarı bölgeler hizalama ve diff aşamasından çıkarıldı
  2. Tek karede birden fazla nesne (su şişesi + çöp kovası) ayrı tespit edilemiyordu
     → Her contour ayrı bounding box olarak raporlanıyor
  3. Işık/kontrast farkı FP'ye yol açıyordu
     → Gaussian blur + CLAHE normalize + Otsu eşiği

Kullanım:
    cd D:/STAJ/akilli_fabrika_staj-2026
    python scripts/ip8_degisiklik_tespiti.py

Seçenekler:
    --ref    : referans kare yolu (varsayılan: data/waypoints/referans_kareler/WP01.jpg)
    --test   : test kare yolu   (varsayılan: data/waypoints/abnormal/WP01_degisik.jpg)
    --wp     : waypoint ID      (varsayılan: WP01)
    --batch  : tüm WP'leri işle (data/ip8_test/etiketler.json'u okur)
    --tune   : sarı maske HSV sınırlarını görmek için görsel debug modu
"""

import cv2
import numpy as np
import json
import argparse
from datetime import datetime
from pathlib import Path
from skimage.metrics import structural_similarity as ssim

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from scripts.core import config_okuyucu
from scripts.core.kaynak_adaptoru import KaynakAdaptoru

# ─── Proje Ayarları ───────────────────────────────────────────────────────────
PROJECT_DIR  = config_okuyucu.PROJECT_ROOT
CONFIG       = config_okuyucu.CONFIG

OUT_DIR      = PROJECT_DIR / "data" / "ip8_test"
RESULTS_PATH = OUT_DIR / "sonuclar.json"

# ─── Algılama Parametreleri ────────────────────────────────────────────────────
_vis_conf = CONFIG.get("vision", {})

DIFF_THRESHOLD  = 40
MIN_AREA        = _vis_conf.get("min_area", 1000)
MORPH_KERNEL    = 9
BLUR_KERNEL     = 7
CLAHE_CLIP      = 2.0

YELLOW_HSV_LOWER = np.array(_vis_conf.get("yellow_hsv_lower", [18, 80, 80]))
YELLOW_HSV_UPPER = np.array(_vis_conf.get("yellow_hsv_upper", [38, 255, 255]))
YELLOW_DILATE_PX = _vis_conf.get("yellow_dilate_px", 12)

# ─── Senaryo → Severity eşlemesi ──────────────────────────────────────────────
SEVERITY_MAP = {
    "yerde_birakilan_cisim": "HIGH",
    "yol_engeli":            "HIGH",
    "kapi_anomalisi":        "HIGH",
    "levha_degisikligi":     "MEDIUM",
    "kablo_karmasa":         "LOW",

}

# Zemin + Kapi ROI: Resmin en ust bolgesi (tavan vs) parallax'a ugrar.
# %20 yeterli: hem zemin nesnelerini hem de koridor sonundaki kapilari yakalar.
# NOT: Eski deger 0.4 idi — bu kapi anomalilerini tamamen kaciryordu!
FLOOR_ROI_TOP_CROP = 0.20
# ──────────────────────────────────────────────────────────────────────────────


def build_yellow_mask(img_bgr: np.ndarray) -> np.ndarray:
    """
    Sarı zemin çizgilerinin bulunduğu pikselleri döndürür (0=sarı değil, 255=sarı).
    ORB hizalamasında ve diff hesaplamasında bu bölgeler maskelenir.
    """
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, YELLOW_HSV_LOWER, YELLOW_HSV_UPPER)

    # Çizgi kenarlarını biraz genişlet — hizalama kayması marjı için
    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (YELLOW_DILATE_PX, YELLOW_DILATE_PX)
    )
    mask_dilated = cv2.dilate(mask, kernel, iterations=1)
    return mask_dilated   # 255 → sarı bölge (görmezden gelinecek)


def normalize_illumination(gray: np.ndarray) -> np.ndarray:
    """CLAHE ile aydınlatma farklarını normalize et."""
    clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP, tileGridSize=(8, 8))
    return clahe.apply(gray)


def orb_align(ref_bgr: np.ndarray, test_bgr: np.ndarray,
              yellow_mask_ref: np.ndarray) -> tuple[np.ndarray, bool]:
    """
    ORB özellik eşleştirme + Homografi ile test görüntüsünü
    referans görüntüsüne hizala.

    yellow_mask_ref  : referanstaki sarı bölgeler — ORB bu bölgelerde
                       özellik aramaz (tekrarlı desen = yanlış eşleşme)
    Döndürür: (aligned_gray, başarılı_mı)
    """
    ref_gray  = cv2.cvtColor(ref_bgr, cv2.COLOR_BGR2GRAY)
    test_gray = cv2.cvtColor(test_bgr, cv2.COLOR_BGR2GRAY)
    h, w = ref_gray.shape

    # Sarı maskenin tersini ORB'a ver: 0=görmezden gel, 255=tara
    orb_roi = cv2.bitwise_not(yellow_mask_ref)

    # nfeatures arttirildi: daha fazla aday nokta → daha iyi esleme sansı
    # fastThreshold dusuruldu: daha az tekrarlı bolgede bile keypoint bulur
    orb = cv2.ORB_create(nfeatures=2000, fastThreshold=5, scaleFactor=1.2, nlevels=10)
    kp1, des1 = orb.detectAndCompute(ref_gray,  mask=orb_roi)
    kp2, des2 = orb.detectAndCompute(test_gray, mask=None)   # test'i tam tara

    if des1 is None or des2 is None or len(kp1) < 10 or len(kp2) < 10:
        print("  [!] Yeterli keypoint bulunamadi -- hizalama atlaniyor")
        h, w = ref_gray.shape
        return cv2.resize(test_gray, (w, h)), False

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    raw_matches = bf.knnMatch(des1, des2, k=2)

    # Lowe ratio test — 0.80'e yumuşatıldı: az texturlu koridorlarda daha fazla eşleşme
    good = [m for m, n in raw_matches if m.distance < 0.80 * n.distance]
    print(f"  [ORB] iyi esleme: {len(good)}/{len(raw_matches)}")

    if len(good) < 10:
        print("  [!] Esleme yetersiz -- hizalama atlaniyor")
        h, w = ref_gray.shape
        return cv2.resize(test_gray, (w, h)), False

    # Parallax sorununu çözmek için: Homografiyi sadece zemine göre hizala
    # Resmin üst kısmındaki (tavan/duvar) keypoint'leri yoksay
    crop_h = int(h * FLOOR_ROI_TOP_CROP)
    valid_matches = []
    for m in good:
        pt = kp2[m.trainIdx].pt
        if pt[1] > crop_h:  # Sadece alt kısımdaki (zemindeki) özellikler
            valid_matches.append(m)

    if len(valid_matches) < 10:
        print("  [!] Zeminde yeterli esleme yok -- hizalama atlaniyor")
        return cv2.resize(test_gray, (w, h)), False

    src_pts = np.float32([kp1[m.queryIdx].pt for m in valid_matches]).reshape(-1, 1, 2)
    dst_pts = np.float32([kp2[m.trainIdx].pt for m in valid_matches]).reshape(-1, 1, 2)

    M, inliers = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC,
                                    ransacReprojThreshold=5.0)
    if M is None:
        print("  [!] Homografi hesaplanamadi")
        return cv2.resize(test_gray, (w, h)), False

    aligned = cv2.warpPerspective(test_gray, M, (w, h))
    inlier_count = int(np.sum(inliers)) if inliers is not None else 0
    print(f"  [OK] Zemin Homografi inlier: {inlier_count}/{len(valid_matches)}")
    return aligned, True


def compute_diff_mask(ref_bgr: np.ndarray, aligned_gray: np.ndarray,
                      yellow_mask: np.ndarray) -> np.ndarray:
    """
    Referans ile hizalanmış test arasındaki farkı hesapla.
    Sarı çizgi bölgeleri maske ile sıfırlanır → false positive yok.
    """
    ref_gray = cv2.cvtColor(ref_bgr, cv2.COLOR_BGR2GRAY)

    # Gaussian blur ile ufak piksel kaymalarını (1-3 px) kaynaştır
    ref_blur  = cv2.GaussianBlur(ref_gray,  (BLUR_KERNEL, BLUR_KERNEL), 0)
    test_blur = cv2.GaussianBlur(aligned_gray, (BLUR_KERNEL, BLUR_KERNEL), 0)

    # SSIM (Yapısal Benzerlik) hesapla
    # SSIM, absdiff'e göre ışık ve ufak kaymalara ÇOK daha dayanıklıdır
    score, diff_img = ssim(ref_blur, test_blur, full=True, data_range=255)
    
    # SSIM diff_img [-1, 1] döner (1 = aynı, -1 = zıt).
    # Bunu 0-255 arasına çevir ve tersini al (farklı olan yerler BEYAZ olsun)
    diff = (255 - (diff_img * 255).clip(0, 255)).astype(np.uint8)

    # Eşikleme (Otsu'ya gerek yok, SSIM zaten normalize edilmiş bir harita verir)
    _, binary = cv2.threshold(diff, DIFF_THRESHOLD, 255, cv2.THRESH_BINARY)
    print(f"  [SSIM] Skoru: {score:.4f}")

    # ── ROI ve Sarı bölgeleri maskele ──────────────────────────────
    # Resmin üst kısmını (tavan/duvar) tamamen yoksay
    h_img = binary.shape[0]
    binary[0:int(h_img * FLOOR_ROI_TOP_CROP), :] = 0
    
    binary[yellow_mask > 0] = 0   # sarı bölgedeki pikselleri sıfırla

    # Morfolojik temizlik
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (MORPH_KERNEL, MORPH_KERNEL))
    clean = cv2.morphologyEx(binary, cv2.MORPH_OPEN,  k)
    clean = cv2.morphologyEx(clean,  cv2.MORPH_CLOSE, k)

    return clean


def detect_objects(diff_mask: np.ndarray,
                   ref_bgr: np.ndarray) -> list[dict]:
    """
    Fark maskesindeki contour'ları bul, filtrele ve
    her biri için bounding box + alan hesapla.
    Döndürür: [ {x, y, w, h, area, cx, cy}, ... ]
    """
    contours, _ = cv2.findContours(diff_mask, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    img_h, img_w = diff_mask.shape
    img_area = img_h * img_w
    # Resmin max %35'ini kaplayan bbox gercek nesne olamaz (hizalama hatasi).
    MAX_AREA_RATIO = 0.35

    objects = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < MIN_AREA:
            continue   # gürültü

        x, y, w, h = cv2.boundingRect(cnt)
        bbox_area = w * h

        # Tum resmi kaplayan dev bbox -> hizalama hatasi, atla
        if bbox_area > img_area * MAX_AREA_RATIO:
            print(f"  [FILTRE] Cok buyuk bbox atildi: {bbox_area}px2 (resmin %{100*bbox_area/img_area:.0f}'i)")
            continue
        
        # Nesne merkezi ROI disindaysa (en ust %20 tavan bolgesi) yoksay.
        # Merkez kontrolu kullaniyoruz (y degil cy) — buyuk nesneler ROI sinirinda olabilir.
        cy_obj = y + h // 2
        if cy_obj < diff_mask.shape[0] * FLOOR_ROI_TOP_CROP:
            continue

        objects.append({
            "x": int(x), "y": int(y),
            "w": int(w), "h": int(h),
            "area": int(w * h),
            "cx": int(x + w // 2),
            "cy": int(y + h // 2),
        })

    # Büyükten küçüğe sırala
    objects.sort(key=lambda o: o["area"], reverse=True)
    return objects


def draw_result(ref_bgr: np.ndarray, test_bgr: np.ndarray,
                diff_mask: np.ndarray, objects: list[dict],
                yellow_mask: np.ndarray, wp_id: str) -> np.ndarray:
    """
    4 panelli görsel oluştur:
      Sol üst:  Referans kare
      Sağ üst:  Test kare + tespit kutuları
      Sol alt:  Fark maskesi (sarı bölge overlay ile)
      Sağ alt:  Test üzerine sarı maske overlay
    """
    H, W = ref_bgr.shape[:2]
    panel_h, panel_w = H, W

    # ── Panel 1: Referans ─────────────────────────────────────────────────
    p1 = ref_bgr.copy()
    cv2.putText(p1, "REFERANS", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    # ── Panel 2: Test + Bounding Box ─────────────────────────────────────
    p2 = test_bgr.copy()
    colors = [(0, 0, 255), (0, 165, 255), (0, 255, 0), (255, 0, 0)]  # kırmızı önce
    for i, obj in enumerate(objects):
        color = colors[i % len(colors)]
        cv2.rectangle(p2,
                      (obj["x"], obj["y"]),
                      (obj["x"] + obj["w"], obj["y"] + obj["h"]),
                      color, 2)
        label = f"Nesne {i+1}  {obj['area']}px²"
        cv2.putText(p2, label, (obj["x"], obj["y"] - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
    status = f"Tespit: {len(objects)} nesne"
    cv2.putText(p2, status, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                (0, 0, 255) if objects else (0, 200, 0), 2)

    # ── Panel 3: Fark maskesi + sarı bölge sarı overlay ──────────────────
    p3 = cv2.cvtColor(diff_mask, cv2.COLOR_GRAY2BGR)
    yellow_overlay = np.zeros_like(p3)
    yellow_overlay[yellow_mask > 0] = (0, 200, 200)  # sarı bölge = sarı renk
    p3 = cv2.addWeighted(p3, 0.8, yellow_overlay, 0.5, 0)
    cv2.putText(p3, "FARK MASKESI (sari=bastirilan)", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)

    # ── Panel 4: Sarı maske görsel ────────────────────────────────────────
    p4 = test_bgr.copy()
    p4[yellow_mask > 0] = (p4[yellow_mask > 0] * 0.4 +
                           np.array([0, 180, 180]) * 0.6).astype(np.uint8)
    cv2.putText(p4, "SARI MASKE (bastirilan bolgeler)", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 200, 200), 1)

    # ── Birleştir ─────────────────────────────────────────────────────────
    top    = np.hstack([p1, p2])
    bottom = np.hstack([p3, p4])
    grid   = np.vstack([top, bottom])

    # Başlık şeridi
    title_bar = np.zeros((40, grid.shape[1], 3), dtype=np.uint8)
    title_bar[:] = (30, 30, 30)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(title_bar,
                f"İP8 Değişiklik Tespiti — {wp_id}   |   {ts}",
                (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 200, 200), 1)
    return np.vstack([title_bar, grid])


def process_pair(wp_id: str, ref_img: str | np.ndarray, test_img: str | np.ndarray,
                 degisiklik_tipi: str = "bilinmiyor",
                 aciklama: str = "") -> dict:
    """
    Bir referans-test çifti için tam analiz pipline'ı çalıştır.
    ref_img ve test_img string (dosya yolu) veya doğrudan cv2 matrisi olabilir.
    Döndürür: sonuç sözlüğü (JSON'a yazılır)
    """
    ref_path_str = str(ref_img) if isinstance(ref_img, (str, Path)) else "canli_akis"
    test_path_str = str(test_img) if isinstance(test_img, (str, Path)) else "canli_akis"
    
    print(f"\n{'='*55}")
    print(f"  Waypoint: {wp_id}")
    print(f"  Referans: {ref_path_str}")
    print(f"  Test    : {test_path_str}")
    print(f"{'='*55}")

    if isinstance(ref_img, (str, Path)):
        ref_bgr = cv2.imread(str(ref_img))
    else:
        ref_bgr = ref_img.copy()
        
    if isinstance(test_img, (str, Path)):
        test_bgr = cv2.imread(str(test_img))
    else:
        test_bgr = test_img.copy()

    if ref_bgr is None:
        raise FileNotFoundError(f"Referans okunamadı: {ref_path_str}")
    if test_bgr is None:
        raise FileNotFoundError(f"Test okunamadı: {test_path_str}")

    # Boyutları eşitle (farklı çözünürlük varsa)
    h, w = ref_bgr.shape[:2]
    test_bgr = cv2.resize(test_bgr, (w, h))

    # 1. Sarı bölge maskesi
    yellow_mask = build_yellow_mask(ref_bgr)
    yellow_px   = int(np.sum(yellow_mask > 0))
    print(f"  [Sari] bölge pikseli: {yellow_px}  ({100*yellow_px/(h*w):.1f}%)")

    # 2. ORB hizalama
    aligned_gray, aligned_ok = orb_align(ref_bgr, test_bgr, yellow_mask)

    # 3. Fark maskesi
    diff_mask = compute_diff_mask(ref_bgr, aligned_gray, yellow_mask)

    # 4. Nesne tespiti (birden fazla!)
    objects = detect_objects(diff_mask, ref_bgr)
    print(f"  [Tespit] Nesne sayisi: {len(objects)}")
    for i, obj in enumerate(objects):
        print(f"     Nesne {i+1}: bbox=({obj['x']},{obj['y']},{obj['w']},{obj['h']})  alan={obj['area']}px2")

    # 5. Degisim skoru (maskedeki beyaz piksel orani)
    change_score = float(np.sum(diff_mask > 0)) / diff_mask.size

    # Karar mantigi:
    # a) En az bir nesne bbox bulunduysa -> UYARI
    # b) Nesne bulunamasa bile change_score > 0.30 ise (yüksek genel degisim)
    #    kapi/global degisim var demektir -> SSIM-UYARI
    CHANGE_ALERT_THRESHOLD = 0.30
    ssim_global_alert = (not bool(objects)) and (change_score > CHANGE_ALERT_THRESHOLD)
    is_alert = bool(objects) or ssim_global_alert
    if ssim_global_alert:
        print(f"  [SSIM-UYARI] Nesne bbox bulunamadi ama change_score={change_score:.4f} yuksek -- global degisim!")

    severity = SEVERITY_MAP.get(degisiklik_tipi, "MEDIUM") if is_alert else "NONE"

    # 6. Görsel kaydet
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    vis = draw_result(ref_bgr, test_bgr, diff_mask, objects, yellow_mask, wp_id)
    vis_path = OUT_DIR / f"{wp_id}_analiz.png"
    cv2.imwrite(str(vis_path), vis)

    mask_path = OUT_DIR / f"{wp_id}_maske.png"
    cv2.imwrite(str(mask_path), diff_mask)

    print(f"  [Kayit] Gorsel: {vis_path}")
    print(f"  [Durum] {'>>> UYARI <<<' if is_alert else 'Normal'}  |  change_score={change_score:.4f}")

    return {
        "waypoint_id":     wp_id,
        "referans":        ref_path_str,
        "test":            test_path_str,
        "degisiklik_tipi": degisiklik_tipi,
        "aciklama":        aciklama,
        "is_alert":        is_alert,
        "severity":        severity,
        "change_score":    round(change_score, 4),
        "nesne_sayisi":    len(objects),
        "nesneler":        objects,
        "maske_path":      str(mask_path),
        "gorseli_path":    str(vis_path),
        "hizalama_basari": aligned_ok,
        "ts":              datetime.now().isoformat(),
    }


def run_single(wp_id: str, ref_path: str, test_path: str):
    """Tek bir çift için çalıştır."""
    result = process_pair(wp_id, ref_path, test_path)
    out = OUT_DIR / f"{wp_id}_sonuc.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] Sonuc kaydedildi: {out}")
    return result


def run_batch(etiket_path: str):
    """etiketler.json içindeki tüm çiftleri işle."""
    with open(etiket_path, encoding="utf-8") as f:
        data = json.load(f)

    all_results = []
    for pair in data["test_ciftleri"]:
        result = process_pair(
            wp_id          = pair["waypoint_id"],
            ref_path       = PROJECT_DIR / pair["referans"],
            test_path      = PROJECT_DIR / pair["degisik"],
            degisiklik_tipi= pair.get("degisiklik_tipi", "bilinmiyor"),
            aciklama       = pair.get("aciklama", ""),
        )
        all_results.append(result)

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "tur":    data.get("tur", "ip8_degisiklik_turu"),
            "tarih":  datetime.now().isoformat(),
            "toplam": len(all_results),
            "uyari_sayisi": sum(1 for r in all_results if r["is_alert"]),
            "sonuclar": all_results,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*55}")
    print(f"  [OK] BATCH tamamlandi -- {len(all_results)} cift islendi")
    print(f"  [!]  Uyari: {sum(1 for r in all_results if r['is_alert'])}")
    print(f"  [->] Sonuclar: {RESULTS_PATH}")
    print(f"{'='*55}")

def run_live(wp_id: str, ref_path: str, kaynak_yolu: str):
    """Canlı akıştan (RTSP/Webcam) sürekli okuyarak analiz yapar."""
    adaptor = KaynakAdaptoru(kaynak_yolu)
    
    print(f"\n[IP8] Canlı Akış Modu Başlıyor...")
    print(f"Kaynak: {kaynak_yolu}")
    print("Çıkmak için 'q' tuşuna basın.")
    
    while True:
        ret, frame = adaptor.oku()
        if not ret:
            break
            
        result = process_pair(wp_id, ref_path, frame)
        
        vis = cv2.imread(result["gorseli_path"])
        if vis is not None:
            cv2.imshow("IP8 Canli Akis Analizi", vis)
            
        if cv2.waitKey(100) & 0xFF == ord('q'):
            break
            
    adaptor.release()
    cv2.destroyAllWindows()


def tune_yellow_mask(img_path: str):
    """
    Sarı maske HSV sınırlarını görsel olarak ayarlamak için debug modu.
    Ekranda iki pencere açar: orijinal ve maske.
    Çıkmak için 'q' tuşuna bas.
    """
    img = cv2.imread(img_path)
    if img is None:
        print(f"Görüntü okunamadı: {img_path}")
        return

    print("TUNE MODU — 'q' ile çık")
    print(f"Mevcut aralık: {YELLOW_HSV_LOWER} — {YELLOW_HSV_UPPER}")

    while True:
        mask = build_yellow_mask(img)
        overlay = img.copy()
        overlay[mask > 0] = (0, 0, 255)  # sarı bölgeleri kırmızı göster
        blended = cv2.addWeighted(img, 0.6, overlay, 0.4, 0)
        cv2.imshow("Orijinal", img)
        cv2.imshow("Sarı Maske (kırmızı = maskelendi)", blended)
        if cv2.waitKey(100) & 0xFF == ord('q'):
            break
    cv2.destroyAllWindows()


# ─── Argüman Ayrıştırma ────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="İP8 Değişiklik Tespiti (v2 — sarı çizgi bastırmalı)"
    )
    parser.add_argument("--ref",   default=str(PROJECT_DIR / "data/waypoints/referans_kareler/WP01.jpg"))
    parser.add_argument("--test",  default=str(PROJECT_DIR / "data/waypoints/abnormal/WP01_degisik.jpg"))
    parser.add_argument("--wp",    default="WP01")
    parser.add_argument("--batch", action="store_true",
                        help="data/ip8_test/etiketler.json üzerinden tüm çiftleri işle")
    parser.add_argument("--live", action="store_true",
                        help="Canlı akış modunda sürekli test et")
    parser.add_argument("--tune",  metavar="IMG_PATH",
                        help="Sarı maske HSV sınırlarını debug et")
    args = parser.parse_args()

    if args.tune:
        tune_yellow_mask(args.tune)
    elif args.batch:
        etiket = OUT_DIR / "etiketler.json"
        if not etiket.exists():
            print(f"[HATA] {etiket} bulunamadı.")
            print("       Önce etiketler.json dosyasını oluşturman gerekiyor.")
            print("       Bkz: DOKUMANLAR/Ozgur_is_paketleri.md -> IP8")
        else:
            run_batch(str(etiket))
    elif args.live:
        run_live(args.wp, args.ref, args.test)
    else:
        run_single(args.wp, args.ref, args.test)
