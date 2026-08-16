"""
İP3 Tekrar — 2. Adım: Waypoint Kareleri Seç
=============================================
Kaggle'dan indirdiğin PLY/NPZ çıktısı gelince bunu çalıştırmana gerek yok.
Bu script, yerel makinende frames/ klasöründen waypoint karelerini seçer
ve ip3_tekrar/outputs/waypoints/ altına kopyalar.

Kullanım:
    cd d:/STAJ/akilli_fabrika_staj-2026
    python ip3_tekrar/scripts/2_waypoint_sec.py

Not: Waypoint zamanlarını (saniye) aşağıdaki WAYPOINTS listesinde düzenle.
     meta.json'dan effective_fps değerini kullanarak frame numarasını hesaplar.
"""

import cv2
import os
import json
import shutil

# ─── Ayarlar ──────────────────────────────────────────────────────────────────
FRAMES_DIR    = os.path.join(os.path.dirname(__file__), "..", "frames")
WAYPOINTS_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs", "waypoints")

# Videon boyunca durakların zamanları (saniye cinsinden)
# → kendi çektiğin videoya göre düzenle
WAYPOINTS = [
    {"id": "WP01", "saniye": 3.0,  "aciklama": "Giriş noktası"},
    {"id": "WP02", "saniye": 8.0,  "aciklama": "Koridor başı"},
    {"id": "WP03", "saniye": 13.0, "aciklama": "Orta nokta"},
    {"id": "WP04", "saniye": 18.0, "aciklama": "Koridor sonu"},
    {"id": "WP05", "saniye": 23.0, "aciklama": "Çıkış noktası"},
]
# ──────────────────────────────────────────────────────────────────────────────


def sec_waypoints():
    frames_dir    = os.path.abspath(FRAMES_DIR)
    waypoints_dir = os.path.abspath(WAYPOINTS_DIR)
    os.makedirs(waypoints_dir, exist_ok=True)

    # Meta bilgisini oku
    meta_path = os.path.join(frames_dir, "meta.json")
    if not os.path.exists(meta_path):
        print(f"[HATA] meta.json bulunamadı: {meta_path}")
        print("       Önce 1_video_to_frames.py çalıştır.")
        return

    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    eff_fps = meta["effective_fps"]
    total   = meta["saved_frames"]
    print(f"📋 Meta: {meta['saved_frames']} kare, effective_fps={eff_fps:.1f}")
    print()

    saved_wps = []
    for wp in WAYPOINTS:
        frame_no = int(wp["saniye"] * eff_fps)
        frame_no = max(0, min(frame_no, total - 1))  # sınır kontrolü

        src = os.path.join(frames_dir, f"frame_{frame_no:05d}.jpg")
        dst = os.path.join(waypoints_dir, f"{wp['id']}.jpg")

        if not os.path.exists(src):
            print(f"[⚠️]  {wp['id']} — kare bulunamadı (frame_{frame_no:05d}.jpg)")
            continue

        shutil.copy(src, dst)

        # Üzerine waypoint etiketi bas
        img = cv2.imread(dst)
        label = f"{wp['id']}  |  {wp['saniye']}s  |  kare #{frame_no}"
        cv2.putText(img, label, (15, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 100), 2)
        cv2.imwrite(dst, img)

        print(f"  ✅ {wp['id']:5s}  saniye={wp['saniye']:5.1f}  →  kare #{frame_no:05d}  {wp['aciklama']}")
        saved_wps.append({**wp, "frame_no": frame_no, "dosya": dst})

    # YAML benzeri özet kaydet
    wp_summary_path = os.path.join(waypoints_dir, "waypoint_ozet.json")
    with open(wp_summary_path, "w", encoding="utf-8") as f:
        json.dump(saved_wps, f, indent=2, ensure_ascii=False)

    print()
    print(f"✅ {len(saved_wps)} waypoint kaydedildi  →  {waypoints_dir}")
    print(f"📄 Özet  →  {wp_summary_path}")


if __name__ == "__main__":
    sec_waypoints()
