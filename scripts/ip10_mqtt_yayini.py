# -*- coding: utf-8 -*-
from __future__ import annotations
import sys, io
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf-16'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
"""
İP10: MQTT Yayını — patrol/alert
==================================
Doküman : DOKUMANLAR/Ozgur_is_paketleri.md -- İP10
Bitti kriteri: Broker'da şema uyumlu patrol/alert mesajları

MQTT Şeması (pan_tilt_robot_projesi.md ile uyumlu):
    Topic   : patrol/alert
    Payload : JSON
    {
        "type"      : "patrol_alert",
        "severity"  : "HIGH" | "MEDIUM" | "LOW" | "NONE",
        "waypoint"  : "WP01",
        "score"     : 0.84,          -- PatchCore anomali skoru (0-1)
        "det_count" : 2,             -- MOG2 tespit edilen nesne sayısı
        "fg_ratio"  : 0.012,         -- MOG2 foreground oranı
        "img_ref"   : "data/ip8_test/WP01_degisik.jpg",
        "vis_path"  : "data/ip9_ensemble/WP01_ensemble_analiz.png",
        "ts"        : "2026-08-17T12:34:56.123456",
        "degisiklik_tipi": "yerde_birakilan_cisim",
        "mog2_aktif"     : true,
        "patchcore_aktif": true
    }

KULLANIM:
    # Sadece ip9 ensemble sonuçlarını MQTT ile yayınla:
    python scripts/ip10_mqtt_yayini.py

    # Belirli broker:
    python scripts/ip10_mqtt_yayini.py --broker 192.168.1.100 --port 1883

    # Offline mod (broker yoksa JSON'a kaydet):
    python scripts/ip10_mqtt_yayini.py --offline

    # Canlı izleme modu (ip9 çıktılarını sürekli izle, değişince yayınla):
    python scripts/ip10_mqtt_yayini.py --izle

BAĞIMLILIK:
    pip install paho-mqtt    # MQTT istemcisi
    (broker yoksa --offline flag'i ile broker'sız çalışır)
"""


import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent))
import config_okuyucu

# paho-mqtt isteğe bağlı
try:
    import paho.mqtt.client as mqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    print("[UYARI] paho-mqtt bulunamadı — offline mod aktif.")
    print("        Kurmak için: pip install paho-mqtt")

# ──────────────────────────────────────────────────────────────────────────────
# PROJE AYARLARI
# ──────────────────────────────────────────────────────────────────────────────
PROJECT_DIR  = config_okuyucu.PROJECT_ROOT
CONFIG       = config_okuyucu.CONFIG

ENSEMBLE_DIR = PROJECT_DIR / "data" / "ip9_ensemble"
ETIKET_PATH  = config_okuyucu.get_path(CONFIG.get("paths", {}).get("etiketler_json", "data/ip8_test/etiketler.json"))
OUT_DIR      = PROJECT_DIR / "outputs" / "mqtt_kayitlari"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# MQTT varsayılan ayarları
_mqtt_conf   = CONFIG.get("mqtt", {})
MQTT_BROKER  = _mqtt_conf.get("broker", "localhost")
MQTT_PORT    = _mqtt_conf.get("port", 1883)
MQTT_TOPIC   = _mqtt_conf.get("topic", "patrol/alert")
MQTT_CLIENT_ID = "anomali_modul_ozgur"
MQTT_QOS     = 1
MQTT_RETAIN  = False

# ──────────────────────────────────────────────────────────────────────────────
# MESAJ ŞEMASI DOĞRULAMASI
# ──────────────────────────────────────────────────────────────────────────────

GEREKLI_ALANLAR = {
    "type", "severity", "waypoint", "score",
    "det_count", "img_ref", "ts"
}

SEVERITY_SIRASI = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "NONE": 3}


def mesaj_dogrula(mesaj: dict) -> tuple[bool, list[str]]:
    """Mesajın şema gerekliliklerini karşılayıp karşılamadığını kontrol et."""
    hatalar = []

    # Zorunlu alanlar
    eksik = GEREKLI_ALANLAR - set(mesaj.keys())
    if eksik:
        hatalar.append(f"Eksik alanlar: {eksik}")

    # Severity değeri geçerli mi?
    if "severity" in mesaj and mesaj["severity"] not in SEVERITY_SIRASI:
        hatalar.append(
            f"Geçersiz severity: {mesaj['severity']} "
            f"(beklenen: {list(SEVERITY_SIRASI)})"
        )

    # Score 0-1 arasında mı?
    if "score" in mesaj:
        s = mesaj["score"]
        if not (isinstance(s, (int, float)) and -0.01 <= float(s) <= 1.01):
            hatalar.append(f"Score 0-1 dışında: {s}")

    return len(hatalar) == 0, hatalar


