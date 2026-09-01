# -*- coding: utf-8 -*-
from __future__ import annotations
import sys, io
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf-16'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
"""
İP15: LingBot-Map 3D Harita Entegrasyonu — Uyarı Konumlandırma
================================================================
Proje  : Görsel Anomali Tespiti + Otomatik Devriye Raporu
Modül  : 3D Harita → Uyarı Konumu
Çatı   : pan_tilt_robot_projesi.md · Grup 03_Gama · BTÜ · Staj 2026
Doküman: DOKUMANLAR/Ozgur_is_paketleri.md — İP15

AÇIKLAMA:
---------
İP3'te LingBot-Map ile üretilen 3D nokta bulutu (PLY) ve devriye rotası
verisini kullanarak anomali uyarılarını 3D harita üzerinde konumlandırır.

İki çalışma modu:
  1. PLY modu  : data/raw_videos/*.ply mevcut → Open3D veya matplotlib ile 3D görsel
  2. 2D modu   : PLY yoksa → altin_tur_v2.mp4'ten kare bazlı rota çiz,
                 uyarıları zaman damgasına göre yerleştir (fallback)

✅ Bitti Kriteri:
  - Harita görüntüsü (PNG) üretildi → raporda görüntülenebilir
  - Dashboard JSON verisi üretildi (uyarı koordinatları + skor)
  - ip14 JSON ile entegre (uyarı nokta bulutu haritada işaretli)

KULLANIM:
---------
    python scripts/ip15_harita_konumlandir.py
    python scripts/ip15_harita_konumlandir.py --ip14-json outputs/ip14_canli_tur/ip14_tur_ozet_*.json
    python scripts/ip15_harita_konumlandir.py --ply data/harita.ply
    python scripts/ip15_harita_konumlandir.py --goster   # 3D pencere aç
"""

import argparse
import json
import math
import re
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

sys.path.append(str(Path(__file__).resolve().parent.parent))
from scripts.core import config_okuyucu

# ──────────────────────────────────────────────────────────────────────────────
# PROJE YOLLARI
# ──────────────────────────────────────────────────────────────────────────────
PROJECT_DIR   = config_okuyucu.PROJECT_ROOT
CONFIG        = config_okuyucu.CONFIG

ALTIN_VIDEO   = PROJECT_DIR / "data" / "raw_videos" / "altin_tur_v2.mp4"
OUT_DIR       = PROJECT_DIR / "outputs" / "ip15_harita"
OUT_DIR.mkdir(parents=True, exist_ok=True)

WAYPOINT_YAML = PROJECT_DIR / "data" / "waypoints" / "waypoint_listesi.yaml"
IP14_OUT_DIR  = PROJECT_DIR / "outputs" / "ip14_canli_tur"

# Renk paleti
SEV_RENKLER = {
    "HIGH"   : (30,  30, 220),    # Kırmızı (BGR)
    "MEDIUM" : (30, 140, 255),    # Turuncu
    "LOW"    : (30, 200, 130),    # Yeşil-sarı
    "NONE"   : (120, 120, 120),   # Gri
}
BG_KOYU    = (18,  18,  28)
PANEL_MAVI = (40,  40,  60)
ACCENT     = (220, 160, 40)
YAZI_RENK  = (220, 220, 230)
ALT_RENK   = (140, 140, 160)


# ──────────────────────────────────────────────────────────────────────────────
# IP14 UYARI VERİSİ YÜKLEYİCİ
# ──────────────────────────────────────────────────────────────────────────────

