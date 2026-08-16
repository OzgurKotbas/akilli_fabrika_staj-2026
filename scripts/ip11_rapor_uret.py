# -*- coding: utf-8 -*-
"""
İP11: Devriye Raporu v1 — Jinja2 → MD
========================================
Doküman : DOKUMANLAR/Ozgur_is_paketleri.md -- İP11
Bitti kriteri: Örnek tur raporu repoda

Rapor içeriği:
  - Uyarılar (HIGH → MEDIUM → LOW sırası, görüntü kanıtlı)
  - Normal waypoint'ler
  - Performans metrikleri (TP/FP/Precision/Recall/F1)
  - Ensemble mimarisi özeti

Kaynak: ip9_ensemble_analiz.py çıktıları (data/ip9_ensemble/*.json)
Çıktı : outputs/devriye_raporu/devriye_raporu_<tarih>.md
        outputs/devriye_raporu/devriye_raporu_<tarih>.html (opsiyonel)

KULLANIM:
    python scripts/ip11_rapor_uret.py

    # Belirli özet JSON'dan:
    python scripts/ip11_rapor_uret.py --ozet data/ip9_ensemble/ensemble_ozet.json

    # HTML de üret:
    python scripts/ip11_rapor_uret.py --html

    # Şablonu özelleştir:
    python scripts/ip11_rapor_uret.py --sablon docs/baska_sablon.md.j2

BAĞIMLILIK:
    pip install jinja2
    (jinja2 yoksa basit string format fallback çalışır)
"""

from __future__ import annotations
import sys, io
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf-16'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

# Jinja2 isteğe bağlı — yoksa basit fallback
try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False
    print("[UYARI] jinja2 bulunamadi — basit MD formatına geçiliyor.")
    print("        Kurmak için: pip install jinja2")

# ──────────────────────────────────────────────────────────────────────────────
# PROJE AYARLARI
# ──────────────────────────────────────────────────────────────────────────────
PROJECT_DIR  = Path(__file__).resolve().parent.parent
ENSEMBLE_DIR = PROJECT_DIR / "data" / "ip9_ensemble"
SABLON_PATH  = PROJECT_DIR / "docs" / "rapor_sablonu.md.j2"
OUT_DIR      = PROJECT_DIR / "outputs" / "devriye_raporu"


SEVERITY_SIRASI  = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "NONE": 3}
PATCHCORE_ESIK   = 0.50


# ──────────────────────────────────────────────────────────────────────────────
# VERİ OKUMA
# ──────────────────────────────────────────────────────────────────────────────

def ozet_json_oku(ozet_path: Path) -> dict:
    """ensemble_ozet.json dosyasını oku ve döndür."""
    with open(ozet_path, encoding="utf-8") as f:
        return json.load(f)


def bireysel_json_topla() -> dict | None:
    """
    ensemble_ozet.json yoksa bireysel WP JSON'larından sentetik özet oluştur.
    """
    sonuc_listesi = []
    for jp in sorted(ENSEMBLE_DIR.glob("*_ensemble_sonuc.json")):
        with open(jp, encoding="utf-8") as f:
            sonuc_listesi.append(json.load(f))

    if not sonuc_listesi:
        return None

    uyari_sayisi = sum(1 for s in sonuc_listesi if s.get("is_alert"))
    tp_toplam    = sum(s.get("tp_fp", {}).get("tp") or 0 for s in sonuc_listesi
                       if s.get("tp_fp", {}).get("tp") is not None)
    fp_toplam    = sum(s.get("tp_fp", {}).get("fp") or 0 for s in sonuc_listesi
                       if s.get("tp_fp", {}).get("fp") is not None)
    fn_toplam    = sum(s.get("tp_fp", {}).get("fn") or 0 for s in sonuc_listesi
                       if s.get("tp_fp", {}).get("fn") is not None)
    prec = tp_toplam / (tp_toplam + fp_toplam) if (tp_toplam + fp_toplam) > 0 else 0.0
    rec  = tp_toplam / (tp_toplam + fn_toplam) if (tp_toplam + fn_toplam) > 0 else 0.0
    f1   = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0

    return {
        "tur"           : "ip11_rapor",
        "tarih"         : datetime.now().isoformat(),
        "toplam_wp"     : len(sonuc_listesi),
        "uyari_sayisi"  : uyari_sayisi,
        "mimari"        : "MOG2 + PatchCore Ensemble",
        "patchcore_aktif": any(s.get("patchcore_aktif") for s in sonuc_listesi),
        "metrikler"     : {
            "TP": tp_toplam, "FP": fp_toplam, "FN": fn_toplam,
            "precision": round(prec, 3),
            "recall"   : round(rec, 3),
            "F1"       : round(f1, 3),
        },
        "sonuclar": sonuc_listesi,
    }


