# -*- coding: utf-8 -*-
"""
İP9: MOG2 + PatchCore Ensemble Anomali Tespiti
===============================================
Doküman : DOKUMANLAR/Ozgur_is_paketleri.md -- İP9
Bitti kriteri: Senaryo setinde TP/FP sayımı raporlu

MİMARİ KARAR (15.08.2026):
---------------------------
Önceki yaklaşım (SSIM/ORB piksel kıyası) robot köpek senaryosunda yapısal
olarak yetersizdir: robot her turda birebir aynı açıyı tutamaz, ORB homografi
~20° tolerans sonrası kırılır, SSIM yanlış alarm üretir.

Bu script iki açı-bağımsız katmanı birleştirir:

  KATMAN 1 → MOG2 Arka Plan Çıkarma
  ------------------------------------
  Engel videosunu kendi içinde tarayarak durağan yeni nesneleri tespit eder.
  Farklı açıyla çekilmiş ikinci videoyla kıyaslama yapmaz — bu yüzden açıya
  tamamen bağımsızdır.

  KATMAN 2 → PatchCore Anomali Skoru
  ------------------------------------
  İP5'te MVTec-AD'de eğitilen PatchCore mantığının waypoint karelere
  uyarlanması: altın tur kareleri "normal" sınıf, güncel kare → anomali skoru.
  Embedding (özellik vektörü) seviyesinde kıyas yapıldığından ~40° açı
  farkına kadar dayanıklıdır.

  KARAR MANTIGI:
  --------------
  is_alert = (mog2_nesne_sayisi > 0) OR (patchcore_score > PATCHCORE_THRESH)
  severity = HIGH/MEDIUM/LOW  →  SEVERITY_MAP'ten

KULLANIM:
    cd D:/STAJ/akilli_fabrika_staj-2026
    python scripts/ip9_ensemble_analiz.py

    # Sadece MOG2 katmanı (PatchCore modeli yoksa):
    python scripts/ip9_ensemble_analiz.py --no-patchcore

    # Belirli eşik ile:
    python scripts/ip9_ensemble_analiz.py --patchcore-thresh 0.45
"""

import cv2
import numpy as np
import json
import argparse
from datetime import datetime
from pathlib import Path

# Config okuyucu modülünü import et (scripts dizininde olduğumuz için aynı hiyerarşi)
import sys
sys.path.append(str(Path(__file__).resolve().parent))
import config_okuyucu

# PatchCore için anomalib (opsiyonel — yoksa sadece MOG2 çalışır)
try:
    import torch
    from torchvision import transforms
    from PIL import Image
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("[UYARI] PyTorch bulunamadı — sadece MOG2 katmanı aktif.")


# =============================================================================
# PROJE AYARLARI
# =============================================================================
PROJECT_DIR    = config_okuyucu.PROJECT_ROOT
CONFIG         = config_okuyucu.CONFIG

WAYPOINTS_YAML = config_okuyucu.get_path(CONFIG.get("paths", {}).get("waypoints_yaml", "data/waypoints/waypoint_listesi.yaml"))
ALTIN_VIDEO    = config_okuyucu.get_path(CONFIG.get("paths", {}).get("default_altin_video", "data/raw_videos/altin_tur_v2.mp4"))
ENGEL_VIDEO    = config_okuyucu.get_path(CONFIG.get("paths", {}).get("default_engel_video", "data/raw_videos/engel.mp4"))
OUT_DIR        = PROJECT_DIR / "data" / "ip9_ensemble"
REF_DIR        = PROJECT_DIR / "data" / "waypoints" / "referans_kareler"

# Etiketler (İP8'den — gt_bbox içeren)
ETIKET_PATH    = config_okuyucu.get_path(CONFIG.get("paths", {}).get("etiketler_json", "data/ip8_test/etiketler.json"))

