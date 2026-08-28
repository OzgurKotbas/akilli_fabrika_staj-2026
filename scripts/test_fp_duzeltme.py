# -*- coding: utf-8 -*-
"""
test_fp_duzeltme.py — Ö1+Ö2 düzeltmelerini WP01 çifti üzerinde
ÖNCE / SONRA karşılaştırması olarak ölçer.

Çıktılar: outputs/analiz_fp/test_duzeltme_oncesi.png
                            test_duzeltme_sonrasi.png
                            karsilastirma.png
"""
import sys, io
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8','utf-16'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from pathlib import Path
import cv2
import numpy as np
import json

ROOT    = Path(__file__).resolve().parent.parent
REF     = cv2.imread(str(ROOT / "data/waypoints/referans_kareler/WP01.jpg"))
TEST    = cv2.imread(str(ROOT / "data/ip8_test/WP01_degisik.jpg"))
OUT_DIR = ROOT / "outputs/analiz_fp"
OUT_DIR.mkdir(parents=True, exist_ok=True)

with open(ROOT / "data/ip8_test/etiketler.json", encoding="utf-8") as f:
    gt_data = json.load(f)
gt = next(c for c in gt_data["test_ciftleri"] if c["waypoint_id"] == "WP01")["gt_bbox"]

H, W = REF.shape[:2]
TEST = cv2.resize(TEST, (W, H))

k_open  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
YELLOW_LO = np.array([18, 80, 80])
YELLOW_HI = np.array([38, 255, 255])

def yellow_mask(bgr):
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, YELLOW_LO, YELLOW_HI)
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    return cv2.dilate(m, k, iterations=1)

def mog2_run(ref, test, warmup_n=0, tavan_oran=0.0):
    mog2 = cv2.createBackgroundSubtractorMOG2(history=200, varThreshold=20, detectShadows=True)
    if warmup_n > 0:
        for _ in range(warmup_n):
            mog2.apply(ref, learningRate=1.0)
    else:
        mog2.apply(ref)                # eski yöntem: 1 kare arka plan

    fg = mog2.apply(test)
    fg[fg == 127] = 0
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN,  k_open)
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, k_close)

    if tavan_oran > 0:
        sinir = int(fg.shape[0] * tavan_oran)
        fg[:sinir, :] = 0              # Ö2: tavan bastır

    ym = yellow_mask(test)
    fg[ym > 0] = 0

    cnts, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    nesneler = []
    for cnt in cnts:
        if cv2.contourArea(cnt) < 1500:
            continue
        x, y, bw, bh = cv2.boundingRect(cnt)
        if bw * bh > H * W * 0.40:
            continue
        cx, cy = x + bw // 2, y + bh // 2
        try:
            if ym[cy, cx] > 0:
                continue
        except IndexError:
            pass
        nesneler.append({"x": x, "y": y, "w": bw, "h": bh, "area": bw * bh})

    return fg, sorted(nesneler, key=lambda o: o["area"], reverse=True)

def iou(a, b):
    ax1,ay1,ax2,ay2 = a["x"],a["y"],a["x"]+a["w"],a["y"]+a["h"]
    bx1,by1,bx2,by2 = b["x"],b["y"],b["x"]+b["w"],b["y"]+b["h"]
    ix1,iy1 = max(ax1,bx1), max(ay1,by1)
    ix2,iy2 = min(ax2,bx2), min(ay2,by2)
    inter = max(0, ix2-ix1) * max(0, iy2-iy1)
    union = (ax2-ax1)*(ay2-ay1) + (bx2-bx1)*(by2-by1) - inter
    return inter / union if union > 0 else 0.0