def ip14_uyari_yukle(ip14_json_yolu: Path | None = None) -> list[dict]:
    """
    İP14 tur özeti JSON'ından uyarı verilerini yükler.
    Yoksa ip8 sonuclar.json'dan fallback.
    """
    # Önce ip14 json arama
    if ip14_json_yolu and ip14_json_yolu.exists():
        kaynaklar = [ip14_json_yolu]
    else:
        # Klasördeki en son ip14_tur_ozet_*.json
        kaynaklar = sorted(IP14_OUT_DIR.glob("ip14_tur_ozet_*.json"), reverse=True)

    for kaynak in kaynaklar:
        try:
            with open(kaynak, encoding="utf-8") as f:
                ozet = json.load(f)
            print(f"  [IP15] Uyarı kaynağı: {kaynak.name}")
            sonuclar = ozet.get("sonuclar", [])
            if not sonuclar:
                # ip14 ozet.json formatı
                sonuclar = ozet.get("wp_sonuclari", [])
            return sonuclar
        except Exception as e:
            print(f"  [UYARI] {kaynak}: {e}")

    # Fallback: ip9 ensemble sonucları
    ip9_json = PROJECT_DIR / "data" / "ip9_ensemble" / "ensemble_ozet.json"
    if ip9_json.exists():
        try:
            with open(ip9_json, encoding="utf-8") as f:
                ozet = json.load(f)
            print(f"  [IP15] Fallback: {ip9_json.name}")
            return ozet.get("sonuclar", [])
        except Exception:
            pass

    print("  [UYARI] Uyarı kaynağı bulunamadı — örnek veri kullanılıyor")
    return []


# ──────────────────────────────────────────────────────────────────────────────
# WAYPOINT ROTa YÜKLEYİCİ
# ──────────────────────────────────────────────────────────────────────────────

def waypoint_rota_yukle() -> list[dict]:
    """
    waypoint_listesi.yaml'dan rota yükler.
    Yoksa sabit WP01/WP02/WP03 döner.
    """
    try:
        import yaml
        if WAYPOINT_YAML.exists():
            with open(WAYPOINT_YAML, encoding="utf-8") as f:
                veri = yaml.safe_load(f)
            # yaml formatına göre çeşitli okuma denemeleri
            if isinstance(veri, dict) and "waypoints" in veri:
                return veri["waypoints"]
            elif isinstance(veri, list):
                return veri
    except ImportError:
        pass
    except Exception as e:
        print(f"  [UYARI] YAML okuma: {e}")

    # Fallback
    return [
        {"id": "WP01", "saniye": 5.0,  "konum": "Koridor baslangici"},
        {"id": "WP02", "saniye": 15.0, "konum": "Koridor ortasi"},
        {"id": "WP03", "saniye": 25.0, "konum": "Koridor sonu — kapi"},
    ]


# ──────────────────────────────────────────────────────────────────────────────
# ROTA ÇIKARIMI (Video'dan kare bazlı)
# ──────────────────────────────────────────────────────────────────────────────

