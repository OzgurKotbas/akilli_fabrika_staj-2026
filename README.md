# Görsel Anomali Tespiti ve Otomatik Devriye Raporu Sistemi

![Proje Durumu](https://img.shields.io/badge/Proje_Durumu-Geliştirme_Aşamasında-orange)
![Kütüphane](https://img.shields.io/badge/Kütüphane-anomalib-blue)
![Model](https://img.shields.io/badge/Model-PatchCore%20%7C%20PaDiM-green)

Bu depo (repository), akıllı fabrika konseptinde çalışan otonom bir devriye sisteminin **Görsel Anomali Tespiti** modülünün geliştirilmesi amacıyla oluşturulmuştur. Özgür Kotbaş'ın 2026 yılı staj projesinin bir parçasıdır.

## 📋 İçindekiler
- [Projenin Amacı ve Kapsamı](#-projenin-amacı-ve-kapsamı)
- [Bu Depoda (Repo) Neler Yapılıyor?](#-bu-depoda-repo-neler-yapılıyor)
- [Klasör Yapısı ve İçerik](#-klasör-yapısı-ve-içerik)
- [Kurulum ve Başlangıç](#-kurulum-ve-başlangıç)
- [Proje Ekibi](#-proje-ekibi)

---

## 🎯 Projenin Amacı ve Kapsamı

Fabrikalarda veya endüstriyel tesislerde gerçekleştirilen devriye turları sırasında; çevresel sorunların, üretim hattındaki aksaklıkların veya güvenlik ihlallerinin hızlıca tespit edilmesi hayati önem taşır.

Bu projenin temel amacı: **Sistemdeki kameranın elde ettiği görüntüleri "normal (altın tur)" referanslarla karşılaştırarak, devriye sırasında oluşmuş olağandışı durumları (anomalileri) yapay zeka ile otomatik olarak tespit etmektir.**

Örnek Anomali Senaryoları:
* Yerde bırakılmış yabancı nesneler (kutu, çanta vb.)
* Acil çıkış kapılarının önünün kapanması
* Fabrika zeminindeki su veya yağ sızıntıları

Sistem, anomali tespit ettiği noktaları piksel bazlı ısı haritaları (heatmaps) ile işaretleyerek tur sonunda insan müdahalesine gerek kalmadan kanıtlı bir **Markdown/PDF Devriye Raporu** oluşturmayı hedefler.

---

## 🔍 Bu Depoda (Repo) Neler Yapılıyor?

Bu depo, yukarıda bahsedilen büyük projenin **"Anomali Tespiti ve Raporlama"** ayağını (Özgür Kotbaş'ın sorumluluğu) içerir. Bu repodaki kodlar ve modeller şu görevleri üstlenir:

1. **Altın Tur (Referans) Veri Seti Oluşturma:** Kameranın normal zamanlardaki turundan "waypoint" adı verilen referans karelerin çıkarılması ve indekslenmesi.
2. **Model Eğitimi:** `anomalib` kütüphanesinin sağladığı son teknoloji (SOTA) makine öğrenmesi modelleriyle (Özellikle **PatchCore** ve **PaDiM**) sistemin sadece "normali" görerek eğitilmesi.
3. **Anomali Çıkarımı (Inference):** Yeni bir test görüntüsü geldiğinde, referans kare ile hizalama yapıp üzerindeki anomaliyi tespit etme ve ısı haritası oluşturma.
4. **Loglama ve Raporlama:** Tüm sürecin dokümante edilmesi.

---

## 📂 Klasör Yapısı ve İçerik

Proje modüler ve sürdürülebilir olması adına aşağıdaki yapıya göre organize edilmiştir:

* **`docs/`** 📚: Proje tanımı, literatür özetleri, anomali senaryoları listesi ve eski raporların bulunduğu dokümantasyon dizini.
* **`data/`** 🗃️: Model eğitiminde ve testinde kullanılan ham videolar (`raw_videos/`) ile çıkartılan referans karelerin (`waypoints/`) tutulduğu veri seti dizini.
* **`scripts/`** 💻: 
  * `anomali_test.py`: Anomalib kullanılarak yazılmış model inferans/test kodları.
  * `referans_kareler_cikart.py`: Videodan waypoint resimleri kesme kodları.
  * `AI.md`: Geliştirme süreci boyunca yapay zeka ile yapılan teknik müzakereler.
* **`outputs/`** 📈: Eğitilen modellerin ürettiği ısı haritaları (heatmaps) ve performans değerlendirme raporları (F1, AUROC gibi metrikler).
* **`DOKUMANLAR/`**: Eski iş paketleri listesi ve ilk proje tanımlarının arşivlendiği klasör.
* **`daily_log.md`**: Proje boyunca gerçekleştirilen işlerin gün gün kaydedildiği ilerleme takip dosyası.

---

## 🚀 Kurulum ve Başlangıç

Projede anomali tespiti işlemleri için [Anomalib](https://github.com/open-edge-platform/anomalib) kütüphanesinden faydalanılmaktadır. MVTec-AD veri seti üzerinde temel baseline testini (PaDiM/PatchCore) başlatmak için:

1. Gerekli kütüphaneleri kurun:
   ```bash
   pip install anomalib
   ```

2. Test scriptini çalıştırın:
   ```bash
   python scripts/anomali_test.py
   ```
*(Not: İlk çalıştırmada model ağırlıkları ve MVTec-AD veri seti otomatik olarak indirilecektir.)*

Daha detaylı senaryoları incelemek için `docs/proje_tanimi/senaryo_listesi.md` dosyasına göz atabilirsiniz.

---

## 👥 Proje Ekibi

Bu otonom sistem 3 kişilik bir stajyer ekibi tarafından eşzamanlı ve haberleşmeli olarak geliştirilmektedir:
* **Bedirhan:** Vizyon, YOLO nesne tespiti, Navigasyon ve ROS2.
* **Reşit:** Arayüz, Veri Tabanı (MongoDB) ve MQTT Göstergeleri.
* **Özgür (Bu Repo):** Anomalib, PatchCore/PaDiM model eğitimleri ve Devriye Raporlama.
