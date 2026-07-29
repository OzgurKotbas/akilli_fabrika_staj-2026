# Anomali Test Raporu - Özgür Kotbaş
**Tarih:** 29 Temmuz 2026

## Proje ve Klasör Yapısı

### `results` Klasörü İçeriği
Anomali testinin tamamlanması sonucunda oluşan çıktılar `results/Padim/MVTecAD/bottle/v1/` dizini altına kaydedilmiştir:
- **`weights/`:** Eğitilen Padim modelinin ağırlık (model) dosyalarını barındırır.
- **`images/`:** Modelin test aşamasında ürettiği anomali tahmin çıktılarını ve ısı haritalarını (heatmap) içerir.
- **`config.yaml`:** Çalıştırılan eğitime ait parametre ve yapılandırma bilgilerini saklar.

## Neler Yapıldı?
"Görsel Anomali Tespiti + Otomatik Devriye Raporu" staj projesi hedefleri (İP1 ve İP5 iş paketleri) doğrultusunda, `anomalib` kütüphanesi kullanılarak MVTec-AD veri seti üzerinde anomali tespiti model eğitimi ve testi gerçekleştirildi. 

Çalıştırılan komut:
`anomalib train --model Padim --data MVTecAD --data.category bottle`

Bu komut ile:
- Hugging Face üzerinden önceden eğitilmiş ResNet18 ağırlıkları (`timm/resnet18.a1_in1k`) yüklendi.
- MVTec-AD veri seti indirilip dizine çıkartıldı.
- Model olarak **Padim** (Patch Distribution Modeling) mimarisi kullanıldı ve eğitim işlemi tamamlandı.

## Nasıl Sonuçlar Alındı?
Modelin eğitim ve test aşamaları başarıyla tamamlanmış olup yüksek AUROC ve F1 skorları elde edildi. Elde edilen değerler modelin "bottle" (şişe) kategorisindeki anomalileri başarıyla tespit edebildiğini göstermektedir.

- **Eğitim Süresi:** ~40.35 saniye
- **Test Süresi:** ~15.41 saniye
- **İşlem Hızı (Throughput):** 5.38 FPS

**Test Metrikleri:**
- `image_AUROC`: 0.9952
- `image_F1Score`: 0.9687
- `pixel_AUROC`: 0.9799
- `pixel_F1Score`: 0.6944

## Loglardan İlgili Kısımlar

```text
...
| Name          | Type           | Params | Mode  | FLOPs |
|---------------|----------------|--------|-------|-------|
| pre_processor | PreProcessor   | 0      | train | 0     |
| post_processor| PostProcessor  | 0      | train | 0     |
| evaluator     | Evaluator      | 0      | train | 0     |
| model         | PadimModel     | 2.8 M  | train | 0     |
...
INFO - Fitting a Gaussian to the embedding collected from the training set.
INFO - Training took 40.35 seconds
...
INFO - Testing took 15.41229510307312 seconds
Throughput (batch_size=32) : 5.3853108472761 FPS

| Test metric   | DataLoader 0       |
|---------------|--------------------|
| image_AUROC   | 0.9952388061149597 |
| image_F1Score | 0.96875            |
| pixel_AUROC   | 0.9799723625183105 |
| pixel_F1Score | 0.6944619417190552 |
```
