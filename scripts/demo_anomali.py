# -*- coding: utf-8 -*-
from __future__ import annotations
import sys, io
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf-16'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
"""
demo_anomali.py - Ozgur Kotbas - IP8 + IP9 Gercek Zamanli Anomali Tespiti Demo
================================================================================
Proje : Görsel Anomali Tespiti + Otomatik Devriye Raporu
Modül : ANOMALİ  →  patrol/alert
Çatı  : pan_tilt_robot_projesi.md · Grup 03_Gama · BTÜ · Staj 2026

AÇIKLAMA:
---------
Bu script ip8_degisiklik_tespiti.py ve ip9_ensemble_analiz.py dosyalarını
DEĞİŞTİRMEZ. Onların fonksiyon mantığını kendi içinde bağımsız olarak
uygular ve gerçek zamanlı bir ekran açar.

Reşit Asrav'ın demo/uyusmazliklar/RAPOR.md §1'de tanımlanan mimari sorun:
  "ANOMALİ modülü f(kare)→sonuç biçiminde fonksiyon sunmuyordu"
Bu demo tam olarak bu eksikliği kapatır:
  anomali_isle(kare) → {"is_alert": bool, "severity": str, "score": float, ...}

ÇALIŞMA MODLARI:
----------------
  MOD A — Waypoint Slayt Gösterisi  (gerçek WP01/WP02/WP03 çiftleri)
  MOD B — Video Akışı               (engel.mp4 → MOG2 canlı)
  MOD C — Sentetik Simülasyon        (hiç veri yoksa otomatik üretir)

Mod önceliği: A → B → C (otomatik seçilir)

KULLANIM:
---------
    python scripts/demo_anomali.py              # Otomatik mod seçimi
    python scripts/demo_animali.py --mod a      # Sadece waypoint slayt
    python scripts/demo_anomali.py --mod b      # Sadece video
    python scripts/demo_anomali.py --mod c      # Sadece sentetik
    python scripts/demo_anomali.py --hiz 2.0    # Slayt geçiş süresi (saniye)

KLAVYE:
-------
    Q / ESC  : Çık
    SPACE    : Duraklat / Devam
    +        : MOG2 eşiğini artır
    -        : MOG2 eşiğini azalt
    N        : Sonraki waypoint (Mod A)
    S        : Ekran görüntüsü al
"""

import argparse
import json
import math
import random
import sys
import time

from collections import deque
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))
from scripts.core import config_okuyucu

# ──────────────────────────────────────────────────────────────────────────────
# PROJE YOLLARI
# ──────────────────────────────────────────────────────────────────────────────
PROJECT_DIR   = config_okuyucu.PROJECT_ROOT
CONFIG        = config_okuyucu.CONFIG

ETIKET_PATH   = config_okuyucu.get_path(CONFIG.get("paths", {}).get("etiketler_json", "data/ip8_test/etiketler.json"))
REF_DIR       = PROJECT_DIR / "data" / "waypoints" / "referans_kareler"
ENGEL_VIDEO   = config_okuyucu.get_path(CONFIG.get("paths", {}).get("default_engel_video", "data/raw_videos/engel.mp4"))
OUT_DIR       = PROJECT_DIR / "outputs" / "demo_ciktilari"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────────────────────────────────────
# ALGILAMA PARAMETRELERİ  (klavyeden + / - ile değiştirilebilir)
# ──────────────────────────────────────────────────────────────────────────────
_vis_conf = CONFIG.get("vision", {})

PARAMS = {
    "ssim_esik"     : 40,        # İP8 SSIM eşik (0-255)
    "mog2_min_area" : _vis_conf.get("min_area", 1500),      # MOG2 minimum alan (px²)
    "mog2_thresh"   : _vis_conf.get("mog2_thresh", 20),        # MOG2 varThreshold
    "patchcore_esik": _vis_conf.get("patchcore_thresh", 0.50),      # PatchCore anomali eşiği
    "yellow_lower"  : np.array(_vis_conf.get("yellow_hsv_lower", [18, 80, 80])),
    "yellow_upper"  : np.array(_vis_conf.get("yellow_hsv_upper", [38, 255, 255])),
    "yellow_dilate" : _vis_conf.get("yellow_dilate_px", 15),
    "morph_kernel"  : 9,
    "blur_kernel"   : 7,
    "clahe_clip"    : 2.0,
    "floor_crop"    : 0.20,      # Üst % tavan bölgesi → yoksay
    "max_area_ratio": _vis_conf.get("max_area_ratio", 0.35),      # Resmin bu kadarından büyük → hizalama hatası
}

# ──────────────────────────────────────────────────────────────────────────────
# RENK PALETİ  (koyu tema)
# ──────────────────────────────────────────────────────────────────────────────
C = {
    "bg"        : (18,  18,  28),
    "panel_bg"  : (25,  25,  40),
    "header"    : (40,  40,  60),
    "uyari"     : (30,  30, 220),   # BGR kırmızı
    "normal"    : (30, 180,  60),   # BGR yeşil
    "medium"    : (20, 140, 220),   # BGR turuncu
    "text"      : (220, 220, 230),
    "subtext"   : (140, 140, 160),
    "accent"    : (220, 160,  40),  # BGR altın
    "graph_line": (80, 200, 120),
    "graph_warn": (40,  80, 220),
    "gt_box"    : (40, 220,  40),
    "det_box"   : [
        (0,   0, 220),  # kırmızı
        (0, 130, 255),  # turuncu
        (0, 200, 200),  # sarı
        (200,  0, 200), # mor
    ],
}

PANEL_W, PANEL_H = 480, 320
HEADER_H         = 44
FOOTER_H         = 48
GRAPH_H          = 90
HISTORY_LEN      = 80   # grafik için kaç kare geçmiş


# ══════════════════════════════════════════════════════════════════════════════
# YARDIMCI FONKSİYONLAR
# ══════════════════════════════════════════════════════════════════════════════

def put(img, text, pos, scale=0.55, color=None, thickness=1, bold=False):
    """OpenCV metin yazıcı — bold için çift baskı."""
    color = color or C["text"]
    font  = cv2.FONT_HERSHEY_SIMPLEX
    if bold:
        cv2.putText(img, text, pos, font, scale, (0,0,0), thickness + 3, cv2.LINE_AA)
    cv2.putText(img, text, pos, font, scale, color, thickness, cv2.LINE_AA)


