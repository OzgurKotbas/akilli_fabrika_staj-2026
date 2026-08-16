"""
İP3 Tekrar — 1. Adım: Video → Kareler
=======================================
Yeni çektiğin altın tur videosunu frame'lere böler.
Kaggle'a atmadan önce yerel makinende çalıştır.

Kullanım:
    cd d:/STAJ/akilli_fabrika_staj-2026
    python ip3_tekrar/scripts/1_video_to_frames.py <video_yolu>

Örnek:
    python ip3_tekrar/scripts/1_video_to_frames.py data/raw_videos/altin_tur_v2.mp4

Çıktı:
    ip3_tekrar/frames/   ← bu klasörü ZIP'leyip Kaggle'a yükleyeceksin
"""

import cv2
import os
import sys
import json

# ─── Ayarlar ──────────────────────────────────────────────────────────────────
# 1034 frame sorununu aşmak için:
#   - STRIDE=1  → tüm kareler (30fps @ 2dk = 3600 frame — T4'te çalışır)
#   - STRIDE=2  → her ikinci kare (30fps @ 5dk = 4500 frame — güvenli)
#   - STRIDE=3  → her üçüncü kare (çok uzun videolar için)
#
# Kaggle T4 GPU 16GB VRAM → ~4000-5000 frame'e kadar sorunsuz işler
# (eski Colab denemende 1034 limitinde crash oldu, çünkü windowed inference
#  kullanılmamıştı. Kaggle notebook'ta --keyframe_interval flag'i ekledik.)

STRIDE       = 1       # Her kaçıncı frame alınsın
MAX_FRAMES   = 6000    # Güvenlik limiti
JPEG_QUALITY = 95      # Görüntü kalitesi (100=kayıpsız ama büyük dosya)
OUTPUT_DIR   = os.path.join(os.path.dirname(__file__), "..", "frames")
# ──────────────────────────────────────────────────────────────────────────────


def video_to_frames(video_path):
    output_dir = os.path.abspath(OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[HATA] Video açılamadı: {video_path}")
        sys.exit(1)

    fps        = cap.get(cv2.CAP_PROP_FPS)
    total      = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_s = total / fps if fps > 0 else 0
    w          = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h          = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print("=" * 55)
    print("📹 VİDEO BİLGİSİ")
    print("=" * 55)
    print(f"  Dosya       : {os.path.basename(video_path)}")
    print(f"  Boyut       : {w}x{h}")
    print(f"  FPS         : {fps:.1f}")
    print(f"  Toplam kare : {total}")
    print(f"  Süre        : {duration_s:.1f} sn  ({duration_s/60:.1f} dk)")
    print(f"  Stride      : {STRIDE}  →  ~{total//STRIDE} kare çıkacak")
    print("=" * 55)

    if total // STRIDE > MAX_FRAMES:
        print(f"\n⚠️  {total//STRIDE} kare > MAX_FRAMES({MAX_FRAMES})")
        print(f"   STRIDE değerini artır ya da MAX_FRAMES'i yükselt.")

    saved = 0
    idx   = 0

    while saved < MAX_FRAMES:
        ret, frame = cap.read()
        if not ret:
            break
        if idx % STRIDE == 0:
            out_path = os.path.join(output_dir, f"frame_{saved:05d}.jpg")
            cv2.imwrite(out_path, frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
            saved += 1
            if saved % 100 == 0:
                print(f"  ... {saved} kare kaydedildi", end="\r")
        idx += 1

    cap.release()
    print(f"\n✅ {saved} kare kaydedildi  →  {output_dir}")

    # Meta bilgi — Kaggle'da waypoint hesabı ve inference için lazım
    meta = {
        "source_video"    : os.path.basename(video_path),
        "resolution"      : f"{w}x{h}",
        "original_fps"    : fps,
        "original_frames" : total,
        "duration_sec"    : round(duration_s, 2),
        "stride"          : STRIDE,
        "saved_frames"    : saved,
        "effective_fps"   : round(fps / STRIDE, 2),
    }
    meta_path = os.path.join(output_dir, "meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f"📄 Meta bilgi  →  {meta_path}")
    print()
    print("─" * 55)
    print("📌 SONRAKI ADIM")
    print("─" * 55)
    print(f"  1. {output_dir} klasörünü ZIP'le:")
    print(f"     Compress-Archive ip3_tekrar/frames frames.zip  (PowerShell)")
    print(f"  2. Kaggle → Datasets → New Dataset → ZIP'i yükle")
    print(f"  3. ip3_tekrar/kaggle/ip3_lingbotmap_notebook.py dosyasını")
    print(f"     Kaggle Notebook olarak çalıştır")

    return meta


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Kullanım : python 1_video_to_frames.py <video_yolu>")
        print("Örnek    : python 1_video_to_frames.py data/raw_videos/altin_tur_v2.mp4")
        sys.exit(1)

    video_to_frames(sys.argv[1])
