# Bu kod akilli_fabrika_staj-2026 (root) kök dizininde çalıştırılmalı
from torchvision import transforms
from PIL import Image
import os

aug = transforms.Compose([
    transforms.ColorJitter(brightness=0.3, contrast=0.2),
    transforms.RandomHorizontalFlip(p=0.5),
])

input_dir = "D:\\STAJ\\akilli_fabrika_staj-2026\\data\\waypoints\\referans_kareler"
output_dir = "D:\\STAJ\\akilli_fabrika_staj-2026\\data\\waypoints\\normal"
os.makedirs(output_dir, exist_ok=True)

for img_file in os.listdir(input_dir):
    img = Image.open(f"{input_dir}/{img_file}")
    # Orjinali de kaydet
    img.save(f"{output_dir}/{img_file}")
    # 5 farklı augmented versiyon üret
    for i in range(5):
        aug_img = aug(img)
        aug_img.save(f"{output_dir}/{img_file.replace('.jpg', f'_aug{i}.jpg')}")
