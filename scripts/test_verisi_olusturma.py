import cv2, os

project_dir = "d:/STAJ/akilli_fabrika_staj-2026"
abnormal_dir = os.path.join(project_dir, "data/waypoints/abnormal")
os.makedirs(abnormal_dir, exist_ok=True)

img_path = os.path.join(project_dir, "data/waypoints/referans_kareler/WP01.jpg")
img = cv2.imread(img_path)
# Sahneye "bırakılmış nesne" ekle: siyah dikdörtgen
h, w = img.shape[:2]
cv2.rectangle(img, (w//3, h//3), (w//2, h//2), (0, 0, 0), -1)
out_path = os.path.join(abnormal_dir, "WP01_degisik.jpg")
cv2.imwrite(out_path, img)
print(f"Test verisi başarıyla oluşturuldu: {out_path}")
