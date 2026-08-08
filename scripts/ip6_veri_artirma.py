from torchvision import transforms
from PIL import Image
import os

aug = transforms.Compose([
    transforms.ColorJitter(brightness=0.3, contrast=0.2),
    transforms.RandomHorizontalFlip(p=0.5),
])

# Projenin ana dizininden çalıştırılacağı varsayılarak yollar (paths) böyle verilmiştir.
input_dir = "data/waypoints/referans_kareler"
output_dir = "data/waypoints/normal"
os.makedirs(output_dir, exist_ok=True)

for img_file in os.listdir(input_dir):
    # Sadece .jpg resim dosyalarını işle, diğerlerini atla
    if not img_file.endswith(".jpg"):
        continue
        
    img = Image.open(f"{input_dir}/{img_file}")
    # Orjinali de normal klasörüne kopyala/kaydet
    img.save(f"{output_dir}/{img_file}")
    # 5 farklı augmented versiyon üret
    for i in range(5):
        aug_img = aug(img)
        aug_img.save(f"{output_dir}/{img_file.replace('.jpg', f'_aug{i}.jpg')}")

print("Veri artırma işlemi tamamlandı. Yeni resimler data/waypoints/normal klasörüne eklendi.")