# ──────────────────────────────────────────────────────────────────────────────
# ENSEMBLE JSON → MQTT MESAJI DÖNÜŞÜMÜ
# ──────────────────────────────────────────────────────────────────────────────

def ensemble_sonuc_to_mesaj(sonuc: dict) -> dict:
    """
    ip9_ensemble_analiz.py çıktısını patrol/alert MQTT mesajına dönüştür.
    Şema: pan_tilt_robot_projesi.md ile uyumlu.
    """
    return {
        "type"            : "patrol_alert",
        "severity"        : sonuc.get("severity", "NONE"),
        "waypoint"        : sonuc.get("waypoint_id", "?"),
        "score"           : sonuc.get("patchcore_score", -1.0),
        "det_count"       : sonuc.get("mog2_nesne_sayisi", 0),
        "fg_ratio"        : sonuc.get("mog2_fg_ratio", 0.0),
        "is_alert"        : sonuc.get("is_alert", False),
        "img_ref"         : sonuc.get("test", ""),
        "vis_path"        : sonuc.get("ensemble_gorseli", ""),
        "ts"              : datetime.now().isoformat(),
        "degisiklik_tipi" : sonuc.get("degisiklik_tipi", "bilinmiyor"),
        "mog2_aktif"      : True,
        "patchcore_aktif" : sonuc.get("patchcore_aktif", False),
        "karar_aciklama"  : sonuc.get("karar_aciklama", ""),
        "tp_fp"           : sonuc.get("tp_fp", {}),
    }


def ozet_to_mesajlar(ozet_json: Path) -> list[dict]:
    """ensemble_ozet.json dosyasından tüm waypoint mesajlarını üret."""
    with open(ozet_json, encoding="utf-8") as f:
        ozet = json.load(f)

    mesajlar = []
    for sonuc in ozet.get("sonuclar", []):
        mesaj = ensemble_sonuc_to_mesaj(sonuc)
        ok, hatalar = mesaj_dogrula(mesaj)
        if not ok:
            print(f"  [UYARI] {mesaj['waypoint']} şema hatası: {hatalar}")
        mesajlar.append(mesaj)

    # Severity'ye göre sırala (HIGH önce)
    mesajlar.sort(key=lambda m: SEVERITY_SIRASI.get(m["severity"], 9))
    return mesajlar


def bireysel_json_to_mesajlar() -> list[dict]:
    """
    ensemble_ozet.json yoksa bireysel WP JSON'larından mesaj üret.
    ip9_ensemble_analiz.py'nin ürettiği WP01_ensemble_sonuc.json gibi dosyalar.
    """
    mesajlar = []
    for json_path in sorted(ENSEMBLE_DIR.glob("*_ensemble_sonuc.json")):
        with open(json_path, encoding="utf-8") as f:
            sonuc = json.load(f)
        mesaj = ensemble_sonuc_to_mesaj(sonuc)
        ok, hatalar = mesaj_dogrula(mesaj)
        if not ok:
            print(f"  [UYARI] {json_path.name} şema hatası: {hatalar}")
        mesajlar.append(mesaj)

    mesajlar.sort(key=lambda m: SEVERITY_SIRASI.get(m["severity"], 9))
    return mesajlar


# ──────────────────────────────────────────────────────────────────────────────
# MQTT BAĞLANTISI VE YAYINI
# ──────────────────────────────────────────────────────────────────────────────