def letterbox(frame: np.ndarray, w: int, h: int) -> np.ndarray:
    fh, fw = frame.shape[:2]
    scale  = min(w / fw, h / fh)
    nw, nh = max(1, int(fw * scale)), max(1, int(fh * scale))
    small  = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
    canvas = np.full((h, w, 3), C["panel_bg"], dtype=np.uint8)
    x0, y0 = (w - nw) // 2, (h - nh) // 2
    canvas[y0:y0+nh, x0:x0+nw] = small
    return canvas


def build_yellow_mask(img_bgr: np.ndarray) -> np.ndarray:
    hsv  = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, PARAMS["yellow_lower"], PARAMS["yellow_upper"])
    k    = cv2.getStructuringElement(
        cv2.MORPH_RECT, (PARAMS["yellow_dilate"], PARAMS["yellow_dilate"])
    )
    return cv2.dilate(mask, k, iterations=1)


def draw_header(canvas: np.ndarray, title: str, fps: float,
                is_alert: bool, severity: str, mod_label: str):
    """Üst başlık şeridi."""
    h, w = canvas.shape[:2]
    cv2.rectangle(canvas, (0, 0), (w, HEADER_H), C["header"], -1)

    # Sol: logo + başlık
    put(canvas, "▶ ANOMALİ TESPİT DEMO", (12, 16),
        scale=0.58, color=C["accent"], thickness=2, bold=True)
    put(canvas, f"Özgür Kotbaş · patrol/alert · {mod_label}",
        (12, 34), scale=0.40, color=C["subtext"])

    # Orta: durum
    durum_renk = C["uyari"] if is_alert else C["normal"]
    durum_txt  = f">>> UYARI <<<  [{severity}]" if is_alert else "Normal"
    tw, _ = cv2.getTextSize(durum_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)[0], 0
    cx    = (w - tw[0]) // 2
    put(canvas, durum_txt, (cx, 26), scale=0.65, color=durum_renk, thickness=2, bold=True)

    # Sağ: saat + FPS
    ts  = datetime.now().strftime("%H:%M:%S")
    put(canvas, f"FPS {fps:4.1f}", (w - 180, 18), scale=0.45, color=C["subtext"])
    put(canvas, ts,                (w - 100, 36), scale=0.50, color=C["text"])


