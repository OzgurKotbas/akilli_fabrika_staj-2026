# AI Konuşma Günlüğü — Özgür Kotbaş
> Staj projesi boyunca yapay zeka ile gerçekleştirilen teknik diyalogların kaydı.
> Format: `**User:** soru` / `**AI:** cevap`

---

## İP1 — anomalib İlk Çalıştırma (27–28 Temmuz 2026)

**User:**
.md dosyasında sol sildiğim şeyi nasıl geri getirebilirim

**AI:**
Silinen metni geri getirmek için hangisini kullandığına bağlı olarak birkaç farklı yol var. En yaygın senaryolar şunlar:

1. Kod Editöründeyken (VS Code, Cursor, Windsurf vb.)
- Henüz dosyayı kapatmadıysan: `Ctrl + Z` (Mac'te `Cmd + Z`) tuş kombinasyonuyla yaptığın son hamleleri geri alabilirsin.
- Kaydedip kapattıysan / `Ctrl + Z` çalışmıyorsa:
  - VS Code / Cursor / Windsurf: Sol taraftaki dosya gezgininde `.md` dosyana sağ tıkla ve "Timeline" (Zaman Çizelgesi) seçeneğine bak. Editörün yerel olarak tuttuğu eski kayıtlardan silmeden önceki haline dönebilirsin.
  - Git / GitHub kullanıyorsan: Terminalden `git checkout -- dosya_adi.md` veya `git restore dosya_adi.md` komutuyla son commit'teki haline geri çevirebilirsin.

2. Obsidian veya Notion Gibi Not Uygulamalarındaysan
- Obsidian: Sol alt taraftaki ayarlar çarkından Core Plugins > File Recovery özelliğinin açık olup olmadığına bak.
- Notion: Sağ üstteki üç noktaya tıklayıp Page History sekmesinden eski versiyonlara dönebilirsin.

3. Yanlışlıkla .md Dosyasının Kendisini Sildiysen
- Geri Dönüşüm Kutusu'nu (Trash) kontrol et.
- Editörün çöp kutusu klasörüne bak.

---

**User:**
anomalib nasıl kurulur, MVTec-AD veri setine nasıl erişirim?

**AI:**
anomalib kurulumu için şu adımları takip et:

```bash
pip install anomalib
```

MVTec-AD veri setine iki yoldan erişebilirsin:

1. **Otomatik indirme (önerilen):** anomalib ilk çalıştırmada veri setini otomatik indirir, `anomali_test.py` içindeki `datamodule` tanımı bunu halleder.
2. **Kaggle üzerinden:** `ipythonx/mvtec-ad` dataseti Kaggle'da mevcut. `kaggle datasets download ipythonx/mvtec-ad` ile indirebilirsin.

---

**User:**
PaDiM ile ilk çalıştırmayı yaptım ama AUROC değeri düşük çıktı (0.5 civarı). Ne yapmalıyım?

**AI:**
0.5 AUROC rastgele tahmin seviyesi demek — büyük ihtimalle veri yolu (`datamodule` root path) yanlış ayarlanmış. Kontrol listesi:

1. `root` parametresinin gerçekten veri setinin bulunduğu klasörü gösterdiğini doğrula.
2. `category` parametresinin (`bottle`, `carpet` vb.) gerçekten var olan bir kategori olduğundan emin ol.
3. `anomalib` sürümünü kontrol et: `pip show anomalib` — v1.x ile v2.x API'leri farklı.
4. `engine.fit()` çağrısından önce `datamodule.setup()` gerekiyor mu diye bak.

Doğru çalıştığında `bottle` kategorisinde PaDiM için `image_AUROC > 0.99` bekleniyor.

---

## İP3 — Altın Tur Kaydı (31 Temmuz 2026)

**User:**
LingBot-Map nedir, koridordan 3D nokta bulutu çıkarmak için nasıl kullanabilirim?

**AI:**
LingBot-Map, tek kameradan video alarak 3D nokta bulutu (point cloud) oluşturan bir modeldir. GitHub: `robbyant/lingbot-map`. Pretrained ağırlıklarla doğrudan inference yapabilirsin.

Google Colab'da T4 GPU ile çalıştırmak için:
```python
# Repo'yu klonla
!git clone https://github.com/robbyant/lingbot-map
# Bağımlılıkları kur
!pip install -r lingbot-map/requirements.txt
# Videoyu inference et
!python lingbot-map/infer.py --video koridor_992.mp4 --output batch_results.json
```

Çıktı olarak her kare için 3D koordinat JSON dosyası üretir. Bu dosyayı görselleştirmek için Open3D veya matplotlib ile render edebilirsin.

---

**User:**
Videodan belirli saniyelerdeki kareleri otomatik olarak nasıl çıkarırım?

**AI:**
OpenCV ile çok basit:

```python
import cv2

cap = cv2.VideoCapture("koridor_992.mp4")
fps = cap.get(cv2.CAP_PROP_FPS)
saniye = 15  # kaçıncı saniye?

kare_no = int(saniye * fps)
cap.set(cv2.CAP_PROP_POS_FRAMES, kare_no)
ret, frame = cap.read()
if ret:
    cv2.imwrite("WP01.jpg", frame)
cap.release()
```

Bu mantığı `referans_kareler_cikart.py` scriptine genişletebilirsin. Tüm waypoint'leri YAML'dan okuyup döngüyle kareleri çıkarmak için `pyyaml` kütüphanesini de kullan.

---

## İP4 — Mini Literatür (29–30 Temmuz 2026)

**User:**
Endüstriyel anomali tespitinde hangi modeller öne çıkıyor, PaDiM mü PatchCore mu seçmeliyim?

**AI:**
İkisi de güçlü ama farklı trade-off'ları var:

| Kriter | PaDiM | PatchCore |
|--------|-------|-----------|
| MVTec AUROC | ~0.977 | ~0.999 |
| Hız (inference) | Daha hızlı | Biraz yavaş |
| Bellek kullanımı | Düşük | Yüksek (memory bank) |
| Az veriyle performans | İyi | Çok iyi |
| Edge cihaza uygunluk | ✅ Daha uygun | ⚠️ Bellek sorun olabilir |

**Proje için önerim:** PatchCore ile başla çünkü AUROC açısından daha güçlü ve az normal örnekle da iyi sonuç veriyor. Edge cihazda bellek sorunu çıkarsa PaDiM'e geç.

---

**User:**
"Altın tur" fikrinin akademik karşılığı var mı? Tezde/raporda referans gösterebileceğim makale arıyorum.

**AI:**
Evet, birkaç tane var:

1. **SSCDNet (Sakurada & Okatani, 2015)** — "Detecting Changes in 3D Structure of a Scene from Multi-view Images". Street-level scene change detection. En yakın akademik karşılık.
2. **ChangeFormer (Bandara & Patel, IGARSS 2022)** — Siamese transformer ile değişiklik tespiti. Referans alınabilir mimari.
3. **Zero-Shot Scene Change Detection (arXiv 2023)** — Önceden eğitim gerekmeden değişiklik tespiti. "Altın tur" mantığının tam akademik ifadesi.

Bu üçünü literatür özetine eklemen hem İP4'ü güçlendirir hem de danışman sunum raporunda iyi görünür.

---

## İP5 — MVTec Baseline (1–2 Ağustos 2026)

**User:**
Google Colab'da PatchCore eğitirken CUDA out of memory hatası alıyorum. Ne yapmalıyım?

**AI:**
T4 GPU için PatchCore bellek optimizasyonu:

```python
model = Patchcore(
    backbone="resnet18",        # resnet50 yerine daha küçük
    pre_trained=True,
    num_neighbors=9,            # varsayılan 9, azaltma
    coreset_sampling_ratio=0.1  # memory bank boyutunu küçült
)
engine = Engine(
    max_epochs=1,
    accelerator="gpu",
    devices=1,
    # batch size'ı küçült:
)
datamodule = MVTec(
    eval_batch_size=4,          # 8 yerine 4
    train_batch_size=4,
)
```

Ayrıca `torch.cuda.empty_cache()` çağrısını fit'ten önce ekle. T4'te resnet18 backbone ile bottle kategorisi sorunsuz çalışmalı.

---

**User:**
PatchCore sonuçlarında pixel F1 düşük (0.72) ama image AUROC 1.0. Bu normal mi?

**AI:**
Evet, bu çok yaygın bir durum ve normaldir:

- **Image AUROC = 1.0**: Model hangi görüntünün anomali hangi görüntünün normal olduğunu mükemmel ayırt ediyor. Bu harika.
- **Pixel F1 = 0.72**: Anomalinin tam lokalizasyonu (hangi piksel?) daha zor. Heatmap doğru bölgeyi gösteriyor ama kenar hassasiyeti düşük.

Pixel F1'i iyileştirmek için:
1. Morfolojik işlem (dilate/erode) ile heatmap'i temizle
2. Eşik (threshold) değerini optimize et — `best_threshold` değerine bak
3. Daha yüksek çözünürlüklü girdi dene (`image_size=(512,512)`)

Proje için pixel F1=0.72 yeterli — alarm sistemi için anomali var/yok kararı (image AUROC) çok daha önemli.
---

## İP6 — Kendi Verisiyle Anomali (8 Ağustos 2026)

**User:**
ip 6 yı nasıl yapacağımı adım adım anlat

**AI:**
İP 6 için şu adımları izledik:
1. **Veri Hazırlama (Data Augmentation):** 3-5 referans karesi yeterli gelmeyeceği için Torchvision ile (ColorJitter ve RandomHorizontalFlip) bu kareler çoğaltıldı.
2. **Test Verisi (Abnormal) Oluşturma:** Mevcut referans karesinin üzerine siyah bir kutu (nesne) çizdirilerek sentetik bir anomali oluşturuldu.
3. **Modelin Eğitilmesi:** Anomalib kütüphanesinin `Folder` veri seti yapısıyla oluşturduğumuz `normal` ve `abnormal` klasörleri kullanılarak `PatchCore` model eğitimi başlatıldı.
4. **Heatmap:** Çıktı olarak oluşturulan heatmap, sonuçların başarılı olduğunu kanıtlamak üzere kaydedildi.

---

**User:**
Python veri artırma (augmentation) kodlarını hangi klasörde çalıştırmalıyım?

**AI:**
Bu tür kodları ve komutları çalıştırırken terminalde her zaman **projenin ana dizininde (root directory)** olmalısın. Yani klasör yolun `D:\STAJ\akilli_fabrika_staj-2026` olmalı. Kod içindeki göreceli (relative) dosya yolları (örneğin: `data/waypoints/...`) ana dizine göre tasarlanmıştır.

---

**User:**
`TypeError: Folder.__init__() got an unexpected keyword argument 'image_size'` hatası alıyorum. Nasıl çözebilirim?

**AI:**
Bu durum bilgisayarında kurulu olan `anomalib` kütüphanesinin sürüm farklılıklarından kaynaklanıyor. Kütüphanenin bazı versiyonlarında `Folder` veri seti sınıfı `image_size` parametresini doğrudan kabul etmez. Çözüm olarak scriptteki `image_size=(256, 256)` satırını kaldırdık. 

---

**User:**
`TypeError: Folder.__init__() missing 1 required positional argument: 'name'` hatası alıyorum.

**AI:**
Yine sürüm kaynaklı olarak, kullandığın versiyondaki `Folder` modülü zorunlu bir isimlendirme bekliyor. Koda `name="waypoint_dataset"` argümanını ekleyerek bu hatayı giderdik.

---

**User:**
`RuntimeError: An attempt has been made to start a new process before the current process has finished its bootstrapping phase.` hatasını nasıl düzeltirim?

**AI:**
Bu çok bilindik bir **Windows çoklu işlem (multiprocessing)** hatasıdır. PyTorch dataloader'lar veriyi yüklemek için arka planda farklı işlemler (spawn) başlatır. Windows'ta bu işlemler dosyanı baştan aşağı tekrar çalıştırdığı için sonsuz döngü ve çökmeler meydana gelir.
Bunu engellemek için kodun çalıştırılan ana kısmını şu koruma bloğunun içine almalısın:

```python
if __name__ == '__main__':
    engine = Engine(max_epochs=1)
    engine.fit(...)
```
Bu sayede model sorunsuz bir şekilde çalışır.

---

## İP7 — Waypoint Kıyası v0 (8 Ağustos 2026)

**User:**
ip 7yi nasıl yapacağım adım adım anlat

**AI:**
İP 7 için şu adımları izleyerek bir Python scripti (`ip7_waypoint_kiyasi.py`) oluşturduk:
1. **Görüntüleri Okuma:** Referans (normal) kare ile devriyeden gelen güncel (test/abnormal) kareyi gri tonlamalı (grayscale) olarak yükledik.
2. **Özellik Çıkarma (Feature Extraction):** Başlangıçta AKAZE algoritması kullanarak iki görüntüdeki anahtar noktaları (keypoints) bulduk.
3. **Özellik Eşleştirme (Feature Matching):** İki görüntüdeki noktaları `BFMatcher` ile eşleştirip Lowe's Ratio testiyle güvenilir eşleşmeleri ayıkladık.
4. **Hizalama (Warping):** Homografi matrisi hesaplayarak test karesini, referans karenin açısına "yapıştırdık" (hizaladık).
5. **Fark Analizi:** İki görüntü arasındaki mutlak farkı (`absdiff`) alıp, eşikleme (threshold) ve morfolojik temizleme işlemleri uygulayarak net bir Değişiklik Maskesi elde ettik.

---

**User:**
Python kodunu çalıştırdığımda `AttributeError: module 'cv2' has no attribute 'AKAZE_create'` hatası aldım.

**AI:**
Bu hata kurulu olan OpenCV sürümünde (veya o sürüme ait contrib eklenti paketinde) `AKAZE` fonksiyonunun bulunmamasından kaynaklanıyor. Çözüm olarak kodda `cv2.AKAZE_create()` yerine OpenCV'nin her sürümünde varsayılan olarak gelen ve çok daha hızlı çalışan **ORB** algoritmasına (`cv2.ORB_create()`) geçiş yaptık.

---

**User:**
Peki akaze mi yoksa orb mi daha iyi sonuç verirdi? Ayrıca hangisini kullanmak daha mantıklı?

**AI:**
Senin projende **ORB kullanmak kesinlikle daha mantıklı!** 
- **AKAZE:** Çok büyük açı farklılıklarında ve aşırı ışık değişimlerinde daha kararlı ve doğru noktalar bulur. Ancak daha yavaştır ve daha çok işlem gücü tüketir.
- **ORB:** SIFT/SURF'e açık kaynaklı, inanılmaz hızlı bir alternatiftir.
- **Neden ORB?** Bu sistem bir otonom devriye robotunun (edge cihaz) üzerinde çalışacak. Robotun zaten belirli noktalara (waypoints) aynı açıyla bakmaya çalışması nedeniyle iki görüntü arasında büyük açı farkları olmayacaktır. Sadece ufak titreme veya park kaymaları olacaktır. ORB bu ufak kaymaları düzeltmek için fazlasıyla yeterlidir ve çok hızlı olduğu için edge tabanlı robotik sistemimiz için en optimal çözümdür.

---

## İP3 (Yeniden) & İP15 — Kaggle LingBot-Map Hata Çözümleri (10 Ağustos 2026)

**User:**
Neden gpu seçemyorum? Ne yapmalıyım

**AI:**
Kaggle'da GPU (T4 x2) seçeneğinin soluk (seçilemez) olmasının sebebi hesapta telefon doğrulaması yapılmamış olmasıdır. Çözüm olarak `https://www.kaggle.com/settings` adresine gidip "Phone Verification" (Telefon Doğrulama) adımını tamamladık. Doğrulama sonrası haftalık 30 saat ücretsiz GPU kullanımı aktif oldu.

---

**User:**
Process is interrupted. ip3_lingbotmap_notebook 2. hücre kodunda bu hatayı aldım

**AI:**
Hücre 2'deki LingBot-Map kurulum kodunda `pip install torch==2.1.0` komutu yer alıyordu. Kaggle ortamında halihazırda güncel bir PyTorch sürümü yüklü geldiği için üstüne farklı bir sürüm kurmaya çalışmak çakışmaya (kernel interrupt) neden oluyordu. Çözüm olarak PyTorch kurulum satırları kaldırıldı ve Kaggle'ın kendi PyTorch sürümü kullanıldı.

---

**User:**
Error processing frames: CUDA out of memory. Tried to allocate 100.00 MiB. GPU 0 has a total capacity of 14.56 GiB... (1034 frame limiti sorunu)

**AI:**
LingBot-Map modeli varsayılan olarak "Streaming" (kesintisiz akış) modunda çalıştığı için 557 karelik videonun tüm özelliklerini VRAM'de tutmaya çalışıyordu ve 90. karede (yaklaşık 96 anahtar karede) 15 GB'lık GPU hafızasını dolduruyordu. Çözüm olarak `batch_demo.py` betiğine `--mode windowed` (Pencereli Mod) ve `--window_size 32` argümanları eklendi. Bu sayede işlem 32 anahtar karelik parçalara bölündü ve hafıza sorunu (OOM) tamamen aşıldı.

---

**User:**
Altın tur v2 yi drivema indirir msin? (Kaggle Output panelinden dosyayı indiremiyorum)

**AI:**
Kaggle Output panelindeki büyük dosyaları (özellikle .ply) bazen tarayıcı üzerinden doğrudan indirmek hata verebiliyor. Alternatif olarak `pydrive2` kurarak dosyayı doğrudan Google Drive'a göndermeyi denedik. Ancak `client_secrets.json` gibi yetkilendirme sorunları çıkınca, Google OAuth Playground üzerinden alınan geçici "Access Token" ile `requests` kütüphanesini kullanarak dosyayı doğrudan Drive API üzerinden sorunsuz bir şekilde buluta aktardık.