# PatchCore model ağırlıkları
PATCHCORE_CKPT = config_okuyucu.get_path(CONFIG.get("paths", {}).get("patchcore_ckpt", "outputs/model_results/ip6_patchcore_ckpt"))

# =============================================================================
# ALGILAMA PARAMETRELERİ
# =============================================================================
_vis_config = CONFIG.get("vision", {})

# ── MOG2 ──────────────────────────────────────────────────────────────────────
MOG2_HISTORY      = _vis_config.get("mog2_history", 200)
MOG2_THRESH       = _vis_config.get("mog2_thresh", 20)
MOG2_WINDOW_S     = _vis_config.get("mog2_window_s", 10)
MIN_AREA          = _vis_config.get("min_area", 1500)
MAX_AREA_RATIO    = _vis_config.get("max_area_ratio", 0.40)
MORPH_KERNEL      = 11
YELLOW_HSV_LOWER  = np.array(_vis_config.get("yellow_hsv_lower", [18, 80, 80]))
YELLOW_HSV_UPPER  = np.array(_vis_config.get("yellow_hsv_upper", [38, 255, 255]))
YELLOW_DILATE_PX  = _vis_config.get("yellow_dilate_px", 15)

# ── PatchCore ─────────────────────────────────────────────────────────────────
PATCHCORE_THRESH  = _vis_config.get("patchcore_thresh", 0.50)
IMG_SIZE          = (224, 224)   # ResNet18 giriş boyutu

# ── Severity eşlemesi ─────────────────────────────────────────────────────────
SEVERITY_MAP = {
    "yerde_birakilan_cisim": "HIGH",
    "yol_engeli":            "HIGH",
    "kapi_anomalisi":        "HIGH",
    "levha_degisikligi":     "MEDIUM",
    "kablo_karmasa":         "LOW",
}


# =============================================================================
# YARDIMCI FONKSİYONLAR
# =============================================================================

def load_yaml_waypoints(yaml_path: Path) -> list:
    """waypoint_listesi.yaml'ı yükle."""
    try:
        import yaml
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data.get("waypoints", [])
    except Exception as e:
        print(f"[HATA] YAML okunamadı: {e}")
        return []


def load_etiketler(etiket_path: Path) -> dict:
    """etiketler.json'ı yükle (İP8 GT verisi)."""
    with open(etiket_path, encoding="utf-8") as f:
        return json.load(f)


def build_yellow_mask(img_bgr: np.ndarray) -> np.ndarray:
    """Sarı zemin çizgilerini maskele."""
    hsv  = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, YELLOW_HSV_LOWER, YELLOW_HSV_UPPER)
    k    = cv2.getStructuringElement(
        cv2.MORPH_RECT, (YELLOW_DILATE_PX, YELLOW_DILATE_PX)
    )
    return cv2.dilate(mask, k, iterations=1)


# =============================================================================
# KATMAN 1 — MOG2 ARKA PLAN ÇIKARMA (açı-bağımsız)
# =============================================================================

