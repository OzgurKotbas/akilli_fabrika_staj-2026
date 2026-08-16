# -*- coding: utf-8 -*-
"""
IP8 v3: Hibrit Anomali Tespiti
==============================
Doküman: DOKUMANLAR/Ozgur_is_paketleri.md -- IP8
Bitti kriteri: data/ip8_test/ klasöründe etiketli test cifti seti commit'li

NEDEN V3?
---------
V1 ve V2'de iki farkli açıdan cekilmis videolari piksel pixel karsilastirmaya
calismak ORB hizalamasinin basarisiz olmasina yol aciyordu (inlier ratio cok dusuk).

V3 YAKLASIMI:
-------------
Iki asama:

1) ARKA PLAN CIKARMA (MOG2) -- Engel videosunu kendi icinde analiz et.
   Sabit arka plandan farkli olan hareketli/yeni nesneleri tespit et.
   Su sisesi ve cop kovasi hareket etmeden duruyor -- bu onlari tespit eder.
   
2) REFERANS KARE KARSILASTIRMA -- Engel videosunun en iyi eslesen frame'ini bul.
   Eger MOG2 yeterli nesne yakalayamazsa (kamera acisi cok farkliysa),
   change_score ve SSIM-UYARI ile genel degisim yakala.

KULLANIM:
    cd D:/STAJ/akilli_fabrika_staj-2026
    python scripts/ip8_video_eslestir_analiz.py

PARAMETRE SECENEKLERI:
    --altin     : Altin tur video yolu (varsayilan: data/raw_videos/altin_tur_v2.mp4)
    --engel     : Engel videosu yolu   (varsayilan: data/raw_videos/engel.mp4)
    --waypoints : Waypoint YAML yolu   (varsayilan: data/waypoints/waypoint_listesi.yaml)
    --outdir    : Cikti dizini         (varsayilan: data/ip8_test)
"""

import cv2
import numpy as np
import json
import argparse
import yaml
from datetime import datetime
from pathlib import Path
from skimage.metrics import structural_similarity as ssim_func

import sys
sys.path.append(str(Path(__file__).resolve().parent))
import config_okuyucu

# =============================================================================
# PROJE AYARLARI
# =============================================================================
PROJECT_DIR    = config_okuyucu.PROJECT_ROOT
CONFIG         = config_okuyucu.CONFIG

WAYPOINTS_YAML = config_okuyucu.get_path(CONFIG.get("paths", {}).get("waypoints_yaml", "data/waypoints/waypoint_listesi.yaml"))
ALTIN_VIDEO    = config_okuyucu.get_path(CONFIG.get("paths", {}).get("default_altin_video", "data/raw_videos/altin_tur_v2.mp4"))
ENGEL_VIDEO    = config_okuyucu.get_path(CONFIG.get("paths", {}).get("default_engel_video", "data/raw_videos/engel.mp4"))
OUT_DIR        = PROJECT_DIR / "data" / "ip8_test"

# =============================================================================
# ALGILAMA PARAMETRELERI
# =============================================================================
_vis_config = CONFIG.get("vision", {})

# Sarı zemin cizgisi HSV aralik (fabrika standart sari)
YELLOW_HSV_LOWER = np.array(_vis_config.get("yellow_hsv_lower", [18, 80, 80]))
YELLOW_HSV_UPPER = np.array(_vis_config.get("yellow_hsv_upper", [38, 255, 255]))
YELLOW_DILATE_PX = _vis_config.get("yellow_dilate_px", 15)

# Fark analizi
MIN_AREA       = _vis_config.get("min_area", 1500)
MAX_AREA_RATIO = _vis_config.get("max_area_ratio", 0.40)
MORPH_KERNEL   = 11
BLUR_KERNEL    = 5

# MOG2 arka plan cikarma
MOG2_HISTORY   = _vis_config.get("mog2_history", 200)
MOG2_THRESH    = _vis_config.get("mog2_thresh", 20)
MOG2_DETECT_S  = _vis_config.get("mog2_window_s", 10)

# Eslestirme
HISTOGRAM_BINS = 64