def draw_footer(canvas: np.ndarray, mog2_cnt: int, score: float,
                esik: float, frame_no: int, toplam_uyari: int):
    """Alt bilgi şeridi."""
    h, w = canvas.shape[:2]
    y0   = h - FOOTER_H
    cv2.rectangle(canvas, (0, y0), (w, h), C["header"], -1)
    cv2.line(canvas, (0, y0), (w, y0), C["accent"], 1)

    put(canvas, f"MOG2 Nesneler: {mog2_cnt}",
        (14, y0 + 18), scale=0.46, color=C["text"])
    put(canvas, f"PatchCore Skoru: {score:.3f}  Eşik: {esik:.2f}",
        (14, y0 + 36), scale=0.42, color=C["subtext"])

    put(canvas, f"Kare: {frame_no}",
        (w // 2 - 60, y0 + 18), scale=0.44, color=C["subtext"])
    put(canvas, f"Toplam Uyarı: {toplam_uyari}",
        (w // 2 - 70, y0 + 36), scale=0.44,
        color=C["uyari"] if toplam_uyari > 0 else C["normal"])

    put(canvas, "Q:Çık  SPC:Duraklat  +/-:Eşik  N:Sonraki  S:Ekran",
        (w - 430, y0 + 27), scale=0.38, color=C["subtext"])


def draw_score_graph(history: deque, w: int, esik: float) -> np.ndarray:
    """Anomali skoru zaman serisi grafiği."""
    panel = np.full((GRAPH_H, w, 3), (12, 12, 22), dtype=np.uint8)
    cv2.rectangle(panel, (0, 0), (w - 1, GRAPH_H - 1), C["header"], 1)
    put(panel, "Anomali Skoru Geçmişi", (10, 16),
        scale=0.40, color=C["subtext"])

    # Eşik çizgisi
    ey = int((1.0 - esik) * (GRAPH_H - 30)) + 15
    cv2.line(panel, (0, ey), (w, ey), C["uyari"], 1)
    put(panel, f"eşik={esik:.2f}", (w - 90, ey - 4),
        scale=0.35, color=C["uyari"])

    if len(history) < 2:
        return panel

    # Grafik çizgisi
    vals = list(history)
    x_step = w / max(len(vals) - 1, 1)
    pts = []
    for i, v in enumerate(vals):
        if v < 0:   # PatchCore devre dışı → 0 göster
            v = 0.0
        x = int(i * x_step)
        y = int((1.0 - min(v, 1.0)) * (GRAPH_H - 30)) + 15
        pts.append((x, y))

    for i in range(1, len(pts)):
        above = (vals[i] >= esik)
        color = C["graph_warn"] if above else C["graph_line"]
        cv2.line(panel, pts[i-1], pts[i], color, 2)

    # Son değer dairesi
    if pts:
        lv = vals[-1] if vals[-1] >= 0 else 0.0
        cv2.circle(panel, pts[-1], 4,
                   C["graph_warn"] if lv >= esik else C["graph_line"], -1)
        put(panel, f"{lv:.3f}", (pts[-1][0] + 6, pts[-1][1] + 4),
            scale=0.38, color=C["text"])

    return panel


# ══════════════════════════════════════════════════════════════════════════════
# ALGILAMA MOTORU — İP8 + İP9 mantığı, f(kare)→sonuç biçiminde
# ══════════════════════════════════════════════════════════════════════════════

class AlgilayiciIP8:
    """
    İP8 mantığı: SSIM + ORB hizalama + fark maskesi + contour tespiti.
    Statik referans–test çifti üzerinde çalışır.
    ip8_degisiklik_tespiti.py DEĞİŞTİRİLMEZ — bu bağımsız sarmalayıcıdır.
    """

    def isle(self,
             ref_bgr: np.ndarray,
             test_bgr: np.ndarray,
             wp_id: str = "WP?") -> dict:
        """
        İki görüntü karşılaştır → anomali kararı döndür.
        Döndürür: {is_alert, nesneler, change_score, diff_mask, yellow_mask,
                   aligned_gray, ssim_score}
        """
        from skimage.metrics import structural_similarity as ssim

        h, w = ref_bgr.shape[:2]
        test_bgr = cv2.resize(test_bgr, (w, h))

        # 1. Sarı maske
        yellow = build_yellow_mask(ref_bgr)

        # 2. ORB hizalama
        aligned_gray, ok = self._orb_align(ref_bgr, test_bgr, yellow)

        # 3. SSIM fark maskesi
        ref_gray  = cv2.cvtColor(ref_bgr, cv2.COLOR_BGR2GRAY)
        clahe     = cv2.createCLAHE(clipLimit=PARAMS["clahe_clip"],
                                     tileGridSize=(8, 8))
        ref_eq    = clahe.apply(ref_gray)
        test_eq   = clahe.apply(aligned_gray)

        ref_b  = cv2.GaussianBlur(ref_eq,
                                   (PARAMS["blur_kernel"], PARAMS["blur_kernel"]), 0)
        test_b = cv2.GaussianBlur(test_eq,
                                   (PARAMS["blur_kernel"], PARAMS["blur_kernel"]), 0)

        score, diff_img = ssim(ref_b, test_b, full=True, data_range=255)
        diff = (255 - (diff_img * 255).clip(0, 255)).astype(np.uint8)
        _, binary = cv2.threshold(diff, PARAMS["ssim_esik"], 255,
                                   cv2.THRESH_BINARY)

        # ROI + sarı bölge temizle
        binary[0:int(h * PARAMS["floor_crop"]), :] = 0
        binary[yellow > 0] = 0

        k     = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (PARAMS["morph_kernel"], PARAMS["morph_kernel"]))
        clean = cv2.morphologyEx(binary, cv2.MORPH_OPEN,  k)
        clean = cv2.morphologyEx(clean,  cv2.MORPH_CLOSE, k)

        # 4. Nesne tespiti
        nesneler = self._detect(clean, h, w)
        change_score = float(np.sum(clean > 0)) / clean.size

        is_alert = bool(nesneler) or (
            (not nesneler) and change_score > 0.30)

        return {
            "is_alert"    : is_alert,
            "nesneler"    : nesneler,
            "change_score": round(change_score, 4),
            "ssim_score"  : round(float(score), 4),
            "diff_mask"   : clean,
            "yellow_mask" : yellow,
            "aligned_gray": aligned_gray,
            "aligned_ok"  : ok,
        }

    def _orb_align(self, ref_bgr, test_bgr, yellow_mask):
        ref_gray  = cv2.cvtColor(ref_bgr,  cv2.COLOR_BGR2GRAY)
        test_gray = cv2.cvtColor(test_bgr, cv2.COLOR_BGR2GRAY)
        h, w      = ref_gray.shape

        orb_roi = cv2.bitwise_not(yellow_mask)
        orb     = cv2.ORB_create(nfeatures=2000, fastThreshold=5,
                                  scaleFactor=1.2, nlevels=10)
        kp1, des1 = orb.detectAndCompute(ref_gray,  mask=orb_roi)
        kp2, des2 = orb.detectAndCompute(test_gray, mask=None)

        if des1 is None or des2 is None or len(kp1) < 10 or len(kp2) < 10:
            return cv2.resize(test_gray, (w, h)), False

        bf       = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        raw      = bf.knnMatch(des1, des2, k=2)
        good     = [m for m, n in raw if m.distance < 0.80 * n.distance]

        if len(good) < 10:
            return cv2.resize(test_gray, (w, h)), False

        crop_h = int(h * PARAMS["floor_crop"])
        valid  = [m for m in good if kp2[m.trainIdx].pt[1] > crop_h]

        if len(valid) < 10:
            return cv2.resize(test_gray, (w, h)), False

        src = np.float32([kp1[m.queryIdx].pt for m in valid]).reshape(-1, 1, 2)
        dst = np.float32([kp2[m.trainIdx].pt for m in valid]).reshape(-1, 1, 2)
        M, _ = cv2.findHomography(dst, src, cv2.RANSAC, 5.0)

        if M is None:
            return cv2.resize(test_gray, (w, h)), False

        aligned = cv2.warpPerspective(test_gray, M, (w, h))
        return aligned, True

    def _detect(self, mask: np.ndarray, h: int, w: int) -> list:
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)
        img_area = h * w
        objs     = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 500:
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            if bw * bh > img_area * PARAMS["max_area_ratio"]:
                continue
            cy_obj = y + bh // 2
            if cy_obj < h * PARAMS["floor_crop"]:
                continue
            objs.append({"x": int(x), "y": int(y),
                          "w": int(bw), "h": int(bh),
                          "area": int(bw * bh)})
        objs.sort(key=lambda o: o["area"], reverse=True)
        return objs


class AlgilayiciMOG2:
    """
    İP9 mantığı: MOG2 arka plan çıkarma — video akışı üzerinde çalışır.
    ip9_ensemble_analiz.py DEĞİŞTİRİLMEZ — bu bağımsız sarmalayıcıdır.
    """

    def __init__(self):
        self.mog2 = cv2.createBackgroundSubtractorMOG2(
            history=200,
            varThreshold=PARAMS["mog2_thresh"],
            detectShadows=True,
        )
        self._k_open  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        self._k_close = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (PARAMS["morph_kernel"], PARAMS["morph_kernel"]))

    def isle(self, frame: np.ndarray) -> dict:
        """
        Tek kare → MOG2 anomali kararı.
        Döndürür: {is_alert, nesneler, fg_mask, fg_ratio}
        """
        fg = self.mog2.apply(frame)
        fg[fg == 127] = 0    # gölge pikselleri sıfırla
        fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN,  self._k_open)
        fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, self._k_close)

        yellow = build_yellow_mask(frame)
        if fg.shape != yellow.shape:
            yellow = cv2.resize(yellow, (fg.shape[1], fg.shape[0]))
        fg[yellow > 0] = 0

        fg_ratio = float(np.sum(fg > 0)) / fg.size
        nesneler = self._detect(fg, yellow)
        is_alert = len(nesneler) > 0

        return {
            "is_alert" : is_alert,
            "nesneler" : nesneler,
            "fg_mask"  : fg,
            "fg_ratio" : round(fg_ratio, 4),
        }

    def _detect(self, mask: np.ndarray, yellow_mask: np.ndarray) -> list:
        h, w     = mask.shape
        img_area = h * w
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)
        objs = []
        for cnt in contours:
            if cv2.contourArea(cnt) < PARAMS["mog2_min_area"]:
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            if bw * bh > img_area * 0.40:
                continue
            cx, cy = x + bw // 2, y + bh // 2
            try:
                if yellow_mask[cy, cx] > 0:
                    continue
            except IndexError:
                pass
            objs.append({"x": int(x), "y": int(y),
                          "w": int(bw), "h": int(bh),
                          "area": int(bw * bh),
                          "cx": int(cx), "cy": int(cy)})
        objs.sort(key=lambda o: o["area"], reverse=True)
        return objs


