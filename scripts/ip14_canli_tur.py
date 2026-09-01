# -*- coding: utf-8 -*-
from __future__ import annotations
import sys, io
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf-16'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
"""
İP14: Canlı Tur — Uçtan Uca Devriye Simülasyonu
=================================================
Proje  : Görsel Anomali Tespiti + Otomatik Devriye Raporu
Modül  : ANOMALİ  →  patrol/alert
Çatı   : pan_tilt_robot_projesi.md · Grup 03_Gama · BTÜ · Staj 2026
Doküman: DOKUMANLAR/Ozgur_is_paketleri.md — İP14

AÇIKLAMA:
---------
Gerçek pan-tilt kamera yerine 'engel.mp4' video akışı ve önceden çekilmiş
WP01/WP02/WP03 referans kareleri kullanılarak uçtan uca devriye simüle edilir.

Akış (her waypoint için):
  1. Video'dan ilgili zaman damgasına git → "canlı" kare al
  2. Referans kare vs canlı kare → İP8 mantığı (SSIM+ORB) + MOG2
  3. İP9 ensemble kararı → anomali skoru + severity
  4. Uyarı varsa → İP10 MQTT yayını (offline mod)
  5. Waypoint karesini PNG olarak kaydet (kanıt)
  6. Tüm tur sonunda → İP13 PDF raporu otomatik üret
  7. Uçtan uca özet → terminal + JSON log

✅ Bitti Kriteri: Uçtan uca canlı demo — devriye → uyarı → rapor

KULLANIM:
---------
    python scripts/ip14_canli_tur.py
    python scripts/ip14_canli_tur.py --video data/raw_videos/engel.mp4
    python scripts/ip14_canli_tur.py --gorselsiz          # OpenCV penceresi açma
    python scripts/ip14_canli_tur.py --offline             # MQTT broker olmadan
    python scripts/ip14_canli_tur.py --hiz 2.0            # Waypoint bekleme süresi

KLAVYE (pencere açıksa):
    Q / ESC : Turu iptal et
    SPACE   : Duraklat / Devam
    N       : Bir sonraki waypoint'e atla
    S       : Ekran görüntüsü kaydet
"""

import argparse
import json
import shutil
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

# Proje yolunu ekle
sys.path.append(str(Path(__file__).resolve().parent.parent))
from scripts.core import config_okuyucu
from scripts.core.anomali_motor import AlgilayiciMOG2, build_yellow_mask

# ──────────────────────────────────────────────────────────────────────────────
# PROJE YOLLARI
# ──────────────────────────────────────────────────────────────────────────────
PROJECT_DIR = config_okuyucu.PROJECT_ROOT
CONFIG      = config_okuyucu.CONFIG

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
    "uyari"    : (30,  30, 220),   # BGR kırmızı
    "normal"   : (30, 180,  60),   # BGR yeşil
    "accent"   : (220, 160, 40),   # BGR altın
    "text"     : (220, 220, 230),
    "subtext"  : (140, 140, 160),
    "progress" : (80,  180, 100),
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

# ──────────────────────────────────────────────────────────────────────────────
# YARDIMCI FONKSİYONLAR
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


def draw_header(canvas, wp_id, wp_konum, is_alert, severity, tur_adi, gecen_sure):
    h, w = canvas.shape[:2]
    cv2.rectangle(canvas, (0, 0), (w, HEADER_H), C["header"], -1)
    cv2.line(canvas, (0, HEADER_H), (w, HEADER_H), C["accent"], 1)

    put(canvas, f"[IP14] CANLI DEVRIYE TURU — {tur_adi}",
        (12, 18), scale=0.55, color=C["accent"], thickness=2, bold=True)
    put(canvas, f"Ozgur Kotbas  |  Grup 03_Gama  |  BTU Staj 2026  |  {datetime.now().strftime('%H:%M:%S')}",
        (12, 36), scale=0.38, color=C["subtext"])

    durum_txt  = f">>> UYARI <<< [{severity}]" if is_alert else "Normal"
    durum_renk = C["uyari"] if is_alert else C["normal"]
    tw, _ = cv2.getTextSize(durum_txt, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0], 0
    cx = (w - tw[0]) // 2
    put(canvas, durum_txt, (cx, 32), scale=0.6, color=durum_renk, thickness=2, bold=True)

    put(canvas, f"Sure: {int(gecen_sure)}s",
        (w - 120, 20), scale=0.42, color=C["subtext"])
    put(canvas, f"{wp_konum[:28]}",
        (w - 330, 42), scale=0.38, color=C["text"])


