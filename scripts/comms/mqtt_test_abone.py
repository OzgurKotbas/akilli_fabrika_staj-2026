# -*- coding: utf-8 -*-
"""
mqtt_test_abone.py — patrol/alert MQTT Abone Test Scripti
==========================================================
İP10 doğrulama aracı: broker'da yayınlanan patrol/alert mesajlarını dinler
ve şema uyumluluğunu ekrana basar.

KULLANIM:
    # Aynı anda iki terminal aç:
    # Terminal 1 (Abone):
    python scripts/mqtt_test_abone.py

    # Terminal 2 (Yayıncı):
    python scripts/ip10_mqtt_yayini.py --test

✅ İP10 bitti kriteri: Bu script broker'da şema uyumlu mesajlar aldığını doğrular.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("[HATA] paho-mqtt bulunamadi. Kurmak icin: pip install paho-mqtt")
    sys.exit(1)

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from scripts.core import config_okuyucu

_mqtt_conf = config_okuyucu.CONFIG.get("mqtt", {})
MQTT_BROKER = _mqtt_conf.get("broker", "localhost")
MQTT_PORT   = _mqtt_conf.get("port", 1883)
MQTT_TOPIC  = _mqtt_conf.get("topic", "patrol/alert")

GEREKLI_ALANLAR = {"type", "severity", "waypoint", "score", "det_count", "img_ref", "ts"}
SEVERITY_GECERLI = {"HIGH", "MEDIUM", "LOW", "NONE"}

alınan_sayac = 0
uyari_sayac  = 0


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[ABONE] Broker'a baglandi: {MQTT_BROKER}:{MQTT_PORT}")
        print(f"[ABONE] Dinlenen topic: {MQTT_TOPIC}")
        print("=" * 60)
        client.subscribe(MQTT_TOPIC, qos=1)
    else:
        print(f"[HATA] Baglanamadi (rc={rc})")


def on_message(client, userdata, msg):
    global alınan_sayac, uyari_sayac
    alınan_sayac += 1

    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Mesaj #{alınan_sayac} alindi")
    print(f"  Topic  : {msg.topic}")

    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except json.JSONDecodeError as e:
        print(f"  [HATA] JSON parse hatasi: {e}")
        return

    # Şema doğrula
    eksik = GEREKLI_ALANLAR - set(payload.keys())
    gecersiz_sev = payload.get("severity") not in SEVERITY_GECERLI

    if eksik or gecersiz_sev:
        print(f"  [SEMA HATASI]")
        if eksik:
            print(f"    Eksik alanlar : {eksik}")
        if gecersiz_sev:
            print(f"    Gecersiz severity: {payload.get('severity')}")
        return

    # Başarılı mesaj
    sev = payload.get("severity", "?")
    wp  = payload.get("waypoint", "?")
    alr = payload.get("is_alert", False)
    scr = payload.get("score", -1)
    det = payload.get("det_count", 0)
    tip = payload.get("degisiklik_tipi", "?")

    if alr:
        uyari_sayac += 1

    sembol = "UYARI" if alr else "NORMAL"
    print(f"  [SEMA OK] {sembol}")
    print(f"    Waypoint  : {wp}")
    print(f"    Severity  : {sev}")
    print(f"    Score     : {scr:.3f}")
    print(f"    Det.Count : {det}")
    print(f"    Tip       : {tip}")
    print(f"    Zaman     : {payload.get('ts', '?')}")
    print(f"  Toplam alınan: {alınan_sayac}  |  Uyarı: {uyari_sayac}")


def on_disconnect(client, userdata, rc):
    print("\n[ABONE] Bağlantı kesildi.")


def main():
    print("=" * 60)
    print("  IP10 Test Abone — patrol/alert Dinleyici")
    print("=" * 60)
    print(f"  Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"  Topic : {MQTT_TOPIC}")
    print("  Cikis icin Ctrl+C\n")

    client = mqtt.Client(client_id="patrol_test_abone", protocol=mqtt.MQTTv311)
    client.on_connect    = on_connect
    client.on_message    = on_message
    client.on_disconnect = on_disconnect

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_forever()
    except KeyboardInterrupt:
        print(f"\n[ABONE] Durduruldu. Toplam alınan: {alınan_sayac}, Uyarı: {uyari_sayac}")
    except ConnectionRefusedError:
        print(f"[HATA] Broker'a baglanilamiyor: {MQTT_BROKER}:{MQTT_PORT}")
        print("       Mosquitto broker calisyor mu?")
        print("       Windows: net start mosquitto")
        print("       veya: mosquitto -v")
    finally:
        client.disconnect()


if __name__ == "__main__":
    main()