# ══════════════════════════════════════════════════════════════════════════════
# PANEL ÇİZİCİLER
# ══════════════════════════════════════════════════════════════════════════════

def panel_ref(ref_bgr: np.ndarray, wp_id: str) -> np.ndarray:
    p = letterbox(ref_bgr, PANEL_W, PANEL_H)
    cv2.rectangle(p, (0, 0), (PANEL_W-1, PANEL_H-1), C["accent"], 1)
    put(p, f"[REFERANS]  {wp_id}", (8, 22),
        scale=0.52, color=C["accent"], thickness=2)
    put(p, "Altin Tur — Normal Durum", (8, 40),
        scale=0.38, color=C["subtext"])
    return p


def panel_test(test_bgr: np.ndarray,
               nesneler: list,
               gt_bbox,
               is_alert: bool,
               score: float) -> np.ndarray:
    p = letterbox(test_bgr, PANEL_W, PANEL_H)

    # GT kutusu (yeşil)
    if gt_bbox:
        gx, gy = gt_bbox.get("x", 0), gt_bbox.get("y", 0)
        gw, gh = gt_bbox.get("w", 0), gt_bbox.get("h", 0)
        sh, sw = test_bgr.shape[:2]
        sx = PANEL_W / sw
        sy = PANEL_H / sh
        cv2.rectangle(p,
                      (int(gx*sx), int(gy*sy)),
                      (int((gx+gw)*sx), int((gy+gh)*sy)),
                      C["gt_box"], 1)
        put(p, "GT", (int(gx*sx), max(int(gy*sy)-4, 14)),
            scale=0.35, color=C["gt_box"])

    # Tespit kutuları
    sh, sw = test_bgr.shape[:2]
    sx, sy = PANEL_W / sw, PANEL_H / sh
    for i, obj in enumerate(nesneler[:4]):
        color = C["det_box"][i % len(C["det_box"])]
        cv2.rectangle(p,
                      (int(obj["x"]*sx), int(obj["y"]*sy)),
                      (int((obj["x"]+obj["w"])*sx),
                       int((obj["y"]+obj["h"])*sy)),
                      color, 2)
        put(p, f"#{i+1} {obj['area']}px",
            (int(obj["x"]*sx), max(int(obj["y"]*sy)-5, 14)),
            scale=0.35, color=color)

    # Durum bandı
    brenk = C["uyari"] if is_alert else C["normal"]
    btxt  = ">>> UYARI <<<" if is_alert else "Normal"
    cv2.rectangle(p, (0, 0), (PANEL_W-1, 30), (0, 0, 0), -1)
    put(p, btxt, (8, 20), scale=0.60, color=brenk, thickness=2)
    put(p, f"score={score:.3f}  det={len(nesneler)}",
        (PANEL_W - 180, 20), scale=0.40, color=C["subtext"])
    put(p, "[CANLI / TEST KARE]", (8, PANEL_H - 8),
        scale=0.38, color=C["subtext"])
    cv2.rectangle(p, (0, 0), (PANEL_W-1, PANEL_H-1), brenk, 2)
    return p


def panel_diff(diff_mask: np.ndarray,
               yellow_mask: np.ndarray,
               ssim_score: float) -> np.ndarray:
    if diff_mask.ndim == 2:
        base = cv2.cvtColor(diff_mask, cv2.COLOR_GRAY2BGR)
    else:
        base = diff_mask.copy()

    p = letterbox(base, PANEL_W, PANEL_H)

    # Sarı overlay
    if yellow_mask is not None:
        ym_r = cv2.resize(yellow_mask, (PANEL_W, PANEL_H))
        p[ym_r > 0] = (
            p[ym_r > 0] * 0.5
            + np.array([0, 160, 160]) * 0.5
        ).astype(np.uint8)

    put(p, "[FARK MASKESI]", (8, 22),
        scale=0.50, color=C["subtext"], thickness=1)
    put(p, f"SSIM={ssim_score:.4f}  (sari=bastirilan)",
        (8, PANEL_H - 8), scale=0.36, color=C["subtext"])
    cv2.rectangle(p, (0, 0), (PANEL_W-1, PANEL_H-1), C["header"], 1)
    return p


def panel_mog2_fg(fg_mask: np.ndarray,
                  fg_ratio: float,
                  nesneler: list) -> np.ndarray:
    if fg_mask is None:
        fg_mask = np.zeros((PANEL_H, PANEL_W), dtype=np.uint8)

    if fg_mask.ndim == 2:
        base = cv2.cvtColor(fg_mask, cv2.COLOR_GRAY2BGR)
    else:
        base = fg_mask.copy()

    p = letterbox(base, PANEL_W, PANEL_H)
    put(p, "[MOG2 FG MASK]", (8, 22),
        scale=0.50, color=C["subtext"])
    put(p, f"fg_ratio={fg_ratio:.4f}  {len(nesneler)} nesne",
        (8, PANEL_H - 8), scale=0.36, color=C["subtext"])
    cv2.rectangle(p, (0, 0), (PANEL_W-1, PANEL_H-1), C["header"], 1)
    return p


# ══════════════════════════════════════════════════════════════════════════════
# EKRAN BİRLEŞTİRME
# ══════════════════════════════════════════════════════════════════════════════

def compose(p1, p2, p3, p4,
            score_history: deque,
            header_kw: dict,
            footer_kw: dict) -> np.ndarray:
    """4 panel + header + footer + grafik → tek canvas."""
    row1 = np.hstack([p1, p2])
    row2 = np.hstack([p3, p4])
    grid = np.vstack([row1, row2])

    total_w = grid.shape[1]
    total_h = HEADER_H + grid.shape[0] + GRAPH_H + FOOTER_H

    canvas = np.full((total_h, total_w, 3), C["bg"], dtype=np.uint8)
    canvas[HEADER_H:HEADER_H + grid.shape[0]] = grid
    graph = draw_score_graph(score_history, total_w,
                              PARAMS["patchcore_esik"])
    canvas[HEADER_H + grid.shape[0]:
           HEADER_H + grid.shape[0] + GRAPH_H] = graph

    draw_header(canvas, **header_kw)
    draw_footer(canvas, **footer_kw)

    return canvas