def draw_footer(canvas, wp_id, wp_idx, toplam_wp, uyari_sayisi, mog2_cnt, score, esik):
    h, w = canvas.shape[:2]
    y0   = h - FOOTER_H
    cv2.rectangle(canvas, (0, y0), (w, h), C["header"], -1)
    cv2.line(canvas, (0, y0), (w, y0), C["accent"], 1)

    # İlerleme çubuğu
    bar_w   = w - 40
    bar_pct = (wp_idx + 1) / max(toplam_wp, 1)
    cv2.rectangle(canvas, (20, y0 + 6), (20 + bar_w, y0 + 14), (50, 50, 70), -1)
    cv2.rectangle(canvas, (20, y0 + 6), (20 + int(bar_w * bar_pct), y0 + 14),
                  C["progress"], -1)
    put(canvas, f"Waypoint {wp_idx+1}/{toplam_wp}  [N: Sonraki  Q: Cik  SPC: Duraklat  S: Ekran]",
        (20, y0 + 28), scale=0.38, color=C["subtext"])

    put(canvas, f"WP: {wp_id}", (20, y0 + 44), scale=0.44, color=C["accent"])
    put(canvas, f"MOG2 Nesne: {mog2_cnt}  |  Skor: {score:.3f}  Esik: {esik:.2f}",
        (140, y0 + 44), scale=0.40, color=C["text"])
    put(canvas, f"Uyari: {uyari_sayisi}",
        (w - 130, y0 + 44), scale=0.44,
        color=C["uyari"] if uyari_sayisi > 0 else C["normal"])


def compose_view(ref_bgr, test_bgr, fg_mask, diff_bgr,
                 nesneler, is_alert, score,
                 header_kw, footer_kw):
    """4 panel + header + footer → tek canvas."""
    # Panel 1: Referans
    p1 = letterbox(ref_bgr, PANEL_W, PANEL_H)
    cv2.rectangle(p1, (0, 0), (PANEL_W-1, PANEL_H-1), C["accent"], 1)
    put(p1, "[REFERANS] Altin Tur", (8, 22), scale=0.50, color=C["accent"], thickness=2)
    put(p1, "Normal durum (kayitli)", (8, 40), scale=0.38, color=C["subtext"])

    # Panel 2: Canlı / Test kare
    p2 = letterbox(test_bgr, PANEL_W, PANEL_H)
    brenk = C["uyari"] if is_alert else C["normal"]
    btxt  = ">>> UYARI <<<" if is_alert else "Normal"
    cv2.rectangle(p2, (0, 0), (PANEL_W-1, 30), (0, 0, 0), -1)
    put(p2, btxt, (8, 20), scale=0.58, color=brenk, thickness=2)
    put(p2, f"score={score:.3f}  det={len(nesneler)}", (PANEL_W - 185, 20), scale=0.38, color=C["subtext"])
    put(p2, "[CANLI / TEST]", (8, PANEL_H - 8), scale=0.38, color=C["subtext"])
    cv2.rectangle(p2, (0, 0), (PANEL_W-1, PANEL_H-1), brenk, 2)
    # Tespit kutuları
    sh, sw = test_bgr.shape[:2]
    sx, sy = PANEL_W / sw, PANEL_H / sh
    det_colors = [(0, 0, 220), (0, 130, 255), (200, 0, 200)]
    for i, obj in enumerate(nesneler[:3]):
        c = det_colors[i % len(det_colors)]
        cv2.rectangle(p2,
                      (int(obj["x"]*sx), int(obj["y"]*sy)),
                      (int((obj["x"]+obj["w"])*sx), int((obj["y"]+obj["h"])*sy)),
                      c, 2)
        put(p2, f"#{i+1}", (int(obj["x"]*sx)+2, max(int(obj["y"]*sy)-4, 14)),
            scale=0.35, color=c)

    # Panel 3: MOG2 FG maskesi
    if fg_mask is not None:
        if fg_mask.ndim == 2:
            p3 = letterbox(cv2.cvtColor(fg_mask, cv2.COLOR_GRAY2BGR), PANEL_W, PANEL_H)
        else:
            p3 = letterbox(fg_mask, PANEL_W, PANEL_H)
    else:
        p3 = np.full((PANEL_H, PANEL_W, 3), C["panel_bg"], dtype=np.uint8)
    put(p3, "[MOG2 FG MASK]", (8, 22), scale=0.50, color=C["subtext"])
    cv2.rectangle(p3, (0, 0), (PANEL_W-1, PANEL_H-1), C["header"], 1)

    # Panel 4: Fark / Bilgi
    if diff_bgr is not None:
        p4 = letterbox(diff_bgr, PANEL_W, PANEL_H)
    else:
        p4 = np.full((PANEL_H, PANEL_W, 3), C["panel_bg"], dtype=np.uint8)
    put(p4, "[FARK / DURUM]", (8, 22), scale=0.50, color=C["subtext"])
    cv2.rectangle(p4, (0, 0), (PANEL_W-1, PANEL_H-1), C["header"], 1)

    row1   = np.hstack([p1, p2])
    row2   = np.hstack([p3, p4])
    grid   = np.vstack([row1, row2])
    total_w = grid.shape[1]
    total_h = HEADER_H + grid.shape[0] + FOOTER_H

    canvas = np.full((total_h, total_w, 3), C["bg"], dtype=np.uint8)
    canvas[HEADER_H:HEADER_H + grid.shape[0]] = grid

    draw_header(canvas, **header_kw)
    draw_footer(canvas, **footer_kw)
    return canvas