# ──────────────────────────────────────────────────────────────────────────────
# RAPOR ŞABLONu HAZIRLA
# ──────────────────────────────────────────────────────────────────────────────

def ozet_to_sablon_kontekst(ozet: dict, kaynak_json: str) -> dict:
    """
    ensemble_ozet.json verisini Jinja2 şablonu için hazırla.
    Uyarıları severity sırasına göre sırala.
    """
    sonuclar = ozet.get("sonuclar", [])

    uyarilar  = [s for s in sonuclar if s.get("is_alert")]
    normaller = [s for s in sonuclar if not s.get("is_alert")]

    # Uyarıları öncelik sırası: HIGH > MEDIUM > LOW > NONE
    uyarilar.sort(
        key=lambda s: SEVERITY_SIRASI.get(s.get("severity", "NONE"), 9)
    )

    toplam_wp     = ozet.get("toplam_wp", len(sonuclar))
    uyari_sayisi  = ozet.get("uyari_sayisi", len(uyarilar))
    normal_sayisi = toplam_wp - uyari_sayisi
    uyari_oran    = uyari_sayisi / toplam_wp if toplam_wp > 0 else 0.0

    metrikler = ozet.get("metrikler", {
        "TP": 0, "FP": 0, "FN": 0,
        "precision": 0.0, "recall": 0.0, "F1": 0.0
    })

    now = datetime.now()
    return {
        "tarih"           : now.strftime("%d %B %Y"),
        "saat"            : now.strftime("%H:%M:%S"),
        "tur_no"          : now.strftime("%Y%m%d_%H%M"),
        "toplam_wp"       : toplam_wp,
        "uyari_sayisi"    : uyari_sayisi,
        "normal_sayisi"   : normal_sayisi,
        "uyari_oran"      : uyari_oran,
        "patchcore_aktif" : ozet.get("patchcore_aktif", False),
        "patchcore_esik"  : PATCHCORE_ESIK,
        "uyarilar"        : uyarilar,
        "normaller"       : normaller,
        "metrikler"       : metrikler,
        "kaynak_json"     : kaynak_json,
    }


# ──────────────────────────────────────────────────────────────────────────────
# JINJA2 RAPOR ÜRETİMİ
# ──────────────────────────────────────────────────────────────────────────────

def jinja2_rapor_uret(kontekst: dict, sablon_path: Path) -> str:
    """Jinja2 şablonu ile MD rapor metni üret."""
    env = Environment(
        loader      = FileSystemLoader(str(sablon_path.parent)),
        autoescape  = select_autoescape([]),
        trim_blocks = True,
        lstrip_blocks = True,
    )
    sablon = env.get_template(sablon_path.name)
    return sablon.render(**kontekst)