class PatrolMQTTYayinci:
    """
    patrol/alert MQTT yayıncısı.
    paho-mqtt yoksa veya broker bağlantısı kurulamazsa offline mod devreye girer.
    """

    def __init__(self, broker: str = MQTT_BROKER, port: int = MQTT_PORT,
                 offline: bool = False):
        self.broker  = broker
        self.port    = port
        self.offline = offline or not MQTT_AVAILABLE
        self._client = None
        self._bagli  = False
        self._gonderilen: list[dict] = []

        if not self.offline:
            self._baglanti_kur()

    def _baglanti_kur(self):
        """Broker'a bağlan."""
        try:
            self._client = mqtt.Client(client_id=MQTT_CLIENT_ID,
                                       protocol=mqtt.MQTTv311)
            self._client.on_connect    = self._on_connect
            self._client.on_disconnect = self._on_disconnect
            self._client.on_publish    = self._on_publish
            self._client.connect(self.broker, self.port, keepalive=60)
            self._client.loop_start()
            time.sleep(0.5)   # bağlantının oturması için kısa bekle
        except Exception as e:
            print(f"  [UYARI] Broker bağlantısı kurulamadı ({self.broker}:{self.port}): {e}")
            print("  [BİLGİ] Offline moda geçiliyor — mesajlar JSON'a kaydedilecek.")
            self.offline = True
            self._client = None

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._bagli = True
            print(f"  [MQTT] Broker'a bağlandı: {self.broker}:{self.port}")
        else:
            print(f"  [MQTT] Bağlantı başarısız (rc={rc})")

    def _on_disconnect(self, client, userdata, rc):
        self._bagli = False

    def _on_publish(self, client, userdata, mid):
        pass   # sessiz kabul

    def yayinla(self, mesaj: dict) -> bool:
        """
        Tek bir mesajı patrol/alert topic'ine gönder.
        Offline moddaysa dosyaya yaz.
        Döndürür: gönderim başarılı mı
        """
        self._gonderilen.append(mesaj)
        payload = json.dumps(mesaj, ensure_ascii=False, indent=None)

        if self.offline or self._client is None:
            # Offline: sadece ekrana bas
            self._offline_yazdir(mesaj)
            return True

        if not self._bagli:
            print("  [UYARI] Broker bağlantısı yok — offline olarak kaydediliyor.")
            self._offline_yazdir(mesaj)
            return False

        result = self._client.publish(MQTT_TOPIC, payload, qos=MQTT_QOS,
                                       retain=MQTT_RETAIN)
        return result.rc == mqtt.MQTT_ERR_SUCCESS

    def _offline_yazdir(self, mesaj: dict):
        """Offline moddaki mesajı terminale ve dosyaya yaz."""
        wp  = mesaj.get("waypoint", "?")
        sev = mesaj.get("severity", "?")
        alr = mesaj.get("is_alert", False)

        sembol = "[HIGH]" if sev == "HIGH" else "[MED]" if sev == "MEDIUM" else "[OK]"
        print(f"  [OFFLINE] {sembol} Topic: {MQTT_TOPIC}")
        print(f"           Waypoint: {wp}  |  Severity: {sev}  |  Alert: {alr}")
        print(f"           Score: {mesaj.get('score', -1):.3f}  "
              f"DetCount: {mesaj.get('det_count', 0)}")
        print(f"           Tip: {mesaj.get('degisiklik_tipi', '?')}")

    def tum_mesajlari_kaydet(self) -> Path:
        """Gönderilen tüm mesajları JSON'a kaydet (audit log)."""
        ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = OUT_DIR / f"patrol_alert_kayit_{ts}.json"
        kayit   = {
            "kayit_tarihi": datetime.now().isoformat(),
            "broker"      : self.broker,
            "port"        : self.port,
            "offline"     : self.offline,
            "topic"       : MQTT_TOPIC,
            "mesaj_sayisi": len(self._gonderilen),
            "mesajlar"    : self._gonderilen,
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(kayit, f, ensure_ascii=False, indent=2)
        return out_path

    def kapat(self):
        if self._client is not None:
            self._client.loop_stop()
            self._client.disconnect()


# ──────────────────────────────────────────────────────────────────────────────
# ANA YAYIM FONKSİYONLARI
# ──────────────────────────────────────────────────────────────────────────────

def ip9_ciktilari_yayinla(yayinci: PatrolMQTTYayinci) -> list[dict]:
    """ip9 ensemble çıktılarını oku ve MQTT ile yayınla."""

    ozet_path = ENSEMBLE_DIR / "ensemble_ozet.json"

    if ozet_path.exists():
        print(f"  [Kaynak] ensemble_ozet.json ({ozet_path})")
        mesajlar = ozet_to_mesajlar(ozet_path)
    else:
        # Bireysel JSON'lardan topla
        print(f"  [Kaynak] Bireysel WP JSON dosyaları ({ENSEMBLE_DIR})")
        mesajlar = bireysel_json_to_mesajlar()

    if not mesajlar:
        print("  [UYARI] Yayınlanacak mesaj bulunamadı.")
        print(f"         ip9_ensemble_analiz.py çalıştırılmış olmalı → {ENSEMBLE_DIR}")
        return []

    print(f"\n  Toplam {len(mesajlar)} waypoint mesajı yayınlanıyor...")
    print(f"  Topic: {MQTT_TOPIC}\n")

    basarili = 0
    for mesaj in mesajlar:
        wp  = mesaj["waypoint"]
        sev = mesaj["severity"]
        ok  = yayinci.yayinla(mesaj)
        if ok:
            basarili += 1
            print(f"  [{'OK' if ok else 'HATA'}] {wp}  severity={sev}  "
                  f"score={mesaj.get('score', -1):.3f}  "
                  f"det={mesaj.get('det_count', 0)}")
        time.sleep(0.1)   # mesajlar arası kısa bekleme

    print(f"\n  Sonuç: {basarili}/{len(mesajlar)} mesaj başarıyla yayınlandı.")
    return mesajlar


def izleme_modu(yayinci: PatrolMQTTYayinci, aralik: float = 5.0):
    """
    Canlı izleme modu: ensemble_ozet.json değiştiğinde otomatik yayınla.
    Robot devriye sırasında sürekli çalışacak mod.
    """
    print(f"\n[İZLEME MODU] {ENSEMBLE_DIR} izleniyor... (Ctrl+C ile çık)")
    print(f"  Kontrol aralığı: {aralik} saniye\n")

    ozet_path = ENSEMBLE_DIR / "ensemble_ozet.json"
    son_mtime = 0.0

    try:
        while True:
            if ozet_path.exists():
                mtime = ozet_path.stat().st_mtime
                if mtime > son_mtime:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] "
                          f"Güncelleme algılandı, yayınlanıyor...")
                    ip9_ciktilari_yayinla(yayinci)
                    son_mtime = mtime
            time.sleep(aralik)
    except KeyboardInterrupt:
        print("\n  İzleme modu durduruldu.")


