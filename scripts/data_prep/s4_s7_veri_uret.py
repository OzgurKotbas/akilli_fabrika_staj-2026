# -*- coding: utf-8 -*-
"""
S4-S7 Sentetik Test Verisi Üretici
===================================
Mevcut WP01/WP02 koridor referans kareleri üzerine
programatik anomali enjeksiyonu ile S4-S7 senaryoları için
gerçekçi test çiftleri üretir.

NOT: WP03'teki amfi/kapı uyumsuzluğu nedeniyle
     S2 senaryosu (kapı) WP01 üzerinde yeniden üretilmektedir.

KULLANIM:
    cd D:/STAJ/akilli_fabrika_staj-2026
    python scripts/data_prep/s4_s7_veri_uret.py

ÇIKTILAR:
    data/ip8_test/
        WP01_s4_sizinti.jpg        -- S4: Zemin su/yağ birikintisi
        WP01_s7_kablo.jpg          -- S7: Zemin uzatma kablosu
        WP02_s5_tup_yok.jpg        -- S5: Yangın tüpü yok (WP02 üzerinde)
        WP02_s6_levha_degis.jpg    -- S6: Uyarı levhası değişmiş
        WP02_s2_kapi_duzeltme.jpg  -- S2 düzeltme: Kapı anomalisi (WP02 kapısı)
    data/waypoints/referans_kareler/
        WP02_s5_tup_var.jpg        -- S5 referansı: Tüp mevcut hali
        WP02_s6_levha_normal.jpg   -- S6 referansı: Levha normal hali
"""

import sys
import json
import cv2
import numpy as np
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from scripts.core import config_okuyucu

ROOT   = config_okuyucu.PROJECT_ROOT
REF    = ROOT / "data" / "waypoints" / "referans_kareler"
OUT    = ROOT / "data" / "ip8_test"
OUT.mkdir(parents=True, exist_ok=True)

print("=" * 60)
print("  S4-S7 Sentetik Test Verisi Üretici")
print("=" * 60)


# ─────────────────────────────────────────────────────────────
# YARDIMCI: görüntüyü yükle
# ─────────────────────────────────────────────────────────────
def yukle(dosya: Path) -> np.ndarray:
    img = cv2.imread(str(dosya))
    if img is None:
        raise FileNotFoundError(f"Görüntü okunamadı: {dosya}")
    return img


# ─────────────────────────────────────────────────────────────
# S4 — Zemin Sızıntısı / Su Birikintisi (WP01 zemini)
# ─────────────────────────────────────────────────────────────
def uret_s4_sizinti():
    print("\n[S4] Zemin sızıntısı üretiliyor...")
    ref = yukle(REF / "WP01.jpg")
    h, w = ref.shape[:2]
    out = ref.copy()

    # Zeminin ortasında iki üst üste binen elips → su birikintisi
    overlay = out.copy()
    cx, cy = int(w * 0.38), int(h * 0.72)   # sarı çizgilerin solunda

    # Dış elips — soluk mavi-gri (yansıma)
    cv2.ellipse(overlay, (cx, cy), (130, 38), 10, 0, 360, (190, 175, 155), -1)
    # İç parlama — daha açık
    cv2.ellipse(overlay, (cx - 10, cy - 8), (55, 16), 10, 0, 360, (215, 205, 190), -1)

    # Alpha blend — gerçekçi geçiş
    cv2.addWeighted(overlay, 0.55, out, 0.45, 0, out)

    # Kenar bulanıklaştırma
    mask = np.zeros((h, w), np.uint8)
    cv2.ellipse(mask, (cx, cy), (130, 38), 10, 0, 360, 255, -1)
    mask_blur = cv2.GaussianBlur(mask, (41, 41), 0).astype(float) / 255.0
    out_f = out.astype(float)
    ref_f = ref.astype(float)
    out_blend = (out_f * mask_blur[:, :, None] +
                 ref_f * (1 - mask_blur[:, :, None])).astype(np.uint8)

    path = OUT / "WP01_s4_sizinti.jpg"
    cv2.imwrite(str(path), out_blend)
    print(f"  → {path.name}  ({cx},{cy}) elips ~260×76 px")

    gt = {"x": cx - 130, "y": cy - 38, "w": 260, "h": 76}
    return {"senaryo": "S4", "wp": "WP01", "dosya": str(path), "gt_bbox": gt,
            "tip": "zemin_sizintisi", "aciklama": "Zemin su/yağ birikintisi"}


