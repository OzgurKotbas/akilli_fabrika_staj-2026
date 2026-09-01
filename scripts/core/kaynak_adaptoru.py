# -*- coding: utf-8 -*-
from __future__ import annotations
import cv2
import time
from pathlib import Path

class KaynakAdaptoru:
    """
    Evrensel görüntü kaynağı adaptörü (Video / Stream / Kamera / Resim).
    Destekler:
      - Video (.mp4, .avi vs) : 0, 1, 2... indexleri webcam
      - RTSP / HTTP streams   : "rtsp://..." veya "http://..."
      - Tekil resim           : "test.jpg"
      - Resim dizini          : "/path/to/frames/"
    """
    def __init__(self, kaynak_yolu: str | int | Path):
        self.kaynak = str(kaynak_yolu)
        self.tip = self._kaynak_tipini_belirle(self.kaynak)
        self.cap = None
        self.img = None
        self.bitis = False
        
        # Kamera ısınması vb. için frame okuma gecikmesi
        self.read_delay_ms = 0

        if self.tip == "resim":
            self.img = cv2.imread(self.kaynak)
            if self.img is None:
                raise ValueError(f"Resim okunamadi: {self.kaynak}")
        elif self.tip in ["video", "kamera", "stream"]:
            # Eğer int dönüşümü başarılı olursa webcam indexidir
            try:
                k = int(self.kaynak)
                self.cap = cv2.VideoCapture(k)
            except ValueError:
                self.cap = cv2.VideoCapture(self.kaynak)
                
            if not self.cap.isOpened():
                raise ValueError(f"Video/Stream acilamadi: {self.kaynak}")
                
            self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 25.0
            self.toplam_fr = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Kamera veya stream ise buffer birikmesini önlemek için okuma stratejisi eklenebilir
            if self.tip in ["kamera", "stream"]:
                self.read_delay_ms = 50  # basit stream throttling
        elif self.tip == "dizin":
            self.frame_yollari = sorted(Path(self.kaynak).glob("*.jpg"))
            self.frame_idx = 0
            if not self.frame_yollari:
                raise ValueError(f"Dizinde .jpg bulunamadi: {self.kaynak}")
        else:
            raise ValueError(f"Bilinmeyen kaynak tipi: {self.kaynak}")

    def _kaynak_tipini_belirle(self, kaynak: str) -> str:
        if str(kaynak).isdigit():
            return "kamera"
        
        k_lower = kaynak.lower()
        if k_lower.startswith("rtsp://") or k_lower.startswith("http://") or k_lower.startswith("https://"):
            return "stream"
            
        p = Path(kaynak)
        if p.is_file():
            ext = p.suffix.lower()
            if ext in [".jpg", ".jpeg", ".png", ".bmp"]:
                return "resim"
            if ext in [".mp4", ".avi", ".mov", ".mkv"]:
                return "video"
                
        if p.is_dir():
            return "dizin"
            
        return "bilinmiyor"

    def kare_al(self, saniye: float | None = None) -> np.ndarray | None:
        """
        Kaynaktan kare al.
        saniye: Video modunda belirtilen saniyeye git. None → bir sonraki kare.
        Statik modda her zaman aynı görüntü döner (saniye yok sayılır).
        """
        if self.bitis:
            return None

        if self.tip == "resim":
            return self.img.copy()

        if self.tip == "dizin":
            if self.frame_idx >= len(self.frame_yollari):
                self.bitis = True
                return None
            fr = cv2.imread(str(self.frame_yollari[self.frame_idx]))
            self.frame_idx += 1
            return fr

        if self.cap is None or not self.cap.isOpened():
            return None

        if saniye is not None and getattr(self, "toplam_fr", 0) > 0 and self.tip == "video":
            kare_no = int(saniye * getattr(self, "fps", 25.0))
            kare_no = max(0, min(kare_no, getattr(self, "toplam_fr", 1) - 1))
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, kare_no)

        if getattr(self, "read_delay_ms", 0) > 0:
            time.sleep(getattr(self, "read_delay_ms", 0) / 1000.0)
            
        ret, frame = self.cap.read()
        if not ret:
            self.bitis = True
            
        return frame if ret else None
        
    def oku(self) -> tuple[bool, cv2.Mat | None]:
        """Siradaki kareyi okur."""
        fr = self.kare_al()
        return (fr is not None, fr)

    def release(self):
        """Kaynaklari serbest birakir."""
        if self.cap:
            self.cap.release()