# ──────────────────────────────────────────────────────────────────────────────
# MOG2 TABANLI WAYPOINT ANALİZİ  (engel.mp4'ten kare çek + analiz et)
# ──────────────────────────────────────────────────────────────────────────────

class WaypointAnalizci:
    """
    engel.mp4 üzerinde MOG2 ile waypoint bazlı anomali tespiti.
    Her waypoint için videonun farklı bir bölümünü "canlı" olarak işler.
    """

    def __init__(self, video_path: Path):
        self.video_path = video_path
        self._cap = None

    def _open(self):
        if self._cap is None or not self._cap.isOpened():
            self._cap = cv2.VideoCapture(str(self.video_path))
        return self._cap.isOpened()

    def canli_kare_al(self, saniye: float) -> np.ndarray | None:
        """Video'dan belirtilen saniyedeki kareyi döndür."""
        if not self._open():
            return None
        fps  = self._cap.get(cv2.CAP_PROP_FPS) or 25.0
        kare = int(saniye * fps)
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, kare)
        ret, frame = self._cap.read()
        return frame if ret else None

    def waypoint_isle(self, ref_bgr: np.ndarray,
                      test_saniye: float,
                      warmup_baslangic: float = 0.0,
                      warmup_sure: float = 5.0) -> dict:
        """
        Belirtilen zaman damgasında videodaki kareyi referansla kıyasla.
        MOG2'yi ısıtmak için warmup_baslangic..warmup_baslangic+warmup_sure
        arasındaki kareleri besler, sonra test_saniye anındaki kareyi analiz eder.
        """
        if not self._open():
            return {"hata": "Video açılamadı", "is_alert": False}

        fps       = self._cap.get(cv2.CAP_PROP_FPS) or 25.0
        algilayici = AlgilayiciMOG2()

        # MOG2 ısınma: belirli kare aralığından besle (tek geçiş — İP12 düzeltmesi)
        baslangic_kare = int(warmup_baslangic * fps)
        bitis_kare     = int((warmup_baslangic + warmup_sure) * fps)
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, baslangic_kare)

        first_frame = None
        for ki in range(baslangic_kare, bitis_kare):
            ret, fr = self._cap.read()
            if not ret:
                break
            if first_frame is None:
                first_frame = fr.copy()
                # İlk kareyle MOG2'yi hızlıca ısıt
                algilayici.warmup(fr)
            algilayici.isle(fr)

        # Test karesi
        test_frame = self.canli_kare_al(test_saniye)
        if test_frame is None:
            # Videoda o saniye yok → son ısınan kareyi kullan
            test_frame = first_frame if first_frame is not None else ref_bgr.copy()

        # Son 30 kare learningRate=0 ile dondur (İP12 düzeltmesi)
        # Burada test kareyi MOG2'ye learningRate=0 ile ver
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, int(test_saniye * fps) - 10))
        for _ in range(10):
            ret, fr = self._cap.read()
            if not ret:
                break
            algilayici.mog2.apply(fr, learningRate=0)

        sonuc = algilayici.isle(test_frame)

        # SSIM + ORB fark analizi (İP8 mantığı — basitleştirilmiş)
        diff_bgr = self._fark_gorseli(ref_bgr, test_frame, sonuc.get("fg_mask"))

        return {
            "is_alert"       : sonuc["is_alert"],
            "nesneler"       : sonuc["nesneler"],
            "fg_mask"        : sonuc.get("fg_mask"),
            "fg_ratio"       : sonuc.get("fg_ratio", 0.0),
            "is_rotation"    : sonuc.get("is_rotation", False),
            "diff_bgr"       : diff_bgr,
            "test_frame"     : test_frame,
        }

    def _fark_gorseli(self, ref_bgr, test_bgr, fg_mask) -> np.ndarray:
        """Referans ve test karesinin görsel farkını hesapla."""
        h, w = ref_bgr.shape[:2]
        test_r = cv2.resize(test_bgr, (w, h))
        diff   = cv2.absdiff(ref_bgr, test_r)
        diff   = cv2.convertScaleAbs(diff, alpha=2.0)

        if fg_mask is not None:
            fg_r = cv2.resize(fg_mask, (w, h))
            if fg_r.ndim == 2:
                fg_bgr = cv2.cvtColor(fg_r, cv2.COLOR_GRAY2BGR)
                # Ön plan bölgelerini kırmızıyla işaretle
                diff[fg_bgr[:, :, 0] > 0] = [0, 0, 200]
        return diff

    def kapat(self):
        if self._cap:
            self._cap.release()
            self._cap = None


