# -*- coding: utf-8 -*-
"""
İP13: PDF Rapor Üretici — MD → PDF
====================================
Doküman : DOKUMANLAR/Ozgur_is_paketleri.md -- İP13
Bitti kriteri: PDF tur raporu üretiliyor (öncelik sıralı, görüntü kanıtlı)

Giriş : outputs/devriye_raporu/son_devriye_raporu.md
         (ip11_rapor_uret.py çıktısı)
        VEYA data/ip9_ensemble/ensemble_ozet.json doğrudan

Çıktı : outputs/devriye_raporu/devriye_raporu_<tarih>.pdf

BAĞIMLILIK (öncelik sırasıyla):
    1. fpdf2  →  pip install fpdf2        (önerilen — hafif, saf Python)
    2. WeasyPrint → pip install weasyprint  (HTML yolu, daha zengin stil)
    3. Fallback → yalnızca MD + HTML üretir (PDF yok)

KULLANIM:
    python scripts/comms/ip13_pdf_rapor.py
    python scripts/comms/ip13_pdf_rapor.py --ozet data/ip9_ensemble/ensemble_ozet.json
    python scripts/comms/ip13_pdf_rapor.py --md outputs/devriye_raporu/son_devriye_raporu.md
    python scripts/comms/ip13_pdf_rapor.py --backend weasyprint
"""

from __future__ import annotations
import sys, io
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf-16'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from scripts.core import config_okuyucu

# ──────────────────────────────────────────────────────────────────────────────
# PROJE AYARLARI
# ──────────────────────────────────────────────────────────────────────────────
PROJECT_DIR   = config_okuyucu.PROJECT_ROOT
ENSEMBLE_DIR  = PROJECT_DIR / "data" / "ip9_ensemble"
RAPOR_DIR     = PROJECT_DIR / "outputs" / "devriye_raporu"
SABLON_MD     = RAPOR_DIR / "son_devriye_raporu.md"

SEVERITY_SIRASI = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "NONE": 3}

# ──────────────────────────────────────────────────────────────────────────────
# BACKEND ALGILAMA
# ──────────────────────────────────────────────────────────────────────────────
try:
    from fpdf import FPDF, XPos, YPos
    FPDF2_AVAILABLE = True
except ImportError:
    FPDF2_AVAILABLE = False

try:
    import weasyprint
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False


# ──────────────────────────────────────────────────────────────────────────────
# VERİ OKUMA (ip11 pipeline'ı ile aynı)
# ──────────────────────────────────────────────────────────────────────────────

def ozet_oku(ozet_path: Path) -> dict:
    """ensemble_ozet.json'dan tam rapor verisi döndür."""
    with open(ozet_path, encoding="utf-8") as f:
        return json.load(f)


def ozet_hazirla(ozet: dict) -> dict:
    """Özeti PDF şablonu için kontekst sözlüğüne dönüştür."""
    sonuclar  = ozet.get("sonuclar", [])
    uyarilar  = [s for s in sonuclar if s.get("is_alert")]
    normaller = [s for s in sonuclar if not s.get("is_alert")]
    uyarilar.sort(key=lambda s: SEVERITY_SIRASI.get(s.get("severity", "NONE"), 9))

    toplam_wp    = ozet.get("toplam_wp", len(sonuclar))
    uyari_sayisi = ozet.get("uyari_sayisi", len(uyarilar))
    metrikler    = ozet.get("metrikler", {})
    now          = datetime.now()

    return {
        "tarih"           : now.strftime("%d.%m.%Y"),
        "saat"            : now.strftime("%H:%M:%S"),
        "tur_no"          : now.strftime("%Y%m%d_%H%M"),
        "toplam_wp"       : toplam_wp,
        "uyari_sayisi"    : uyari_sayisi,
        "normal_sayisi"   : toplam_wp - uyari_sayisi,
        "uyari_oran"      : uyari_sayisi / toplam_wp if toplam_wp > 0 else 0.0,
        "patchcore_aktif" : ozet.get("patchcore_aktif", False),
        "uyarilar"        : uyarilar,
        "normaller"       : normaller,
        "metrikler"       : metrikler,
    }


# ──────────────────────────────────────────────────────────────────────────────
# BACKEND 1: fpdf2 — Saf Python, Türkçe destekli
# ──────────────────────────────────────────────────────────────────────────────