def fallback_rapor_uret(kontekst: dict) -> str:
    """
    Jinja2 yoksa basit Python string formatıyla rapor üret.
    Tüm temel bilgileri içerir ama şablonsuz.
    """
    now    = datetime.now()
    lines  = []
    add    = lines.append

    add("# Devriye Tur Raporu")
    add(f"**Oluşturan:** Özgür Kotbaş · Anomali Modülü")
    add(f"**Tarih:** {kontekst['tarih']}  **Saat:** {kontekst['saat']}")
    add(f"**Proje:** Görsel Anomali Tespiti · Grup 03_Gama · BTÜ · 2026")
    add("")
    add("---")
    add("")
    add("## Özet")
    add("")
    add("| Metrik | Değer |")
    add("|--------|-------|")
    add(f"| Toplam Waypoint | {kontekst['toplam_wp']} |")
    add(f"| Anomali Tespit | {kontekst['uyari_sayisi']} |")
    add(f"| Normal | {kontekst['normal_sayisi']} |")
    add(f"| Uyarı Oranı | {kontekst['uyari_oran']*100:.1f}% |")
    add(f"| PatchCore Aktif | {'Evet' if kontekst['patchcore_aktif'] else 'Hayır'} |")
    add("")

    if kontekst["uyari_sayisi"] > 0:
        add(f"> ⚠️ **{kontekst['uyari_sayisi']} waypoint anomali tespit edildi.**")
    else:
        add("> ✅ **Tüm waypoint'ler normal.**")
    add("")
    add("---")
    add("")
    add("## Uyarılar")
    add("")

    for uyari in kontekst["uyarilar"]:
        wp  = uyari.get("waypoint_id", "?")
        tip = uyari.get("degisiklik_tipi", "?").replace("_", " ")
        sev = uyari.get("severity", "?")
        sc  = uyari.get("patchcore_score", -1)
        det = uyari.get("mog2_nesne_sayisi", 0)
        add(f"### {wp} — {tip.title()}")
        add(f"- Severity: **{sev}**")
        add(f"- MOG2 Nesne: {det}")
        add(f"- PatchCore: {sc:.4f}" if sc >= 0 else "- PatchCore: Devre Dışı")
        add(f"- Karar: {uyari.get('karar_aciklama', '')}")
        tp_fp = uyari.get("tp_fp", {})
        if tp_fp.get("tp") is not None:
            add(f"- TP={tp_fp.get('tp')} FP={tp_fp.get('fp')} "
                f"IoU={tp_fp.get('iou_best', '?')}")
        add(f"- Test görüntüsü: `{uyari.get('test', '?')}`")
        add("")

    # Metrikler
    m = kontekst["metrikler"]
    add("---")
    add("")
    add("## Performans Metrikleri")
    add("")
    add("| Metrik | Değer |")
    add("|--------|-------|")
    add(f"| TP | {m.get('TP', 0)} |")
    add(f"| FP | {m.get('FP', 0)} |")
    add(f"| FN | {m.get('FN', 0)} |")
    add(f"| Precision | {m.get('precision', 0):.3f} |")
    add(f"| Recall | {m.get('recall', 0):.3f} |")
    add(f"| F1 | {m.get('F1', 0):.3f} |")
    add("")
    add("---")
    add("")
    add(f"*Bu rapor `ip11_rapor_uret.py` tarafından otomatik üretilmiştir.*")
    add(f"*Kaynak: `{kontekst['kaynak_json']}`*")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# HTML DÖNÜŞÜMÜ
# ──────────────────────────────────────────────────────────────────────────────

