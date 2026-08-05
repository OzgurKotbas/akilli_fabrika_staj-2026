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

## İP6 — Kendi Verisiyle Anomali (Planlanan — H3)

**User:**
Kendi waypoint görüntülerimle PatchCore eğitmek istiyorum ama çok az görüntüm var (3-5 kare). Bu yeterli mi?

**AI:**
PatchCore'un güçlü yanı tam da bu: **az normal örnekle da çalışıyor**. Memory bank tabanlı yaklaşımı nedeniyle 5-10 normal görüntü bile makul sonuç verir.

Ancak daha güvenilir sonuç için şunu öneriyorum:
1. **Veri augmentation**: Aynı kareyi farklı parlaklık/kontrast değerleriyle çoğalt:
```python
from torchvision import transforms
aug = transforms.Compose([
    transforms.ColorJitter(brightness=0.3, contrast=0.2),
    transforms.RandomHorizontalFlip(p=0.3),
])
```
2. Her waypoint için 10-15 farklı versiyon oluştur → toplam 30-45 görüntü
3. `Folder` datamodule kullan, `MVTec` değil

5 görüntüyle de çalışır ama alarm hassasiyeti düşük olacak. Augmentation ile bu sorunu büyük ölçüde aşarsın.

---

## İP7 — Waypoint Kıyas Hattı (Planlanan — H3)

**User:**
ORB feature matching ne zaman başarısız olur? Alternatifi nedir?

**AI:**
ORB şu durumlarda başarısız olur:

1. **Aydınlatma değişimi** (gündüz vs. gece, pencere gölgesi): ORB aydınlatmaya hassas.
2. **Büyük açı farkı**: Kamera açısı 15°'den fazla değiştiyse homografi hesabı bozulur.
3. **Az doku** (düz duvar, tekdüze zemin): Feature point bulunamaz.

**Alternatifler:**
| Yöntem | Avantaj | Ne zaman kullan |
|--------|---------|-----------------|
| SIFT | Aydınlatmaya daha dayanıklı | Işık değişimi varsa |
| AKAZE | Hız+dayanıklılık dengesi | Genel öneri |
| ECC (Enhanced Correlation Coefficient) | Doku gerektirmez | Düz yüzeylerde |
| Sabit kamera (tripod) | Hizalamaya hiç gerek yok | Kamera sabitlenebildiyse |

Waypoint kıyasında **tripod kullanıyorsan** hizalamaya gerek bile kalmayabilir — direk piksel farkı alabilirsin.

---