# Senaryo -> severity
SEVERITY_MAP = {
    "yerde_birakilan_cisim": "HIGH",
    "yol_engeli":            "HIGH",
    "kapi_anomalisi":        "HIGH",
    "levha_degisikligi":     "MEDIUM",
    "kablo_karmasa":         "LOW",
}


# =============================================================================
# YARDIMCI FONKSIYONLAR
# =============================================================================

def load_waypoints(yaml_path: str) -> list:
    """waypoint_listesi.yaml'i yukle."""
    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("waypoints", [])


def get_frame_at(video_path: str, second: float) -> "np.ndarray | None":
    """Videodan belirtilen saniyedeki frame'i dondur."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return None
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(second * fps))
    ret, frame = cap.read()
    cap.release()
    return frame if ret else None


def frame_histogram(frame_bgr: np.ndarray) -> np.ndarray:
    """BGR histogrami hesapla (normalize)."""
    hist = []
    for ch in range(3):
        h = cv2.calcHist([frame_bgr], [ch], None, [HISTOGRAM_BINS], [0, 256])
        cv2.normalize(h, h)
        hist.append(h)
    return np.concatenate(hist).flatten()


def build_yellow_mask(img_bgr: np.ndarray) -> np.ndarray:
    """Sari zemin cizgilerini maskele (255 = sari bolge)."""
    hsv  = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, YELLOW_HSV_LOWER, YELLOW_HSV_UPPER)
    k = cv2.getStructuringElement(
        cv2.MORPH_RECT, (YELLOW_DILATE_PX, YELLOW_DILATE_PX)
    )
    return cv2.dilate(mask, k, iterations=1)


# =============================================================================
# YONTEM 1: MOG2 ARKA PLAN CIKARMA
# Engel videosunu kendi icinde analiz et -- hareket etmeyen yabanci nesne
# =============================================================================

def detect_static_objects_mog2(engel_video: str,
                                ref_second: float,
                                window_s: float = MOG2_DETECT_S
                                ) -> "tuple[np.ndarray | None, np.ndarray, float]":
    """
    MOG2 arka plan modeliyle engel videosunun belirtilen bolgesinde
    duragan anomalileri tespit et.

    Neden bu yontem:
    - Cop kovasi ve su sisesi kameradan bakinca DURAGAN duruyor.
    - MOG2 hareket eden her seyi arka plan sayar; uzun sure duruk kalan
      bir yabanci nesneyi foreground olarak isaretler.
    - Cok isi / golgeden etkilenmez.

    Dondurur: (ornek_frame, fg_maskesi, fg_orani)
    """
    cap = cv2.VideoCapture(str(engel_video))
    if not cap.isOpened():
        return None, np.zeros((480, 640), np.uint8), 0.0

    fps         = cap.get(cv2.CAP_PROP_FPS)
    total_fr    = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    total_s     = total_fr / fps

    # Analiz penceresi: ref_second civarinda veya videonun son kismi
    start_s  = max(0, min(ref_second - window_s / 2, total_s - window_s))
    end_s    = min(total_s, start_s + window_s)
    start_fr = int(start_s * fps)
    end_fr   = int(end_s   * fps)

    mog2 = cv2.createBackgroundSubtractorMOG2(
        history=MOG2_HISTORY, varThreshold=MOG2_THRESH, detectShadows=True
    )

    sample_frame = None
    k_open  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (MORPH_KERNEL, MORPH_KERNEL))

    # Ilk gecis: MOG2'ye arka plani ogret
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_fr)
    for _ in range(start_fr, end_fr + 1):
        ret, fr = cap.read()
        if not ret:
            break
        mog2.apply(fr)
        if sample_frame is None:
            sample_frame = fr.copy()

    # Ikinci gecis: son frame uzerinde arka plan maskesi al
    cap.set(cv2.CAP_PROP_POS_FRAMES, max(start_fr, end_fr - 30))
    last_frame = None
    fg_mask    = None
    for _ in range(30):
        ret, fr = cap.read()
        if not ret:
            break
        fg = mog2.apply(fr, learningRate=0)  # artik ogrenme yok
        # Golgeleri (127) sifirla, sadece tam foreground (255) tut
        fg[fg == 127] = 0
        # Morfolojik temizlik
        fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN,  k_open)
        fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, k_close)
        fg_mask    = fg
        last_frame = fr.copy()

    cap.release()

    if fg_mask is None or last_frame is None:
        return sample_frame, np.zeros((480, 640), np.uint8), 0.0

    fg_ratio = float(np.sum(fg_mask > 0)) / fg_mask.size
    return last_frame, fg_mask, fg_ratio


# =============================================================================
# YONTEM 2: ORB + SSIM KARSILASTIRMA (Referans vs Engel)
# =============================================================================

def find_best_match(engel_video: str,
                    ref_hist: np.ndarray) -> "tuple[np.ndarray | None, float, float]":
    """
    Engel videosunda referans frame'e histogram olarak en benzer kareyi bul.
    Tum videoyu tara.
    Dondurur: (frame, korelasyon, saniye)
    """
    cap = cv2.VideoCapture(str(engel_video))
    if not cap.isOpened():
        return None, 0.0, 0.0

    fps = cap.get(cv2.CAP_PROP_FPS)
    best_frame, best_score, best_sec = None, -1.0, 0.0
    fi = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        h = frame_histogram(frame)
        score = float(cv2.compareHist(
            ref_hist.astype(np.float32).reshape(-1, 1),
            h.astype(np.float32).reshape(-1, 1),
            cv2.HISTCMP_CORREL
        ))
        if score > best_score:
            best_score, best_frame, best_sec = score, frame.copy(), fi / fps
        fi += 1
    cap.release()
    return best_frame, best_score, best_sec


def orb_align(ref_bgr: np.ndarray,
              test_bgr: np.ndarray,
              yellow_mask: np.ndarray) -> "tuple[np.ndarray, bool]":
    """ORB + Homografi ile test karesini referansa hizala."""
    ref_g  = cv2.cvtColor(ref_bgr,  cv2.COLOR_BGR2GRAY)
    test_g = cv2.cvtColor(test_bgr, cv2.COLOR_BGR2GRAY)
    h, w   = ref_g.shape
    roi    = cv2.bitwise_not(yellow_mask)

    orb = cv2.ORB_create(nfeatures=3000, fastThreshold=5,
                         scaleFactor=1.2, nlevels=12)
    kp1, d1 = orb.detectAndCompute(ref_g,  mask=roi)
    kp2, d2 = orb.detectAndCompute(test_g, mask=None)

    if d1 is None or d2 is None or len(kp1) < 10 or len(kp2) < 10:
        print("  [!] Keypoint yetersiz -- hizalama atlanıyor")
        return cv2.resize(test_g, (w, h)), False

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    raw = bf.knnMatch(d1, d2, k=2)
    good = [m for m, n in raw if m.distance < 0.80 * n.distance]
    print(f"  [ORB] iyi esleme: {len(good)}/{len(raw)}")

    if len(good) < 8:
        print("  [!] Esleme yetersiz -- hizalama atlanıyor")
        return cv2.resize(test_g, (w, h)), False

    src = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    M, inl = cv2.findHomography(dst, src, cv2.RANSAC, 5.0)
    if M is None:
        return cv2.resize(test_g, (w, h)), False
    n_inl = int(np.sum(inl)) if inl is not None else 0
    print(f"  [OK] Homografi inlier: {n_inl}/{len(good)}")
    aligned = cv2.warpPerspective(test_g, M, (w, h))
    return aligned, True


def ssim_diff(ref_bgr: np.ndarray,
              aligned_gray: np.ndarray,
              yellow_mask: np.ndarray) -> "tuple[np.ndarray, float]":
    """SSIM tabanli fark maskesi uret."""
    ref_g  = cv2.GaussianBlur(
        cv2.cvtColor(ref_bgr, cv2.COLOR_BGR2GRAY),
        (BLUR_KERNEL, BLUR_KERNEL), 0
    )
    test_g = cv2.GaussianBlur(aligned_gray, (BLUR_KERNEL, BLUR_KERNEL), 0)

    score, diff_img = ssim_func(ref_g, test_g, full=True, data_range=255)
    diff = (255 - (diff_img * 255).clip(0, 255)).astype(np.uint8)
    _, binary = cv2.threshold(diff, 35, 255, cv2.THRESH_BINARY)
    print(f"  [SSIM] Skoru: {score:.4f}")

    binary[yellow_mask > 0] = 0
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,
                                  (MORPH_KERNEL, MORPH_KERNEL))
    clean = cv2.morphologyEx(binary, cv2.MORPH_OPEN,  k)
    clean = cv2.morphologyEx(clean,  cv2.MORPH_CLOSE, k)
    return clean, float(score)


# =============================================================================
# ORTAK: NESNE TESPITI
# =============================================================================

def detect_objects(diff_mask: np.ndarray,
                   yellow_mask: "np.ndarray | None" = None) -> list:
    """
    Fark maskesindeki contoür'lari bul ve filtrele.
    - Kucuk gurultuler (< MIN_AREA) atilir
    - Tum resmi kaplayan dev bbox'lar (hizalama hatasi) atilir
    - Sari cizgi bölgesinde kalan kutular atilir
    """
    img_h, img_w = diff_mask.shape
    img_area = img_h * img_w

    contours, _ = cv2.findContours(diff_mask, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
    objects = []
    for cnt in contours:
        if cv2.contourArea(cnt) < MIN_AREA:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        bbox_area = w * h
        if bbox_area > img_area * MAX_AREA_RATIO:
            print(f"  [FILTRE] Dev bbox atildi: {bbox_area}px2 (resmin %{100*bbox_area/img_area:.0f}'i)")
            continue
        cx, cy = x + w // 2, y + h // 2
        # Sari cizgi bölgesi kontrolu
        if yellow_mask is not None:
            try:
                if yellow_mask[cy, cx] > 0:
                    continue
            except IndexError:
                pass
        objects.append({"x": int(x), "y": int(y),
                         "w": int(w), "h": int(h),
                         "area": int(bbox_area),
                         "cx": int(cx), "cy": int(cy)})

    objects.sort(key=lambda o: o["area"], reverse=True)
    return objects


# =============================================================================
# GORSEL KAYIT
# =============================================================================

def draw_result(ref_bgr: np.ndarray,
                test_bgr: np.ndarray,
                diff_mask: np.ndarray,
                fg_mask: np.ndarray,
                objects: list,
                yellow_mask: np.ndarray,
                wp_id: str,
                hist_score: float,
                engel_sec: float,
                mog2_objects: list) -> np.ndarray:
    """6 panelli gorsel: referans, engel, SSIM fark, MOG2 fg, sari overlay, sonuc."""
    H, W = ref_bgr.shape[:2]

    # Renk paleti
    COLORS = [(0, 0, 255), (0, 165, 255), (0, 255, 0), (255, 0, 0), (255, 0, 255)]

    def draw_boxes(img, boxes, label_prefix="N"):
        out = img.copy()
        for i, obj in enumerate(boxes):
            c = COLORS[i % len(COLORS)]
            cv2.rectangle(out, (obj["x"], obj["y"]),
                          (obj["x"] + obj["w"], obj["y"] + obj["h"]), c, 2)
            lbl = f"{label_prefix}{i+1} {obj['area']}px2"
            ly  = max(obj["y"] - 6, 18)
            cv2.putText(out, lbl, (obj["x"], ly),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, c, 2)
        return out

    # Panel 1: Referans
    p1 = ref_bgr.copy()
    cv2.putText(p1, "REFERANS (Altin Tur)", (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

    # Panel 2: Engel + SSIM tespit kutulari
    p2 = draw_boxes(cv2.resize(test_bgr, (W, H)), objects, "SSIM")
    n2 = f"SSIM Tespit: {len(objects)} nesne"
    cv2.putText(p2, n2, (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                (0, 0, 255) if objects else (0, 200, 0), 2)
    cv2.putText(p2, f"HistKor={hist_score:.3f} t={engel_sec:.1f}s",
                (10, H - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 200, 200), 1)

    # Panel 3: SSIM fark maskesi
    p3 = cv2.cvtColor(diff_mask, cv2.COLOR_GRAY2BGR)
    ov = np.zeros_like(p3)
    ov[yellow_mask > 0] = (0, 200, 200)
    p3 = cv2.addWeighted(p3, 0.8, ov, 0.5, 0)
    cv2.putText(p3, "SSIM FARK MASKESI (sari=bastirilan)", (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.50, (200, 200, 200), 1)

    # Panel 4: MOG2 foreground + tespit kutulari
    fg_bgr = cv2.cvtColor(
        cv2.resize(fg_mask, (W, H)), cv2.COLOR_GRAY2BGR
    )
    p4 = draw_boxes(fg_bgr, mog2_objects, "MOG2")
    n4 = f"MOG2 Tespit: {len(mog2_objects)} nesne"
    cv2.putText(p4, n4, (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                (0, 0, 255) if mog2_objects else (0, 200, 0), 2)

    # Panel 5: Engel + sari overlay
    p5 = cv2.resize(test_bgr, (W, H)).copy()
    ym_r = cv2.resize(yellow_mask, (W, H))
    p5[ym_r > 0] = (p5[ym_r > 0] * 0.35 + np.array([0, 180, 180]) * 0.65).astype(np.uint8)
    cv2.putText(p5, "SARI BOLGE OVERLAY", (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 200, 200), 1)

    # Panel 6: Engel + tum tespitler (SSIM + MOG2 birlikte)
    all_objs = objects + mog2_objects
    p6 = draw_boxes(cv2.resize(test_bgr, (W, H)), all_objs, "T")
    cv2.putText(p6, f"BIRLESIK: {len(all_objs)} tespit", (10, 28),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65,
                (0, 0, 255) if all_objs else (0, 200, 0), 2)

    # 2x3 grid
    row1 = np.hstack([cv2.resize(p1, (W, H)),
                      cv2.resize(p2, (W, H)),
                      cv2.resize(p3, (W, H))])
    row2 = np.hstack([cv2.resize(p4, (W, H)),
                      cv2.resize(p5, (W, H)),
                      cv2.resize(p6, (W, H))])
    grid = np.vstack([row1, row2])

    bar = np.full((42, grid.shape[1], 3), (20, 20, 30), np.uint8)
    ts  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(bar,
                f"IP8 Degisiklik Tespiti -- {wp_id}   |   {ts}",
                (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (190, 190, 190), 1)
    return np.vstack([bar, grid])


# =============================================================================
# ANA PIPELINE -- TEK WAYPOINT
# =============================================================================

def process_waypoint(wp: dict,
                     altin_video: str,
                     engel_video: str,
                     out_dir: Path) -> dict:
    wp_id   = wp["id"]
    ref_sec = float(wp["saniye"])

    print(f"\n{'='*60}")
    print(f"  Waypoint: {wp_id}  |  Altin tur t={ref_sec}s")
    print(f"{'='*60}")

    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Adim 1: Referans frame yukle ──────────────────────────────────────
    ref_dir       = PROJECT_DIR / "data/waypoints/referans_kareler"
    ref_dir.mkdir(parents=True, exist_ok=True)
    ref_save_path = ref_dir / f"{wp_id}.jpg"

    if ref_save_path.exists():
        ref_bgr = cv2.imread(str(ref_save_path))
        print(f"  [OK] Referans mevcut: {ref_save_path}")
    else:
        ref_bgr = get_frame_at(altin_video, ref_sec)
        if ref_bgr is None:
            print(f"  [HATA] Referans alinamadi: {altin_video} @ {ref_sec}s")
            return {}
        cv2.imwrite(str(ref_save_path), ref_bgr)
        print(f"  [OK] Referans altin turdan alindi: {ref_save_path}")

    # ── Adim 2: MOG2 ile engel videosunda duragan nesne bul ───────────────
    print("  [MOG2] Arka plan cikarma basliyor...")
    engel_last, fg_mask, fg_ratio = detect_static_objects_mog2(
        engel_video, ref_sec
    )
    print(f"  [MOG2] fg_ratio: {fg_ratio:.4f}")

    # Sari maskeyi engel frame uzerinde hesapla
    yellow_mask_engel = build_yellow_mask(engel_last) if engel_last is not None \
        else np.zeros(ref_bgr.shape[:2], np.uint8)

    # MOG2 maskesine sari bolgeleri uygula
    if fg_mask.shape[:2] != ref_bgr.shape[:2]:
        fg_mask = cv2.resize(fg_mask, (ref_bgr.shape[1], ref_bgr.shape[0]))
    fg_mask_clean = fg_mask.copy()
    fg_mask_clean[yellow_mask_engel > 0] = 0

    mog2_objects = detect_objects(fg_mask_clean, yellow_mask_engel)
    print(f"  [MOG2] Tespit: {len(mog2_objects)} nesne")
    for i, obj in enumerate(mog2_objects):
        print(f"     M{i+1}: bbox=({obj['x']},{obj['y']},{obj['w']},{obj['h']})  alan={obj['area']}px2")

    # ── Adim 3: Histogram ile engel videosunda en benzer frame bul ─────────
    print("  [HIST] Engel video taranıyor...")
    ref_hist = frame_histogram(ref_bgr)
    engel_frame, hist_score, engel_sec = find_best_match(engel_video, ref_hist)
    print(f"  [HIST] Engel t={engel_sec:.2f}s  |  Korelasyon: {hist_score:.4f}")

    if engel_frame is None:
        engel_frame = engel_last if engel_last is not None else ref_bgr.copy()
        engel_sec   = ref_sec

    # Engel frame'i kaydet
    engel_save = out_dir / f"{wp_id}_degisik.jpg"
    cv2.imwrite(str(engel_save), engel_frame)

    # Boyutlari esitle
    h_r, w_r = ref_bgr.shape[:2]
    engel_frame_r = cv2.resize(engel_frame, (w_r, h_r))

    # ── Adim 4: ORB + SSIM fark maskesi ───────────────────────────────────
    yellow_mask_ref = build_yellow_mask(ref_bgr)
    yellow_px = int(np.sum(yellow_mask_ref > 0))
    print(f"  [Sari] Referans sarı bolge: {yellow_px}  ({100*yellow_px/(h_r*w_r):.1f}%)")

    aligned_gray, aligned_ok = orb_align(ref_bgr, engel_frame_r, yellow_mask_ref)
    diff_mask, ssim_score = ssim_diff(ref_bgr, aligned_gray, yellow_mask_ref)

    ssim_objects = detect_objects(diff_mask, yellow_mask_ref)
    print(f"  [SSIM] Tespit: {len(ssim_objects)} nesne")
    for i, obj in enumerate(ssim_objects):
        print(f"     S{i+1}: bbox=({obj['x']},{obj['y']},{obj['w']},{obj['h']})  alan={obj['area']}px2")

    # ── Adim 5: Karar -- SSIM veya MOG2'den herhangi biri bulursa UYARI ──
    change_score = float(np.sum(diff_mask > 0)) / diff_mask.size
    CHANGE_ALERT_THRESHOLD = 0.30

    has_ssim_objects  = bool(ssim_objects)
    has_mog2_objects  = bool(mog2_objects)
    global_change     = (not has_ssim_objects and not has_mog2_objects
                         and change_score > CHANGE_ALERT_THRESHOLD)

    is_alert = has_ssim_objects or has_mog2_objects or global_change
    if global_change:
        print(f"  [SSIM-UYARI] change_score={change_score:.4f} yuksek -- global degisim!")

    severity  = SEVERITY_MAP.get(wp.get("degisiklik_tipi", ""), "MEDIUM") \
        if is_alert else "NONE"
    durum_str = ">>> UYARI <<<" if is_alert else "Normal"
    print(f"  [Durum] {durum_str}  |  SSIM_obj={len(ssim_objects)}  MOG2_obj={len(mog2_objects)}  change={change_score:.4f}")

    # ── Adim 6: Gorsel kaydet ──────────────────────────────────────────────
    vis = draw_result(
        ref_bgr       = ref_bgr,
        test_bgr      = engel_frame_r,
        diff_mask     = diff_mask,
        fg_mask       = fg_mask_clean,
        objects       = ssim_objects,
        yellow_mask   = yellow_mask_ref,
        wp_id         = wp_id,
        hist_score    = hist_score,
        engel_sec     = engel_sec,
        mog2_objects  = mog2_objects,
    )
    vis_path  = out_dir / f"{wp_id}_analiz.png"
    mask_path = out_dir / f"{wp_id}_maske.png"
    fg_path   = out_dir / f"{wp_id}_fg_mog2.png"
    cv2.imwrite(str(vis_path),  vis)
    cv2.imwrite(str(mask_path), diff_mask)
    cv2.imwrite(str(fg_path),   fg_mask_clean)
    print(f"  [Kayit] {vis_path}")

    return {
        "waypoint_id":       wp_id,
        "konum":             wp.get("konum", ""),
        "altin_tur_second":  ref_sec,
        "engel_second":      round(engel_sec, 2),
        "histogram_korelas": round(hist_score, 4),
        "ssim_skoru":        round(ssim_score, 4),
        "mog2_fg_ratio":     round(fg_ratio, 4),
        "referans_kare":     str(ref_save_path),
        "engel_kare":        str(engel_save),
        "analiz_gorseli":    str(vis_path),
        "diff_maskesi":      str(mask_path),
        "fg_mog2":           str(fg_path),
        "is_alert":          is_alert,
        "severity":          severity,
        "change_score":      round(change_score, 4),
        "ssim_nesne_sayisi": len(ssim_objects),
        "mog2_nesne_sayisi": len(mog2_objects),
        "ssim_nesneler":     ssim_objects,
        "mog2_nesneler":     mog2_objects,
        "hizalama_basari":   aligned_ok,
        "ts":                datetime.now().isoformat(),
    }


# =============================================================================
# ANA PIPELINE -- TUM WAYPOINTS
# =============================================================================

def run_all(altin_video: str, engel_video: str,
            waypoints_yaml: str, out_dir: Path):
    waypoints = load_waypoints(waypoints_yaml)
    if not waypoints:
        print(f"[HATA] Waypoint bulunamadi: {waypoints_yaml}")
        return

    print(f"\nAltin Tur  : {altin_video}")
    print(f"Engel Video: {engel_video}")
    print(f"Waypoint   : {len(waypoints)} adet")
    print(f"Cikti      : {out_dir}")

    all_results = []
    for wp in waypoints:
        result = process_waypoint(wp, altin_video, engel_video, out_dir)
        if result:
            all_results.append(result)
            j_path = out_dir / f"{wp['id']}_sonuc.json"
            with open(j_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

    results_path = out_dir / "sonuclar.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump({
            "tur":          "ip8_degisiklik_turu_v3",
            "tarih":        datetime.now().isoformat(),
            "altin_video":  str(altin_video),
            "engel_video":  str(engel_video),
            "toplam":       len(all_results),
            "uyari_sayisi": sum(1 for r in all_results if r["is_alert"]),
            "sonuclar":     all_results,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"  [OK] TAMAMLANDI -- {len(all_results)} waypoint islendi")
    print(f"  [!]  Uyari: {sum(1 for r in all_results if r['is_alert'])}")
    print(f"  [->] Sonuclar: {results_path}")
    print(f"{'='*60}")


# =============================================================================
# ARGÜMAN AYRIŞIMA
# =============================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="IP8 v3: MOG2 + SSIM hibrit anomali tespiti"
    )
    parser.add_argument("--altin",    default=str(ALTIN_VIDEO))
    parser.add_argument("--engel",    default=str(ENGEL_VIDEO))
    parser.add_argument("--waypoints",default=str(WAYPOINTS_YAML))
    parser.add_argument("--outdir",   default=str(OUT_DIR))
    args = parser.parse_args()

    run_all(
        altin_video    = args.altin,
        engel_video    = args.engel,
        waypoints_yaml = args.waypoints,
        out_dir        = Path(args.outdir),
    )
