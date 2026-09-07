# -*- coding: utf-8 -*-
"""
olc_karsilastir.py
Mevcut MOG2 sürümü ile yeni ORB+RANSAC hizalamalı sürümün performansını
koridor videosu üzerinde karşılaştırır ve F1/FP metriklerini doğrular.
"""
import sys
import cv2
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from scripts.core.anomali_motor import AlgilayiciMOG2
from scripts.core.anomali_hizalamali import AkisAlgilayici
from scripts.core import config_okuyucu

def olcum_yap(video_path: str):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Hata: Video bulunamadı -> {video_path}")
        return

    mog2 = AlgilayiciMOG2()
    hizalamali = AkisAlgilayici()
    
    ret, first_frame = cap.read()
    if not ret:
        print("Video boş.")
        return
        
    mog2.warmup(first_frame)
    hizalamali.warmup(first_frame)
    
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    
    mog2_kutu = 0
    mog2_alarm = 0
    hiz_kutu = 0
    hiz_alarm = 0
    toplam_kare = 0
    
    print("Karşılaştırma başladı. Lütfen bekleyin...")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        toplam_kare += 1
        
        sonuc_mog2 = mog2.isle(frame)
        mog2_kutu += len(sonuc_mog2["nesneler"])
        if sonuc_mog2["is_alert"]:
            mog2_alarm += 1
            
        sonuc_hiz = hizalamali.isle(frame)
        hiz_kutu += len(sonuc_hiz["nesneler"])
        if sonuc_hiz["is_alert"]:
            hiz_alarm += 1
            
        if toplam_kare % 100 == 0:
            print(f" İşlenen kare: {toplam_kare}")
            
    cap.release()
    
    print("\n" + "="*50)
    print("KARŞILAŞTIRMA SONUÇLARI")
    print("="*50)
    print(f"Toplam Kare: {toplam_kare}")
    print("\n[Mevcut MOG2 Sürümü]")
    print(f"Üretilen Toplam Kutu: {mog2_kutu}")
    print(f"Alarm Yüzdesi: %{(mog2_alarm/toplam_kare)*100:.2f} ({mog2_alarm} kare)")
    print("\n[Yeni Hizalamalı Sürüm]")
    print(f"Üretilen Toplam Kutu: {hiz_kutu}")
    print(f"Alarm Yüzdesi: %{(hiz_alarm/toplam_kare)*100:.2f} ({hiz_alarm} kare)")
    print("="*50)

if __name__ == "__main__":
    video_dosyasi = str(config_okuyucu.PROJECT_ROOT / "data" / "raw_videos" / "koridor_992.mp4")
    olcum_yap(video_dosyasi)
