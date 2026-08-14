import cv2
import os
import argparse
from pathlib import Path

def extract_frames_from_video(video_path, output_dir, timestamps_and_names):
    """
    Belirli saniyelerdeki frame'leri çıkarıp istenilen isimle kaydeder.
    
    Args:
        video_path (str): Video dosyasının yolu.
        output_dir (str): Çıktıların kaydedileceği dizin.
        timestamps_and_names (list of tuples): [(saniye, dosya_adi.jpg), ...]
    """
    if not os.path.exists(video_path):
        print(f"[HATA] Video bulunamadı: {video_path}")
        return

    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"[HATA] Video açılamadı: {video_path}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_duration = total_frames / fps if fps > 0 else 0
    
    print(f"Video yüklendi: {video_path}")
    print(f"Süre: {video_duration:.2f} sn, FPS: {fps:.2f}, Toplam Kare: {total_frames}")
    
    for time_sec, filename in timestamps_and_names:
        if time_sec > video_duration:
            print(f"[UYARI] İstenen zaman ({time_sec} sn) video süresinden ({video_duration:.2f} sn) büyük. Atlanıyor: {filename}")
            continue

        # Saniyeyi frame numarasına çevir
        frame_number = int(time_sec * fps)
        
        # İlgili frame'e atla
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        
        ret, frame = cap.read()
        if ret:
            output_path = os.path.join(output_dir, filename)
            cv2.imwrite(output_path, frame)
            print(f"[OK] {time_sec}. saniye kaydedildi: {output_path}")
        else:
            print(f"[HATA] {time_sec}. saniye okunamadi: {filename}")

    cap.release()
    print("İşlem tamamlandı.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Videodan belirli saniyelerdeki frame'leri çıkarır.")
    parser.add_argument("--video", required=True, help="Video dosyasının yolu (örn: data/raw_videos/engel.mp4)")
    parser.add_argument("--outdir", default="data/ip8_test", help="Çıktı dizini")
    
    args = parser.parse_args()
    
    # ─── ÇIKARILACAK ANOMALİ LİSTESİ ──────────────────────────────────────────
    # Burayı kendi videonuzdaki saniyelere ve dosya isimlerine göre düzenleyin.
    # Format: (saniye, "dosya_adi.jpg")
    anomali_listesi = [
        (5.0,  "WP01_degisik.jpg"),  # 5. saniyede WP01 için anomali var (su şişesi vb.)
        (15.0, "WP02_degisik.jpg"),  # 15. saniyede WP02 için anomali var
        (23.0, "WP03_degisik.jpg"),  # 23. saniyede WP03 için anomali var
        # (32.5, "ekstra_anomali.jpg"), # Virgüllü saniye (float) kullanabilirsiniz
    ]
    # ──────────────────────────────────────────────────────────────────────────

    extract_frames_from_video(args.video, args.outdir, anomali_listesi)
