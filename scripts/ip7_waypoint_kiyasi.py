import cv2
import numpy as np
import os

def detect_changes(ref_path, test_path, output_path):
    # 1. Resimleri oku
    ref_img = cv2.imread(ref_path)
    test_img = cv2.imread(test_path)

    # İşlemleri kolaylaştırmak için gri tonlamaya çevir
    ref_gray = cv2.cvtColor(ref_img, cv2.COLOR_BGR2GRAY)
    test_gray = cv2.cvtColor(test_img, cv2.COLOR_BGR2GRAY)

    # 2. ORB (Özellik Çıkarıcı) oluştur
    orb = cv2.ORB_create()
    kp1, des1 = orb.detectAndCompute(ref_gray, None)
    kp2, des2 = orb.detectAndCompute(test_gray, None)

    # 3. Özellikleri eşleştir (BFMatcher)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    matches = bf.knnMatch(des1, des2, k=2)

    # İyi eşleşmeleri ayır (Lowe's ratio test)
    good_matches = []
    for m, n in matches:
        if m.distance < 0.75 * n.distance:
            good_matches.append(m)

    # 4. Yeterli eşleşme varsa Homografi hesapla ve Hizala (Warp)
    if len(good_matches) > 10:
        src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

        # Matrisi bul
        M, mask = cv2.findHomography(dst_pts, src_pts, cv2.RANSAC, 5.0)

        # Test resmini referans resmine hizala (yapıştır)
        h, w = ref_gray.shape
        aligned_test = cv2.warpPerspective(test_gray, M, (w, h))

        # 5. Farkı Al (Absolute Difference)
        diff = cv2.absdiff(ref_gray, aligned_test)

        # Farkı belirginleştir (Thresholding)
        _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)

        # Ufak gürültüleri temizle (Morfolojik işlemler)
        kernel = np.ones((5,5), np.uint8)
        clean_mask = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        clean_mask = cv2.morphologyEx(clean_mask, cv2.MORPH_CLOSE, kernel)

        # 6. Sonucu kaydet
        cv2.imwrite(output_path, clean_mask)
        print(f"Hizalama başarılı! Maske kaydedildi: {output_path}")

    else:
        print("Yeterli eşleşme bulunamadı, resimler çok farklı!")

# Kod doğrudan çalıştırıldığında testimizi yapalım:
if __name__ == '__main__':
    project_dir = "D:/STAJ/akilli_fabrika_staj-2026"
    
    # İP 6'da oluşturduğumuz verileri test için kullanıyoruz
    ref = f"{project_dir}/data/waypoints/referans_kareler/WP01.jpg"
    test = f"{project_dir}/data/waypoints/abnormal/WP01_degisik.jpg"
    out = f"{project_dir}/outputs/ip7_degisiklik_maskesi.png"
    
    os.makedirs(f"{project_dir}/outputs", exist_ok=True)
    detect_changes(ref, test, out)
