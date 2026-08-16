import matplotlib.pyplot as plt
import numpy as np
import torch
from anomalib.data import MVTecAD
from anomalib.engine import Engine
from anomalib.models import Padim  # Patchcore kullanmak istersen: from anomalib.models import Patchcore

# 1. Veri setini ve kategoriyi tanımla (MVTec-AD otomatik indirilecektir)
datamodule = MVTecAD(
    root="./datasets/MVTecAD",
    category="bottle",
    train_batch_size=32,
    eval_batch_size=32,
)

# 2. Modeli tanımla (PaDiM veya Patchcore)
model = Padim()
# Alternatif: model = Patchcore()

# 3. Training Engine oluştur ve modeli eğit
engine = Engine(max_epochs=1)
engine.fit(datamodule=datamodule, model=model)

# 4. Test seti üzerinde tahmin yap (Heatmap ve Anomaly Score üretir)
predictions = engine.predict(datamodule=datamodule, model=model)

# 5. Anomali Heatmap Çıktılarını Görselleştir
for prediction in predictions[:3]:  # İlk 3 örnek için gösterelim
    # Orijinal Görüntü (CHW -> HWC dönüşümü)
    image = prediction.image.permute(1, 2, 0).cpu().numpy()
    # Normalize edilmişse [0, 1] aralığına getir
    image = (image - image.min()) / (image.max() - image.min())

    # Pixel-level Anomali Haritası (Heatmap)
    anomaly_map = prediction.anomaly_map.squeeze().cpu().numpy()

    # Çizim
    fig, axes = plt.subplots(1, 2, figsize=(8, 4))
    axes[0].imshow(image)
    axes[0].set_title("Orijinal Test Görüntüsü")
    axes[0].axis("off")

    im = axes[1].imshow(anomaly_map, cmap="jet")
    axes[1].set_title(
        f"Anomali Heatmap (Skor: {prediction.pred_score.item():.2f})"
    )
    axes[1].axis("off")

    plt.colorbar(im, ax=axes[1])
    plt.show()