def test_mesaji_gonder(yayinci: PatrolMQTTYayinci):
    """Şema doğrulaması için test mesajı gönder."""
    test_msg = {
        "type"            : "patrol_alert",
        "severity"        : "HIGH",
        "waypoint"        : "TEST_WP",
        "score"           : 0.75,
        "det_count"       : 2,
        "fg_ratio"        : 0.015,
        "is_alert"        : True,
        "img_ref"         : "data/ip8_test/WP01_degisik.jpg",
        "vis_path"        : "data/ip9_ensemble/WP01_ensemble_analiz.png",
        "ts"              : datetime.now().isoformat(),
        "degisiklik_tipi" : "yerde_birakilan_cisim",
        "mog2_aktif"      : True,
        "patchcore_aktif" : False,
        "karar_aciklama"  : "Test mesajı — MOG2: 2 nesne",
        "tp_fp"           : {},
    }

    ok, hatalar = mesaj_dogrula(test_msg)
    if not ok:
        print(f"  [HATA] Test mesajı şema hatası: {hatalar}")
        return

    print("  [TEST] Şema doğrulaması geçti — mesaj gönderiliyor...")
    yayinci.yayinla(test_msg)
    print("  [TEST] Tamamlandı.")


# ──────────────────────────────────────────────────────────────────────────────
# GİRİŞ NOKTASI
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="İP10: patrol/alert MQTT Yayıncısı"
    )
    parser.add_argument("--broker",  default=MQTT_BROKER,
                        help=f"MQTT broker adresi (varsayılan: {MQTT_BROKER})")
    parser.add_argument("--port",    type=int, default=MQTT_PORT,
                        help=f"MQTT port (varsayılan: {MQTT_PORT})")
    parser.add_argument("--offline", action="store_true",
                        help="Broker olmadan JSON'a yaz")
    parser.add_argument("--izle",    action="store_true",
                        help="Canlı izleme modu (ip9 çıktıları değişince yayınla)")
    parser.add_argument("--aralik",  type=float, default=5.0,
                        help="İzleme modu kontrol aralığı (saniye)")
    parser.add_argument("--test",    action="store_true",
                        help="Test mesajı gönder (şema doğrulaması)")
    args = parser.parse_args()

    print("=" * 60)
    print("  IP10: patrol/alert MQTT Yayincisi — Ozgur Kotbas")
    print("  Grup 03_Gama · BTU · Staj 2026")
    print("=" * 60)
    print(f"  Broker : {args.broker}:{args.port}")
    print(f"  Topic  : {MQTT_TOPIC}")
    print(f"  Mod    : {'OFFLINE' if args.offline else 'CANLI'}")
    print("=" * 60)

    yayinci = PatrolMQTTYayinci(
        broker  = args.broker,
        port    = args.port,
        offline = args.offline,
    )

    try:
        if args.test:
            test_mesaji_gonder(yayinci)
        elif args.izle:
            izleme_modu(yayinci, aralik=args.aralik)
        else:
            mesajlar = ip9_ciktilari_yayinla(yayinci)

        # Audit kaydı
        kayit_path = yayinci.tum_mesajlari_kaydet()
        print(f"\n  Audit kaydı: {kayit_path}")

    finally:
        yayinci.kapat()
        print("\nIP10 tamamlandi.")


if __name__ == "__main__":
    main()