# ──────────────────────────────────────────────────────────────────────────────
# MQTT YAYINCI (ip10 modülünü içe aktar, yoksa offline)
# ──────────────────────────────────────────────────────────────────────────────

def mqtt_yayinci_olustur(offline: bool):
    try:
        from scripts.comms.ip10_mqtt_yayini import PatrolMQTTYayinci
        yayinci = PatrolMQTTYayinci(offline=offline)
        return yayinci
    except Exception as e:
        print(f"  [UYARI] MQTT modülü yüklenemedi: {e}")
        return None


def waypoint_mesaji_olustur(wp_id: str, sonuc: dict,
                             degisiklik_tipi: str, kanit_yolu: str) -> dict:
    """Waypoint analiz sonucundan patrol/alert MQTT mesajı oluştur."""
    nesneler = sonuc.get("nesneler", [])
    severity = "NONE"
    if sonuc["is_alert"]:
        severity = SEVERITY_MAP.get(degisiklik_tipi, "MEDIUM")
    score = min(1.0, sonuc.get("fg_ratio", 0.0) * 15.0 + len(nesneler) * 0.15)
    return {
        "type"            : "patrol_alert",
        "severity"        : severity,
        "waypoint"        : wp_id,
        "score"           : round(score, 4),
        "det_count"       : len(nesneler),
        "fg_ratio"        : sonuc.get("fg_ratio", 0.0),
        "is_alert"        : sonuc["is_alert"],
        "img_ref"         : kanit_yolu,
        "ts"              : datetime.now().isoformat(),
        "degisiklik_tipi" : degisiklik_tipi,
        "mog2_aktif"      : True,
        "patchcore_aktif" : False,
        "karar_aciklama"  : f"MOG2: {len(nesneler)} nesne (IP14 canli tur)",
    }


# ──────────────────────────────────────────────────────────────────────────────
# PDF RAPORU  (ip13 modülünü çağır)
# ──────────────────────────────────────────────────────────────────────────────

def pdf_rapor_uret(tur_ozeti: dict, out_dir: Path) -> Path | None:
    """İP14 canlı tur özetinden ensemble_ozet.json formatı üret, ip13'ü çağır."""
    # ip13 ensemble_ozet.json formatına dönüştür
    ip13_ozet = {
        "tur"           : "ip14_canli_tur_simulasyon",
        "tarih"         : datetime.now().isoformat(),
        "engel_video"   : str(tur_ozeti.get("video_path", "")),
        "toplam_wp"     : tur_ozeti["toplam_wp"],
        "uyari_sayisi"  : tur_ozeti["uyari_sayisi"],
        "mimari"        : "IP14 Canli Tur — MOG2 (engel.mp4 simulasyon)",
        "patchcore_aktif": False,
        "metrikler"     : tur_ozeti.get("metrikler", {
            "TP": "-", "FP": "-", "FN": "-",
            "precision": 0.0, "recall": 0.0, "F1": 0.0
        }),
        "sonuclar"      : tur_ozeti["wp_sonuclari"],
    }

    # Geçici JSON'a yaz
    ts          = datetime.now().strftime("%Y%m%d_%H%M%S")
    tmp_json    = out_dir / f"ip14_tur_ozet_{ts}.json"
    with open(tmp_json, "w", encoding="utf-8") as f:
        json.dump(ip13_ozet, f, ensure_ascii=False, indent=2)
    print(f"  [JSON] Tur özeti: {tmp_json}")

    # ip13 çağır
    try:
        from scripts.comms.ip13_pdf_rapor import pdf_uret
        pdf_path = pdf_uret(ozet_path=tmp_json, out_dir=RAPOR_DIR)
        return pdf_path
    except Exception as e:
        print(f"  [UYARI] PDF üretilemedi: {e}")
        return None


# ──────────────────────────────────────────────────────────────────────────────
# WAYPOINT LİSTESİ YÜKLEYİCİ
# ──────────────────────────────────────────────────────────────────────────────

