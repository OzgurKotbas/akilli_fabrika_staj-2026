# Akıllı Fabrika Anomali Tespiti - Kullanım Kılavuzu

Bu belge, Pan-Tilt Robot Anomali Tespiti sistemini sıfırdan kurmak ve çalıştırmak isteyen kullanıcılar (operatörler, yöneticiler, jüri üyeleri) için hazırlanmıştır.

## 1. Kurulum (Installation)

Projeyi bilgisayarınıza indirdikten sonra, bağımlılıkları yüklemek için kök dizinde (ana klasörde) terminal/komut satırı açın ve şu komutu çalıştırın:
```bash
pip install -r requirements.txt
```
> [!NOTE]
> Sistem, derin öğrenme altyapısı için opsiyonel olarak `anomalib` kullanmaktadır. Eğer GPU tabanlı (PatchCore vb.) analiz yapacaksanız `pip install anomalib` komutunu ayrıca çalıştırmanız önerilir.

## 2. Yapılandırma (`config.yaml`)

Sistem tamamen `config.yaml` dosyası üzerinden yönetilmektedir. Kodu değiştirmenize gerek yoktur.
- **MQTT Ayarları:** `mqtt -> broker` ve `port` ayarlarını kendi yerel veya uzak sunucunuza göre değiştirebilirsiniz.
- **Görüntü İşleme:** `vision -> patchcore_thresh` (anomali algılama eşiği) veya sarı çizgi HSV değerlerini, fabrikanızın ışıklandırma koşullarına göre esnetebilirsiniz.
- **Dosya Yolları:** Sistem, dosyaları bulunduğu dizinden otomatik bulacak şekilde tasarlanmıştır (Göreceli Yollar). Ekstra bir dizin ayarı yapmanıza gerek yoktur.

## 3. Sistemi Çalıştırma

Kodlar profesyonel bir python paketi olarak modülerleştirilmiştir (`scripts/` altında). 

### a) Görsel Demo Uygulaması (Canlı İzleme)
Sistemin tüm yeteneklerini tek bir görsel arayüzde görmek için:
```bash
python scripts/demo_anomali.py
```
> [!TIP]
> Eğer tespit edilen hataların MQTT üzerinden **patrol/alert** topic'ine yayınlanmasını (bildirim atılmasını) isterseniz komutu şu şekilde çalıştırın:
> `python scripts/demo_anomali.py --mqtt`

### b) Veri Analizi ve Rapor Üretimi (IP9 & IP11)
Arka planda (komut satırında) devriye verilerini analiz edip HTML/MD formatında bir "Tur Raporu" oluşturmak için:
```bash
python -m scripts.vision.ip9_ensemble_analiz
python -m scripts.comms.ip11_rapor_uret --html
```
Bu komutların ardından `outputs/devriye_raporu/` klasörü içinde analiz kanıtlarıyla dolu, yöneticilere sunulmaya hazır raporlar bulacaksınız.

### c) MQTT Testi (Alarm Dinleme)
Sistemin ürettiği anomali uyarısını bir kontrolcü (örneğin robotun durması veya siren çalması) gibi dinlemek için yeni bir terminal açıp abone (subscriber) betiğini çalıştırın:
```bash
python -m scripts.comms.mqtt_test_abone
```
Bu ekran açıkken anomali bulunduğunda otomatik uyarı metinleri terminale düşecektir.

---
**İletişim:** Özgür Kotbaş · BTÜ Staj Projesi · Grup 03_Gama