def mog2_detect(engel_video: str,
                ref_second: float,
                window_s: float = MOG2_WINDOW_S
                ) -> tuple:
    """
    Engel videosunu kendi içinde analiz eder.
    Referans videoyla KIYASLAMA YAPILMAZ — bu yüzden açıya bağımsız.

    Döndürür: (sample_frame, fg_mask, fg_ratio, nesne_listesi)
    """
    cap = cv2.VideoCapture(str(engel_video))
    if not cap.isOpened():
        return None, np.zeros((480, 640), np.uint8), 0.0, []

    fps      = cap.get(cv2.CAP_PROP_FPS)
    total_fr = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    total_s  = total_fr / fps if fps > 0 else 0

    start_s  = max(0, min(ref_second - window_s / 2, total_s - window_s))
    end_s    = min(total_s, start_s + window_s)
    start_fr = int(start_s * fps)
    end_fr   = int(end_s   * fps)

    mog2 = cv2.createBackgroundSubtractorMOG2(
        history=MOG2_HISTORY, varThreshold=MOG2_THRESH, detectShadows=True
    )

    k_open  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (MORPH_KERNEL, MORPH_KERNEL))

    sample_frame = None
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_fr)
    for _ in range(start_fr, end_fr + 1):
        ret, fr = cap.read()
        if not ret:
            break
        mog2.apply(fr)
        if sample_frame is None:
            sample_frame = fr.copy()

    # Son karede sabit yabancı nesne maskesi al (learningRate=0 → artık öğrenme yok)
    cap.set(cv2.CAP_PROP_POS_FRAMES, max(start_fr, end_fr - 30))
    fg_mask    = None
    last_frame = None
    for _ in range(30):
        ret, fr = cap.read()
        if not ret:
            break
        fg = mog2.apply(fr, learningRate=0)
        fg[fg == 127] = 0   # gölgeleri sıfırla
        fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN,  k_open)
        fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, k_close)
        fg_mask    = fg
        last_frame = fr.copy()

    cap.release()

    if fg_mask is None or last_frame is None:
        return sample_frame, np.zeros((480, 640), np.uint8), 0.0, []

    # Sarı bölgeyi maskele
    yellow = build_yellow_mask(last_frame)
    if fg_mask.shape[:2] != last_frame.shape[:2]:
        fg_mask = cv2.resize(fg_mask, (last_frame.shape[1], last_frame.shape[0]))
    fg_mask[yellow > 0] = 0

    fg_ratio  = float(np.sum(fg_mask > 0)) / fg_mask.size
    nesneler  = _detect_contours(fg_mask, yellow)
    return last_frame, fg_mask, fg_ratio, nesneler


def _detect_contours(mask: np.ndarray,
                     yellow_mask: np.ndarray | None = None) -> list:
    """Fark maskesindeki contour'ları bul, filtrele."""
    h, w    = mask.shape
    img_area = h * w
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    objs = []
    for cnt in contours:
        if cv2.contourArea(cnt) < MIN_AREA:
            continue
        x, y, bw, bh = cv2.boundingRect(cnt)
        if bw * bh > img_area * MAX_AREA_RATIO:
            continue
        cx, cy = x + bw // 2, y + bh // 2
        if yellow_mask is not None:
            try:
                if yellow_mask[cy, cx] > 0:
                    continue
            except IndexError:
                pass
        objs.append({"x": int(x), "y": int(y), "w": int(bw), "h": int(bh),
                     "area": int(bw * bh), "cx": int(cx), "cy": int(cy)})
    objs.sort(key=lambda o: o["area"], reverse=True)
    return objs


# =============================================================================
# KATMAN 2 — PATCHCORE ANOMALİ SKORU (açıya ~40° toleranslı)
# =============================================================================