# ─────────────────────────────────────────────────────────────
# S5 — Yangın Tüpü Eksik (WP02 sol duvarı)
# ─────────────────────────────────────────────────────────────
def uret_s5_tup():
    print("\n[S5] Yangın tüpü eksik üretiliyor...")
    ref = yukle(REF / "WP02.jpg")
    h, w = ref.shape[:2]

    # Referans: tüp VAR — kırmızı silindir sol duvara ekle
    ref_tup = ref.copy()
    tx, ty, tw, th = int(w * 0.07), int(h * 0.38), 38, 100

    # Tüp gövdesi (kırmızı)
    cv2.rectangle(ref_tup, (tx, ty), (tx + tw, ty + th), (25, 25, 200), -1)
    # Tüp başlığı (siyah metal)
    cv2.rectangle(ref_tup, (tx + 5, ty - 14), (tx + tw - 5, ty), (30, 30, 30), -1)
    # Tüp etiketi (beyaz şerit)
    cv2.rectangle(ref_tup, (tx + 3, ty + 20), (tx + tw - 3, ty + 48), (230, 230, 230), -1)
    cv2.putText(ref_tup, "YANGIN", (tx + 2, ty + 35),
                cv2.FONT_HERSHEY_SIMPLEX, 0.28, (20, 20, 20), 1)
    # Tüp altı (tutamaç)
    cv2.rectangle(ref_tup, (tx + 8, ty + th), (tx + tw - 8, ty + th + 10), (60, 60, 60), -1)

    # Gerçekçilik için hafif Gaussian blur
    roi = ref_tup[ty - 14:ty + th + 10, tx:tx + tw]
    ref_tup[ty - 14:ty + th + 10, tx:tx + tw] = cv2.GaussianBlur(roi, (3, 3), 0)

    ref_tup_path = REF / "WP02_s5_tup_var.jpg"
    cv2.imwrite(str(ref_tup_path), ref_tup)
    print(f"  → Referans (tüp var): {ref_tup_path.name}")

    # Test: tüp YOK — orijinal WP02 (tüp ekli değil)
    test_path = OUT / "WP02_s5_tup_yok.jpg"
    cv2.imwrite(str(test_path), ref)   # tüp olmadığı için normal referans
    print(f"  → Test (tüp yok): {test_path.name}")

    gt = {"x": tx, "y": ty - 14, "w": tw, "h": th + 24}
    return {"senaryo": "S5", "wp": "WP02_tup", "dosya": str(test_path),
            "referans_ozel": str(ref_tup_path),
            "gt_bbox": gt, "tip": "yangin_tupu_eksik",
            "aciklama": "Yangın tüpü duvardan alınmış — referansta tüp vardı",
            "not": "TERS SENARYO: referansta nesne VAR, testte YOK"}


