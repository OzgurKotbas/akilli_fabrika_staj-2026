# -*- coding: utf-8 -*-
"""
anomali_hizalamali.py
ORB + RANSAC ile kareleri hizalayıp farkı alan yeni anomali motoru.
Eşik sabit değil, görüntünün kendi dağılımından (Otsu) hesaplanır.
Zemindeki yansımalar için parlama maskesi eklenmiştir.
"""
import cv2
import numpy as np
from scripts.core.anomali_motor import build_yellow_mask, PARAMS

class AkisAlgilayici:
    def __init__(self):
        self.warmed_up = False
        self.ref_frame = None
        self.ref_gray = None
        self.ref_kp = None
        self.ref_des = None
        self.orb = cv2.ORB_create(nfeatures=2000, fastThreshold=5, scaleFactor=1.2, nlevels=10)
        self.bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        self._k_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        self._k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (PARAMS["morph_kernel"], PARAMS["morph_kernel"]))
        
    def warmup(self, frame: np.ndarray, n: int = None):
        self.ref_frame = frame.copy()
        self.ref_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        yellow_mask = build_yellow_mask(frame)
        mask = cv2.bitwise_not(yellow_mask)
        
        h, w = frame.shape[:2]
        tavan_sinir = int(h * PARAMS.get("tavan_crop_oran", 0.18))
        mask[:tavan_sinir, :] = 0
        
        self.ref_kp, self.ref_des = self.orb.detectAndCompute(self.ref_gray, mask=mask)
        self.warmed_up = True

    def build_glare_mask(self, frame: np.ndarray) -> np.ndarray:
        # Parlama maskesi (glare mask) - beyaz/parlak yansımaları maskele
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, glare = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY)
        glare = cv2.dilate(glare, np.ones((7, 7), np.uint8), iterations=2)
        return glare

    def _align(self, test_bgr: np.ndarray):
        test_gray = cv2.cvtColor(test_bgr, cv2.COLOR_BGR2GRAY)
        h, w = test_gray.shape
        test_kp, test_des = self.orb.detectAndCompute(test_gray, mask=None)
        
        if self.ref_des is None or test_des is None or len(self.ref_kp) < 10 or len(test_kp) < 10:
            return test_bgr, False
            
        raw = self.bf.knnMatch(self.ref_des, test_des, k=2)
        good = [m for m, n in raw if m.distance < 0.80 * n.distance]
        
        if len(good) < 10:
            return test_bgr, False
            
        src = np.float32([self.ref_kp[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst = np.float32([test_kp[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
        M, _ = cv2.findHomography(dst, src, cv2.RANSAC, 5.0)
        
        if M is None:
            return test_bgr, False
            
        aligned = cv2.warpPerspective(test_bgr, M, (w, h))
        return aligned, True

    def isle(self, frame: np.ndarray) -> dict:
        if not self.warmed_up:
            self.warmup(frame)
            
        aligned_frame, ok = self._align(frame)
        if not ok:
            aligned_frame = frame.copy()
            
        aligned_gray = cv2.cvtColor(aligned_frame, cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(self.ref_gray, aligned_gray)
        
        # Otsu eşikleme ile dinamik threshold
        _, fg = cv2.threshold(diff, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, self._k_open)
        fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, self._k_close)
        
        h, w = fg.shape
        tavan_sinir = int(h * PARAMS.get("tavan_crop_oran", 0.18))
        fg[:tavan_sinir, :] = 0
        
        yellow = build_yellow_mask(aligned_frame)
        if fg.shape != yellow.shape:
            yellow = cv2.resize(yellow, (w, h))
        fg[yellow > 0] = 0
        
        glare = self.build_glare_mask(aligned_frame)
        fg[glare > 0] = 0
        
        fg_ratio = float(np.sum(fg > 0)) / fg.size
        
        nesneler = self._detect(fg, yellow)
        
        is_alert = len(nesneler) > 0
        
        return {
            "is_alert": is_alert,
            "nesneler": nesneler,
            "fg_mask": fg,
            "fg_ratio": round(fg_ratio, 4),
            "is_rotation": not ok,
            "flow_mag": 0.0,
            "aligned_ok": ok
        }

    def _detect(self, mask: np.ndarray, yellow_mask: np.ndarray) -> list:
        h, w = mask.shape
        img_area = h * w
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        objs = []
        for cnt in contours:
            if cv2.contourArea(cnt) < PARAMS.get("mog2_min_area", 1500):
                continue
            x, y, bw, bh = cv2.boundingRect(cnt)
            if bw * bh > img_area * 0.40:
                continue
            cx, cy = x + bw // 2, y + bh // 2
            try:
                if yellow_mask[cy, cx] > 0:
                    continue
            except IndexError:
                pass
            objs.append({"x": int(x), "y": int(y), "w": int(bw), "h": int(bh),
                         "area": int(bw * bh), "cx": int(cx), "cy": int(cy)})
        objs.sort(key=lambda o: o["area"], reverse=True)
        return objs