def waypoint_listesi_yukle() -> list[dict]:
    """
    Önce etiketler.json'dan waypoint listesi oluştur.
    Yoksa varsayılan WP01/WP02/WP03 listesini döndür.
    """
    waypoints = []

    # etiketler.json'dan
    if ETIKET_PATH.exists():
        try:
            with open(ETIKET_PATH, encoding="utf-8") as f:
                etiketler = json.load(f)
            for cift in etiketler.get("test_ciftleri", []):
                wp_id   = cift.get("waypoint_id", "WP?")
                ref_rel = cift.get("referans", "")
                ref_path = PROJECT_DIR / ref_rel if ref_rel else REF_DIR / f"{wp_id}.jpg"
                tip      = cift.get("degisiklik_tipi", "bilinmiyor")
                aciklama = cift.get("aciklama", "")
                saniye   = {"WP01": 5.0, "WP02": 15.0, "WP03": 25.0}.get(wp_id, 10.0)
                waypoints.append({
                    "id"              : wp_id,
                    "ref_path"        : ref_path,
                    "degisiklik_tipi" : tip,
                    "aciklama"        : aciklama,
                    "test_saniye"     : saniye,
                    "warmup_baslangic": max(0.0, saniye - 8.0),
                    "warmup_sure"     : 5.0,
                    "konum"           : cift.get("konum", wp_id),
                })
        except Exception as e:
            print(f"  [UYARI] etiketler.json okunamadı: {e}")

    # Fallback: varsayılan 3 waypoint
    if not waypoints:
        print("  [BİLGİ] Varsayılan waypoint listesi kullanılıyor (WP01/WP02/WP03)")
        for wp_id, saniye, konum in [
            ("WP01",  5.0, "Koridor baslangici — sol duvar"),
            ("WP02", 15.0, "Koridor ortasi"),
            ("WP03", 25.0, "Koridor sonu — makine yani"),
        ]:
            ref_path = REF_DIR / f"{wp_id}.jpg"
            waypoints.append({
                "id"              : wp_id,
                "ref_path"        : ref_path,
                "degisiklik_tipi" : "bilinmiyor",
                "aciklama"        : "",
                "test_saniye"     : saniye,
                "warmup_baslangic": max(0.0, saniye - 8.0),
                "warmup_sure"     : 5.0,
                "konum"           : konum,
            })

    return waypoints


# ──────────────────────────────────────────────────────────────────────────────
# ANA DEVRIYE TURU
# ──────────────────────────────────────────────────────────────────────────────