# ─────────────────────────────────────────────────────────────
# S6 — Uyarı Levhası Değişikliği (WP02 sağ duvarı)
# ─────────────────────────────────────────────────────────────
def uret_s6_levha():
    print("\n[S6] Levha değişikliği üretiliyor...")
    ref = yukle(REF / "WP02.jpg")
    h, w = ref.shape[:2]

    # Referans: Yeşil ÇIKIŞ levhası sağ duvarın üst kısmında
    lx, ly, lw, lh = int(w * 0.72), int(h * 0.28), 90, 38

    ref_levha = ref.copy()
    cv2.rectangle(ref_levha, (lx, ly), (lx + lw, ly + lh), (25, 140, 25), -1)
    cv2.putText(ref_levha, "CIKIS ->", (lx + 4, ly + 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)
    # Levhaya ince beyaz çerçeve
    cv2.rectangle(ref_levha, (lx, ly), (lx + lw, ly + lh), (220, 220, 220), 1)

    ref_levha_path = REF / "WP02_s6_levha_normal.jpg"
    cv2.imwrite(str(ref_levha_path), ref_levha)
    print(f"  → Referans (yeşil levha): {ref_levha_path.name}")

    # Test: Levha değişmiş — sarı GIRIS levhası
    test_levha = ref_levha.copy()
    cv2.rectangle(test_levha, (lx, ly), (lx + lw, ly + lh), (10, 180, 220), -1)  # sarı
    cv2.putText(test_levha, "<- GIRIS", (lx + 4, ly + 24),
                cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 1)
    cv2.rectangle(test_levha, (lx, ly), (lx + lw, ly + lh), (220, 220, 220), 1)

    test_path = OUT / "WP02_s6_levha_degis.jpg"
    cv2.imwrite(str(test_path), test_levha)
    print(f"  → Test (sarı levha): {test_path.name}")

    gt = {"x": lx, "y": ly, "w": lw, "h": lh}
    return {"senaryo": "S6", "wp": "WP02_levha", "dosya": str(test_path),
            "referans_ozel": str(ref_levha_path),
            "gt_bbox": gt, "tip": "levha_degisikligi",
            "aciklama": "Uyarı levhası değiştirilmiş (ÇIKIŞ→GİRİŞ, yeşil→sarı)"}


# ─────────────────────────────────────────────────────────────
# S7 — Zemin Kablaj / Uzatma Kablosu (WP01)
# ─────────────────────────────────────────────────────────────
def uret_s7_kablo():
    print("\n[S7] Zemin kablo üretiliyor...")
    ref = yukle(REF / "WP01.jpg")
    h, w = ref.shape[:2]
    out = ref.copy()

    # Koridoru çapraz kesen uzatma kablosu
    # Sarı çizgilerin solundan karşı duvara uzanan çapraz
    np.random.seed(42)
    start = (int(w * 0.03), int(h * 0.68))
    end   = (int(w * 0.62), int(h * 0.60))

    # Ana kablo — koyu gri (plastik kılıf)
    cv2.line(out, start, end, (35, 32, 30), 7)

    # Kablo üzerinde hafif kıvrım efekti (4 kontrol noktası)
    for i in range(1, 4):
        t = i / 4.0
        mid_x = int(start[0] + (end[0] - start[0]) * t)
        mid_y = int(start[1] + (end[1] - start[1]) * t +
                    np.random.randint(-8, 8))
        cv2.circle(out, (mid_x, mid_y), 4, (40, 37, 35), -1)

    # Kablo uçları (açık gri fişler)
    cv2.circle(out, start, 9, (110, 105, 100), -1)
    cv2.circle(out, end,   9, (110, 105, 100), -1)

    # Zemin yansıması — kablonun altında hafif gölge
    shadow = out.copy()
    cv2.line(shadow, (start[0] + 2, start[1] + 4),
             (end[0] + 2, end[1] + 4), (18, 16, 14), 5)
    cv2.addWeighted(shadow, 0.35, out, 0.65, 0, out)

    path = OUT / "WP01_s7_kablo.jpg"
    cv2.imwrite(str(path), out)

    x_min = min(start[0], end[0]) - 10
    y_min = min(start[1], end[1]) - 12
    x_max = max(start[0], end[0]) + 10
    y_max = max(start[1], end[1]) + 12
    print(f"  → {path.name}  kablo: {start}→{end}")

    gt = {"x": x_min, "y": y_min, "w": x_max - x_min, "h": y_max - y_min}
    return {"senaryo": "S7", "wp": "WP01", "dosya": str(path), "gt_bbox": gt,
            "tip": "zemin_kablaj", "aciklama": "Koridoru çapraz kesen uzatma kablosu"}


# ─────────────────────────────────────────────────────────────
# S2 Düzeltme — Kapı Anomalisi WP01 üzerinde (WP03 düzeltmesi)
# ─────────────────────────────────────────────────────────────
def uret_s2_kapi_duzelt():
    print("\n[S2 DUZELTME] Kapı anomalisi WP01 üzerinde yeniden üretiliyor...")
    ref = yukle(REF / "WP01.jpg")
    h, w = ref.shape[:2]

    # WP01'in derinliğindeki kapı görünüyor (fotoğrafta var)
    # Kapıyı "açık" göstermek için kapı bölgesini aydınlat + kenar çiz
    out = ref.copy()

    # Kapı bölgesi: görüntünün derinliğinde, ortada gri kapı var
    kx, ky, kw, kh = int(w * 0.35), int(h * 0.28), int(w * 0.18), int(h * 0.28)

    # Kapı "açıldı" — soluk turuncu/sıcak ışık açıklığı simüle et
    acik = out[ky:ky + kh, kx:kx + kw].copy()
    acik = cv2.addWeighted(acik, 0.45,
                            np.full_like(acik, (80, 120, 180)), 0.55, 0)
    out[ky:ky + kh, kx:kx + kw] = acik

    # Kapı kenarı (belirgin değişim)
    cv2.rectangle(out, (kx, ky), (kx + kw, ky + kh), (70, 90, 130), 2)

    path = OUT / "WP01_s2_kapi_acik.jpg"
    cv2.imwrite(str(path), out)
    print(f"  → {path.name}  (WP03 yerine WP01 üzerinde kapı anomalisi)")

    gt = {"x": kx, "y": ky, "w": kw, "h": kh}
    return {"senaryo": "S2_duzeltme", "wp": "WP01",
            "dosya": str(path), "gt_bbox": gt,
            "tip": "kapi_anomalisi",
            "aciklama": "Kapı açık kalmış (WP01 üzerinde — WP03 sahne hatası nedeniyle)"}


# ─────────────────────────────────────────────────────────────
# ÇALIŞITIR
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sonuclar = []

    sonuclar.append(uret_s4_sizinti())
    sonuclar.append(uret_s5_tup())
    sonuclar.append(uret_s6_levha())
    sonuclar.append(uret_s7_kablo())
    sonuclar.append(uret_s2_kapi_duzelt())

    # etiketler_s4_s7.json kaydet
    etiket_path = OUT / "etiketler_s4_s7.json"
    with open(etiket_path, "w", encoding="utf-8") as f:
        json.dump({
            "tur": "s4_s7_sentetik_test",
            "tarih": "2026-09-07",
            "aciklama": "S4-S7 senaryoları için programatik anomali enjeksiyonuyla üretilmiş test çiftleri",
            "wp03_notu": "WP03 referans=amfi, test=kapı uyumsuzluğu nedeniyle S2 senaryosu WP01 üzerinde yeniden üretildi",
            "test_ciftleri": sonuclar
        }, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"  TAMAMLANDI — {len(sonuclar)} senaryo üretildi")
    for s in sonuclar:
        print(f"  [{s['senaryo']:12s}] {Path(s['dosya']).name}")
    print(f"  Etiket: {etiket_path.name}")
    print(f"{'=' * 60}")