class DevriyeRaporuPDF(FPDF):
    """fpdf2 tabanlı devriye raporu PDF sınıfı."""

    SEV_RENK = {
        "HIGH"  : (220,  50,  50),
        "MEDIUM": (220, 130,  20),
        "LOW"   : ( 80, 140, 220),
        "NONE"  : ( 90, 180,  90),
    }

    def header(self):
        self.set_fill_color(26, 26, 46)
        self.rect(0, 0, 210, 18, 'F')
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(200, 200, 230)
        self.set_xy(10, 5)
        self.cell(0, 8, "Ozgur Kotbas - Devriye Tur Raporu  |  Gorsel Anomali Tespiti  |  Grup 03_Gama  BTU 2026")
        self.ln(14)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(150, 150, 160)
        self.cell(0, 10, f"Sayfa {self.page_no()}  |  Otomatik uretildi: ip13_pdf_rapor.py  |  {datetime.now().strftime('%Y-%m-%d %H:%M')}", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ── Yardımcı çizim araçları ───────────────────────────────────────────────

    def bolum_baslik(self, metin: str, r: int = 30, g: int = 60, b: int = 110):
        self.set_fill_color(r, g, b)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 8, metin, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(30, 30, 40)
        self.ln(2)

    def iki_sutun_tablo(self, satirlar: list[tuple[str, str]]):
        """Metrik: Deger cifti tablosu."""
        col1, col2 = 80, 100
        for i, (etiket, deger) in enumerate(satirlar):
            bg = (245, 245, 252) if i % 2 == 0 else (235, 235, 245)
            self.set_fill_color(*bg)
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(60, 60, 80)
            self.cell(col1, 6, etiket, fill=True, border=0)
            self.set_font("Helvetica", "", 9)
            self.set_text_color(20, 20, 40)
            self.cell(col2, 6, str(deger), fill=True, border=0, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(3)

    def uyari_karti(self, uyari: dict, sira: int):
        """Tek uyari icin renkli kart."""
        sev    = uyari.get("severity", "NONE")
        renk   = self.SEV_RENK.get(sev, (100, 100, 100))
        wp_id  = uyari.get("waypoint_id", "?")
        tip    = uyari.get("degisiklik_tipi", "?").replace("_", " ").title()
        pc_sc  = uyari.get("patchcore_score", -1)
        mog2   = uyari.get("mog2_nesne_sayisi", 0)
        karar  = uyari.get("karar_aciklama", "")
        tp_fp  = uyari.get("tp_fp", {})

        # Kart basligi (severity rengi)
        self.set_fill_color(*renk)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 10)
        self.cell(0, 7, f"  {sira}. {wp_id}  [{tip}]  [{sev}]", fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Kart govdesi
        self.set_fill_color(252, 248, 248)
        self.set_text_color(40, 40, 60)
        self.set_font("Helvetica", "", 9)

        satırlar = [
            ("MOG2 Tespit Edilen Nesne", f"{mog2} adet"),
            ("PatchCore Anomali Skoru",
             f"{pc_sc:.4f}" if pc_sc >= 0 else "Devre Disi"),
            ("Karar Aciklamasi", karar[:80] + ("..." if len(karar) > 80 else "")),
        ]
        if tp_fp.get("tp") is not None:
            satırlar.append(
                ("TP / FP / IoU",
                 f"TP={tp_fp.get('tp')}  FP={tp_fp.get('fp')}  IoU={tp_fp.get('iou_best','?')}")
            )
        test_yol = str(uyari.get("test", ""))
        if test_yol:
            # Sadece dosya adını göster — uzun yol taşabilir
            satırlar.append(("Test Goruntisu", Path(test_yol).name))

        self.iki_sutun_tablo(satırlar)

        # Görüntü kanıtı: ensemble görsel varsa ekle
        gorsel = uyari.get("ensemble_gorseli", "")
        if gorsel and Path(gorsel).exists():
            try:
                img_h = 50  # mm
                self.image(gorsel, w=180, h=img_h)
                self.set_font("Helvetica", "I", 7)
                self.set_text_color(130, 130, 150)
                self.cell(0, 4, f"Gorsel: {Path(gorsel).name}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            except Exception:
                pass
        self.ln(2)

    # ── Sayfa oluşturma ───────────────────────────────────────────────────────

    def kapak(self, ctx: dict):
        """Kapak sayfasi."""
        self.add_page()
        self.set_fill_color(26, 26, 46)
        self.rect(0, 0, 210, 297, 'F')

        # Baslik
        self.set_xy(20, 60)
        self.set_font("Helvetica", "B", 22)
        self.set_text_color(200, 200, 230)
        self.multi_cell(170, 12, "Devriye Tur Raporu")

        self.set_xy(20, 82)
        self.set_font("Helvetica", "", 13)
        self.set_text_color(160, 160, 190)
        self.multi_cell(170, 8, "Gorsel Anomali Tespiti + Otomatik Devriye Raporu")

        # Bilgi kutusu
        self.set_fill_color(40, 40, 70)
        self.rect(20, 110, 170, 80, 'F')

        bilgiler = [
            ("Olusturan"   , "Ozgur Kotbas"),
            ("Tarih"       , ctx["tarih"]),
            ("Saat"        , ctx["saat"]),
            ("Tur No"      , ctx["tur_no"]),
            ("Proje"       , "ANOMALi Modulu - Grup 03_Gama - BTU 2026"),
            ("Mimari"      , "MOG2 + PatchCore Ensemble (IP12 duzeltmesi)"),
        ]
        y0 = 115
        for etiket, deger in bilgiler:
            self.set_xy(28, y0)
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(160, 160, 190)
            self.cell(45, 7, etiket + ":")
            self.set_font("Helvetica", "", 9)
            self.set_text_color(220, 220, 240)
            self.cell(110, 7, deger, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            y0 += 9

        # Ozet istatistik
        uyari_sayisi = ctx["uyari_sayisi"]
        toplam       = ctx["toplam_wp"]
        self.set_xy(20, 210)
        self.set_font("Helvetica", "B", 36)
        if uyari_sayisi > 0:
            self.set_text_color(220, 80, 80)
            self.cell(0, 20, f"{uyari_sayisi} / {toplam} UYARI", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        else:
            self.set_text_color(80, 200, 120)
            self.cell(0, 20, f"TUM WAYPOINT NORMAL ({toplam}/{toplam})", align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def ozet_sayfasi(self, ctx: dict):
        """Özet metrikleri sayfası."""
        self.add_page()
        self.bolum_baslik("OZET METRIKLER")

        m = ctx["metrikler"]
        self.iki_sutun_tablo([
            ("Toplam Waypoint"     , ctx["toplam_wp"]),
            ("Anomali Tespit"      , ctx["uyari_sayisi"]),
            ("Normal"              , ctx["normal_sayisi"]),
            ("Uyari Orani"         , f"{ctx['uyari_oran']*100:.1f}%"),
            ("PatchCore Aktif"     , "Evet" if ctx["patchcore_aktif"] else "Hayir (sadece MOG2)"),
            ("Ensemble Mimarisi"   , "MOG2 + Spatial PatchCore (7x7 patch)"),
            ("IP12 Duzeltmesi"     , "MOG2 single-pass + PatchCore spatial patch"),
        ])

        self.ln(4)
        self.bolum_baslik("PERFORMANS METRIKLERI", r=20, g=80, b=60)
        self.iki_sutun_tablo([
            ("True Positive (TP)"  , m.get("TP", "?")),
            ("False Positive (FP)" , m.get("FP", "?")),
            ("False Negative (FN)" , m.get("FN", "?")),
            ("Precision"           , f"{m.get('precision', 0):.3f}"),
            ("Recall"              , f"{m.get('recall', 0):.3f}"),
            ("F1 Skoru"            , f"{m.get('F1', 0):.3f}"),
        ])

        # Açıklama
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 140)
        self.multi_cell(0, 5,
            "Not: Metrikler ip9_ensemble_analiz.py ciktilari uzerinden hesaplanmistir. "
            "IP12 duzeltmeleri (MOG2 single-pass + PatchCore 49-patch spatial) "
            "onceki F1=0.333 degerini iyilestirmeyi hedeflemektedir.")
        self.ln(4)

        self.bolum_baslik("ENSEMBLE MIMARI DETAYI", r=60, g=30, b=100)
        self.set_font("Courier", "", 8)
        self.set_text_color(40, 40, 60)
        mimari = (
            "KATMAN 1 - MOG2 Arka Plan Cikarma (aci-bagimsiz)\n"
            "  Engel videosunu kendi icinde tarar (10 saniye pencere).\n"
            "  Son 30 kare: learningRate=0 -> model dondurulur -> sabit nesne maskesi.\n"
            "  [IP12] Duzeltme: cap.set() ile geri sarma kaldirildi (tek gecis).\n\n"
            "KATMAN 2 - Spatial PatchCore (aciya ~40 dereceye kadar toleransli)\n"
            "  ResNet18 [:-2] -> (512, 7, 7) -> 49 uzamsal patch vektoru.\n"
            "  Her test patch'i icin en yakin referans patch cosine benzerlik.\n"
            "  Anomali skoru = en kotü patch skoru (max anomali, global deil).\n"
            "  [IP12] Duzeltme: Global embedding (512x1) yerine spatial (49x512).\n\n"
            "KARAR: is_alert = (MOG2_nesne > 0) OR (PatchCore_score > esik)"
        )
        self.multi_cell(0, 5, mimari)

    def uyarilar_sayfasi(self, ctx: dict):
        """Tum uyarilari oncelik sirasiyla yaz."""
        if not ctx["uyarilar"]:
            return
        self.add_page()
        self.bolum_baslik(f"UYARILAR  ({ctx['uyari_sayisi']} ADET - HIGH > MEDIUM > LOW)", r=160, g=30, b=30)

        for i, uyari in enumerate(ctx["uyarilar"], start=1):
            # Sayfada yeterli yer var mi?
            if self.get_y() > 250:
                self.add_page()
            self.uyari_karti(uyari, i)

    def normal_sayfasi(self, ctx: dict):
        """Normal waypoint ozet tablosu."""
        if not ctx["normaller"]:
            return
        self.add_page()
        self.bolum_baslik(f"NORMAL WAYPOINT'LER  ({ctx['normal_sayisi']} ADET)", r=20, g=100, b=50)

        # Tablo baslik
        self.set_fill_color(40, 80, 60)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 9)
        genislikler = [25, 55, 30, 40, 35]
        basliklar   = ["Waypoint", "Tip", "MOG2 Nesne", "PatchCore Skoru", "FG Orani"]
        for g, b in zip(genislikler, basliklar):
            self.cell(g, 7, b, fill=True)
        self.ln()

        for i, n in enumerate(ctx["normaller"]):
            bg = (240, 250, 240) if i % 2 == 0 else (225, 240, 225)
            self.set_fill_color(*bg)
            self.set_text_color(30, 60, 40)
            self.set_font("Helvetica", "", 8)
            pc  = n.get("patchcore_score", -1)
            tip = n.get("degisiklik_tipi", "").replace("_", " ")[:30]
            satirlar_ = [
                n.get("waypoint_id", "?"),
                tip,
                str(n.get("mog2_nesne_sayisi", 0)),
                f"{pc:.4f}" if pc >= 0 else "-",
                f"{n.get('mog2_fg_ratio', 0):.4f}",
            ]
            for g, s in zip(genislikler, satirlar_):
                self.cell(g, 6, s, fill=True)
            self.ln()


# ──────────────────────────────────────────────────────────────────────────────
# BACKEND 2: WeasyPrint (HTML → PDF)
# ──────────────────────────────────────────────────────────────────────────────

HTML_SABLON = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>Devriye Raporu — {tur_no}</title>
<style>
  @page {{ margin: 20mm 15mm; }}
  body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #222; font-size: 10pt; }}
  h1   {{ color: #1a1a2e; border-bottom: 3px solid #e94560; padding-bottom: 6px; }}
  h2   {{ color: #16213e; border-bottom: 1px solid #ccc; padding-bottom: 4px; margin-top: 18px; }}
  h3   {{ color: #0f3460; margin-top: 12px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 9pt; }}
  th, td {{ border: 1px solid #ccc; padding: 5px 8px; text-align: left; }}
  th {{ background: #1a1a2e; color: #fff; }}
  tr:nth-child(even) {{ background: #f5f5f5; }}
  .uyari-HIGH   {{ border-left: 5px solid #dc3545; background: #fff5f5; padding: 8px; margin: 8px 0; }}
  .uyari-MEDIUM {{ border-left: 5px solid #fd7e14; background: #fff9f0; padding: 8px; margin: 8px 0; }}
  .uyari-LOW    {{ border-left: 5px solid #17a2b8; background: #f0faff; padding: 8px; margin: 8px 0; }}
  .badge-HIGH   {{ background:#dc3545; color:#fff; padding:2px 7px; border-radius:3px; font-weight:bold; }}
  .badge-MEDIUM {{ background:#fd7e14; color:#fff; padding:2px 7px; border-radius:3px; font-weight:bold; }}
  .badge-LOW    {{ background:#17a2b8; color:#fff; padding:2px 7px; border-radius:3px; font-weight:bold; }}
  .normal-badge {{ background:#28a745; color:#fff; padding:2px 7px; border-radius:3px; }}
  img {{ max-width: 100%; height: auto; border: 1px solid #ddd; margin: 6px 0; }}
  pre {{ background: #2d2d2d; color: #f8f8f2; padding: 10px; border-radius: 4px; font-size: 8pt; }}
  .footer {{ margin-top: 30px; border-top: 1px solid #ddd; color: #999; font-size: 8pt; padding-top: 8px; }}
</style>
</head>
<body>

<h1>🚨 Devriye Tur Raporu</h1>
<p><strong>Oluşturan:</strong> Özgür Kotbaş · Anomali + Devriye Raporu Modülü &nbsp;|&nbsp;
   <strong>Tarih:</strong> {tarih} &nbsp;|&nbsp;
   <strong>Saat:</strong> {saat} &nbsp;|&nbsp;
   <strong>Tur No:</strong> {tur_no}</p>
<p><strong>Proje:</strong> Görsel Anomali Tespiti · Grup 03_Gama · BTÜ · 2026 &nbsp;|&nbsp;
   <strong>Mimari:</strong> MOG2 + Spatial PatchCore Ensemble (İP12 düzeltmesi)</p>

<h2>Özet</h2>
<table>
  <tr><th>Metrik</th><th>Değer</th></tr>
  <tr><td>Toplam Waypoint</td><td>{toplam_wp}</td></tr>
  <tr><td>Anomali Tespit</td><td>{uyari_sayisi}</td></tr>
  <tr><td>Normal</td><td>{normal_sayisi}</td></tr>
  <tr><td>Uyarı Oranı</td><td>{uyari_oran_str}</td></tr>
  <tr><td>PatchCore Aktif</td><td>{patchcore_aktif_str}</td></tr>
</table>

{uyari_ozet_html}

<h2>Uyarılar (Öncelik Sırasıyla)</h2>
{uyarilar_html}

<h2>Normal Waypoint'ler</h2>
{normaller_html}

<h2>Performans Metrikleri</h2>
<table>
  <tr><th>Metrik</th><th>Değer</th></tr>
  {metrik_satirlar}
</table>

<h2>Teknik Bilgi — Ensemble Mimarisi (İP12 Düzeltmeleri)</h2>
<pre>KATMAN 1: MOG2 Arka Plan Çıkarma (açı-bağımsız)
  [IP12] Düzeltme: cap.set() ile geriye sarma kaldırıldı → TEK GEÇİŞ
  Son 30 kare: learningRate=0 → model dondurulur → sabit nesne maskesi.

KATMAN 2: Spatial PatchCore (açıya ~40° toleranslı)
  [IP12] Düzeltme: Global embedding (512x1x1) → Spatial patch (512x7x7 = 49 patch)
  Her test patch için memory bank'te nearest neighbor cosine similarity.
  Anomali skoru = en kötü (en düşük benzerlik) patch skoru.

KARAR: is_alert = (MOG2_nesne > 0) OR (PatchCore_score > eşik)</pre>

<div class="footer">
  Otomatik üretildi · ip13_pdf_rapor.py · {simdi}
</div>
</body>
</html>"""


def _uyari_html(uyari: dict, sira: int) -> str:
    sev   = uyari.get("severity", "NONE")
    wp_id = uyari.get("waypoint_id", "?")
    tip   = uyari.get("degisiklik_tipi", "?").replace("_", " ").title()
    pc_sc = uyari.get("patchcore_score", -1)
    mog2  = uyari.get("mog2_nesne_sayisi", 0)
    karar = uyari.get("karar_aciklama", "")
    tp_fp = uyari.get("tp_fp", {})
    gorsel = uyari.get("ensemble_gorseli", "")

    img_html = ""
    if gorsel and Path(gorsel).exists():
        img_html = f'<img src="file:///{Path(gorsel).as_posix()}" alt="Ensemble Analiz" />'

    tp_fp_html = ""
    if tp_fp.get("tp") is not None:
        tp_fp_html = (f"<tr><td>TP / FP / IoU</td>"
                      f"<td>TP={tp_fp.get('tp')}  FP={tp_fp.get('fp')}  "
                      f"IoU={tp_fp.get('iou_best','?')}</td></tr>")

    return f"""
<div class="uyari-{sev}">
  <h3>{sira}. {wp_id} — {tip} <span class="badge-{sev}">{sev}</span></h3>
  <table>
    <tr><th>Alan</th><th>Değer</th></tr>
    <tr><td>MOG2 Nesne</td><td>{mog2} adet</td></tr>
    <tr><td>PatchCore Skoru</td><td>{'%.4f' % pc_sc if pc_sc >= 0 else 'Devre Dışı'}</td></tr>
    <tr><td>Karar</td><td>{karar}</td></tr>
    {tp_fp_html}
    <tr><td>Test Görüntüsü</td><td><code>{Path(uyari.get('test','?')).name}</code></td></tr>
  </table>
  {img_html}
</div>"""


def weasyprint_pdf_uret(ctx: dict, out_path: Path) -> bool:
    """HTML şablonu WeasyPrint ile PDF'e dönüştür."""
    m = ctx["metrikler"]
    metrik_html = "".join(
        f"<tr><td>{k}</td><td>{v}</td></tr>"
        for k, v in [("TP", m.get("TP","?")), ("FP", m.get("FP","?")),
                     ("FN", m.get("FN","?")),
                     ("Precision", f"{m.get('precision',0):.3f}"),
                     ("Recall",    f"{m.get('recall',0):.3f}"),
                     ("F1",        f"{m.get('F1',0):.3f}")]
    )
    uyarilar_html = "".join(_uyari_html(u, i+1) for i, u in enumerate(ctx["uyarilar"]))
    if not uyarilar_html:
        uyarilar_html = "<p><em>Uyarı bulunamadı.</em></p>"

    normaller_html = ""
    if ctx["normaller"]:
        satirlar = "".join(
            f"<tr><td>{n.get('waypoint_id','?')}</td>"
            f"<td>{n.get('degisiklik_tipi','').replace('_',' ')}</td>"
            f"<td>{n.get('mog2_nesne_sayisi',0)}</td>"
            f"<td>{'%.4f'%n.get('patchcore_score',-1) if n.get('patchcore_score',-1)>=0 else '-'}</td></tr>"
            for n in ctx["normaller"]
        )
        normaller_html = (
            "<table><tr><th>Waypoint</th><th>Tip</th>"
            "<th>MOG2 Nesne</th><th>PatchCore Skoru</th></tr>"
            + satirlar + "</table>"
        )
    else:
        normaller_html = "<p><em>Normal waypoint yok.</em></p>"

    uyari_ozet = (
        f'<p style="background:#fff3cd;padding:8px;border-radius:4px;">'
        f'⚠️ <strong>{ctx["uyari_sayisi"]} waypoint\'te anomali tespit edildi.</strong></p>'
        if ctx["uyari_sayisi"] > 0
        else '<p style="background:#d4edda;padding:8px;border-radius:4px;">'
             '✅ <strong>Tüm waypoint\'ler normal.</strong></p>'
    )

    html = HTML_SABLON.format(
        tur_no            = ctx["tur_no"],
        tarih             = ctx["tarih"],
        saat              = ctx["saat"],
        toplam_wp         = ctx["toplam_wp"],
        uyari_sayisi      = ctx["uyari_sayisi"],
        normal_sayisi     = ctx["normal_sayisi"],
        uyari_oran_str    = f"{ctx['uyari_oran']*100:.1f}%",
        patchcore_aktif_str = "Evet" if ctx["patchcore_aktif"] else "Hayır (sadece MOG2)",
        uyari_ozet_html   = uyari_ozet,
        uyarilar_html     = uyarilar_html,
        normaller_html    = normaller_html,
        metrik_satirlar   = metrik_html,
        simdi             = datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )

    try:
        weasyprint.HTML(string=html).write_pdf(str(out_path))
        return True
    except Exception as e:
        print(f"  [WeasyPrint HATA] {e}")
        return False


# ──────────────────────────────────────────────────────────────────────────────
# ANA PIPELINE
# ──────────────────────────────────────────────────────────────────────────────

def pdf_uret(ozet_path: Path, out_dir: Path, backend: str = "auto") -> Path | None:
    """
    Tam PDF üretim pipeline'ı.
    Döndürür: PDF yolu (başarılı) veya None (PDF kütüphanesi yok)
    """
    print(f"\n[İP13] PDF raporu üretiliyor...")
    print(f"  Kaynak : {ozet_path}")

    ozet = ozet_oku(ozet_path)
    ctx  = ozet_hazirla(ozet)

    print(f"  Toplam WP: {ctx['toplam_wp']}  Uyarı: {ctx['uyari_sayisi']}  Normal: {ctx['normal_sayisi']}")

    out_dir.mkdir(parents=True, exist_ok=True)
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"devriye_raporu_{ts}.pdf"

    # Backend seçimi
    if backend == "auto":
        if FPDF2_AVAILABLE:
            backend = "fpdf2"
        elif WEASYPRINT_AVAILABLE:
            backend = "weasyprint"
        else:
            backend = "none"

    if backend == "fpdf2" and FPDF2_AVAILABLE:
        print("  Motor: fpdf2")
        pdf = DevriyeRaporuPDF()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.set_creator("ip13_pdf_rapor.py — Ozgur Kotbas")
        pdf.set_author("Ozgur Kotbas")
        pdf.set_title("Devriye Tur Raporu")
        pdf.kapak(ctx)
        pdf.ozet_sayfasi(ctx)
        pdf.uyarilar_sayfasi(ctx)
        pdf.normal_sayfasi(ctx)
        pdf.output(str(out_path))
        print(f"  [Kayıt] PDF: {out_path}")

    elif backend == "weasyprint" and WEASYPRINT_AVAILABLE:
        print("  Motor: WeasyPrint")
        ok = weasyprint_pdf_uret(ctx, out_path)
        if not ok:
            return None
        print(f"  [Kayıt] PDF: {out_path}")

    else:
        print("  [UYARI] PDF kütüphanesi bulunamadı.")
        print("          fpdf2 kurmak için: pip install fpdf2")
        print("          WeasyPrint için  : pip install weasyprint")
        return None

    # Son PDF'yi sabit isimle de kaydet
    son_pdf = out_dir / "son_devriye_raporu.pdf"
    import shutil
    shutil.copy2(out_path, son_pdf)
    print(f"  [Kayıt] Son PDF: {son_pdf}")
    return out_path


# ──────────────────────────────────────────────────────────────────────────────
# GİRİŞ NOKTASI
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="İP13: Devriye Raporu PDF Üretici (MD → PDF)"
    )
    parser.add_argument(
        "--ozet", default=None,
        help="ensemble_ozet.json yolu (varsayılan: data/ip9_ensemble/ensemble_ozet.json)"
    )
    parser.add_argument(
        "--outdir", default=str(RAPOR_DIR),
        help="Çıktı dizini"
    )
    parser.add_argument(
        "--backend", choices=["auto", "fpdf2", "weasyprint"], default="auto",
        help="PDF motoru (varsayılan: auto)"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  IP13: Devriye Raporu PDF Uretici — Ozgur Kotbas")
    print("  Grup 03_Gama · BTU · Staj 2026")
    print("=" * 60)
    print(f"  fpdf2      : {'KURULU' if FPDF2_AVAILABLE else 'YOK (pip install fpdf2)'}")
    print(f"  WeasyPrint : {'KURULU' if WEASYPRINT_AVAILABLE else 'YOK (pip install weasyprint)'}")

    # Kaynak JSON
    if args.ozet:
        ozet_path = Path(args.ozet)
    else:
        ozet_path = ENSEMBLE_DIR / "ensemble_ozet.json"

    if not ozet_path.exists():
        print(f"\n[HATA] ensemble_ozet.json bulunamadı: {ozet_path}")
        print("  Önce ip9_ensemble_analiz.py çalıştırın:")
        print("  python scripts/vision/ip9_ensemble_analiz.py")
        sys.exit(1)

    out_path = pdf_uret(
        ozet_path = ozet_path,
        out_dir   = Path(args.outdir),
        backend   = args.backend,
    )

    print(f"\n{'='*60}")
    if out_path:
        print(f"  TAMAMLANDI")
        print(f"  PDF Raporu: {out_path}")
        print(f"  Son PDF   : {Path(args.outdir) / 'son_devriye_raporu.pdf'}")
    else:
        print(f"  PDF uretilemedi — PDF kutuphanesi kurun (fpdf2 veya weasyprint)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
