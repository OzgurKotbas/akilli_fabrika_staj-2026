<div align="center">
  <img src="https://img.shields.io/badge/Proje_Durumu-Tamamlandı-success?style=for-the-badge" alt="Durum">
  <img src="https://img.shields.io/badge/Kütüphane-anomalib_|_OpenCV-blue?style=for-the-badge" alt="Kütüphane">
  <img src="https://img.shields.io/badge/Mimari-İki_Fazlı_Hibrit-purple?style=for-the-badge" alt="Mimari">
</div>

# 🏭 Akıllı Fabrika Staj 2026: Otonom Devriye Robotu – Görsel Anomali Tespiti

Bu depo (repository), akıllı fabrika konseptinde çalışan otonom bir devriye robotunun **Görsel Anomali Tespiti ve Raporlama** modülünü içermektedir. Bursa Teknik Üniversitesi (BTÜ) 2026 Yaz Stajı kapsamında **Özgür Kotbaş** tarafından geliştirilmiştir.

---

## 🎯 Projenin Amacı ve Kapsamı

Otonom devriye gezen pan-tilt kameralı bir robotun (robot köpek), fabrikadaki olağan dışı durumları (anomalileri) insan müdahalesi olmadan tespit etmesi ve vardiya sonunda otomatik kanıtlı PDF raporları oluşturması amaçlanmıştır.

**Hedeflenen Anomali Senaryoları:**
* Yerde unutulan alet çantaları veya yabancı nesneler (`YABANCI_NESNE`)
* Fabrika zeminindeki tehlikeli su, yağ ve kimyasal sızıntıları (`ZEMIN_SIZINTISI`)
* Acil çıkış kapılarının önünün kapanması, yapısal bükülmeler (`YAPI_ANOMALISI`)

---

## 🧠 Gelişmiş Anomali Takibi: İki Fazlı (Hibrit) Mimari

Otonom robotların kameraları hareket halindeyken derinlik (3D Parallax) kaymaları yaşar. Geleneksel arka plan çıkarma algoritmaları bu kaymaları anomali sanarak binlerce yanlış alarm (False Positive) üretir. 

Bu sorunu kökünden çözmek için **İki Fazlı (Hibrit) Mimari** tasarlanmış ve donanım verisi olmamasına rağmen **Optik Akış (Optical Flow)** ile Ego-Motion simülasyonu koda entegre edilmiştir.

### 🚶‍♂️ Faz 1: Transit Yürüyüş (Uyku Modu)
Robot bir kontrol noktasına (waypoint) yürürken:
* **Optik Akış (Lucas-Kanade):** Piksellerin kayma miktarını ölçer. 1.5px üzerindeki kaymalar robotun hareket ettiğini kanıtlar.
* **MOG2 Uykuya Alınır:** 3D Parallax hatalarını önlemek için arka plan çıkarma algoritması devre dışı bırakılır.
* Sadece **YOLO** nesne tespiti çalışarak önceden tanımlanmış tehlikeleri (İnsan, Baret, Forklift) arar.

### 🛑 Faz 2: Waypoint İncelemesi (Derin Tarama)
Robot kontrol noktasına (ör: bir vananın önüne) ulaştığında:
* Kamera sadece kendi ekseni etrafında (Pan-Tilt) döner (Parallax oluşmaz).
* **Uyanış:** Optik akış durmayı algılar ve **MOG2** ile **PatchCore (anomalib)** algoritmaları uyanır.
* **ORB + RANSAC Hizalama:** Görüntü titreşimlerine karşı kareler milimetrik olarak hizalanır.
* Kategori tabanlı filtreleme ile anomaliler renk (HSV) ve boyutlarına göre ayrıştırılır.

---

## 🛠️ Modüller ve Teknolojiler

Proje salt bir derin öğrenme kodundan ibaret değildir; endüstriyel kalitede bir "Pipeline" (veri hattı) mimarisine sahiptir:

1. **Denetimsiz Yapay Zeka (anomalib):** `PatchCore` ve `PaDiM` modelleri kullanılarak sistemin sadece "normal" fotoğrafları (Altın Tur) görmesi sağlanmış, anomaliler bu normale olan sapmalardan hesaplanmıştır.
2. **Kategori Tabanlı Filtreleme:** Sadece "anomali var" demez; sızıntıları yatay ve karanlık yapısından, yapısal sorunları ise dikey yapısından analiz ederek etiketler.
3. **MQTT Entegrasyonu:** Tüm modüller `patrol/alert` başlığı altında JSON tabanlı haberleşir. Çevrimdışı durumlarda veriler `.jsonl` olarak diskte yedeklenir.
4. **Otomatik Raporlama:** Devriye bittiğinde saniyeler içinde kanıt fotoğraflarıyla dolu, metriklerin bulunduğu Markdown/PDF raporu oluşturur.

---

## 📂 Klasör Yapısı

* `scripts/run_demo.py`: Tüm ekibin kodlarını birleştiren, Optik Akış ve Anomali tespiti entegre edilmiş **Ana Demo Çalıştırıcı**.
* `data/`: Model eğitiminde kullanılan referans kareler (Altın Tur - Waypoints).
* `outputs/`: Algoritmaların ürettiği ısı haritaları (Heatmaps) ve otomatik raporlar.
* `DOKUMANLAR/`: Proje mimarisi, literatür taraması, günlük loglar (`daily_log.md`) ve **Teknik Sunum Raporu**.

*(Not: Diğer ekip üyelerine ait modeller ve ağır klasörler `.gitignore` ile yalıtılmış olup, deponun temiz kalması sağlanmıştır.)*

---

## 🚀 Demoyu Çalıştırma

Ortak geliştirilen demoyu çalıştırmak için ana dizindeki betiği kullanabilirsiniz (Ekip arkadaşlarının kodlarının aynı dizinde bulunduğu varsayılır):

```bash
# Gerekli bağımlılıkları yükleyin
pip install -r requirements.txt

# Demoyu Başlatın
python scripts/run_demo.py --video "koridor.mp4" --gosterge-agirlik "best.pt"
```

> **Not:** Demo sırasında sağ taraftaki panelde, robot yürürken MOG2'nin uyku moduna geçtiğini ve durduğunda ortamı taradığını canlı olarak izleyebilirsiniz!

---
*Bu proje, BTÜ Akıllı Fabrika 2026 Yaz Stajı 03_Gama Grubu tarafından geliştirilmiştir.*