class PatchCoreScorer:
    """
    Basit cosine-similarity tabanlı PatchCore puanlayıcı.
    
    Tam anomalib bağımlılığı olmadan çalışabilmesi için ResNet18 feature
    extractor + memory bank (altın tur kareleri = normal) kullanır.
    
    Açı toleransı: ResNet18 embedding'i global spatial bilgiyi özetler,
    bu yüzden ~40° açı farkında bile anlamlı benzerlik skoru üretir.
    """

    def __init__(self, backbone: str = "resnet18"):
        if not TORCH_AVAILABLE:
            self.model = None
            return

        import torchvision.models as models
        m = models.resnet18(weights="IMAGENET1K_V1")
        # Sınıflandırıcıyı çıkar, sadece özellik çıkarıcı olarak kullan
        self.model = torch.nn.Sequential(*list(m.children())[:-1])
        self.model.eval()
        if torch.cuda.is_available():
            self.model = self.model.cuda()

        self.transform = transforms.Compose([
            transforms.Resize(IMG_SIZE),
            transforms.ToTensor(),
            transforms.Normalize([0.485, 0.456, 0.406],
                                 [0.229, 0.224, 0.225]),
        ])
        self.memory_bank: list[np.ndarray] = []   # normal özellik vektörleri

    def _extract(self, img_bgr: np.ndarray) -> np.ndarray | None:
        if self.model is None:
            return None
        rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)
        t   = self.transform(pil).unsqueeze(0)
        if torch.cuda.is_available():
            t = t.cuda()
        with torch.no_grad():
            feat = self.model(t).squeeze().cpu().numpy()
        return feat / (np.linalg.norm(feat) + 1e-8)   # L2 normalize

    def fit_normal(self, ref_frames: list[np.ndarray]):
        """Altın tur kareleriyle memory bank'i doldur."""
        self.memory_bank = []
        for fr in ref_frames:
            feat = self._extract(fr)
            if feat is not None:
                self.memory_bank.append(feat)
        print(f"  [PatchCore] Memory bank: {len(self.memory_bank)} referans vektör")

    def score(self, test_frame: np.ndarray) -> float:
        """
        Anomali skoru: 0.0 (tamamen normal) → 1.0 (tamamen anomali).
        1 - max_cosine_similarity formülü kullanılır.
        """
        if not self.memory_bank or self.model is None:
            return -1.0   # PatchCore devre dışı

        feat = self._extract(test_frame)
        if feat is None:
            return -1.0

        sims = [float(np.dot(feat, ref)) for ref in self.memory_bank]
        best_sim = max(sims)
        # cosine benzerliği: 1.0 = aynı, 0.0 = dik, -1.0 = zıt
        # Anomali skoru: yüksek benzerlik → düşük skor (normal)
        anomali_score = 1.0 - best_sim
        return round(float(anomali_score), 4)


# Tek global skorlayıcı (waypoint'ler arasında paylaşılır)
_scorer = None

def get_scorer() -> PatchCoreScorer:
    global _scorer
    if _scorer is None:
        _scorer = PatchCoreScorer()
    return _scorer


# =============================================================================
# GÖRSEL KAYIT — 4 PANELLİ ÇIKTI
# =============================================================================

