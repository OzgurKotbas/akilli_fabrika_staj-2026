# -*- coding: utf-8 -*-
"""Hareket telafili anomali tespiti - MOG2'ye alternatif onerisi.

MOG2 her pikselin ZAMAN icindeki renk dagilimini ogrenir; bu ancak o piksel hep
ayni yere bakiyorsa anlamlidir. Devriye robotunda kamera ilerliyor, dolayisiyla
ayni piksel her karede baska sahneye bakiyor ve model her yerde "degisim" goruyor.

Buradaki yol: iki kareyi once GEOMETRIK olarak hizala (ORB + RANSAC homografi),
sonra farki al. Sahnenin sabit yapisi hizalamadan sonra birbirini goturur;
geriye gercekten yeni olan kalir.

Iki mod:
  kare_farki()     - ardisik iki kare (video akisi): HAREKETLI seyleri bulur
  waypoint_farki() - referans tur karesi vs simdiki kare: DURAN yeni cismi bulur

Esikler mutlak degil, gecerli bolgenin kendi dagilimindan (medyan + k*MAD)
seciliyor - aydinlatma degisince kendini ayarlasin diye.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from scripts.core.config_okuyucu import CONFIG

vis_cfg = CONFIG.get("vision", {})

ORB_OZELLIK = vis_cfg.get("orb_features", 2000)
MIN_ESLESME = vis_cfg.get("ransac_min_match", 12)          # bunun altinda homografi guvenilmez -> kare atlanir
MIN_ICERIDE = vis_cfg.get("ransac_min_inlier", 10)          # RANSAC inlier alt siniri
MAD_K = vis_cfg.get("mad_k", 6.0)               # esik = medyan + MAD_K * MAD (gecerli bolgede)
MIN_MUTLAK_FARK = vis_cfg.get("min_abs_diff", 18)      # MAD cok kucukse (duz duvar) taban esik
MORPH = vis_cfg.get("morph_size", 7)
MIN_ALAN = vis_cfg.get("min_area", 1500)
MAX_ALAN_ORANI = vis_cfg.get("max_area_ratio", 0.40)
TAVAN_ORANI = vis_cfg.get("tavan_crop_oran", 0.18)
# Parlama: yuksek parlaklik + dusuk doygunluk. Zemindeki lamba yansimalari
# HSV'de sari araliginda degil, bu yuzden build_yellow_mask'e takilmiyorlar.
PARLAMA_V = vis_cfg.get("parlama_v", 235)
PARLAMA_S = vis_cfg.get("parlama_s", 45)
PARLAMA_GENISLET = vis_cfg.get("parlama_dilate", 9)
SARI_ALT = np.array(vis_cfg.get("yellow_hsv_lower", [18, 80, 80]))
SARI_UST = np.array(vis_cfg.get("yellow_hsv_upper", [38, 255, 255]))
SARI_GENISLET = vis_cfg.get("sari_dilate", 15)


def _gri(img):
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def parlama_maskesi(bgr: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    m = ((hsv[..., 2] >= PARLAMA_V) & (hsv[..., 1] <= PARLAMA_S)).astype(np.uint8) * 255
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (PARLAMA_GENISLET, PARLAMA_GENISLET))
    return cv2.dilate(m, k, 1)


def sari_maskesi(bgr: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    m = cv2.inRange(hsv, SARI_ALT, SARI_UST)
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (SARI_GENISLET, SARI_GENISLET))
    return cv2.dilate(m, k, 1)


@dataclass
class Hizalama:
    ok: bool
    warped: np.ndarray | None = None     # kaynak, hedefe tasinmis hali
    gecerli: np.ndarray | None = None    # ortusen bolge maskesi (uint8 0/255)
    iceride: int = 0
    sebep: str = ""


def hizala(kaynak: np.ndarray, hedef: np.ndarray) -> Hizalama:
    """`kaynak`i `hedef`in bakis acisina tasir. Basarisizsa ok=False."""
    orb = cv2.ORB_create(ORB_OZELLIK)
    k1, d1 = orb.detectAndCompute(_gri(kaynak), None)
    k2, d2 = orb.detectAndCompute(_gri(hedef), None)
    if d1 is None or d2 is None or len(k1) < MIN_ESLESME or len(k2) < MIN_ESLESME:
        return Hizalama(False, sebep="yeterli ozellik yok")

    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    esler = bf.match(d1, d2)
    if len(esler) < MIN_ESLESME:
        return Hizalama(False, sebep=f"eslesme az ({len(esler)})")
    esler = sorted(esler, key=lambda m: m.distance)[:400]

    src = np.float32([k1[m.queryIdx].pt for m in esler]).reshape(-1, 1, 2)
    dst = np.float32([k2[m.trainIdx].pt for m in esler]).reshape(-1, 1, 2)
    H, mask = cv2.findHomography(src, dst, cv2.RANSAC, 3.0)
    if H is None:
        return Hizalama(False, sebep="homografi cozulemedi")
    iceride = int(mask.sum()) if mask is not None else 0
    if iceride < MIN_ICERIDE:
        return Hizalama(False, iceride=iceride, sebep=f"inlier az ({iceride})")

    h, w = hedef.shape[:2]
    warped = cv2.warpPerspective(kaynak, H, (w, h))
    ones = np.full(kaynak.shape[:2], 255, np.uint8)
    gecerli = cv2.warpPerspective(ones, H, (w, h))
    gecerli = cv2.erode(gecerli, np.ones((9, 9), np.uint8), 1)   # kenar artigi
    return Hizalama(True, warped, gecerli, iceride)


def _kutular(fark: np.ndarray, gecerli: np.ndarray, bastir: np.ndarray,
             min_alan: int) -> tuple[list[dict], np.ndarray, float]:
    h, w = fark.shape
    ic = gecerli > 0
    if ic.sum() < 0.10 * fark.size:
        return [], np.zeros_like(fark), 0.0

    degerler = fark[ic]
    medyan = float(np.median(degerler))
    mad = float(np.median(np.abs(degerler - medyan))) or 1.0
    esik = max(medyan + MAD_K * mad, MIN_MUTLAK_FARK)

    maske = ((fark > esik) & ic).astype(np.uint8) * 255
    maske[:int(h * TAVAN_ORANI), :] = 0
    maske[bastir > 0] = 0
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (MORPH, MORPH))
    maske = cv2.morphologyEx(maske, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    maske = cv2.morphologyEx(maske, cv2.MORPH_CLOSE, k)

    konturlar, _ = cv2.findContours(maske, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    nesneler = []
    for c in konturlar:
        if cv2.contourArea(c) < min_alan:
            continue
        x, y, bw, bh = cv2.boundingRect(c)
        if bw * bh > h * w * MAX_ALAN_ORANI:
            continue
        nesneler.append({"x": int(x), "y": int(y), "w": int(bw), "h": int(bh),
                         "area": int(bw * bh), "cx": int(x + bw // 2), "cy": int(y + bh // 2)})
    nesneler.sort(key=lambda o: -o["area"])
    return nesneler, maske, esik


def _fark_haritasi(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    ga = cv2.GaussianBlur(_gri(a), (5, 5), 0)
    gb = cv2.GaussianBlur(_gri(b), (5, 5), 0)
    return cv2.absdiff(ga, gb)


def waypoint_farki(referans: np.ndarray, test: np.ndarray, *, min_alan: int = MIN_ALAN) -> dict:
    """Ayni duragin referans turu ile simdiki hali. DURAN yeni cismi bulur."""
    hz = hizala(referans, test)
    if not hz.ok:
        return {"ok": False, "sebep": hz.sebep, "nesneler": []}
    bastir = cv2.bitwise_or(parlama_maskesi(test), sari_maskesi(test))
    fark = _fark_haritasi(test, hz.warped)
    nesneler, maske, esik = _kutular(fark, hz.gecerli, bastir, min_alan)
    return {"ok": True, "nesneler": nesneler, "maske": maske,
            "esik": round(esik, 1), "iceride": hz.iceride}


@dataclass
class AkisAlgilayici:
    """Video akisi: ardisik kareleri hizalayip farki alir, N karede onaylar."""

    onay_kare: int = 3
    pencere: int = 5
    min_alan: int = MIN_ALAN
    eslesme_mesafesi: int = 60
    _onceki: np.ndarray | None = None
    _izler: list = field(default_factory=list)   # [{"cx","cy","vurus","gorulen"}]
    _sayac: int = 0

    def isle(self, kare: np.ndarray) -> dict:
        self._sayac += 1
        if self._onceki is None:
            self._onceki = kare.copy()
            return {"ok": False, "sebep": "ilk kare", "nesneler": [], "aday": []}

        hz = hizala(self._onceki, kare)
        self._onceki = kare.copy()
        if not hz.ok:
            # Hizalanamayan kare OKUNMAZ - yanlis alarm uretmektense susulur.
            return {"ok": False, "sebep": hz.sebep, "nesneler": [], "aday": []}

        bastir = cv2.bitwise_or(parlama_maskesi(kare), sari_maskesi(kare))
        fark = _fark_haritasi(kare, hz.warped)
        adaylar, _, esik = _kutular(fark, hz.gecerli, bastir, self.min_alan)

        # Zamansal onay: aday ancak `onay_kare` kez gorulunce nesne sayilir.
        for iz in self._izler:
            iz["gorulen"] = False
        for a in adaylar:
            en_iyi = None
            for iz in self._izler:
                d = abs(iz["cx"] - a["cx"]) + abs(iz["cy"] - a["cy"])
                if d < self.eslesme_mesafesi and (en_iyi is None or d < en_iyi[0]):
                    en_iyi = (d, iz)
            if en_iyi:
                iz = en_iyi[1]
                iz.update(cx=a["cx"], cy=a["cy"], vurus=iz["vurus"] + 1,
                          gorulen=True, kutu=a, son=self._sayac)
            else:
                self._izler.append({"cx": a["cx"], "cy": a["cy"], "vurus": 1,
                                    "gorulen": True, "kutu": a, "son": self._sayac})
        self._izler = [iz for iz in self._izler if self._sayac - iz["son"] < self.pencere]

        onayli = [iz["kutu"] for iz in self._izler
                  if iz["vurus"] >= self.onay_kare and iz["gorulen"]]
        onayli.sort(key=lambda o: -o["area"])
        
        # ÖNCELİK 4: Kategori Tabanlı Anomali Sınıflandırması
        for o in onayli:
            x, y, w, h = o["x"], o["y"], o["w"], o["h"]
            roi = kare[max(0, y):y+h, max(0, x):x+w]
            if roi.size > 0:
                hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                v_mean = hsv[..., 2].mean()
                s_mean = hsv[..., 1].mean()
                
                # Zemin sızıntısı (S4): Karanlık, düşük doygunluk, yayvan (ıslak zemin/su)
                if v_mean < 80 and s_mean < 60 and w > h * 1.5:
                    o["kategori"] = "zemin_sizintisi"
                # Yapı/Kapı anomalisi: Dikey, ince uzun (açık kapı, direk vb.)
                elif h > w * 1.5:
                    o["kategori"] = "yapi_anomalisi"
                # Standart anomali
                else:
                    o["kategori"] = "yabanci_sabit_nesne"
            else:
                o["kategori"] = "yabanci_sabit_nesne"

        return {"ok": True, "nesneler": onayli, "aday": adaylar,
                "esik": round(esik, 1), "iceride": hz.iceride}


BIRLESTIR_PAYI = 20   # px - bu kadar yakin kutular tek nesnedir


def birlestir(nesneler: list[dict], pay: int = BIRLESTIR_PAYI) -> list[dict]:
    """Ustuste binen / bitisik kutulari tek nesneye toplar.

    Ayni cismin parcalari (cop kovasinin kapagi ile govdesi) ayri kontur
    veriyor; IoU olcumu bunu iki nesne sayinca dogru tespit dusuk puan aliyor.
    """
    kalan = list(nesneler)
    degisti = True
    while degisti:
        degisti = False
        for i in range(len(kalan)):
            for j in range(i + 1, len(kalan)):
                a, b = kalan[i], kalan[j]
                ax2, ay2 = a["x"] + a["w"], a["y"] + a["h"]
                bx2, by2 = b["x"] + b["w"], b["y"] + b["h"]
                if (a["x"] - pay < bx2 and b["x"] - pay < ax2 and
                        a["y"] - pay < by2 and b["y"] - pay < ay2):
                    x, y = min(a["x"], b["x"]), min(a["y"], b["y"])
                    x2, y2 = max(ax2, bx2), max(ay2, by2)
                    yeni = {"x": x, "y": y, "w": x2 - x, "h": y2 - y,
                            "area": (x2 - x) * (y2 - y),
                            "cx": x + (x2 - x) // 2, "cy": y + (y2 - y) // 2}
                    kalan = [k for n, k in enumerate(kalan) if n not in (i, j)] + [yeni]
                    degisti = True
                    break
            if degisti:
                break
    kalan.sort(key=lambda o: -o["area"])
    return kalan