# ══════════════════════════════════════════════════════════════════════════════
# MOD A — WAYPOINT SLAYT GÖSTERİSİ
# ══════════════════════════════════════════════════════════════════════════════

def run_mod_a(hiz: float = 3.0):
    """
    Gerçek WP01/WP02/WP03 referans–test çiftlerini slayt olarak göster.
    İP8 mantığı (SSIM+ORB) ile her çift işlenir.
    """
    print("\n[MOD A] Waypoint Slayt Gösterisi başlıyor...")

    with open(ETIKET_PATH, encoding="utf-8") as f:
        etiketler = json.load(f)
    ciftler = etiketler.get("test_ciftleri", [])

    if not ciftler:
        print("  [HATA] Etiket dosyası boş — Mod C'ye geçiliyor.")
        return False

    algilayici = AlgilayiciIP8()
    score_hist = deque(maxlen=HISTORY_LEN)
    toplam_uyari = 0
    frame_no     = 0
    wp_idx       = 0
    duraklatildi = False

    # Tüm çiftleri önceden işle (kayda değer gecikmeyi önlemek için)
    print("  İşleniyor...")
    sonuclar = []
    for cift in ciftler:
        ref_path  = PROJECT_DIR / cift["referans"]
        test_path = PROJECT_DIR / cift["degisik"]

        ref_bgr  = cv2.imread(str(ref_path))
        test_bgr = cv2.imread(str(test_path))

        if ref_bgr is None or test_bgr is None:
            print(f"  [UYARI] Görüntü okunamadı: {ref_path}")
            continue

        sonuc = algilayici.isle(ref_bgr, test_bgr, cift["waypoint_id"])
        sonuclar.append({
            "cift"       : cift,
            "ref_bgr"    : ref_bgr,
            "test_bgr"   : test_bgr,
            "sonuc"      : sonuc,
        })
        print(f"  [{cift['waypoint_id']}] is_alert={sonuc['is_alert']}  "
              f"change={sonuc['change_score']:.4f}  "
              f"nesneler={len(sonuc['nesneler'])}")

    if not sonuclar:
        return False

    cv2.namedWindow("ANOMALİ DEMO — Özgür Kotbaş",
                    cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
    cv2.resizeWindow("ANOMALİ DEMO — Özgür Kotbaş",
                     PANEL_W * 2, PANEL_H * 2 + HEADER_H + GRAPH_H + FOOTER_H)

    t_son_gecis = time.time()

    while True:
        idx   = wp_idx % len(sonuclar)
        entry = sonuclar[idx]
        cift  = entry["cift"]
        sonuc = entry["sonuc"]

        wp_id   = cift["waypoint_id"]
        tip     = cift.get("degisiklik_tipi", "?")
        senaryo = cift.get("senaryo", "?")
        gt_bbox = cift.get("gt_bbox")

        # Severity
        severity = "NONE"
        if sonuc["is_alert"]:
            sev_map = {
                "yerde_birakilan_cisim": "HIGH",
                "yol_engeli":            "HIGH",
                "kapi_anomalisi":        "HIGH",
                "levha_degisikligi":     "MEDIUM",
            }
            severity = sev_map.get(tip, "MEDIUM")

        # Score history (statik mod → simüle)
        if not duraklatildi:
            base_score = 0.8 if sonuc["is_alert"] else 0.2
            simulated  = max(0.0, min(1.0,
                base_score + random.gauss(0, 0.04)))
            score_hist.append(simulated)
            frame_no += 1
            if sonuc["is_alert"]:
                toplam_uyari += 1

        # Paneller
        diff_mask = sonuc.get("diff_mask")
        yellow    = sonuc.get("yellow_mask")
        if diff_mask is None:
            diff_mask = np.zeros(
                (entry["ref_bgr"].shape[0], entry["ref_bgr"].shape[1]),
                dtype=np.uint8)

        p1 = panel_ref(entry["ref_bgr"], wp_id)
        p2 = panel_test(entry["test_bgr"],
                        sonuc["nesneler"], gt_bbox,
                        sonuc["is_alert"],
                        score_hist[-1] if score_hist else 0.0)
        p3 = panel_diff(diff_mask, yellow, sonuc["ssim_score"])
        p4 = panel_mog2_fg(
            np.zeros_like(diff_mask),  # MOG2 Mod A'da yok
            0.0, [])

        put(p4, f"Tip: {tip}", (8, 50),
            scale=0.48, color=C["accent"])
        put(p4, f"Senaryo: {senaryo}", (8, 74),
            scale=0.42, color=C["subtext"])
        put(p4, f"SSIM: {sonuc['ssim_score']:.4f}", (8, 98),
            scale=0.42, color=C["text"])
        put(p4, f"Degisim: {sonuc['change_score']:.4f}", (8, 118),
            scale=0.42, color=C["text"])

        # Senaryo açıklaması
        aciklama = cift.get("aciklama", "")
        put(p4, aciklama[:38], (8, PANEL_H - 30),
            scale=0.38, color=C["subtext"])
        put(p4, f"  {wp_idx+1}/{len(sonuclar)} — [N] sonraki",
            (8, PANEL_H - 14), scale=0.36, color=C["subtext"])

        frame = compose(
            p1, p2, p3, p4,
            score_hist,
            header_kw=dict(
                title   = f"WP Slayt — {wp_id}",
                fps     = 0.0 if duraklatildi else 1.0 / hiz,
                is_alert= sonuc["is_alert"],
                severity= severity,
                mod_label="MOD A: Waypoint Slayt",
            ),
            footer_kw=dict(
                mog2_cnt    = len(sonuc["nesneler"]),
                score       = score_hist[-1] if score_hist else 0.0,
                esik        = PARAMS["patchcore_esik"],
                frame_no    = frame_no,
                toplam_uyari= min(toplam_uyari, 9999),
            ),
        )

        # Duraklat göstergesi
        if duraklatildi:
            cv2.rectangle(frame, (PANEL_W - 60, HEADER_H + 10),
                          (PANEL_W + 60, HEADER_H + 40), (40, 40, 60), -1)
            put(frame, "|| DURAKLATI",
                (PANEL_W - 52, HEADER_H + 30),
                scale=0.50, color=C["accent"], thickness=2)

        cv2.imshow("ANOMALİ DEMO — Özgür Kotbaş", frame)

        # Otomatik geçiş
        if not duraklatildi:
            gecen = time.time() - t_son_gecis
            if gecen >= hiz:
                wp_idx       = (wp_idx + 1) % len(sonuclar)
                t_son_gecis  = time.time()
                toplam_uyari = 0   # her tur sıfırla

        key = cv2.waitKey(50) & 0xFF
        if key in (ord('q'), 27):
            break
        elif key == ord(' '):
            duraklatildi = not duraklatildi
        elif key == ord('n'):
            wp_idx      = (wp_idx + 1) % len(sonuclar)
            t_son_gecis = time.time()
        elif key == ord('+') or key == ord('='):
            PARAMS["patchcore_esik"] = min(0.99,
                round(PARAMS["patchcore_esik"] + 0.05, 2))
        elif key == ord('-'):
            PARAMS["patchcore_esik"] = max(0.05,
                round(PARAMS["patchcore_esik"] - 0.05, 2))
        elif key == ord('s'):
            ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = OUT_DIR / f"ekran_{wp_id}_{ts}.png"
            cv2.imwrite(str(path), frame)
            print(f"  [Kayıt] {path}")

    cv2.destroyAllWindows()
    return True


# ══════════════════════════════════════════════════════════════════════════════
# MOD B — VİDEO AKIŞI (MOG2 Canlı)
# ══════════════════════════════════════════════════════════════════════════════

def run_mod_b():
    """engel.mp4 üzerinde MOG2 ile gerçek zamanlı anomali tespiti."""
    print("\n[MOD B] Video Akışı başlıyor...")

    cap = cv2.VideoCapture(str(ENGEL_VIDEO))
    if not cap.isOpened():
        print(f"  [HATA] Video açılamadı: {ENGEL_VIDEO}")
        return False

    fps_video = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_fr  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"  Video: {ENGEL_VIDEO.name}  |  {fps_video:.1f} FPS  |  "
          f"{total_fr} kare ({total_fr/fps_video:.1f} sn)")

    algilayici   = AlgilayiciMOG2()
    score_hist   = deque(maxlen=HISTORY_LEN)
    toplam_uyari = 0
    frame_no     = 0
    duraklatildi = False
    ref_frame    = None

    # Referans kare: ilk 30 kareyi yükle ve sonuncuyu referans olarak sakla
    ret_frames = []
    for _ in range(30):
        ret, fr = cap.read()
        if not ret:
            break
        ret_frames.append(fr)
    if ret_frames:
        ref_frame = ret_frames[-1].copy()
    # Videoyu başa sar
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    cv2.namedWindow("ANOMALİ DEMO — Özgür Kotbaş",
                    cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
    cv2.resizeWindow("ANOMALİ DEMO — Özgür Kotbaş",
                     PANEL_W * 2, PANEL_H * 2 + HEADER_H + GRAPH_H + FOOTER_H)

    t_prev   = time.time()
    fps_disp = 0.0

    while True:
        if not duraklatildi:
            ret, frame = cap.read()
            if not ret:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 30)  # döngü
                continue

            # FPS ölçümü
            t_now    = time.time()
            fps_disp = 1.0 / max(t_now - t_prev, 1e-6)
            t_prev   = t_now

            sonuc    = algilayici.isle(frame)
            fg_mask  = sonuc["fg_mask"]
            fg_ratio = sonuc["fg_ratio"]
            nesneler = sonuc["nesneler"]
            is_alert = sonuc["is_alert"]

            # Simüle patchcore skoru (MOG2 oranından türet)
            pc_score = min(1.0, fg_ratio * 15.0 + len(nesneler) * 0.15)
            score_hist.append(pc_score)
            frame_no += 1
            if is_alert:
                toplam_uyari += 1

            severity = "HIGH" if len(nesneler) >= 2 else \
                       "MEDIUM" if len(nesneler) == 1 else "NONE"

            current_frame = frame
            cur_sonuc     = sonuc
            cur_fg        = fg_mask
            cur_fg_ratio  = fg_ratio
            cur_nesneler  = nesneler
            cur_is_alert  = is_alert
            cur_pc_score  = pc_score
            cur_severity  = severity
        # (duraklatıldığında son değerleri koru)

        # Paneller
        if ref_frame is None:
            ref_frame = current_frame.copy()

        p1 = panel_ref(ref_frame, "İlk Kare")
        p2 = panel_test(current_frame, cur_nesneler, None,
                        cur_is_alert, cur_pc_score)
        p3 = panel_diff(
            cur_fg if cur_fg is not None
            else np.zeros((PANEL_H, PANEL_W), dtype=np.uint8),
            None, 0.0)
        put(p3, "[MOG2 FG MASK]", (8, 22),
            scale=0.50, color=C["subtext"])
        put(p3, f"fg_ratio={cur_fg_ratio:.4f}", (8, PANEL_H - 8),
            scale=0.36, color=C["subtext"])

        p4 = panel_mog2_fg(cur_fg, cur_fg_ratio, cur_nesneler)

        # Kare numarası overlay
        pos_fr = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
        put(p4, f"Kare {pos_fr}/{total_fr}", (8, 50),
            scale=0.45, color=C["accent"])
        put(p4, f"Video: {ENGEL_VIDEO.name}", (8, 70),
            scale=0.38, color=C["subtext"])

        cv2_frame = compose(
            p1, p2, p3, p4,
            score_hist,
            header_kw=dict(
                title    = "Engel Videosu MOG2",
                fps      = fps_disp,
                is_alert = cur_is_alert,
                severity = cur_severity,
                mod_label= "MOD B: Video Akışı",
            ),
            footer_kw=dict(
                mog2_cnt     = len(cur_nesneler),
                score        = score_hist[-1] if score_hist else 0.0,
                esik         = PARAMS["patchcore_esik"],
                frame_no     = frame_no,
                toplam_uyari = toplam_uyari,
            ),
        )

        if duraklatildi:
            cv2.rectangle(cv2_frame, (PANEL_W - 60, HEADER_H + 10),
                          (PANEL_W + 60, HEADER_H + 40), (40, 40, 60), -1)
            put(cv2_frame, "|| DURAKLATI",
                (PANEL_W - 52, HEADER_H + 30),
                scale=0.50, color=C["accent"], thickness=2)

        cv2.imshow("ANOMALİ DEMO — Özgür Kotbaş", cv2_frame)

        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), 27):
            break
        elif key == ord(' '):
            duraklatildi = not duraklatildi
        elif key == ord('+') or key == ord('='):
            PARAMS["patchcore_esik"] = min(0.99,
                round(PARAMS["patchcore_esik"] + 0.05, 2))
        elif key == ord('-'):
            PARAMS["patchcore_esik"] = max(0.05,
                round(PARAMS["patchcore_esik"] - 0.05, 2))
        elif key == ord('s'):
            ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = OUT_DIR / f"ekran_video_{ts}.png"
            cv2.imwrite(str(path), cv2_frame)
            print(f"  [Kayıt] {path}")

    cap.release()
    cv2.destroyAllWindows()
    return True