def gorselle(img, nesneler, gt, baslik, warmup_n, tavan_oran, fg):
    vis = img.copy()
    gx, gy, gw, gh = gt["x"], gt["y"], gt["w"], gt["h"]
    cv2.rectangle(vis, (gx,gy), (gx+gw,gy+gh), (0,200,0), 3)
    cv2.putText(vis, "GT", (gx, max(gy-6,14)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,200,0), 2)

    if tavan_oran > 0:
        sinir = int(H * tavan_oran)
        cv2.line(vis, (0, sinir), (W, sinir), (0, 200, 255), 2)
        cv2.putText(vis, f"tavan crop ({int(tavan_oran*100)}%)", (4, sinir-4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0,200,255), 1)

    best_iou = 0.0
    fp_cnt = fn_cnt = tp_cnt = 0
    for i, n in enumerate(nesneler):
        iou_v = iou({"x":n["x"],"y":n["y"],"w":n["w"],"h":n["h"]}, gt)
        if iou_v >= 0.3:
            renk = (0, 140, 0); tp_cnt += 1
        else:
            renk = (0, 0, 220); fp_cnt += 1
        best_iou = max(best_iou, iou_v)
        cv2.rectangle(vis, (n["x"],n["y"]), (n["x"]+n["w"],n["y"]+n["h"]), renk, 2)
        cv2.putText(vis, f"#{i+1} IoU={iou_v:.2f}", (n["x"], max(n["y"]-4,12)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, renk, 1)
    fn_cnt = 0 if tp_cnt > 0 else 1

    # Alt bilgi bandı
    band = np.zeros((56, W, 3), np.uint8)
    f1 = 2*tp_cnt / (2*tp_cnt + fp_cnt + fn_cnt) if (tp_cnt+fp_cnt+fn_cnt) > 0 else 0
    satir1 = f"Warmup={warmup_n}  TavanCrop={int(tavan_oran*100)}%  Nesne={len(nesneler)}"
    satir2 = f"TP={tp_cnt} FP={fp_cnt} FN={fn_cnt}  BestIoU={best_iou:.3f}  F1={f1:.3f}"
    cv2.putText(band, satir1, (6,18), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (200,200,200), 1)
    cv2.putText(band, satir2, (6,40), cv2.FONT_HERSHEY_SIMPLEX, 0.50,
                (80,220,80) if f1 >= 0.7 else (80,80,220), 1)
    cv2.putText(band, baslik, (W-len(baslik)*9-4, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.50, (180,180,180), 1)
    full = np.vstack([vis, band])
    return full, {"tp": tp_cnt, "fp": fp_cnt, "fn": fn_cnt, "iou": best_iou, "f1": f1,
                  "nesne": len(nesneler)}

# ── ÖNCESİ (orijinal: warmup=0, tavan=0) ──────────────────────────────────────
print("  [ONCESI] warmup=0 tavan=0.0 ...")
fg_once, obj_once = mog2_run(REF, TEST, warmup_n=0, tavan_oran=0.0)
vis_once, m_once  = gorselle(TEST, obj_once, gt, "ONCESI", 0, 0.0, fg_once)

# ── SONRASI (Ö1+Ö2: warmup=40, tavan=0.18) ────────────────────────────────────
print("  [SONRASI] warmup=40 tavan=0.18 ...")
fg_sonra, obj_sonra = mog2_run(REF, TEST, warmup_n=40, tavan_oran=0.18)
vis_sonra, m_sonra  = gorselle(TEST, obj_sonra, gt, "SONRASI (O1+O2)", 40, 0.18, fg_sonra)

# Karşılaştırma kaydı
cv2.imwrite(str(OUT_DIR / "test_duzeltme_oncesi.png"),  vis_once)
cv2.imwrite(str(OUT_DIR / "test_duzeltme_sonrasi.png"), vis_sonra)
karsi = np.hstack([vis_once, vis_sonra])
cv2.imwrite(str(OUT_DIR / "karsilastirma.png"), karsi)

# ── Konsol Özeti ───────────────────────────────────────────────────────────────
print()
print("="*60)
print("  WP01 Ö1+Ö2 Düzeltme — KARŞILAŞTIRMA")
print("="*60)
hdr = f"{'Metrik':20s} {'ÖNCESİ':>12s} {'SONRASI':>12s} {'Değişim':>12s}"
print(f"  {hdr}")
print("  " + "-"*60)

for k, label in [("nesne","Tespit edilen"), ("tp","TP"), ("fp","FP"),
                  ("fn","FN"), ("iou","Best IoU"), ("f1","F1")]:
    o = m_once[k]; s = m_sonra[k]
    delta = s - o
    ok = ("✅" if (k in ("tp","iou","f1") and delta >= 0) or
                 (k in ("fp","fn","nesne") and delta <= 0)
          else "⚠️")
    print(f"  {ok} {label:18s} {o:>12.3f} {s:>12.3f} {delta:>+12.3f}")

print()
if m_sonra["f1"] > m_once["f1"]:
    print(f"  ✅ F1 iyileşti: {m_once['f1']:.3f} → {m_sonra['f1']:.3f} "
          f"(+{m_sonra['f1']-m_once['f1']:.3f})")
else:
    print(f"  ⚠️  F1 değişmedi: {m_once['f1']:.3f} → {m_sonra['f1']:.3f}")

print(f"\n  Görsel çıktılar: {OUT_DIR}")
print(f"  → test_duzeltme_oncesi.png")
print(f"  → test_duzeltme_sonrasi.png")
print(f"  → karsilastirma.png")
