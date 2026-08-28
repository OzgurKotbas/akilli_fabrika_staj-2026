# -*- coding: utf-8 -*-
import cv2
import numpy as np
from collections import deque
from scripts.core import config_okuyucu

CONFIG = config_okuyucu.CONFIG
_vis_conf = CONFIG.get("vision", {})

PARAMS = {
    "mog2_min_area": _vis_conf.get("min_area", 1500),
    "mog2_thresh": _vis_conf.get("mog2_thresh", 20),
    "mog2_history": _vis_conf.get("mog2_history", 200),
    "yellow_lower": np.array(_vis_conf.get("yellow_hsv_lower", [18, 80, 80])),
    "yellow_upper": np.array(_vis_conf.get("yellow_hsv_upper", [38, 255, 255])),
    "yellow_dilate": _vis_conf.get("yellow_dilate_px", 15),
    "morph_kernel": 9,
    "tavan_crop_oran": _vis_conf.get("tavan_crop_oran", 0.18),
    "rotation_flow_thresh": _vis_conf.get("rotation_flow_thresh", 3.5),
    "mog2_lr_drift_reset": _vis_conf.get("mog2_lr_drift_reset", 0.08),
    "mog2_warmup_n": _vis_conf.get("mog2_warmup_n", 40),
}

def build_yellow_mask(img_bgr: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, PARAMS["yellow_lower"], PARAMS["yellow_upper"])
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (PARAMS["yellow_dilate"], PARAMS["yellow_dilate"]))
    return cv2.dilate(mask, k, iterations=1)

class AlgilayiciMOG2:
    """
    İP9 mantığı: MOG2 arka plan çıkarma — video akışı üzerinde çalışır.
    İyileştirilmiş Modül: Tavan Crop + Rotation Guard (Optik Akış) entegredir.
    """
    def __init__(self):
        self.mog2 = cv2.createBackgroundSubtractorMOG2(
            history=PARAMS["mog2_history"],
            varThreshold=PARAMS["mog2_thresh"],
            detectShadows=True,
        )
        self._k_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        self._k_close = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (PARAMS["morph_kernel"], PARAMS["morph_kernel"])
        )
        self.warmed_up = False
        self.prev_gray = None
        self.no_alert_frames = 0
        self.recent_fg_ratios = deque(maxlen=30)
        
    def warmup(self, frame: np.ndarray, n: int = None):
        """İlk kareyi N kez besleyerek MOG2 Gaussian Mixture modelini hızlıca öğrenir."""
        if n is None:
            n = PARAMS["mog2_warmup_n"]
        for _ in range(n):
            self.mog2.apply(frame, learningRate=1.0)
        self.warmed_up = True
        self.prev_gray = cv2.cvtColor(cv2.resize(frame, (0,0), fx=0.25, fy=0.25), cv2.COLOR_BGR2GRAY)

    def isle(self, frame: np.ndarray) -> dict:
        is_rotation = False
        flow_mag_mean = 0.0
        
        # 1. Optical Flow for Rotation Guard
        small_gray = cv2.cvtColor(cv2.resize(frame, (0,0), fx=0.25, fy=0.25), cv2.COLOR_BGR2GRAY)
        if self.prev_gray is not None:
            flow = cv2.calcOpticalFlowFarneback(self.prev_gray, small_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
            mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
            flow_mag_mean = np.mean(mag)
            if flow_mag_mean > PARAMS["rotation_flow_thresh"]:
                is_rotation = True
        self.prev_gray = small_gray
        
        # Dönme sırasında arka plan modelini bozmamak için LR = 0
        learning_rate = 0.0 if is_rotation else -1.0
        
        fg = self.mog2.apply(frame, learningRate=learning_rate)
        fg[fg == 127] = 0
        fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, self._k_open)
        fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, self._k_close)
        
        # 2. Tavan Crop
        h, w = fg.shape
        tavan_sinir = int(h * PARAMS["tavan_crop_oran"])
        fg[:tavan_sinir, :] = 0
        
        yellow = build_yellow_mask(frame)
        if fg.shape != yellow.shape:
            yellow = cv2.resize(yellow, (w, h))
        fg[yellow > 0] = 0
        
        fg_ratio = float(np.sum(fg > 0)) / fg.size
        self.recent_fg_ratios.append(fg_ratio)
        
        nesneler = self._detect(fg, yellow)
        
        # Rotation guard: Dönme anında tespitleri sıfırla
        if is_rotation:
            nesneler = []
            is_alert = False
        else:
            is_alert = len(nesneler) > 0
            
        return {
            "is_alert": is_alert,
            "nesneler": nesneler,
            "fg_mask": fg,
            "fg_ratio": round(fg_ratio, 4),
            "is_rotation": is_rotation,
            "flow_mag": round(flow_mag_mean, 4)
        }

    def _detect(self, mask: np.ndarray, yellow_mask: np.ndarray) -> list:
        h, w = mask.shape
        img_area = h * w
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        objs = []
        for cnt in contours:
            if cv2.contourArea(cnt) < PARAMS["mog2_min_area"]:
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