def draw_ensemble_result(ref_bgr: np.ndarray,
                         test_bgr: np.ndarray,
                         fg_mask: np.ndarray,
                         mog2_objs: list,
                         yellow_mask: np.ndarray,
                         wp_id: str,
                         mog2_fg_ratio: float,
                         patchcore_score: float,
                         is_alert: bool,
                         gt_bbox: dict | None = None) -> np.ndarray:
    """
    4 panelli görsel:
      [P1] Referans (altın tur)  |  [P2] Güncel kare + MOG2 tespitler
      [P3] MOG2 fg maskesi       |  [P4] Sarı bölge overlay + GT bbox
    """
    H, W  = ref_bgr.shape[:2]
    COLORS = [(0, 0, 255), (0, 165, 255), (0, 255, 0), (255, 0, 0), (255, 0, 255)]

    def put(img, txt, pos, scale=0.60, color=(255, 255, 255), thickness=2):
        cv2.putText(img, txt, pos, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness)

    # P1 — Referans
    p1 = cv2.resize(ref_bgr, (W, H)).copy()
    put(p1, "REFERANS (Altin Tur)", (10, 28))

    # P2 — Güncel kare + MOG2 tespitler
    p2 = cv2.resize(test_bgr, (W, H)).copy()
    for i, obj in enumerate(mog2_objs):
        c = COLORS[i % len(COLORS)]
        cv2.rectangle(p2, (obj["x"], obj["y"]),
                      (obj["x"] + obj["w"], obj["y"] + obj["h"]), c, 2)
        put(p2, f"MOG2-{i+1}  {obj['area']}px2", (obj["x"], max(obj["y"] - 6, 18)),
            scale=0.45, color=c)
    # GT bbox (yeşil kesikli çerçeve)
    if gt_bbox:
        gx, gy, gw, gh = gt_bbox["x"], gt_bbox["y"], gt_bbox["w"], gt_bbox["h"]
        cv2.rectangle(p2, (gx, gy), (gx + gw, gy + gh), (0, 255, 0), 2)
        put(p2, "GT", (gx, max(gy - 6, 18)), scale=0.45, color=(0, 255, 0))
    uyari_renk = (0, 0, 255) if is_alert else (0, 200, 0)
    uyari_txt  = ">>> UYARI <<<" if is_alert else "Normal"
    put(p2, f"{uyari_txt}  MOG2={len(mog2_objs)}obj", (10, 28), color=uyari_renk)
    put(p2, f"PC_score={patchcore_score:.3f}  fg={mog2_fg_ratio:.4f}",
        (10, H - 14), scale=0.42, color=(200, 200, 200))

    # P3 — MOG2 fg maskesi
    fg_resized = cv2.resize(fg_mask, (W, H))
    p3 = cv2.cvtColor(fg_resized, cv2.COLOR_GRAY2BGR)
    put(p3, "MOG2 Foreground Maskesi", (10, 28), color=(200, 200, 200))

    # P4 — Sarı overlay
    p4 = cv2.resize(test_bgr, (W, H)).copy()
    ym_r = cv2.resize(yellow_mask, (W, H))
    p4[ym_r > 0] = (p4[ym_r > 0] * 0.35 + np.array([0, 180, 180]) * 0.65).astype(np.uint8)
    put(p4, "SARI BOLGE OVERLAY", (10, 28), color=(0, 200, 200))

    # 2x2 grid
    row1 = np.hstack([p1, p2])
    row2 = np.hstack([p3, p4])
    grid = np.vstack([row1, row2])

    # Başlık şeridi
    bar = np.full((48, grid.shape[1], 3), (20, 20, 30), np.uint8)
    ts  = datetime.now().strftime("%Y-%m-%d %H:%M")
    cv2.putText(bar,
                f"IP9 MOG2+PatchCore Ensemble  |  {wp_id}   |   {ts}",
                (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.60, (190, 190, 190), 1)
    patchcore_info = (f"PatchCore: {'AKTIF' if patchcore_score >= 0 else 'DEVRE DISI'}"
                      f"  |  Esik: {PATCHCORE_THRESH}")
    cv2.putText(bar, patchcore_info,
                (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (150, 150, 150), 1)
    return np.vstack([bar, grid])


# =============================================================================
# ANA İŞLEM — TEK WAYPOINT
# =============================================================================

def process_waypoint_ensemble(pair: dict,
                               engel_video: str,
                               scorer: PatchCoreScorer,
                               use_patchcore: bool,
                               out_dir: Path,
                               ref_second: float) -> dict:
    """
    Bir test çifti için MOG2 + PatchCore ensemble pipeline çalıştır.
    """
    wp_id   = pair["waypoint_id"]
    ref_path  = PROJECT_DIR / pair["referans"]
    test_path = PROJECT_DIR / pair["degisik"]
    deg_tipi  = pair.get("degisiklik_tipi", "bilinmiyor")
    gt_bbox   = pair.get("gt_bbox")

    print(f"\n{'='*60}")
    print(f"  Waypoint: {wp_id}  |  Tip: {deg_tipi}")
    print(f"{'='*60}")

    ref_bgr  = cv2.imread(str(ref_path))
    test_bgr = cv2.imread(str(test_path))

    if ref_bgr is None:
        print(f"  [HATA] Referans okunamadı: {ref_path}")
        return {}
    if test_bgr is None:
        print(f"  [HATA] Test okunamadı: {test_path}")
        return {}

    h, w = ref_bgr.shape[:2]
    test_bgr = cv2.resize(test_bgr, (w, h))

    # ── KATMAN 1: MOG2 ────────────────────────────────────────────────────────
    print("  [MOG2] Arka plan çıkarma başlıyor...")
    engel_last, fg_mask, fg_ratio, mog2_nesneler = mog2_detect(
        str(engel_video), ref_second=ref_second
    )
    print(f"  [MOG2] fg_ratio={fg_ratio:.4f}  |  {len(mog2_nesneler)} nesne")

    # Sarı maske
    yellow = build_yellow_mask(ref_bgr)

    if engel_last is None:
        engel_last = test_bgr.copy()

    # ── KATMAN 2: PatchCore ───────────────────────────────────────────────────
    patchcore_score = -1.0
    if use_patchcore and scorer.model is not None:
        if not scorer.memory_bank:
            print("  [PatchCore] Memory bank boş — referans karesinden dolduruluyor")
            scorer.fit_normal([ref_bgr])
        patchcore_score = scorer.score(test_bgr)
        print(f"  [PatchCore] Anomali skoru: {patchcore_score:.4f}  "
              f"(eşik: {PATCHCORE_THRESH})")
    else:
        print("  [PatchCore] Devre dışı")

    # ── KARAR ─────────────────────────────────────────────────────────────────
    mog2_uyari       = len(mog2_nesneler) > 0
    patchcore_uyari  = (patchcore_score >= 0) and (patchcore_score > PATCHCORE_THRESH)
    is_alert         = mog2_uyari or patchcore_uyari

    karar_aciklama = []
    if mog2_uyari:
        karar_aciklama.append(f"MOG2: {len(mog2_nesneler)} nesne")
    if patchcore_uyari:
        karar_aciklama.append(f"PatchCore: {patchcore_score:.3f} > {PATCHCORE_THRESH}")
    if not is_alert:
        karar_aciklama.append("Normal — iki katman da uyarı vermedi")

    severity  = SEVERITY_MAP.get(deg_tipi, "MEDIUM") if is_alert else "NONE"
    durum_str = ">>> UYARI <<<" if is_alert else "Normal"
    print(f"  [Karar] {durum_str}  |  {' + '.join(karar_aciklama)}")
    print(f"  [Karar] Severity: {severity}")

    # ── GT bbox ile TP/FP değerlendirmesi ─────────────────────────────────────
    tp_fp_degerlendirme = _evaluate_tp_fp(mog2_nesneler, gt_bbox, (h, w))

    # ── Görsel kaydet ──────────────────────────────────────────────────────────
    out_dir.mkdir(parents=True, exist_ok=True)
    vis = draw_ensemble_result(
        ref_bgr       = ref_bgr,
        test_bgr      = test_bgr,
        fg_mask       = fg_mask,
        mog2_objs     = mog2_nesneler,
        yellow_mask   = yellow,
        wp_id         = wp_id,
        mog2_fg_ratio = fg_ratio,
        patchcore_score = patchcore_score,
        is_alert      = is_alert,
        gt_bbox       = gt_bbox,
    )
    vis_path  = out_dir / f"{wp_id}_ensemble_analiz.png"
    fg_path   = out_dir / f"{wp_id}_fg_mog2.png"
    cv2.imwrite(str(vis_path),  vis)
    cv2.imwrite(str(fg_path),   fg_mask)
    print(f"  [Kayıt] {vis_path}")

    return {
        "waypoint_id":         wp_id,
        "degisiklik_tipi":     deg_tipi,
        "senaryo":             pair.get("senaryo", ""),
        "referans":            str(ref_path),
        "test":                str(test_path),
        # MOG2
        "mog2_fg_ratio":       round(fg_ratio, 4),
        "mog2_nesne_sayisi":   len(mog2_nesneler),
        "mog2_nesneler":       mog2_nesneler,
        "mog2_uyari":          mog2_uyari,
        # PatchCore
        "patchcore_score":     patchcore_score,
        "patchcore_esik":      PATCHCORE_THRESH,
        "patchcore_uyari":     patchcore_uyari,
        "patchcore_aktif":     (patchcore_score >= 0),
        # Karar
        "is_alert":            is_alert,
        "severity":            severity,
        "karar_aciklama":      " + ".join(karar_aciklama),
        # GT & TP/FP
        "gt_bbox":             gt_bbox,
        "tp_fp":               tp_fp_degerlendirme,
        # Meta
        "ensemble_gorseli":    str(vis_path),
        "fg_mog2":             str(fg_path),
        "ts":                  datetime.now().isoformat(),
    }


# =============================================================================
# TP/FP DEĞERLENDİRMESİ (İP9 bitti kriteri)
# =============================================================================

def _evaluate_tp_fp(detections: list, gt_bbox: dict | None,
                    img_shape: tuple) -> dict:
    """
    Tespit kutularını GT ile IoU bazında değerlendir.
    IoU >= 0.3 → True Positive

    Döndürür: {tp, fp, fn, iou_best}
    """
    if gt_bbox is None:
        return {"tp": None, "fp": None, "fn": None, "iou_best": None,
                "not": "GT bbox mevcut değil"}

    if not detections:
        return {"tp": 0, "fp": 0, "fn": 1, "iou_best": 0.0,
                "not": "Tespit yok — False Negative"}

    # GT alanı
    gx, gy = gt_bbox["x"], gt_bbox["y"]
    gw, gh = gt_bbox["w"], gt_bbox["h"]

    best_iou = 0.0
    for det in detections:
        iou = _iou(det["x"], det["y"], det["w"], det["h"], gx, gy, gw, gh)
        if iou > best_iou:
            best_iou = iou

    IOU_THRESH = 0.30
    if best_iou >= IOU_THRESH:
        return {"tp": 1, "fp": 0, "fn": 0, "iou_best": round(best_iou, 3),
                "not": f"TP — IoU={best_iou:.3f} >= {IOU_THRESH}"}
    else:
        return {"tp": 0, "fp": 1, "fn": 1, "iou_best": round(best_iou, 3),
                "not": f"FP+FN — IoU={best_iou:.3f} < {IOU_THRESH}"}


def _iou(ax, ay, aw, ah, bx, by, bw, bh) -> float:
    """İki bbox arasındaki IoU (Intersection over Union)."""
    ix1 = max(ax, bx)
    iy1 = max(ay, by)
    ix2 = min(ax + aw, bx + bw)
    iy2 = min(ay + ah, by + bh)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


# =============================================================================
# ANA PIPELINE
# =============================================================================

def run_ensemble(engel_video: str,
                 etiket_path: Path,
                 out_dir: Path,
                 use_patchcore: bool = True):

    etiketler = load_etiketler(etiket_path)
    pairs     = etiketler.get("test_ciftleri", [])

    if not pairs:
        print("[HATA] test_ciftleri boş.")
        return

    waypoints_data = load_yaml_waypoints(WAYPOINTS_YAML)
    wp_seconds = {}
    for wp in waypoints_data:
        if "id" in wp and "saniye" in wp:
            wp_seconds[wp["id"]] = float(wp["saniye"])

    scorer = get_scorer()

    # PatchCore için tüm referans karelerini birlikte yükle
    if use_patchcore and scorer.model is not None:
        ref_frames = []
        for p in pairs:
            ref_img = cv2.imread(str(PROJECT_DIR / p["referans"]))
            if ref_img is not None:
                ref_frames.append(ref_img)
        if ref_frames:
            scorer.fit_normal(ref_frames)

    print(f"\nEngel Video : {engel_video}")
    print(f"Test çifti  : {len(pairs)} adet")
    print(f"PatchCore   : {'AKTIF' if (use_patchcore and scorer.model is not None) else 'DEVRE DISI'}")
    print(f"Çıktı       : {out_dir}")

    all_results = []
    for pair in pairs:
        wp_id = pair.get("waypoint_id", "")
        ref_sec = wp_seconds.get(wp_id, 15.0)

        result = process_waypoint_ensemble(
            pair, engel_video, scorer, use_patchcore, out_dir, ref_second=ref_sec
        )
        if result:
            all_results.append(result)
            j_path = out_dir / f"{pair['waypoint_id']}_ensemble_sonuc.json"
            with open(j_path, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)

    # ── Özet istatistik ───────────────────────────────────────────────────────
    uyari_sayisi = sum(1 for r in all_results if r["is_alert"])
    tp_toplam    = sum(r["tp_fp"]["tp"] or 0 for r in all_results
                       if r["tp_fp"].get("tp") is not None)
    fp_toplam    = sum(r["tp_fp"]["fp"] or 0 for r in all_results
                       if r["tp_fp"].get("fp") is not None)
    fn_toplam    = sum(r["tp_fp"]["fn"] or 0 for r in all_results
                       if r["tp_fp"].get("fn") is not None)

    precision = tp_toplam / (tp_toplam + fp_toplam) if (tp_toplam + fp_toplam) > 0 else 0.0
    recall    = tp_toplam / (tp_toplam + fn_toplam) if (tp_toplam + fn_toplam) > 0 else 0.0
    f1        = (2 * precision * recall / (precision + recall)
                 if (precision + recall) > 0 else 0.0)

    ozet = {
        "tur":             "ip9_mog2_patchcore_ensemble",
        "tarih":           datetime.now().isoformat(),
        "engel_video":     str(engel_video),
        "toplam_wp":       len(all_results),
        "uyari_sayisi":    uyari_sayisi,
        "mimari":          "MOG2 + PatchCore Ensemble (SSIM/ORB yok)",
        "patchcore_aktif": (use_patchcore and _scorer is not None
                            and _scorer.model is not None),
        "metrikler": {
            "TP": tp_toplam,
            "FP": fp_toplam,
            "FN": fn_toplam,
            "precision": round(precision, 3),
            "recall":    round(recall, 3),
            "F1":        round(f1, 3),
        },
        "sonuclar": all_results,
    }

    ozet_path = out_dir / "ensemble_ozet.json"
    with open(ozet_path, "w", encoding="utf-8") as f:
        json.dump(ozet, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"  TAMAMLANDI — {len(all_results)} waypoint işlendi")
    print(f"  Uyarı: {uyari_sayisi}/{len(all_results)}")
    print(f"  TP={tp_toplam}  FP={fp_toplam}  FN={fn_toplam}")
    print(f"  Precision={precision:.3f}  Recall={recall:.3f}  F1={f1:.3f}")
    print(f"  Özet: {ozet_path}")
    print(f"{'='*60}\n")


# =============================================================================
# ARGÜMAN AYRIŞIMI
# =============================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="İP9: MOG2 + PatchCore Ensemble Anomali Tespiti"
    )
    parser.add_argument("--engel",          default=str(ENGEL_VIDEO),
                        help="Engel videosu yolu")
    parser.add_argument("--etiketler",      default=str(ETIKET_PATH),
                        help="etiketler.json yolu (İP8 GT verisi)")
    parser.add_argument("--outdir",         default=str(OUT_DIR),
                        help="Çıktı dizini")
    parser.add_argument("--no-patchcore",   action="store_true",
                        help="PatchCore katmanını devre dışı bırak")
    parser.add_argument("--patchcore-thresh", type=float, default=PATCHCORE_THRESH,
                        help=f"PatchCore eşiği (varsayılan: {PATCHCORE_THRESH})")
    args = parser.parse_args()

    PATCHCORE_THRESH = args.patchcore_thresh

    run_ensemble(
        engel_video   = args.engel,
        etiket_path   = Path(args.etiketler),
        out_dir       = Path(args.outdir),
        use_patchcore = not args.no_patchcore,
    )