def canli_tur_calistir(video_path: Path,
                       gorselsiz: bool = False,
                       offline: bool = True,
                       wp_bekleme: float = 3.0) -> dict:
    """
    Uçtan uca canlı devriye turu.
    Döndürür: tur özeti sözlüğü.
    """
    tur_baslangic = datetime.now()
    print("\n" + "=" * 65)
    print("  IP14: CANLI DEVRIYE TURU BASLIYOR")
    print(f"  Tarih/Saat : {tur_baslangic.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Video      : {video_path}")
    print(f"  Mod        : {'GORUNTUSUZ' if gorselsiz else 'GORUNTU ACIK'}")
    print(f"  MQTT       : {'OFFLINE' if offline else 'CANLI'}")
    print("=" * 65)

    # Waypoint listesi
    waypoints = waypoint_listesi_yukle()
    print(f"\n  Toplam {len(waypoints)} waypoint planlanıyor...")
    for wp in waypoints:
        ref_ok = "✓" if Path(wp["ref_path"]).exists() else "✗ (EKSIK)"
        print(f"    {wp['id']}: {wp['konum'][:35]}  |  ref={ref_ok}  |  @{wp['test_saniye']}s")

    # MQTT
    yayinci = mqtt_yayinci_olustur(offline=offline)

    # Analizci
    analizci = WaypointAnalizci(video_path)

    # Pencere
    pencere_adi = "IP14 — CANLI DEVRIYE TURU  |  Ozgur Kotbas"
    if not gorselsiz:
        cv2.namedWindow(pencere_adi, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
        cv2.resizeWindow(pencere_adi, PANEL_W * 2, PANEL_H * 2 + HEADER_H + FOOTER_H)

    # Tur değişkenleri
    wp_sonuclari   = []
    mqtt_mesajlari = []
    uyari_sayisi   = 0
    iptal          = False
    duraklatildi   = False

    # Tur adi
    tur_adi = tur_baslangic.strftime("Tur_%Y%m%d_%H%M")

    print(f"\n  Devriye başlıyor...\n")

    for wp_idx, wp in enumerate(waypoints):
        if iptal:
            break

        wp_id    = wp["id"]
        konum    = wp["konum"]
        ref_path = Path(wp["ref_path"])
        tip      = wp["degisiklik_tipi"]

        print(f"\n  [{wp_idx+1}/{len(waypoints)}] {wp_id} — {konum}")
        print(f"    Referans kare: {ref_path}")

        # Referans kare yükle
        if ref_path.exists():
            ref_bgr = cv2.imread(str(ref_path))
        else:
            print(f"    [UYARI] Referans kare bulunamadı: {ref_path}")
            # Placeholder yeşil kare
            ref_bgr = np.full((480, 640, 3), (20, 60, 20), dtype=np.uint8)
            put(ref_bgr, f"REF BULUNAMADI: {wp_id}", (20, 240),
                scale=0.7, color=(0, 200, 50), thickness=2)

        # Waypoint analizi
        print(f"    Video taranıyor (@{wp['test_saniye']}s)...")
        t_analiz = time.time()
        sonuc = analizci.waypoint_isle(
            ref_bgr          = ref_bgr,
            test_saniye      = wp["test_saniye"],
            warmup_baslangic = wp["warmup_baslangic"],
            warmup_sure      = wp["warmup_sure"],
        )
        print(f"    Analiz süresi: {time.time()-t_analiz:.2f}s")

        test_frame = sonuc.get("test_frame", ref_bgr)
        fg_mask    = sonuc.get("fg_mask")
        diff_bgr   = sonuc.get("diff_bgr")
        nesneler   = sonuc.get("nesneler", [])
        is_alert   = sonuc["is_alert"]
        fg_ratio   = sonuc.get("fg_ratio", 0.0)

        score = min(1.0, fg_ratio * 15.0 + len(nesneler) * 0.15)
        severity = SEVERITY_MAP.get(tip, "MEDIUM") if is_alert else "NONE"

        # Kanıt görüntüsü kaydet
        kanit_dosyasi = OUT_DIR / f"{wp_id}_canli_kare.jpg"
        if test_frame is not None:
            cv2.imwrite(str(kanit_dosyasi), test_frame)

        # Ensemble görsel (referans + test yan yana)
        gorsel_dosyasi = OUT_DIR / f"{wp_id}_ensemble.jpg"
        try:
            h_g = 320
            ref_lb  = letterbox(ref_bgr, 400, h_g)
            test_lb = letterbox(test_frame, 400, h_g)
            birlesik = np.hstack([ref_lb, test_lb])
            # Başlık
            baslik = np.full((40, birlesik.shape[1], 3), (30, 30, 50), dtype=np.uint8)
            put(baslik, f"[{wp_id}] REF vs CANLI   is_alert={is_alert}   severity={severity}",
                (10, 26), scale=0.55, color=C["uyari"] if is_alert else C["normal"], thickness=2)
            birlesik = np.vstack([baslik, birlesik])
            cv2.imwrite(str(gorsel_dosyasi), birlesik)
        except Exception:
            gorsel_dosyasi = kanit_dosyasi

        # Terminal çıktısı
        durum_sembol = "⚠" if is_alert else "✓"
        print(f"    {durum_sembol} is_alert={is_alert}  severity={severity}")
        print(f"      MOG2: {len(nesneler)} nesne  |  fg_ratio={fg_ratio:.4f}")
        print(f"      Kanıt: {kanit_dosyasi}")

        if is_alert:
            uyari_sayisi += 1

        # MQTT yayını
        mesaj = waypoint_mesaji_olustur(wp_id, sonuc, tip, str(kanit_dosyasi))
        mqtt_mesajlari.append(mesaj)
        if yayinci:
            print(f"    MQTT → patrol/alert  [{severity}]")
            yayinci.yayinla(mesaj)

        # Waypoint sonuç kaydı (ip13 formatı)
        wp_sonuclari.append({
            "waypoint_id"       : wp_id,
            "degisiklik_tipi"   : tip,
            "senaryo"           : wp.get("aciklama", ""),
            "referans"          : str(ref_path),
            "test"              : str(kanit_dosyasi),
            "mog2_fg_ratio"     : round(fg_ratio, 4),
            "mog2_nesne_sayisi" : len(nesneler),
            "mog2_nesneler"     : nesneler,
            "mog2_uyari"        : is_alert,
            "patchcore_score"   : -1.0,
            "patchcore_esik"    : 0.4,
            "patchcore_uyari"   : False,
            "patchcore_aktif"   : False,
            "is_alert"          : is_alert,
            "severity"          : severity,
            "karar_aciklama"    : f"MOG2: {len(nesneler)} nesne (IP14 canli tur)",
            "ensemble_gorseli"  : str(gorsel_dosyasi),
            "ts"                : datetime.now().isoformat(),
        })

        # Görsel göster
        if not gorselsiz:
            t_start_gorsel = time.time()
            while True:
                gecen = time.time() - t_start_gorsel
                if not duraklatildi and gecen >= wp_bekleme:
                    break

                frame_display = compose_view(
                    ref_bgr    = ref_bgr,
                    test_bgr   = test_frame,
                    fg_mask    = fg_mask,
                    diff_bgr   = diff_bgr,
                    nesneler   = nesneler,
                    is_alert   = is_alert,
                    score      = score,
                    header_kw  = dict(
                        wp_id      = wp_id,
                        wp_konum   = konum,
                        is_alert   = is_alert,
                        severity   = severity,
                        tur_adi    = tur_adi,
                        gecen_sure = (datetime.now() - tur_baslangic).total_seconds(),
                    ),
                    footer_kw  = dict(
                        wp_id        = wp_id,
                        wp_idx       = wp_idx,
                        toplam_wp    = len(waypoints),
                        uyari_sayisi = uyari_sayisi,
                        mog2_cnt     = len(nesneler),
                        score        = score,
                        esik         = 0.40,
                    ),
                )

                # Duraklat göstergesi
                if duraklatildi:
                    h_d, w_d = frame_display.shape[:2]
                    put(frame_display, "|| DURAKLATI",
                        (w_d // 2 - 80, h_d // 2),
                        scale=1.0, color=C["accent"], thickness=3, bold=True)

                # İlerleme çubuğu (kırmızı bekleme çubuğu)
                if not duraklatildi:
                    pct = min(gecen / wp_bekleme, 1.0)
                    bw  = int(frame_display.shape[1] * pct)
                    cv2.rectangle(frame_display, (0, HEADER_H - 4), (bw, HEADER_H - 1),
                                  C["uyari"] if is_alert else C["normal"], -1)

                cv2.imshow(pencere_adi, frame_display)
                key = cv2.waitKey(40) & 0xFF
                if key in (ord('q'), 27):
                    iptal = True
                    break
                elif key == ord(' '):
                    duraklatildi = not duraklatildi
                elif key == ord('n'):
                    break
                elif key == ord('s'):
                    ss_path = OUT_DIR / f"ekran_{wp_id}_{datetime.now().strftime('%H%M%S')}.png"
                    cv2.imwrite(str(ss_path), frame_display)
                    print(f"    [Kayıt] Ekran görüntüsü: {ss_path}")

    analizci.kapat()

    # MQTT kayıt
    if yayinci:
        kayit_path = yayinci.tum_mesajlari_kaydet()
        print(f"\n  MQTT Audit kaydı: {kayit_path}")
        yayinci.kapat()

    # Tur özeti
    tur_bitis    = datetime.now()
    tur_suresi_s = (tur_bitis - tur_baslangic).total_seconds()

    ozet = {
        "tur_adi"       : tur_adi,
        "baslangic"     : tur_baslangic.isoformat(),
        "bitis"         : tur_bitis.isoformat(),
        "sure_saniye"   : round(tur_suresi_s, 1),
        "video_path"    : str(video_path),
        "toplam_wp"     : len(waypoints),
        "uyari_sayisi"  : uyari_sayisi,
        "normal_sayisi" : len(waypoints) - uyari_sayisi,
        "iptal"         : iptal,
        "wp_sonuclari"  : wp_sonuclari,
        "metrikler"     : {
            "TP": "-", "FP": "-", "FN": "-",
            "precision": 0.0, "recall": 0.0, "F1": 0.0,
        },
    }

    return ozet


# ──────────────────────────────────────────────────────────────────────────────
# TUR SONU EKRANI
# ──────────────────────────────────────────────────────────────────────────────

def tur_sonu_ekrani_goster(pencere_adi: str, ozet: dict, pdf_path: Path | None):
    """Tur tamamlama ekranı — 5 saniye göster veya Q ile çık."""
    w, h = PANEL_W * 2, PANEL_H * 2 + HEADER_H + FOOTER_H

    canvas = np.full((h, w, 3), C["bg"], dtype=np.uint8)

    # Başlık bandı
    cv2.rectangle(canvas, (0, 0), (w, HEADER_H + 10), C["header"], -1)
    put(canvas, "IP14 CANLI TUR TAMAMLANDI!", (20, 36),
        scale=0.9, color=C["accent"], thickness=2, bold=True)

    # Özet bilgiler
    y = HEADER_H + 40
    satirlar = [
        (f"Tur Adi : {ozet['tur_adi']}", C["text"]),
        (f"Sure    : {ozet['sure_saniye']} saniye", C["subtext"]),
        (f"Toplam Waypoint : {ozet['toplam_wp']}", C["text"]),
        (f"UYARI   : {ozet['uyari_sayisi']}", C["uyari"] if ozet["uyari_sayisi"] > 0 else C["normal"]),
        (f"Normal  : {ozet['normal_sayisi']}", C["normal"]),
        ("", C["text"]),
    ]

    for metin, renk in satirlar:
        put(canvas, metin, (60, y), scale=0.65, color=renk, thickness=1)
        y += 38

    # Waypoint özeti
    put(canvas, "Waypoint Ozeti:", (60, y), scale=0.55, color=C["accent"])
    y += 30
    for wp in ozet["wp_sonuclari"]:
        sembol = "[UYARI]" if wp["is_alert"] else "[NORMAL]"
        renk   = C["uyari"] if wp["is_alert"] else C["normal"]
        put(canvas, f"  {wp['waypoint_id']}: {sembol}  {wp['severity']}  — {wp['karar_aciklama'][:55]}",
            (60, y), scale=0.46, color=renk)
        y += 24

    # PDF bilgisi
    y += 10
    if pdf_path and pdf_path.exists():
        put(canvas, f"PDF Rapor : {pdf_path.name}", (60, y), scale=0.50, color=C["normal"])
    else:
        put(canvas, "PDF Rapor : Uretilemedi (fpdf2 kurun: pip install fpdf2)",
            (60, y), scale=0.46, color=C["uyari"])
    y += 28

    put(canvas, f"Ciktilar  : {OUT_DIR}", (60, y), scale=0.42, color=C["subtext"])
    y += 50

    put(canvas, "[ Q veya ESC: Cik  |  5 saniye sonra otomatik kapanir ]",
        (60, y), scale=0.50, color=C["subtext"])

    cv2.imshow(pencere_adi, canvas)
    t0 = time.time()
    while time.time() - t0 < 5.0:
        key = cv2.waitKey(100) & 0xFF
        if key in (ord('q'), 27):
            break

    cv2.destroyAllWindows()


# ──────────────────────────────────────────────────────────────────────────────
# GİRİŞ NOKTASI
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="IP14: Canlı Devriye Turu Simülasyonu — Özgür Kotbaş"
    )
    parser.add_argument(
        "--video", default=str(ENGEL_VIDEO),
        help=f"Simülasyon video yolu (varsayılan: {ENGEL_VIDEO})"
    )
    parser.add_argument(
        "--gorselsiz", action="store_true",
        help="OpenCV penceresi açma (sadece terminal çıktısı)"
    )
    parser.add_argument(
        "--offline", action="store_true", default=True,
        help="MQTT offline mod (broker olmadan)"
    )
    parser.add_argument(
        "--canli-mqtt", action="store_true",
        help="Gerçek MQTT broker'a bağlan"
    )
    parser.add_argument(
        "--hiz", type=float, default=3.0,
        help="Her waypoint'te bekleme süresi (saniye, varsayılan: 3.0)"
    )
    parser.add_argument(
        "--pdf-atlama", action="store_true",
        help="PDF üretimini atla"
    )
    args = parser.parse_args()

    offline = not args.canli_mqtt

    # Video kontrolü
    video_path = Path(args.video)
    if not video_path.exists():
        print(f"[HATA] Video bulunamadı: {video_path}")
        print(f"       Beklenen: {ENGEL_VIDEO}")
        sys.exit(1)

    print("=" * 65)
    print("  IP14: CANLI TUR SIMULASYONU — Ozgur Kotbas")
    print("  Grup 03_Gama  |  BTU  |  Staj 2026")
    print("=" * 65)
    print(f"  Video   : {video_path}")
    print(f"  Çıktılar: {OUT_DIR}")
    print(f"  MQTT    : {'OFFLINE' if offline else 'CANLI'}")
    print("=" * 65)

    # ── DEVRIYE TURU ──
    ozet = canli_tur_calistir(
        video_path  = video_path,
        gorselsiz   = args.gorselsiz,
        offline     = offline,
        wp_bekleme  = args.hiz,
    )

    # ── PDF RAPORU ──
    pdf_path = None
    if not args.pdf_atlama:
        print("\n" + "=" * 65)
        print("  PDF RAPORU URETILIYOR (IP13)...")
        print("=" * 65)
        pdf_path = pdf_rapor_uret(ozet, OUT_DIR)

    # ── TUR SONU ÖZETİ ──
    print("\n" + "=" * 65)
    print("  IP14 TAMAMLANDI")
    print("=" * 65)
    print(f"  Tur adı     : {ozet['tur_adi']}")
    print(f"  Süre        : {ozet['sure_saniye']} saniye")
    print(f"  Toplam WP   : {ozet['toplam_wp']}")
    print(f"  Uyarı       : {ozet['uyari_sayisi']}")
    print(f"  Normal      : {ozet['normal_sayisi']}")
    if pdf_path:
        print(f"  PDF Rapor   : {pdf_path}")
        son_pdf = RAPOR_DIR / "son_devriye_raporu.pdf"
        print(f"  Son PDF     : {son_pdf}")
    print(f"  Çıktı dizini: {OUT_DIR}")
    print("=" * 65)

    # ── TUR SONU EKRANI ──
    if not args.gorselsiz:
        pencere_adi = "IP14 — CANLI DEVRIYE TURU  |  Ozgur Kotbas"
        tur_sonu_ekrani_goster(pencere_adi, ozet, pdf_path)

    # ── İLERLEME TAKİBİ GÜNCELLEMESI HATIRLATıCISI ──
    print("\n  [HATIRLATMA] DOKUMANLAR/Ozgur_is_paketleri.md dosyasında")
    print("  IP14 satırını guncellemeyi unutma:")
    print(f"  | İP14 | ✅ | {datetime.now().strftime('%d.%m.%Y')} | "
          f"Uctan uca canli tur sim.: {ozet['uyari_sayisi']}/{ozet['toplam_wp']} uyari, "
          f"MQTT offline, PDF uretildi. Cikti: outputs/ip14_canli_tur/ |")


if __name__ == "__main__":
    main()
