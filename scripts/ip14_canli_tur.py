# -*- coding: utf-8 -*-
from __future__ import annotations
import sys, io
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf-16'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
"""
İP14: Canlı Tur — Uçtan Uca Devriye Simülasyonu  (v2 — Evrensel Kaynak)
=========================================================================
Proje  : Görsel Anomali Tespiti + Otomatik Devriye Raporu
Modül  : ANOMALİ  →  patrol/alert
Çatı   : pan_tilt_robot_projesi.md · Grup 03_Gama · BTÜ · Staj 2026
Doküman: DOKUMANLAR/Ozgur_is_paketleri.md — İP14

EVRENSEL KAYNAK DESTEĞİ:
-------------------------
  Video dosyası  : python scripts/ip14_canli_tur.py --kaynak data/raw_videos/engel.mp4
  RTSP kamera    : python scripts/ip14_canli_tur.py --kaynak rtsp://192.168.1.10/stream
  Webcam         : python scripts/ip14_canli_tur.py --kaynak 0
  Statik kare    : python scripts/ip14_canli_tur.py --kaynak data/ip8_test/WP01_degisik.jpg

AKIŞ (her waypoint için):
  1. KaynakAdaptoru aracılığıyla "canlı" kare al
  2. MOG2'yi REFERANS KARE'den ısıt  ← WP03 düzeltmesi (v2)
  3. Canlı kare → MOG2 analizi → anomali kararı
  4. İP10 MQTT yayını (offline veya canlı)
  5. Kanıt görüntüsü (referans + canlı yan yana) kaydet
  6. Tur sonunda İP13 PDF raporu otomatik üret

WP03 HATA ANALİZİ (v1'de neden yanlıştı):
  engel.mp4'te engel tüm video boyunca var.
  v1'de warmup video'dan alınıyordu → MOG2 engeli arka plan öğreniyordu
  → test karesinde engel "normal" sayılıyordu → is_alert=False (YANLIŞ)
  
  v2 düzeltmesi: warmup referans kare (normal durum) ile yapılıyor
  → MOG2 sadece "engelsiz, normal" durumu öğreniyor
  → test karesinde engel "yabancı/ön plan" sayılıyor → is_alert=True (DOĞRU)

KLAVYE (pencere açıksa):
  Q / ESC : Turu iptal et
  SPACE   : Duraklat / Devam
  N       : Sonraki waypoint'e atla
  S       : Ekran görüntüsü kaydet
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

sys.path.append(str(Path(__file__).resolve().parent.parent))
from scripts.core import config_okuyucu
from scripts.core.anomali_motor import AlgilayiciMOG2, build_yellow_mask
from scripts.core.kaynak_adaptoru import KaynakAdaptoru
from scripts.comms.ip10_mqtt_yayini import PatrolMQTTYayinci

# ──────────────────────────────────────────────────────────────────────────────
# PROJE YOLLARI
# ──────────────────────────────────────────────────────────────────────────────
PROJECT_DIR  = config_okuyucu.PROJECT_ROOT
CONFIG       = config_okuyucu.CONFIG
_vis_conf    = CONFIG.get("vision", {})

ETIKET_PATH  = config_okuyucu.get_path(
    CONFIG.get("paths", {}).get("etiketler_json", "data/ip8_test/etiketler.json"))
REF_DIR      = PROJECT_DIR / "data" / "waypoints" / "referans_kareler"
ENGEL_VIDEO  = config_okuyucu.get_path(
    CONFIG.get("paths", {}).get("default_engel_video", "data/raw_videos/engel.mp4"))
ENSEMBLE_DIR = PROJECT_DIR / "data" / "ip9_ensemble"

OUT_DIR      = PROJECT_DIR / "outputs" / "ip14_canli_tur"
OUT_DIR.mkdir(parents=True, exist_ok=True)

RAPOR_DIR    = PROJECT_DIR / "outputs" / "devriye_raporu"
RAPOR_DIR.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────────────────────────────────────
# RENK PALETİ & UI SABİTLERİ
# ──────────────────────────────────────────────────────────────────────────────
C = {
    "bg"       : (18,  18,  28),
    "panel_bg" : (25,  25,  40),
    "header"   : (40,  40,  60),
    "uyari"    : (30,  30, 220),
    "normal"   : (30, 180,  60),
    "accent"   : (220, 160, 40),
    "text"     : (220, 220, 230),
    "subtext"  : (140, 140, 160),
    "progress" : (80,  180, 100),
    "freeze"   : (200, 200,  40),
}

PANEL_W  = 480
PANEL_H  = 320
HEADER_H = 50
FOOTER_H = 54

SEVERITY_MAP = {
    "yerde_birakilan_cisim" : "HIGH",
    "yol_engeli"            : "HIGH",
    "kapi_anomalisi"        : "HIGH",
    "levha_degisikligi"     : "MEDIUM",
    "duman_iz"              : "MEDIUM",
    "sizinti"               : "MEDIUM",
}

MOG2_WARMUP_N = _vis_conf.get("mog2_warmup_n", 40)

# KaynakAdaptoru artık scripts.core.kaynak_adaptoru içerisinden kullanılıyor


# ──────────────────────────────────────────────────────────────────────────────
# WAYPOINT ANALİZCİ — Evrensel (v2)
# ──────────────────────────────────────────────────────────────────────────────

class WaypointAnalizci:
    """
    Evrensel waypoint analizi.
    v2 düzeltmesi: MOG2 warmup referans kare'den yapılıyor (video'dan değil).
    Bu sayede:
      - Video boyunca engel var → warmup'ta yanlış öğrenme YOK
      - RTSP/webcam → her zaman referanstan başlatılır
      - Statik görüntü → direkt karşılaştırma
    """

    def __init__(self, adaptoru: KaynakAdaptoru):
        self.adaptoru = adaptoru

    def waypoint_isle(self,
                      ref_bgr: np.ndarray,
                      test_saniye: float | None = None,
                      test_statik: np.ndarray | None = None,
                      warmup_n: int = MOG2_WARMUP_N) -> dict:
        """
        Verilen referans kare üzerinden MOG2 modeli ısıtılır,
        ardından kaynaktan alınan test karesi üzerinde anomali tespiti yapılır.

        Parametreler:
          ref_bgr     : Normal durum referans karesi (altın tur)
          test_saniye : Video modunda bu saniyedeki kare alınır; None → bir sonraki kare
          test_statik : Direkt test görüntüsü (önceliklidir — deg_path'ten okunur)
          warmup_n    : MOG2'yi referansla kaç kez besleme

        v2 Kritik Düzeltme:
          warmup = referans kare ile → sadece NORMAL durumu öğrenir
          WP03 hatası: v1'de engel.mp4'teki tüm karedeki engel warmup'a giriyordu
          → MOG2 engeli "normal" sayıyordu → is_alert=False (YANLIŞ)
          v2: warmup sadece referans kare → is_alert=True (DOĞRU)
        """
        algilayici = AlgilayiciMOG2()
        algilayici.warmup(ref_bgr, n=warmup_n)

        kare = self.adaptoru.kare_al(test_saniye)
        if kare is None:
            print(f"  [UYARI] Test karesi alinamadi (saniye={test_saniye})")
            test_frame = ref_bgr.copy()
        else:
            test_frame = kare

        if test_statik is not None:
            sonuc = self._ssim_analiz(ref_bgr, test_frame)
        else:
            sonuc = algilayici.isle(test_frame)

        diff_bgr = self._fark_gorseli(ref_bgr, test_frame, sonuc.get("fg_mask"))

        return {
            "is_alert"   : sonuc["is_alert"],
            "nesneler"   : sonuc["nesneler"],
            "fg_mask"    : sonuc.get("fg_mask"),
            "fg_ratio"   : sonuc.get("fg_ratio", 0.0),
            "is_rotation": sonuc.get("is_rotation", False),
            "diff_bgr"   : diff_bgr,
            "test_frame" : test_frame,
        }

    def _ssim_analiz(self, ref_bgr: np.ndarray, test_bgr: np.ndarray) -> dict:
        try:
            from skimage.metrics import structural_similarity as ssim
            skimage_ok = True
        except ImportError:
            skimage_ok = False

        h, w   = ref_bgr.shape[:2]
        test_r = cv2.resize(test_bgr, (w, h))

        ref_g  = cv2.cvtColor(ref_bgr, cv2.COLOR_BGR2GRAY)
        test_g = cv2.cvtColor(test_r,  cv2.COLOR_BGR2GRAY)

        clahe   = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        ref_eq  = clahe.apply(ref_g)
        test_eq = clahe.apply(test_g)
        ref_b   = cv2.GaussianBlur(ref_eq,  (7, 7), 0)
        test_b  = cv2.GaussianBlur(test_eq, (7, 7), 0)

        if skimage_ok:
            score, diff_img = ssim(ref_b, test_b, full=True, data_range=255)
            diff = (255 - (diff_img * 255).clip(0, 255)).astype(np.uint8)
        else:
            diff  = cv2.absdiff(ref_b, test_b)
            score = 1.0 - float(diff.mean()) / 255.0

        _, binary = cv2.threshold(diff, 40, 255, cv2.THRESH_BINARY)

        yellow = build_yellow_mask(ref_bgr)
        binary[yellow > 0] = 0
        tavan = int(h * 0.18)
        binary[:tavan, :] = 0

        k     = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        clean = cv2.morphologyEx(binary, cv2.MORPH_OPEN,  k)
        clean = cv2.morphologyEx(clean,  cv2.MORPH_CLOSE, k)

        contours, _ = cv2.findContours(clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        img_area = h * w
        nesneler = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 500:
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            if bw * bh > img_area * 0.40:
                continue
            cy_obj = y + bh // 2
            if cy_obj < h * 0.18:
                continue
            nesneler.append({
                "x": int(x), "y": int(y), "w": int(bw), "h": int(bh),
                "area": int(bw * bh), "cx": int(x+bw//2), "cy": int(cy_obj)
            })
        nesneler.sort(key=lambda o: o["area"], reverse=True)

        fg_ratio = float(np.sum(clean > 0)) / clean.size
        is_alert = len(nesneler) > 0 or fg_ratio > 0.05

        return {
            "is_alert"   : is_alert,
            "nesneler"   : nesneler,
            "fg_mask"    : clean,
            "fg_ratio"   : round(fg_ratio, 4),
            "is_rotation": False,
        }

    def _fark_gorseli(self, ref_bgr, test_bgr, fg_mask) -> np.ndarray:
        h, w   = ref_bgr.shape[:2]
        test_r = cv2.resize(test_bgr, (w, h))
        diff   = cv2.absdiff(ref_bgr, test_r)
        diff   = cv2.convertScaleAbs(diff, alpha=2.0)
        if fg_mask is not None:
            fg_r = cv2.resize(fg_mask, (w, h))
            if fg_r.ndim == 2:
                fg_bgr = cv2.cvtColor(fg_r, cv2.COLOR_GRAY2BGR)
                diff[fg_bgr[:, :, 0] > 0] = [0, 0, 200]
        return diff

# ──────────────────────────────────────────────────────────────────────────────
# UI YARDIMCI FONKSİYONLARI
# ──────────────────────────────────────────────────────────────────────────────

def put(img, text, pos, scale=0.52, color=None, thickness=1, bold=False):
    color = color or C["text"]
    font  = cv2.FONT_HERSHEY_SIMPLEX
    if bold:
        cv2.putText(img, text, pos, font, scale, (0, 0, 0), thickness + 3, cv2.LINE_AA)
    cv2.putText(img, text, pos, font, scale, color, thickness, cv2.LINE_AA)

def letterbox(frame: np.ndarray, w: int, h: int) -> np.ndarray:
    fh, fw  = frame.shape[:2]
    scale   = min(w / fw, h / fh)
    nw, nh  = max(1, int(fw * scale)), max(1, int(fh * scale))
    small   = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
    canvas  = np.full((h, w, 3), C["panel_bg"], dtype=np.uint8)
    x0, y0  = (w - nw) // 2, (h - nh) // 2
    canvas[y0:y0+nh, x0:x0+nw] = small
    return canvas

def compose_view(ref_bgr, test_bgr, fg_mask, diff_bgr,
                 nesneler, is_alert, score,
                 header_kw, footer_kw) -> np.ndarray:
    p1 = letterbox(ref_bgr, PANEL_W, PANEL_H)
    cv2.rectangle(p1, (0, 0), (PANEL_W-1, PANEL_H-1), C["accent"], 1)
    put(p1, "[REFERANS] Altin Tur (Normal)", (8, 22), scale=0.48, color=C["accent"], thickness=2)

    p2 = letterbox(test_bgr, PANEL_W, PANEL_H)
    brenk = C["uyari"] if is_alert else C["normal"]
    btxt  = ">>> UYARI <<<" if is_alert else "Normal"
    cv2.rectangle(p2, (0, 0), (PANEL_W-1, 30), (0, 0, 0), -1)
    put(p2, btxt, (8, 20), scale=0.58, color=brenk, thickness=2)
    put(p2, f"score={score:.3f}  det={len(nesneler)}",
        (PANEL_W - 185, 20), scale=0.38, color=C["subtext"])
    put(p2, "[CANLI / TEST]", (8, PANEL_H - 8), scale=0.38, color=C["subtext"])
    cv2.rectangle(p2, (0, 0), (PANEL_W-1, PANEL_H-1), brenk, 2)
    sh, sw = test_bgr.shape[:2]
    sx, sy = PANEL_W / sw, PANEL_H / sh
    det_colors = [(0, 0, 220), (0, 130, 255), (200, 0, 200), (0, 200, 200)]
    for i, obj in enumerate(nesneler[:4]):
        c = det_colors[i % len(det_colors)]
        cv2.rectangle(p2,
                      (int(obj["x"]*sx), int(obj["y"]*sy)),
                      (int((obj["x"]+obj["w"])*sx), int((obj["y"]+obj["h"])*sy)), c, 2)
        put(p2, f"#{i+1}", (int(obj["x"]*sx)+2, max(int(obj["y"]*sy)-4, 14)),
            scale=0.35, color=c)

    if fg_mask is not None:
        base3 = cv2.cvtColor(fg_mask, cv2.COLOR_GRAY2BGR) if fg_mask.ndim == 2 else fg_mask
        p3 = letterbox(base3, PANEL_W, PANEL_H)
    else:
        p3 = np.full((PANEL_H, PANEL_W, 3), C["panel_bg"], dtype=np.uint8)
    put(p3, "[MOG2 FG MASK]", (8, 22), scale=0.50, color=C["subtext"])
    put(p3, "Ref warmup'tan ogrenildi (v2)", (8, PANEL_H - 8), scale=0.34, color=C["freeze"])
    cv2.rectangle(p3, (0, 0), (PANEL_W-1, PANEL_H-1), C["header"], 1)

    if diff_bgr is not None:
        p4 = letterbox(diff_bgr, PANEL_W, PANEL_H)
    else:
        p4 = np.full((PANEL_H, PANEL_W, 3), C["panel_bg"], dtype=np.uint8)
    put(p4, "[FARK: REF vs CANLI]", (8, 22), scale=0.50, color=C["subtext"])
    cv2.rectangle(p4, (0, 0), (PANEL_W-1, PANEL_H-1), C["header"], 1)

    row1  = np.hstack([p1, p2])
    row2  = np.hstack([p3, p4])
    grid  = np.vstack([row1, row2])
    tw    = grid.shape[1]
    th    = HEADER_H + grid.shape[0] + FOOTER_H
    canvas = np.full((th, tw, 3), C["bg"], dtype=np.uint8)
    canvas[HEADER_H:HEADER_H + grid.shape[0]] = grid
    _draw_header(canvas, **header_kw)
    _draw_footer(canvas, **footer_kw)
    return canvas

def _draw_header(canvas, wp_id, wp_konum, is_alert, severity, tur_adi, gecen_sure):
    h, w = canvas.shape[:2]
    cv2.rectangle(canvas, (0, 0), (w, HEADER_H), C["header"], -1)
    cv2.line(canvas, (0, HEADER_H), (w, HEADER_H), C["accent"], 1)
    put(canvas, f"[IP14 v2] CANLI DEVRIYE — {tur_adi}",
        (12, 18), scale=0.55, color=C["accent"], thickness=2, bold=True)
    put(canvas, f"Ozgur Kotbas · Grup 03_Gama · BTU 2026 · {datetime.now().strftime('%H:%M:%S')}",
        (12, 36), scale=0.38, color=C["subtext"])
    durum_txt  = f">>> UYARI <<< [{severity}]" if is_alert else "Normal"
    durum_renk = C["uyari"] if is_alert else C["normal"]
    tw_sz = cv2.getTextSize(durum_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
    cx = (w - tw_sz[0]) // 2
    put(canvas, durum_txt, (cx, 32), scale=0.6, color=durum_renk, thickness=2, bold=True)
    put(canvas, f"{int(gecen_sure)}s", (w - 90, 20), scale=0.42, color=C["subtext"])
    put(canvas, f"{wp_konum[:28]}", (w - 330, 42), scale=0.38, color=C["text"])

def _draw_footer(canvas, wp_id, wp_idx, toplam_wp, uyari_sayisi, mog2_cnt, score, esik):
    h, w = canvas.shape[:2]
    y0   = h - FOOTER_H
    cv2.rectangle(canvas, (0, y0), (w, h), C["header"], -1)
    cv2.line(canvas, (0, y0), (w, y0), C["accent"], 1)
    bar_w   = w - 40
    bar_pct = (wp_idx + 1) / max(toplam_wp, 1)
    cv2.rectangle(canvas, (20, y0+6), (20+bar_w, y0+14), (50, 50, 70), -1)
    cv2.rectangle(canvas, (20, y0+6), (20+int(bar_w*bar_pct), y0+14), C["progress"], -1)
    put(canvas, f"WP {wp_idx+1}/{toplam_wp}  [N:Sonraki  Q:Cik  SPC:Duraklat  S:Ekran]",
        (20, y0+28), scale=0.38, color=C["subtext"])
    put(canvas, f"WP: {wp_id}", (20, y0+44), scale=0.44, color=C["accent"])
    put(canvas, f"MOG2: {mog2_cnt} nesne  Skor: {score:.3f}  Esik: {esik:.2f}",
        (140, y0+44), scale=0.40, color=C["text"])
    put(canvas, f"Uyari: {uyari_sayisi}",
        (w-130, y0+44), scale=0.44,
        color=C["uyari"] if uyari_sayisi > 0 else C["normal"])

# ──────────────────────────────────────────────────────────────────────────────
# PDF RAPORU
# ──────────────────────────────────────────────────────────────────────────────

def pdf_rapor_uret(ozet: dict, args: argparse.Namespace) -> Path | None:
    tur_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    deployment_dir = PROJECT_DIR / "outputs" / args.deployment_id
    deployment_dir.mkdir(parents=True, exist_ok=True)
    
    ozet_json = deployment_dir / f"ip14_tur_ozet_{tur_id}.json"
    klasik_json = OUT_DIR / f"ip14_tur_ozet_{tur_id}.json"
    
    with open(klasik_json, "w", encoding="utf-8") as f:
        json.dump(ozet, f, ensure_ascii=False, indent=2)
        
    shutil.copy2(str(klasik_json), str(ozet_json))
    
    print(f"\n[Kayıt] Tur özeti: {klasik_json}")
    try:
        from scripts.comms.ip13_pdf_rapor import pdf_uret
        return pdf_uret(ozet_path=klasik_json, out_dir=RAPOR_DIR)
    except Exception as e:
        print(f"  [UYARI] PDF üretilemedi: {e}")
        return None

# ──────────────────────────────────────────────────────────────────────────────
# WAYPOINT LİSTESİ
# ──────────────────────────────────────────────────────────────────────────────

def waypoint_listesi_yukle() -> list[dict]:
    waypoints = []
    if ETIKET_PATH.exists():
        try:
            with open(ETIKET_PATH, encoding="utf-8") as f:
                etiketler = json.load(f)
            for cift in etiketler.get("test_ciftleri", []):
                wp_id      = cift.get("waypoint_id", "WP?")
                ref_rel    = cift.get("referans", "")
                deg_rel    = cift.get("degisik", "")   # anomalili test karesi
                ref_path   = PROJECT_DIR / ref_rel if ref_rel else REF_DIR / f"{wp_id}.jpg"
                deg_path   = PROJECT_DIR / deg_rel if deg_rel else None
                tip        = cift.get("degisiklik_tipi", "bilinmiyor")
                saniye     = {"WP01": 5.0, "WP02": 15.0, "WP03": 25.0}.get(wp_id, 10.0)
                waypoints.append({
                    "id"             : wp_id,
                    "ref_path"       : Path(ref_path),
                    "deg_path"       : Path(deg_path) if deg_path else None,
                    "degisiklik_tipi": tip,
                    "aciklama"       : cift.get("aciklama", ""),
                    "video_saniye"   : saniye,
                    "konum"          : cift.get("konum", wp_id),
                })
        except Exception as e:
            print(f"  [UYARI] etiketler.json okunamadı: {e}")

    if not waypoints:
        print("  [BİLGİ] Varsayılan WP01/WP02/WP03 listesi kullanılıyor")
        for wp_id, saniye, konum in [
            ("WP01",  5.0, "Koridor baslangici — sol duvar"),
            ("WP02", 15.0, "Koridor ortasi"),
            ("WP03", 25.0, "Koridor sonu — makine yani"),
        ]:
            waypoints.append({
                "id"             : wp_id,
                "ref_path"       : REF_DIR / f"{wp_id}.jpg",
                "deg_path"       : None,
                "degisiklik_tipi": "bilinmiyor",
                "aciklama"       : "",
                "video_saniye"   : saniye,
                "konum"          : konum,
            })
    return waypoints

# ──────────────────────────────────────────────────────────────────────────────
# ANA DEVRIYE TURU (Evrensel v2)
# ──────────────────────────────────────────────────────────────────────────────

class TurYonetici:
    def __init__(self, args):
        self.args = args
        self.tur_id = datetime.now().strftime("%Y%m%d_%H%M")
        
        kaynak_yolu = getattr(self.args, "kaynak", ENGEL_VIDEO)
        try:
            if str(kaynak_yolu).isdigit():
                kaynak_yolu = int(kaynak_yolu)
        except:
            pass

        self.adaptoru = KaynakAdaptoru(kaynak_yolu)
        if getattr(self.adaptoru, "cap", None) is None and getattr(self.adaptoru, "img", None) is None:
            print(f"[HATA] Kaynak açılamadı: {kaynak_yolu}")
            return
            
        print(f"Kaynak tipi: {self.adaptoru.tip}")
        
        deployment_id = getattr(self.args, "deployment_id", "default")
        self.mqtt = PatrolMQTTYayinci(
            broker=self.args.broker, 
            port=self.args.port,
            offline_mod=self.args.mqtt_offline,
            deployment_id=deployment_id
        )
        self.analizci = WaypointAnalizci(self.adaptoru)

    def calistir(self):
        tur_baslangic = datetime.now()
        waypoints = waypoint_listesi_yukle()
        wp_sonuclari = []
        uyari_sayisi = 0
        
        for wp_idx, wp in enumerate(waypoints):
            wp_id    = wp["id"]
            ref_path = wp["ref_path"]
            ref_bgr = cv2.imread(str(ref_path)) if ref_path.exists() else np.full((480, 640, 3), (20, 60, 20), dtype=np.uint8)
            
            deg_path      = wp.get("deg_path")
            test_statik   = cv2.imread(str(deg_path)) if deg_path and Path(deg_path).exists() else None
            test_saniye   = wp["video_saniye"] if test_statik is None and self.adaptoru._is_video else None
            
            sonuc = self.analizci.waypoint_isle(ref_bgr, test_saniye, test_statik, warmup_n=self.args.warmup)
            is_alert = sonuc["is_alert"]
            if is_alert: uyari_sayisi += 1
            
            kanit_dosyasi = OUT_DIR / f"{wp_id}_canli_kare.jpg"
            cv2.imwrite(str(kanit_dosyasi), sonuc["test_frame"])
            
            self.mqtt.yayinla({
                "type": "patrol_alert",
                "waypoint": wp_id,
                "is_alert": is_alert,
                "ts": datetime.now().isoformat()
            })
            
            wp_sonuclari.append({
                "waypoint_id": wp_id, "is_alert": is_alert, 
                "karar_aciklama": f"MOG2: {len(sonuc.get('nesneler', []))} nesne"
            })
            
        if self.adaptoru: self.adaptoru.release()
        if self.mqtt: self.mqtt.kapat()
        
        return {
            "tur_adi": self.tur_id,
            "sure_saniye": round((datetime.now() - tur_baslangic).total_seconds(), 1),
            "toplam_wp": len(waypoints),
            "uyari_sayisi": uyari_sayisi,
            "normal_sayisi": len(waypoints) - uyari_sayisi,
            "wp_sonuclari": wp_sonuclari,
            "kaynak": str(self.args.kaynak)
        }

# ──────────────────────────────────────────────────────────────────────────────
# TUR SONU EKRANI
# ──────────────────────────────────────────────────────────────────────────────

def tur_sonu_ekrani_goster(pencere_adi: str, ozet: dict, pdf_path: Path | None):
    w, h = PANEL_W * 2, PANEL_H * 2 + HEADER_H + FOOTER_H
    canvas = np.full((h, w, 3), C["bg"], dtype=np.uint8)
    cv2.rectangle(canvas, (0, 0), (w, HEADER_H+10), C["header"], -1)
    put(canvas, "IP14 v2 — CANLI TUR TAMAMLANDI!", (20, 36),
        scale=0.85, color=C["accent"], thickness=2, bold=True)

    y = HEADER_H + 40
    for metin, renk in [
        (f"Tur Adi : {ozet['tur_adi']}", C["text"]),
        (f"Kaynak  : {ozet.get('kaynak','?')}", C["subtext"]),
        (f"Sure    : {ozet['sure_saniye']} saniye", C["subtext"]),
        (f"Toplam WP : {ozet['toplam_wp']}", C["text"]),
        (f"UYARI     : {ozet['uyari_sayisi']}", C["uyari"] if ozet["uyari_sayisi"]>0 else C["normal"]),
        (f"Normal    : {ozet['normal_sayisi']}", C["normal"]),
        ("", C["text"]),
    ]:
        put(canvas, metin, (60, y), scale=0.60, color=renk)
        y += 36

    put(canvas, "Waypoint Ozeti:", (60, y), scale=0.55, color=C["accent"])
    y += 28
    for wp in ozet.get("wp_sonuclari", []):
        sembol = "[UYARI]" if wp["is_alert"] else "[NORMAL]"
        renk   = C["uyari"] if wp["is_alert"] else C["normal"]
        put(canvas, f"  {wp['waypoint_id']}: {sembol} {wp['severity']} — {wp['karar_aciklama'][:50]}",
            (60, y), scale=0.44, color=renk)
        y += 22

    y += 10
    if pdf_path and pdf_path.exists():
        put(canvas, f"PDF Rapor : {pdf_path.name}", (60, y), scale=0.48, color=C["normal"])
    else:
        put(canvas, "PDF Rapor : Uretilemedi (pip install fpdf2)", (60, y),
            scale=0.44, color=C["uyari"])
    y += 26
    put(canvas, f"Ciktilar  : {OUT_DIR}", (60, y), scale=0.40, color=C["subtext"])
    y += 44
    put(canvas, "[ Q/ESC: Cik  |  5 saniye sonra otomatik kapanir ]",
        (60, y), scale=0.48, color=C["subtext"])

    cv2.imshow(pencere_adi, canvas)
    t0 = time.time()
    while time.time() - t0 < 5.0:
        if cv2.waitKey(100) & 0xFF in (ord('q'), 27):
            break
    cv2.destroyAllWindows()


# ──────────────────────────────────────────────────────────────────────────────
# GİRİŞ NOKTASI
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="IP14 v2: Canlı Devriye Turu Simülasyonu — Evrensel Kaynak"
    )
    parser.add_argument(
        "--kaynak", default=str(ENGEL_VIDEO),
        help=(
            "Görüntü kaynağı (varsayılan: engel.mp4)\n"
            "  Video dosyası : data/raw_videos/engel.mp4\n"
            "  RTSP stream   : rtsp://192.168.1.10:554/stream\n"
            "  Webcam        : 0\n"
            "  Statik görüntü: data/ip8_test/WP01_degisik.jpg"
        )
    )
    parser.add_argument("--gorselsiz", action="store_true",
                        help="OpenCV penceresi açma")
    parser.add_argument("--mqtt-offline", action="store_true",
                        help="Gerçek MQTT broker kapali, json a yaz (varsayılan: offline)")
    parser.add_argument("--hiz", type=float, default=3.0,
                        help="Waypoint bekleme süresi (sn, varsayılan: 3.0)")
    parser.add_argument("--warmup", type=int, default=MOG2_WARMUP_N,
                        help=f"MOG2 warmup iterasyonu (varsayılan: {MOG2_WARMUP_N})")
    parser.add_argument("--pdf-atlama", action="store_true",
                        help="PDF üretimini atla")
    parser.add_argument("--broker", default="localhost")
    parser.add_argument("--port", type=int, default=1883)
    parser.add_argument("--deployment-id", default=CONFIG.get("deployment", {}).get("default_id", "default"),
                        help="Deployment ID (varsayılan: default)")
    args = parser.parse_args()

    # Kaynak: int mi string mi?
    try:
        args.kaynak = int(args.kaynak)
    except (ValueError, TypeError):
        pass

    print("=" * 65)
    print("  IP14 v2: EVRENSEL CANLI TUR — Ozgur Kotbas")
    print("  Grup 03_Gama  |  BTU  |  Staj 2026")
    print("=" * 65)
    print(f"  Kaynak      : {args.kaynak}")
    print(f"  Warmup Modu : REFERANS KAREDEN ({args.warmup} iter) — v2 duzeltmesi")
    print(f"  MQTT        : {'OFFLINE' if args.mqtt_offline else 'CANLI'}")
    print(f"  Deployment  : {args.deployment_id}")
    print("=" * 65)

    yonetici = TurYonetici(args)
    ozet = yonetici.calistir()

    if not ozet:
        sys.exit(1)

    pdf_path = None
    if not args.pdf_atlama:
        print("\n" + "=" * 65)
        print("  PDF RAPORU URETILIYOR (IP13)...")
        print("=" * 65)
        pdf_path = pdf_rapor_uret(ozet, args)

    print("\n" + "=" * 65)
    print("  IP14 v2 TAMAMLANDI")
    print("=" * 65)
    print(f"  Tur         : {ozet['tur_adi']}")
    print(f"  Kaynak      : {ozet.get('kaynak','?')}")
    print(f"  Sure        : {ozet['sure_saniye']} saniye")
    print(f"  Waypoint    : {ozet['toplam_wp']}")
    print(f"  Uyari       : {ozet['uyari_sayisi']}")
    print(f"  Normal      : {ozet['normal_sayisi']}")
    if pdf_path:
        print(f"  PDF         : {pdf_path}")
    print(f"  Ciktilar    : {OUT_DIR}")
    print("=" * 65)

    if not args.gorselsiz:
        pencere_adi = "IP14 v2 — CANLI DEVRIYE  |  Ozgur Kotbas"
        tur_sonu_ekrani_goster(pencere_adi, ozet, pdf_path)

    print(f"\n  [HATIRLATMA] IP14 takip tablosunu guncelle:")
    print(f"  | IP14 | ✅ | {datetime.now().strftime('%d.%m.%Y')} | "
          f"v2 evrensel kaynak: {ozet['uyari_sayisi']}/{ozet['toplam_wp']} uyari, "
          f"WP03 ref-warmup duzeltmesi, MQTT offline, PDF uretildi |")


if __name__ == "__main__":
    main()