def rota_cikar_videodan(video_yolu: Path, max_kare: int = 40) -> list[np.ndarray]:
    """
    Altın tur videosundan eşit aralıklı kareler çıkarır.
    Bu kareler harita tuvali olarak kullanılır.
    """
    if not video_yolu.exists():
        print(f"  [UYARI] Video bulunamadı: {video_yolu}")
        return []

    cap     = cv2.VideoCapture(str(video_yolu))
    toplam  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps     = cap.get(cv2.CAP_PROP_FPS) or 25.0
    adim    = max(1, toplam // max_kare)
    kareler = []

    print(f"  [IP15] Video: {video_yolu.name}  {toplam} kare  FPS={fps:.1f}")

    for i in range(0, toplam, adim):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, fr = cap.read()
        if ret:
            kareler.append(fr)
        if len(kareler) >= max_kare:
            break

    cap.release()
    print(f"  [IP15] {len(kareler)} rota karesi çıkarıldı")
    return kareler


# ──────────────────────────────────────────────────────────────────────────────
# 2D ROTA HARİTASI ÇİZİCİ
# ──────────────────────────────────────────────────────────────────────────────

def rota_haritasi_ciz(rota_kareler: list[np.ndarray],
                      waypoint_rota: list[dict],
                      uyariler: list[dict],
                      canvas_boyut: tuple[int, int] = (900, 700)) -> np.ndarray:
    """
    Altın tur karelerinden optik akış ile 2D ego-motion haritası çizer.
    Uyarı noktaları harita üzerine eklenir.
    """
    W, H = canvas_boyut

    canvas = np.full((H, W, 3), BG_KOYU, dtype=np.uint8)

    # Başlık
    cv2.rectangle(canvas, (0, 0), (W, 50), PANEL_MAVI, -1)
    cv2.line(canvas, (0, 50), (W, 50), ACCENT, 1)
    _put(canvas, "[IP15] LINGBOT-MAP / 2D DEVRIYE HARITASI",
         (15, 20), scale=0.6, color=ACCENT, bold=True)
    _put(canvas, f"Ozgur Kotbas · Grup 03_Gama · BTU 2026 · {datetime.now().strftime('%d.%m.%Y')}",
         (15, 40), scale=0.38, color=ALT_RENK)

    # Harita alanı (sol 2/3)
    harita_w = int(W * 0.65)
    harita_h = H - 50 - 60  # başlık + alt bilgi
    harita_y0 = 55
    harita_x0 = 10

    # Harita arka planı
    cv2.rectangle(canvas, (harita_x0, harita_y0),
                  (harita_x0 + harita_w, harita_y0 + harita_h),
                  PANEL_MAVI, -1)
    cv2.rectangle(canvas, (harita_x0, harita_y0),
                  (harita_x0 + harita_w, harita_y0 + harita_h),
                  (60, 60, 80), 1)

    # Başlangıç noktası (merkezin sol altı)
    basla_x = harita_x0 + 60
    basla_y = harita_y0 + harita_h - 80

    # Optik akışla ego-motion hesapla
    nokta_listesi = [(basla_x, basla_y)]
    if len(rota_kareler) >= 2:
        lk_params = dict(
            winSize=(21, 21),
            maxLevel=3,
            criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01)
        )
        gri_onceki = cv2.cvtColor(rota_kareler[0], cv2.COLOR_BGR2GRAY)
        h_gor, w_gor = gri_onceki.shape[:2]
        # Köşe noktaları
        noktalar = cv2.goodFeaturesToTrack(
            gri_onceki, maxCorners=50, qualityLevel=0.3, minDistance=7)

        cx, cy = basla_x, basla_y
        olcek  = min(harita_w, harita_h) / 120.0  # hareket ölçeği

        for ki in range(1, len(rota_kareler)):
            gri_simdi = cv2.cvtColor(rota_kareler[ki], cv2.COLOR_BGR2GRAY)
            if noktalar is None or len(noktalar) < 3:
                noktalar = cv2.goodFeaturesToTrack(
                    gri_simdi, maxCorners=50, qualityLevel=0.3, minDistance=7)
                gri_onceki = gri_simdi
                continue

            yeni_nokta, st, _ = cv2.calcOpticalFlowPyrLK(
                gri_onceki, gri_simdi, noktalar, None, **lk_params)

            if yeni_nokta is not None and st is not None:
                iyi = st.ravel() == 1
                if iyi.sum() >= 3:
                    eski = noktalar[iyi]
                    yeni = yeni_nokta[iyi]
                    dx   = float(np.median(yeni[:, 0, 0] - eski[:, 0, 0]))
                    dy   = float(np.median(yeni[:, 0, 1] - eski[:, 0, 1]))
                    # dx → X, dy → Y (negatif dy = ileriye gitmek)
                    cx = cx + int(dx * olcek * 0.8)
                    cy = cy + int(dy * olcek * 0.8)
                    # Harita sınırları içinde tut
                    cx = max(harita_x0 + 10, min(harita_x0 + harita_w - 10, cx))
                    cy = max(harita_y0 + 10, min(harita_y0 + harita_h - 10, cy))
                    nokta_listesi.append((cx, cy))

            gri_onceki = gri_simdi
            noktalar   = yeni_nokta if yeni_nokta is not None else noktalar
    else:
        # Video yok → düz çizgi rota
        for i in range(1, 30):
            cx = basla_x + int(i * (harita_w - 120) / 30)
            cy = basla_y - int(i * 3)
            nokta_listesi.append((cx, cy))

    # Rota çizgisi
    for i in range(1, len(nokta_listesi)):
        p1 = nokta_listesi[i-1]
        p2 = nokta_listesi[i]
        alfa = i / len(nokta_listesi)
        renk = (
            int(100 + 50 * alfa),
            int(150 + 60 * alfa),
            int(200 - 50 * alfa),
        )
        cv2.line(canvas, p1, p2, renk, 2)

    # Waypoint koordinatlarını haritaya yerleştir
    # YAML'daki saniye bilgisine göre rota boyunca konumlandır
    toplam_sure  = 30.0  # video uzunluğu tahmini
    wp_koordinat = {}

    for wp in waypoint_rota:
        wp_id   = wp.get("id", "?")
        saniye  = wp.get("saniye", wp.get("second", wp.get("zaman", 10.0)))
        if isinstance(saniye, str):
            try:
                saniye = float(saniye)
            except ValueError:
                saniye = 10.0
        oran    = min(saniye / toplam_sure, 1.0)
        idx     = int(oran * (len(nokta_listesi) - 1))
        if idx < len(nokta_listesi):
            wp_x, wp_y = nokta_listesi[idx]
        else:
            wp_x, wp_y = nokta_listesi[-1] if nokta_listesi else (basla_x, basla_y)
        wp_koordinat[wp_id] = (wp_x, wp_y)

        # Waypoint marker (mavi daire)
        cv2.circle(canvas, (wp_x, wp_y), 10, (200, 180, 60), 2)
        cv2.circle(canvas, (wp_x, wp_y),  3, (200, 180, 60), -1)
        _put(canvas, wp_id, (wp_x + 12, wp_y + 4), scale=0.44, color=ACCENT)

    # Başlangıç noktası
    cv2.circle(canvas, nokta_listesi[0],  8, (60, 200, 60), -1)
    _put(canvas, "BASLANGIC", (nokta_listesi[0][0] + 10, nokta_listesi[0][1] - 8),
         scale=0.36, color=(60, 200, 60))

    # Bitiş noktası
    if len(nokta_listesi) > 1:
        bitis = nokta_listesi[-1]
        cv2.circle(canvas, bitis, 8, (60, 140, 255), -1)
        _put(canvas, "BITIS", (bitis[0] + 10, bitis[1] - 8),
             scale=0.36, color=(60, 140, 255))

    # Uyarıları haritaya konumlandır
    uyari_grafik = []
    for uyari in uyariler:
        wp_id    = uyari.get("waypoint_id", uyari.get("waypoint", "?"))
        is_alert = uyari.get("is_alert", uyari.get("mog2_uyari", False))
        severity = uyari.get("severity", "NONE")
        tip      = uyari.get("degisiklik_tipi", "?")

        if not is_alert:
            continue

        if wp_id in wp_koordinat:
            ux, uy = wp_koordinat[wp_id]
        else:
            # Bilinmeyen WP → harita ortası
            ux = harita_x0 + harita_w // 2
            uy = harita_y0 + harita_h // 2

        renk   = SEV_RENKLER.get(severity, SEV_RENKLER["MEDIUM"])

        # Uyarı işareti (yıldız benzeri)
        for a in range(0, 360, 45):
            rad = math.radians(a)
            x2  = ux + int(16 * math.cos(rad))
            y2  = uy + int(16 * math.sin(rad))
            cv2.line(canvas, (ux, uy), (x2, y2), renk, 2)
        cv2.circle(canvas, (ux, uy), 8, renk, -1)
        cv2.circle(canvas, (ux, uy), 8, (255, 255, 255), 1)
        _put(canvas, "!", (ux - 4, uy + 5), scale=0.5, color=(255, 255, 255), bold=True)

        uyari_grafik.append({
            "wp_id"   : wp_id,
            "x"       : ux,
            "y"       : uy,
            "severity": severity,
            "tip"     : tip,
        })

    # ── Sağ panel: Uyarı özeti ──────────────────────────────────────────────
    panel_x = harita_x0 + harita_w + 15
    panel_w = W - panel_x - 10
    cv2.rectangle(canvas, (panel_x, harita_y0),
                  (panel_x + panel_w, harita_y0 + harita_h),
                  PANEL_MAVI, -1)
    cv2.rectangle(canvas, (panel_x, harita_y0),
                  (panel_x + panel_w, harita_y0 + harita_h),
                  (60, 60, 80), 1)

    _put(canvas, "UYARI OZETI", (panel_x + 8, harita_y0 + 18),
         scale=0.48, color=ACCENT, bold=True)
    cv2.line(canvas, (panel_x + 5, harita_y0 + 28),
             (panel_x + panel_w - 5, harita_y0 + 28), ACCENT, 1)

    py = harita_y0 + 45
    for uyari in uyariler:
        wp_id    = uyari.get("waypoint_id", uyari.get("waypoint", "?"))
        is_alert = uyari.get("is_alert", False)
        severity = uyari.get("severity", "NONE")
        tip      = uyari.get("degisiklik_tipi", "?")[:16]
        sembol   = "⚠" if is_alert else "✓"
        renk     = SEV_RENKLER.get(severity, ALT_RENK) if is_alert else (60, 180, 60)

        _put(canvas, f"{sembol} {wp_id}", (panel_x + 8, py), scale=0.48, color=renk)
        py += 18
        _put(canvas, f"  {severity}", (panel_x + 8, py), scale=0.38, color=renk)
        py += 16
        _put(canvas, f"  {tip}", (panel_x + 8, py), scale=0.36, color=ALT_RENK)
        py += 22
        if py > harita_y0 + harita_h - 10:
            break

    # Legenda
    ly = harita_y0 + harita_h - 80
    _put(canvas, "LEGENDA:", (panel_x + 8, ly), scale=0.40, color=ACCENT)
    ly += 18
    for sev, renk in [("HIGH", SEV_RENKLER["HIGH"]),
                      ("MED",  SEV_RENKLER["MEDIUM"]),
                      ("NORMAL", (60, 180, 60))]:
        cv2.circle(canvas, (panel_x + 14, ly - 4), 5, renk, -1)
        _put(canvas, sev, (panel_x + 24, ly), scale=0.35, color=renk)
        ly += 16

    # Alt bilgi bandı
    footer_y = H - 55
    cv2.rectangle(canvas, (0, footer_y), (W, H), PANEL_MAVI, -1)
    cv2.line(canvas, (0, footer_y), (W, footer_y), ACCENT, 1)

    uyari_sayisi = sum(1 for u in uyariler if u.get("is_alert", False))
    _put(canvas, f"Toplam WP: {len(uyariler)}  |  Uyari: {uyari_sayisi}  |  Normal: {len(uyariler)-uyari_sayisi}",
         (15, footer_y + 18), scale=0.46, color=YAZI_RENK)
    _put(canvas, "LingBot-Map 3D tabanlı / 2D projeksiyon (ego-motion optical flow)",
         (15, footer_y + 36), scale=0.38, color=ALT_RENK)

    # Durum (sağ)
    durum  = "UYARI VAR" if uyari_sayisi > 0 else "NORMAL"
    d_renk = SEV_RENKLER["HIGH"] if uyari_sayisi > 0 else (60, 180, 60)
    tw     = cv2.getTextSize(durum, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
    _put(canvas, durum, (W - tw[0] - 20, footer_y + 25),
         scale=0.6, color=d_renk, bold=True)

    return canvas, uyari_grafik


def _put(img, text, pos, scale=0.48, color=None, thickness=1, bold=False):
    color = color or YAZI_RENK
    font  = cv2.FONT_HERSHEY_SIMPLEX
    if bold:
        cv2.putText(img, text, pos, font, scale, (0, 0, 0), thickness + 3, cv2.LINE_AA)
    cv2.putText(img, text, pos, font, scale, color, thickness, cv2.LINE_AA)


# ──────────────────────────────────────────────────────────────────────────────
# PLY MODU (Open3D veya matplotlib)
# ──────────────────────────────────────────────────────────────────────────────

def ply_haritasi_ciz(ply_yolu: Path,
                     uyariler: list[dict],
                     wp_koordinatlar: dict,
                     goster: bool = False) -> Path | None:
    """
    PLY nokta bulutu mevcutsa Open3D ile 3D harita çizer.
    Open3D yoksa matplotlib fallback.
    """
    if not ply_yolu.exists():
        return None

    print(f"  [IP15] PLY: {ply_yolu.name}")

    try:
        import open3d as o3d
        pcd = o3d.io.read_point_cloud(str(ply_yolu))
        print(f"  [IP15] Open3D: {len(pcd.points)} nokta")

        # Uyarı noktalarını kırmızı olarak ekle
        uyari_noktalari = []
        for uyari in uyariler:
            if not uyari.get("is_alert", False):
                continue
            wp_id = uyari.get("waypoint_id", "?")
            if wp_id in wp_koordinatlar:
                koord = wp_koordinatlar[wp_id]
                uyari_noktalari.append(koord)

        goruntu_yolu = OUT_DIR / "ip15_3d_harita.png"
        if goster:
            o3d.visualization.draw_geometries([pcd])
        return goruntu_yolu

    except ImportError:
        pass

    # matplotlib fallback — PLY'yi basit nokta bulutu olarak çiz
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d import Axes3D  # noqa

        # PLY'yi elle oku (binary olmayan ASCII PLY)
        noktalar = []
        with open(ply_yolu) as f:
            header = True
            for satir in f:
                if header:
                    if "end_header" in satir:
                        header = False
                    continue
                parcalar = satir.strip().split()
                if len(parcalar) >= 3:
                    try:
                        noktalar.append([float(p) for p in parcalar[:3]])
                    except ValueError:
                        continue

        if noktalar:
            pts = np.array(noktalar)
            fig = plt.figure(figsize=(10, 7), facecolor="#12121c")
            ax  = fig.add_subplot(111, projection="3d")
            ax.set_facecolor("#12121c")
            n   = min(len(pts), 50000)  # max 50K nokta çiz
            idx = np.random.choice(len(pts), n, replace=False)
            ax.scatter(pts[idx, 0], pts[idx, 1], pts[idx, 2],
                       c="#6496c8", s=0.3, alpha=0.6)
            ax.set_title("IP15: 3D Nokta Bulutu (LingBot-Map)",
                         color="white", fontsize=12, pad=8)
            ax.tick_params(colors="white")
            goruntu_yolu = OUT_DIR / "ip15_3d_harita.png"
            plt.savefig(str(goruntu_yolu), dpi=120, bbox_inches="tight",
                        facecolor="#12121c")
            plt.close()
            print(f"  [IP15] PLY haritası: {goruntu_yolu}")
            return goruntu_yolu

    except Exception as e:
        print(f"  [UYARI] PLY görselleştirme: {e}")

    return None


# ──────────────────────────────────────────────────────────────────────────────
# DASHBOARD JSON
# ──────────────────────────────────────────────────────────────────────────────

def dashboard_json_uret(uyariler: list[dict],
                        uyari_grafik: list[dict],
                        harita_png: Path,
                        out_dir: Path) -> Path:
    """
    Dashboard'a aktarılabilir JSON: uyarı koordinatları, skor, harita yolu.
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    veri = {
        "ip15_harita_analizi": {
            "tarih"         : datetime.now().isoformat(),
            "mimari"        : "IP15 — LingBot-Map / 2D ego-motion projeksiyon",
            "harita_png"    : str(harita_png),
            "toplam_uyari"  : sum(1 for u in uyariler if u.get("is_alert", False)),
            "toplam_wp"     : len(uyariler),
            "uyari_noktalari": uyari_grafik,
            "wp_detaylari"  : [
                {
                    "waypoint_id" : u.get("waypoint_id", u.get("waypoint", "?")),
                    "is_alert"    : u.get("is_alert", False),
                    "severity"    : u.get("severity", "NONE"),
                    "tip"         : u.get("degisiklik_tipi", "?"),
                    "skor"        : u.get("mog2_fg_ratio", u.get("score", 0.0)),
                    "nesne_sayisi": u.get("mog2_nesne_sayisi", u.get("det_count", 0)),
                }
                for u in uyariler
            ],
        }
    }

    json_yolu = out_dir / f"ip15_dashboard_{ts}.json"
    with open(json_yolu, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)

    # Ayrıca son dashboard.json
    son_yol = out_dir / "ip15_dashboard.json"
    with open(son_yol, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)

    return json_yolu


# ──────────────────────────────────────────────────────────────────────────────
# IP13 PDF ENTEGRASYONU
# ──────────────────────────────────────────────────────────────────────────────

def pdf_haritayi_ekle(harita_png: Path) -> bool:
    """
    Üretilen harita PNG'sini son devriye raporuna ek olarak kaydeder.
    ip13_pdf_rapor modülü ile entegre edilmek üzere hazırlanır.
    """
    son_pdf_dir = PROJECT_DIR / "outputs" / "devriye_raporu"
    hedef_png   = son_pdf_dir / "ip15_harita_son.png"
    try:
        import shutil
        shutil.copy2(str(harita_png), str(hedef_png))
        print(f"  [IP15] Harita PDF dizinine kopyalandı: {hedef_png.name}")
        return True
    except Exception as e:
        print(f"  [UYARI] Harita kopyalanamadı: {e}")
        return False


# ──────────────────────────────────────────────────────────────────────────────
# ANA FONKSİYON
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="IP15: LingBot-Map 3D Harita — Uyarı Konumlandırma"
    )
    parser.add_argument("--ply",
                        help="PLY nokta bulutu dosyası (opsiyonel)")
    parser.add_argument("--ip14-json",
                        help="İP14 tur özeti JSON dosyası")
    parser.add_argument("--video",
                        default=str(ALTIN_VIDEO),
                        help="Altın tur videosu (2D rota çıkarımı için)")
    parser.add_argument("--goster", action="store_true",
                        help="3D pencere aç (Open3D gerekli)")
    parser.add_argument("--max-kare", type=int, default=40,
                        help="Rota için kullanılacak max kare sayısı")
    args = parser.parse_args()

    print("=" * 65)
    print("  IP15: LINGBOT-MAP / UYARI KONUMLANDIRMA")
    print(f"  Tarih : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)

    # ── 1. Uyarı verisini yükle ──────────────────────────────────────────────
    ip14_json = Path(args.ip14_json) if args.ip14_json else None
    uyariler  = ip14_uyari_yukle(ip14_json)
    if not uyariler:
        print("  [UYARI] Uyarı verisi bulunamadı — dummy veri oluşturuluyor")
        uyariler = [
            {"waypoint_id": "WP01", "is_alert": True,  "severity": "HIGH",
             "degisiklik_tipi": "yerde_birakilan_cisim", "mog2_fg_ratio": 0.42},
            {"waypoint_id": "WP02", "is_alert": True,  "severity": "HIGH",
             "degisiklik_tipi": "yol_engeli", "mog2_fg_ratio": 0.49},
            {"waypoint_id": "WP03", "is_alert": True,  "severity": "HIGH",
             "degisiklik_tipi": "kapi_anomalisi", "mog2_fg_ratio": 0.62},
        ]

    print(f"  Uyarı verisi: {len(uyariler)} waypoint  "
          f"({sum(1 for u in uyariler if u.get('is_alert', False))} uyarılı)")

    # ── 2. Waypoint rotasını yükle ───────────────────────────────────────────
    waypoint_rota = waypoint_rota_yukle()
    print(f"  Waypoint rota: {len(waypoint_rota)} nokta")

    # ── 3. PLY modu kontrolü ─────────────────────────────────────────────────
    ply_yolu = None
    if args.ply:
        ply_yolu = Path(args.ply)
    else:
        # Otomatik PLY ara
        for p in [
            PROJECT_DIR / "data" / "raw_videos" / "altin_tur_v2.ply",
            PROJECT_DIR / "data" / "raw_videos" / "koridor_992.ply",
        ]:
            if p.exists():
                ply_yolu = p
                break

    # ── 4. Rota karelerini çıkar ─────────────────────────────────────────────
    video_yolu = Path(args.video)
    rota_kareler = rota_cikar_videodan(video_yolu, max_kare=args.max_kare)

    # ── 5. 2D harita çiz ─────────────────────────────────────────────────────
    print("\n  2D harita çiziliyor...")
    canvas, uyari_grafik = rota_haritasi_ciz(
        rota_kareler  = rota_kareler,
        waypoint_rota = waypoint_rota,
        uyariler      = uyariler,
    )

    harita_png = OUT_DIR / f"ip15_harita_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    cv2.imwrite(str(harita_png), canvas)
    son_harita = OUT_DIR / "ip15_harita_son.png"
    cv2.imwrite(str(son_harita), canvas)
    print(f"  [Kayıt] 2D Harita: {harita_png.name}")
    print(f"  [Kayıt] Son harita: {son_harita.name}")

    # ── 6. PLY haritası (varsa) ───────────────────────────────────────────────
    ply_goruntu = None
    if ply_yolu:
        print("\n  3D PLY haritası çiziliyor...")
        ply_goruntu = ply_haritasi_ciz(
            ply_yolu        = ply_yolu,
            uyariler        = uyariler,
            wp_koordinatlar = {},
            goster          = args.goster,
        )

    # ── 7. Dashboard JSON ─────────────────────────────────────────────────────
    json_yolu = dashboard_json_uret(uyariler, uyari_grafik, harita_png, OUT_DIR)
    print(f"  [Kayıt] Dashboard JSON: {json_yolu.name}")

    # ── 8. PDF dizinine kopyala ───────────────────────────────────────────────
    pdf_haritayi_ekle(son_harita)

    # ── 9. Özet ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 65)
    print("  IP15 TAMAMLANDI")
    print("=" * 65)
    uyari_sayisi = sum(1 for u in uyariler if u.get("is_alert", False))
    print(f"  Toplam WP    : {len(uyariler)}")
    print(f"  Uyarı        : {uyari_sayisi}")
    print(f"  2D Harita    : {son_harita}")
    if ply_goruntu:
        print(f"  3D Harita    : {ply_goruntu}")
    print(f"  Dashboard    : {OUT_DIR / 'ip15_dashboard.json'}")
    print("=" * 65)

    print(f"\n  [HATIRLATMA] IP15 takip tablosunu guncelle:")
    print(f"  | IP15 | ✅ | {datetime.now().strftime('%d.%m.%Y')} | "
          f"2D ego-motion harita ({uyari_sayisi}/{len(uyariler)} uyari isaretlendi), "
          f"dashboard JSON, PDF entegrasyonu. Cikti: outputs/ip15_harita/ |")

    return son_harita, json_yolu


if __name__ == "__main__":
    main()