def md_to_html(md_metin: str, baslik: str = "Devriye Raporu") -> str:
    """
    Basit MD → HTML dönüşümü (harici kütüphane gerektirmez).
    markdown2 veya mistune varsa kullanır, yoksa temel dönüşüm.
    """
    try:
        import markdown2
        govde = markdown2.markdown(md_metin, extras=["tables", "fenced-code-blocks"])
    except ImportError:
        try:
            import mistune
            govde = mistune.html(md_metin)
        except ImportError:
            # Çok basit fallback
            govde = md_metin.replace("\n", "<br>")

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{baslik}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
               max-width: 900px; margin: 40px auto; padding: 0 20px;
               color: #333; background: #fafafa; }}
        h1 {{ color: #1a1a2e; border-bottom: 3px solid #e94560; padding-bottom: 10px; }}
        h2 {{ color: #16213e; border-bottom: 1px solid #ddd; padding-bottom: 6px; }}
        h3 {{ color: #0f3460; }}
        table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
        th {{ background: #1a1a2e; color: white; }}
        tr:nth-child(even) {{ background: #f2f2f2; }}
        code {{ background: #2d2d2d; color: #f8f8f2; padding: 2px 6px;
               border-radius: 3px; font-size: 0.9em; }}
        pre {{ background: #2d2d2d; color: #f8f8f2; padding: 16px;
              border-radius: 6px; overflow-x: auto; }}
        blockquote {{ border-left: 4px solid #e94560; margin: 0; padding: 10px 20px;
                     background: #fff3f3; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd;
                   color: #999; font-size: 0.85em; }}
    </style>
</head>
<body>
{govde}
<div class="footer">
    <p>Otomatik üretilen rapor · ip11_rapor_uret.py · {datetime.now().strftime("%Y-%m-%d %H:%M")}</p>
</div>
</body>
</html>"""


# ──────────────────────────────────────────────────────────────────────────────
# ANA FONKSİYON
# ──────────────────────────────────────────────────────────────────────────────

def rapor_uret(ozet_path: Path,
               sablon_path: Path,
               html_de_uret: bool = False) -> tuple[Path, Path | None]:
    """
    Tam rapor üretim pipeline'ı.
    Döndürür: (md_path, html_path | None)
    """
    print(f"\n[İP11] Devriye raporu üretiliyor...")
    print(f"  Kaynak : {ozet_path}")
    print(f"  Şablon : {sablon_path}")

    # Özet yükle
    ozet       = ozet_json_oku(ozet_path)
    kontekst   = ozet_to_sablon_kontekst(ozet, str(ozet_path))

    print(f"  Toplam WP: {kontekst['toplam_wp']}  "
          f"Uyarı: {kontekst['uyari_sayisi']}  "
          f"Normal: {kontekst['normal_sayisi']}")

    # MD raporu üret
    if JINJA2_AVAILABLE and sablon_path.exists():
        print(f"  Motor: Jinja2")
        md_metin = jinja2_rapor_uret(kontekst, sablon_path)
    else:
        if not JINJA2_AVAILABLE:
            print("  Motor: Basit fallback (jinja2 yok)")
        elif not sablon_path.exists():
            print(f"  [UYARI] Şablon bulunamadı: {sablon_path}")
            print(  "  Motor: Basit fallback")
        md_metin = fallback_rapor_uret(kontekst)

    # MD kaydet
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path  = OUT_DIR / f"devriye_raporu_{ts}.md"
    md_path.write_text(md_metin, encoding="utf-8")
    print(f"  [Kayıt] MD: {md_path}")

    # Son raporu sabit isimle de kaydet (kolayca bulunur)
    son_md = OUT_DIR / "son_devriye_raporu.md"
    son_md.write_text(md_metin, encoding="utf-8")
    print(f"  [Kayıt] Son rapor: {son_md}")

    # HTML (isteğe bağlı)
    html_path = None
    if html_de_uret:
        html_metin = md_to_html(md_metin, "Devriye Raporu")
        html_path  = OUT_DIR / f"devriye_raporu_{ts}.html"
        html_path.write_text(html_metin, encoding="utf-8")
        print(f"  [Kayıt] HTML: {html_path}")

    return md_path, html_path


# ──────────────────────────────────────────────────────────────────────────────
# GİRİŞ NOKTASI
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="İP11: Devriye Raporu Üretici (Jinja2 → MD)"
    )
    parser.add_argument(
        "--ozet", default=None,
        help="ensemble_ozet.json yolu (varsayılan: data/ip9_ensemble/ensemble_ozet.json)"
    )
    parser.add_argument(
        "--sablon", default=str(SABLON_PATH),
        help=f"Jinja2 şablon dosyası (varsayılan: {SABLON_PATH})"
    )
    parser.add_argument(
        "--html", action="store_true",
        help="HTML raporu da üret"
    )
    parser.add_argument(
        "--outdir", default=None,
        help="Cikti dizini (varsayilan: outputs/devriye_raporu)"
    )
    args = parser.parse_args()

    global OUT_DIR
    if args.outdir is not None:
        OUT_DIR = Path(args.outdir)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  IP11: Devriye Raporu Uretici — Ozgur Kotbas")
    print("  Grup 03_Gama · BTU · Staj 2026")
    print("=" * 60)


    # Özet JSON'u bul
    if args.ozet:
        ozet_path = Path(args.ozet)
    else:
        ozet_path = ENSEMBLE_DIR / "ensemble_ozet.json"

    if not ozet_path.exists():
        print(f"\n[UYARI] ensemble_ozet.json bulunamadi: {ozet_path}")
        print("  Bireysel WP JSON'larından sentetik özet oluşturuluyor...")

        ozet = bireysel_json_topla()
        if ozet is None:
            print(f"  [HATA] Hiç ensemble sonucu bulunamadi: {ENSEMBLE_DIR}")
            print("  Önce ip9_ensemble_analiz.py çalıştırın.")
            sys.exit(1)

        # Sentetik özeti geçici dosyaya yaz
        gecici = OUT_DIR / "_gecici_ozet.json"
        with open(gecici, "w", encoding="utf-8") as f:
            json.dump(ozet, f, ensure_ascii=False, indent=2)
        ozet_path = gecici
        print(f"  Sentetik özet: {gecici}")

    sablon_path = Path(args.sablon)

    # Raporu üret
    md_path, html_path = rapor_uret(
        ozet_path   = ozet_path,
        sablon_path = sablon_path,
        html_de_uret = args.html,
    )

    print(f"\n{'='*60}")
    print(f"  TAMAMLANDI")
    print(f"  MD Raporu  : {md_path}")
    if html_path:
        print(f"  HTML Raporu: {html_path}")
    print(f"{'='*60}")

    print("\n--- RAPOR ONIZLEME (ilk 40 satir) ---\n")
    lines = md_path.read_text(encoding="utf-8").split("\n")
    for line in lines[:40]:
        try:
            print(line)
        except UnicodeEncodeError:
            print(line.encode('ascii', errors='replace').decode('ascii'))
    if len(lines) > 40:
        print(f"  ... (+{len(lines)-40} satir daha)")


if __name__ == "__main__":
    main()
