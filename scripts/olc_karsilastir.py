# -*- coding: utf-8 -*-
"""MOG2 (mevcut) vs hizalamali (oneri) - ayni girdi, ayni olcut.

NOT (Geri Bildirim):
Senin koridor_992.mp4 üzerinde ölçtüm, motoruna dokunmadım. Boş koridorda mevcut hâli 992 karede 386 kutu üretiyor, karelerin %22'sinde alarm veriyor. Videoda gerçek nesne yok, hepsi yanlış pozitif. Hizalamalı sürümde 1 kutu kaldı. Rotation guard bu videoda hiç devreye girmiyor, akış medyanı 0.38 ama eşik 3.5. Robot normal hızda giderken tetiklenmiyor. Waypoint tarafında WP02'de referans ve test ikisi de boş koridor, anomali yok ama gt olarak MOG2'nin kendi kutusu yazılmış. WP03'te referans amfi, test bir kapı. Bu ikisi düzelmeden F1 gerçek performansı ölçmüyor. WP01 sağlam, çöp kovasını hizalamalı sürüm buluyor (IoU 0.35), mevcut hâli kaçırıyor (0.09).
"""
import sys, json, statistics
from pathlib import Path
import argparse

OZGUR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(OZGUR))

from scripts.core.config_okuyucu import get_path, CONFIG

SCRATCH = get_path("outputs")
if SCRATCH is None:
    SCRATCH = OZGUR / "outputs"
SCRATCH.mkdir(exist_ok=True)

import cv2, numpy as np
from scripts.core.anomali_motor import AlgilayiciMOG2
from scripts.core import anomali_hizalamali as hizalamali


def parse_args():
    p = argparse.ArgumentParser()
    paths = CONFIG.get("paths", {})
    p.add_argument("--video", type=str, 
                   default=str(get_path(paths.get("default_koridor_video", "data/raw_videos/koridor_992.mp4"))))
    p.add_argument("--gt-json", type=str,
                   default=str(get_path(paths.get("ensemble_ozet_json", "data/ip9_ensemble/ensemble_ozet.json"))))
    p.add_argument("--ref-dir", type=str,
                   default=str(get_path(paths.get("referans_kareler_dir", "data/waypoints/referans_kareler"))))
    p.add_argument("--test-dir", type=str,
                   default=str(get_path(paths.get("ip8_test_dir", "data/ip8_test"))))
    return p.parse_args()


args = parse_args()

def iou(a, b):
    ax2, ay2 = a["x"] + a["w"], a["y"] + a["h"]
    bx2, by2 = b["x"] + b["w"], b["y"] + b["h"]
    ix = max(0, min(ax2, bx2) - max(a["x"], b["x"]))
    iy = max(0, min(ay2, by2) - max(a["y"], b["y"]))
    kesisim = ix * iy
    birlesim = a["w"] * a["h"] + b["w"] * b["h"] - kesisim
    return kesisim / birlesim if birlesim else 0.0


# ---------- 1) YANLIS ALARM: bos koridor videosu ----------
video_path = Path(args.video)
cap = cv2.VideoCapture(str(video_path))
if cap.isOpened():
    ok, ilk = cap.read()
else:
    ok, ilk = False, None
    print(f"[UYARI] Video açılamadı: {video_path}", file=sys.stderr)

if ok:
    mog = AlgilayiciMOG2(); mog.warmup(ilk)
    yeni = hizalamali.AkisAlgilayici()
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
else:
    mog = yeni = None

m_kutu = y_kutu = y_aday = 0
m_alarm = y_alarm = 0
atlanan = 0
kare = 0

if ok:
    while True:
        ok_f, f = cap.read()
        if not ok_f: break
        kare += 1
        r1 = mog.isle(f); r2 = yeni.isle(f)
        m_kutu += len(r1["nesneler"]); m_alarm += bool(r1.get("is_alert", False))
        if not r2["ok"]:
            atlanan += 1
        else:
            y_kutu += len(r2["nesneler"]); y_aday += len(r2["aday"])
            y_alarm += bool(r2["nesneler"])
cap.release()

fp = {
    "kare": kare,
    "mog2_kutu": m_kutu, "mog2_alarmli_kare": m_alarm,
    "hizalamali_kutu": y_kutu, "hizalamali_alarmli_kare": y_alarm,
    "hizalamali_onaysiz_aday": y_aday,
    "hizalanamayan_kare": atlanan,
}

# ---------- 2) YAKALAMA: etiketli waypoint ciftleri ----------
gt_path = Path(args.gt_json)
if gt_path.exists():
    gt = json.loads(gt_path.read_text())
else:
    gt = {"sonuclar": []}
    print(f"[UYARI] GT JSON bulunamadı: {gt_path}", file=sys.stderr)

wp_sonuc = []
for s in gt.get("sonuclar", []):
    wid = s["waypoint_id"]
    ref_path = Path(args.ref_dir) / f"{wid}.jpg"
    tst_path = Path(args.test_dir) / f"{wid}_degisik.jpg"
    ref = cv2.imread(str(ref_path))
    tst = cv2.imread(str(tst_path))
    if ref is None or tst is None:
        wp_sonuc.append({"wp": wid, "hata": "goruntu okunamadi"}); continue
    if ref.shape != tst.shape:
        ref = cv2.resize(ref, (tst.shape[1], tst.shape[0]))
    g = s["gt_bbox"]
    r = hizalamali.waypoint_farki(ref, tst)
    en_iyi = max((iou(n, g) for n in r["nesneler"]), default=0.0)
    wp_sonuc.append({
        "wp": wid, "tip": s["degisiklik_tipi"],
        "gt_kaynagi": g.get("kaynak", "-"),
        "mog2_nesne": s["mog2_nesne_sayisi"], "mog2_iou": s["tp_fp"]["iou_best"],
        "hizalamali_nesne": len(r["nesneler"]), "hizalamali_iou": round(en_iyi, 3),
        "hizalama": "ok" if r["ok"] else r.get("sebep"),
    })

    ciz = tst.copy()
    cv2.rectangle(ciz, (g["x"], g["y"]), (g["x"]+g["w"], g["y"]+g["h"]), (0, 220, 0), 2)
    cv2.putText(ciz, "gt", (g["x"], max(g["y"]-6, 14)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,220,0), 2)
    for n in r["nesneler"]:
        cv2.rectangle(ciz, (n["x"], n["y"]), (n["x"]+n["w"], n["y"]+n["h"]), (0,0,230), 2)
    cv2.imwrite(str(SCRATCH / f"wp_{wid}_hizalamali.jpg"), ciz)

print(json.dumps({"yanlis_alarm": fp, "waypoint": wp_sonuc}, indent=2, ensure_ascii=False))