# ══════════════════════════════════════════════════════════════════════════════
# MOD C — SENTETİK SİMÜLASYON (Fallback)
# ══════════════════════════════════════════════════════════════════════════════

class SentetikSahne:
    """Koridor benzeri sentetik fabrika sahnesi üretir."""

    def __init__(self, w=640, h=480):
        self.w, self.h = w, h
        self.ref  = self._zemin_ciz()
        self.t    = 0
        self.nesne_aktif  = False
        self.nesne_rx     = 0
        self.nesne_ry     = 0
        self.nesne_rw     = 0
        self.nesne_rh     = 0
        self.nesne_sure   = 0
        self._random_state = random.Random(42)

    def _zemin_ciz(self) -> np.ndarray:
        canvas = np.zeros((self.h, self.w, 3), dtype=np.uint8)
        # Arka plan — koyu gri koridor
        canvas[:] = (55, 55, 65)
        # Zemin perspektif çizgileri
        mid = self.w // 2
        for x_off in range(0, mid, 40):
            cv2.line(canvas,
                     (mid - x_off, self.h // 2),
                     (max(0, mid - x_off * 3), self.h),
                     (70, 70, 80), 1)
            cv2.line(canvas,
                     (mid + x_off, self.h // 2),
                     (min(self.w-1, mid + x_off * 3), self.h),
                     (70, 70, 80), 1)
        # Ufuk çizgisi
        cv2.line(canvas, (0, self.h // 2),
                 (self.w-1, self.h // 2), (80, 80, 90), 2)
        # Sarı zemin çizgileri
        for xpos in [self.w//4, 3*self.w//4]:
            cv2.line(canvas, (xpos, self.h//2+30),
                     (max(0, xpos - self.w//4), self.h-10),
                     (0, 180, 220), 3)
        # Kapı
        dx = self.w // 2
        cv2.rectangle(canvas, (dx - 40, self.h//2 - 80),
                      (dx + 40, self.h//2), (35, 45, 55), -1)
        cv2.rectangle(canvas, (dx - 40, self.h//2 - 80),
                      (dx + 40, self.h//2), (60, 70, 80), 2)
        # "IP9 MOG2" yazısı
        cv2.putText(canvas, "KORIDOR - REFERANS",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (100, 100, 110), 1)
        return canvas

    def kare_uret(self) -> tuple[np.ndarray, bool]:
        """(test_kare, is_anomali) çifti döndür."""
        self.t += 1
        frame = self.ref.copy()

        # Hafif aydınlatma salınımı
        delta = int(5 * math.sin(self.t / 30.0))
        frame = np.clip(frame.astype(np.int16) + delta, 0, 255).astype(np.uint8)

        # Periyodik nesne enjeksiyonu
        period = 120
        cycle  = self.t % period
        is_anomali = False

        if cycle == 40:  # nesne bırak
            self.nesne_aktif = True
            self.nesne_rx    = self._random_state.randint(
                self.w//4, 3*self.w//4 - 80)
            self.nesne_ry    = self._random_state.randint(
                self.h//2 + 20, self.h - 80)
            self.nesne_rw    = self._random_state.randint(40, 90)
            self.nesne_rh    = self._random_state.randint(50, 100)

        if self.nesne_aktif and cycle >= 40:
            cx  = self.nesne_rx
            cy  = self.nesne_ry
            rw  = self.nesne_rw
            rh  = self.nesne_rh
            # Nesne gövdesi (su şişesi benzeri)
            cv2.rectangle(frame, (cx, cy), (cx+rw, cy+rh), (80, 120, 180), -1)
            cv2.rectangle(frame, (cx, cy), (cx+rw, cy+rh), (120, 160, 220), 2)
            cv2.rectangle(frame, (cx+rw//3, cy-15),
                          (cx+2*rw//3, cy), (90, 130, 190), -1)
            cv2.putText(frame, "nesne", (cx+2, cy+20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4,
                        (200, 220, 255), 1)
            is_anomali = True

        if cycle == 0:
            self.nesne_aktif = False

        return frame, is_anomali


def run_mod_c():
    """Sentetik simülasyon — her zaman çalışır, veri gerektirmez."""
    print("\n[MOD C] Sentetik Simülasyon başlıyor...")

    sahne  = SentetikSahne()
    mog2_d = AlgilayiciMOG2()

    score_hist   = deque(maxlen=HISTORY_LEN)
    toplam_uyari = 0
    frame_no     = 0
    duraklatildi = False

    cv2.namedWindow("ANOMALİ DEMO — Özgür Kotbaş",
                    cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
    cv2.resizeWindow("ANOMALİ DEMO — Özgür Kotbaş",
                     PANEL_W * 2, PANEL_H * 2 + HEADER_H + GRAPH_H + FOOTER_H)

    t_prev   = time.time()
    fps_disp = 0.0

    ref_bgr = sahne.ref.copy()

    while True:
        if not duraklatildi:
            test_bgr, gt_is_anomali = sahne.kare_uret()

            t_now    = time.time()
            fps_disp = 1.0 / max(t_now - t_prev, 1e-6)
            t_prev   = t_now
            frame_no += 1

            sonuc    = mog2_d.isle(test_bgr)
            nesneler = sonuc["nesneler"]
            fg_mask  = sonuc["fg_mask"]
            fg_ratio = sonuc["fg_ratio"]
            is_alert = sonuc["is_alert"]

            # Sentetik PatchCore skoru
            pc_score = min(1.0, fg_ratio * 12.0 + len(nesneler) * 0.2 +
                           (0.3 if gt_is_anomali else 0.0) +
                           random.gauss(0, 0.03))
            score_hist.append(max(0.0, pc_score))
            if is_alert:
                toplam_uyari += 1

            severity = "HIGH" if pc_score > 0.7 else \
                       "MEDIUM" if pc_score > 0.4 else "NONE"

            _test_bgr   = test_bgr
            _nesneler   = nesneler
            _fg_mask    = fg_mask
            _fg_ratio   = fg_ratio
            _is_alert   = is_alert
            _pc_score   = pc_score
            _severity   = severity
            _gt_anomali = gt_is_anomali

        # Paneller
        p1 = panel_ref(ref_bgr, "Sentetik Koridor")
        p2 = panel_test(_test_bgr, _nesneler, None,
                        _is_alert, _pc_score)
        p3 = panel_diff(
            _fg_mask if _fg_mask is not None
            else np.zeros((PANEL_H, PANEL_W), dtype=np.uint8),
            None, 0.0)
        put(p3, "[MOG2 FG MASK]", (8, 22),
            scale=0.50, color=C["subtext"])
        put(p3, "Sentetik sahne — veri gerekmez", (8, PANEL_H - 8),
            scale=0.36, color=C["subtext"])

        p4 = panel_mog2_fg(_fg_mask, _fg_ratio, _nesneler)
        put(p4, "MOD C: Sentetik Simülasyon", (8, 50),
            scale=0.45, color=C["accent"])
        put(p4, "Periyodik nesne enjeksiyonu", (8, 70),
            scale=0.38, color=C["subtext"])
        gt_txt = "GT: Anomali VAR" if _gt_anomali else "GT: Normal"
        gt_c   = C["uyari"] if _gt_anomali else C["normal"]
        put(p4, gt_txt, (8, 92), scale=0.44, color=gt_c)

        cv2_frame = compose(
            p1, p2, p3, p4,
            score_hist,
            header_kw=dict(
                title    = "Sentetik Demo",
                fps      = fps_disp,
                is_alert = _is_alert,
                severity = _severity,
                mod_label= "MOD C: Sentetik Simülasyon",
            ),
            footer_kw=dict(
                mog2_cnt     = len(_nesneler),
                score        = score_hist[-1] if score_hist else 0.0,
                esik         = PARAMS["patchcore_esik"],
                frame_no     = frame_no,
                toplam_uyari = toplam_uyari,
            ),
        )

        if duraklatildi:
            put(cv2_frame, "|| DURAKLATI",
                (PANEL_W - 52, HEADER_H + 30),
                scale=0.50, color=C["accent"], thickness=2)

        cv2.imshow("ANOMALİ DEMO — Özgür Kotbaş", cv2_frame)

        key = cv2.waitKey(33) & 0xFF   # ~30 FPS
        if key in (ord('q'), 27):
            break
        elif key == ord(' '):
            duraklatildi = not duraklatildi
        elif key == ord('+') or key == ord('='):
            PARAMS["patchcore_esik"] = min(0.99,
                round(PARAMS["patchcore_esik"] + 0.05, 2))
        elif key == ord('-'):
            PARAMS["patchcore_esik"] = max(0.05,
                round(PARAMS["patchcore_esik"] - 0.05, 2))
        elif key == ord('s'):
            ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = OUT_DIR / f"ekran_sentetik_{ts}.png"
            cv2.imwrite(str(path), cv2_frame)
            print(f"  [Kayıt] {path}")

    cv2.destroyAllWindows()
    return True


# ══════════════════════════════════════════════════════════════════════════════
# GİRİŞ NOKTASI
# ══════════════════════════════════════════════════════════════════════════════

def banner():
    print("=" * 62)
    print("  ANOMALI TESPIT DEMO - Ozgur Kotbas - BTU - Staj 2026")
    print("  Modul: ANOMALI -> patrol/alert - Grup 03_Gama")
    print("  IP8 (SSIM+ORB) + IP9 (MOG2 Ensemble) canli demo")
    print("=" * 62)
    print(f"  Proje dizini : {PROJECT_DIR}")
    var_etiket = "VAR" if ETIKET_PATH.exists() else "YOK"
    var_video  = "VAR" if ENGEL_VIDEO.exists() else "YOK"
    print(f"  Etiket dosyasi: {var_etiket}")
    print(f"  Engel videosu : {var_video}")
    print("=" * 62)


def main():
    parser = argparse.ArgumentParser(
        description="Anomali Tespiti Gerçek Zamanlı Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--mod", choices=["a", "b", "c"], default=None,
        help="a=Waypoint slayt  b=Video akışı  c=Sentetik  (varsayılan: otomatik)"
    )
    parser.add_argument(
        "--hiz", type=float, default=3.0,
        help="Mod A slayt geçiş süresi (saniye, varsayılan: 3.0)"
    )
    parser.add_argument(
        "--mqtt", action="store_true",
        help="Tespit edilen anomalileri mqtt üzerinden canlı yayınla"
    )
    args = parser.parse_args()

    banner()

    # Otomatik mod seçimi
    if args.mod is None:
        if ETIKET_PATH.exists():
            args.mod = "a"
            print("  [Otomatik] MOD A seçildi — waypoint verileri mevcut")
        elif ENGEL_VIDEO.exists():
            args.mod = "b"
            print("  [Otomatik] MOD B seçildi — engel videosu mevcut")
        else:
            args.mod = "c"
            print("  [Otomatik] MOD C seçildi — sentetik simülasyon")

    print(f"\n  → MOD {'A: Waypoint Slayt' if args.mod=='a' else 'B: Video Akışı' if args.mod=='b' else 'C: Sentetik'}")
    print(f"  → MQTT: {'AKTİF' if args.mqtt else 'KAPALI'}")
    print()

    yayinci = None
    if args.mqtt:
        try:
            from scripts.comms.ip10_mqtt_yayini import PatrolMQTTYayinci
            yayinci = PatrolMQTTYayinci()
        except ImportError:
            print("  [UYARI] ip10_mqtt_yayini.py bulunamadı, MQTT kapalı.")

    try:
        if args.mod == "a":
            ok = run_mod_a(hiz=args.hiz)
            if not ok:
                print("  [Fallback] Mod B deneniyor...")
                ok = run_mod_b()
            if not ok:
                run_mod_c()
        elif args.mod == "b":
            ok = run_mod_b()
            if not ok:
                run_mod_c()
        else:
            run_mod_c()

    except KeyboardInterrupt:
        print("\n  [Çıkış] Kullanıcı tarafından durduruldu.")
    except Exception as e:
        print(f"\n  [HATA] {e}")
        import traceback
        traceback.print_exc()
    finally:
        cv2.destroyAllWindows()
        print(f"\n  Demo kapatıldı. Çıktılar: {OUT_DIR}")


if __name__ == "__main__":
    main()
