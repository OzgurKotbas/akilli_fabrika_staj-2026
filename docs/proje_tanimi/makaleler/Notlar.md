## 1. Makale - FastFlow: Denetimsiz Anomali Tespiti ve Konumlandırma
1.1 - Denetimsiz anomali tespiti ve konumlandırması, yeterli anomali verisi toplamanın ve etiketlemenin mümkün olmadığı durumlarda pratik uygulama için çok önemlidir.
1.2 - Anomali skoru, özelliklerin arasındaki mesafenin ölçülmesiyle hesaplanır.
1.3 - Anormallikleri belirlemek için 2D ile uygulanan FastFlow, anomali tespitinde %99,4 AUC'ye ulaşmaktadır.
1.4 - Özellik çıkarımı modülü ve dağıtım tahmin modülü olmak üzere 2 ana modül vardır.
1.5 - Dağıtım tahmini modülünde, önceki yaklaşımlar normal görüntüler için özelliklerin dağılımını modellemek üzere parametrik olmayan yöntemi kullanmıştır.
1.6 - Sistem, anormallik tespitinin yanı sıra tüm görüntünün uçtan uca çıkarımını destekler ve doğrudan çıktı verir.
1.7 - Mevcut anomali tespit yöntemleri temel olarak yeniden yapılandırmaya dayalı ve temsile dayalı yöntemlerdir.
1.8 - Yeniden yapılandırmaya dayalı yöntemler, normal verileri kodlamak ve yeniden oluşturmak için oto-kodlayıcılar, üretken modeller ve düşman sinir ağları kullanır.
1.9 - Küresel ve yerel arasındaki ilişkiyi daha iyi hale getirmek için DeiT ve CaiT örnek olarak verilebilir.
1.10 - DeiT, öğretmen-öğrenci modelini tanıtarak görüntü dönüştürücülerin verimli öğrenmesini sağlar ve dönüştürücülere özgü son teknoloji bir stratejidir.
1.11 - CaiT, kodlayıcı/kod çözücü mimarisine uygun tasarlanmış basit ama etkili bir mimaridir.

## 2. Makale - MVTec Anomali Tespiti Veri Kümesi: Kapsamlı Gerçek Dünya Verileri
2.1 - Doğal görüntü verilerindeki anormal yapıların tespiti, özellikle endüstriyel denetim ve kalite kontrol görevleri için kritik öneme sahiptir.
2.2 - MVTec veri seti, algoritmaların anomali konumlandırma performansını ölçebilmek için 70'ten fazla kusur türünü (çizik, kirlenme vb.) barındıran 5354 yüksek çözünürlüklü görüntü ve piksel hassasiyetinde etiketler içerir.
2.3 - Anomali tespiti ve segmentasyonu yapan algoritmalar, test görüntüsündeki her piksel için gerçek değerli bir anomali puanı üreterek değerlendirilir.
2.4 - Görüntülerdeki anomalilerin doğru şekilde konumlandırılıp önceliklendirilmesi için, piksel bazlı ölçümlerin (TPR, FPR vb.) yanı sıra, daha küçük anormalliklerin tespitine de eşit önem veren bölge başına örtüşme (PRO) gibi metrikler kullanılır.

## 3. Makale - PaDiM: Anomali Tespiti ve Konumlandırması için Yama Dağıtım Modelleme Çerçevesi
3.1 - PaDiM, tek sınıflı öğrenme ortamında görüntülerdeki anormallikleri eş zamanlı olarak tespit etmek ve konumlandırmak için tasarlanmış verimli bir çerçevedir.
3.2 - Yöntem, yama gömme işlemleri için önceden eğitilmiş bir Evrişimsel Sinir Ağı (CNN) kullanır ve normal sınıfın temsilini çok değişkenli Gauss dağılımları ile oluşturur.
3.3 - Anormallikleri çok daha iyi konumlandırmak adına, model CNN'nin farklı anlamsal seviyeleri arasındaki korelasyonları da dikkate alarak hesaplama yapar.
3.4 - Test aşamasında, bir piksel yamasının anomali puanı (konumlandırma haritası), test yaması ile öğrenilen normal dağılım arasındaki Mahalanobis mesafesi hesaplanarak bulunur ve yüksek puanlar anomalili alanları gösterir.

## 4. Makale - SimpleNet: Görüntü Anomali Tespiti ve Konumlandırması için Basit Bir Ağ
4.1 - SimpleNet, endüstriyel senaryolardaki anormallikleri hızlı bir şekilde tespit edip yerelleştirmeyi (konumlandırmayı) amaçlayan, uygulaması kolay ve dört bileşenli bir sinir ağı mimarisidir.
4.2 - Ağ; önceden eğitilmiş özellik çıkarıcı, sığ bir özellik adaptörü, Gauss gürültüsü ile anomali özellikleri üreten bir üretici ve ikili bir anomali ayırıcıdan oluşur.
4.3 - Görüntüler üzerinde anormallik sentezlemenin getirdiği zorlukları aşmak için, doğrudan özellik uzayındaki normal özelliklere gürültü eklenerek sahte anormal özellikler üretilir.
4.4 - Çıkarım sırasında, ayırıcı modülü her bir uzamsal konumda anomali puanları üreterek anomali haritasını (lokalizasyon) oluşturur ve bu haritadaki maksimum puan görüntünün genel anomali tespit puanı olarak belirlenir.

## 5. Makale - Sıfır Atışlı Sahne Değişikliği Algılama
5.1 - Anomali ve sahne değişikliği tespiti, zaman farkı olan referans ve sorgu görüntüleri arasında "yeni" veya "kayıp" nesneleri, özel bir eğitim gerektirmeden sıfır atışlı olarak bulmayı hedefler.
5.2 - Görüntülerdeki farklılıkları ve anomalileri konumlandırmak için, bir segmentasyon modeli ile ardışık kareleri takip eden bir izleme modeli entegre çalışır.
5.3 - Büyük zaman aralıklarından kaynaklanan içerik (ani kaybolmalar) ve stil boşlukları (aydınlatma, hava durumu), tespit hatalarını önlemek için içerik eşikleri ve stil köprüleme katmanları kullanılarak aşılır.

## 6. Makale - RMMDet: Yol Kenarı Çok Tipli ve Çok Gruplu Sensör Algılama
6.1 - Otonom sürüş sistemlerinde kamera, radar ve lidar sensör verilerini birleştirerek trafik akışındaki nesne ve durum tespiti görevlerini yerine getirir.
6.2 - Sensörlerden birinin arızalanması veya kirlenmesi gibi anormal koşullarda sistemin çökmemesi için özellik düzeyinde değil, sonuç düzeyinde birleştirme (late fusion) yapar.
6.3 - Alt modül olan çoklu ajanlı planlama sistemi, trafik sıkışıklığı veya yoğunluk gibi anormal durumları haritalandırıp tespit ederek araç rotalarının optimizasyonunu önceliklendirir.

## 7. Makale - ChangeFormer: Değişiklik Tespiti için Transformatör Tabanlı Bir Siamese Ağı
7.1 - Farklı zamanlarda elde edilen uzaktan algılama görüntülerinden afet hasarları veya ormansızlaşma gibi çevresel anormallikleri (değişiklikleri) tespit etmeyi amaçlar.
7.2 - Aydınlatma veya mevsimsel farklılıklar gibi ilgisiz değişimleri filtreleyip, sadece hedeflenen anormallikleri konumlandırmak için hiyerarşik transformatör kodlayıcı ve MLP kod çözücü kullanır.
7.3 - Çok ölçekli ve uzun menzilli bağlamsal bilgileri işleyerek, geleneksel CNN tabanlı yöntemlere kıyasla daha yüksek doğrulukta bir değişiklik ve anomali konumlandırması sağlar.

## 8. Makale - DUSt3R: Geometrik 3D Görüntüleme Kolaylaştırıldı
8.1 - Kısıtlanmamış rastgele görüntü koleksiyonlarından, kamera parametrelerine veya ön bilgiye ihtiyaç duymadan 3B nokta haritaları üreterek derinlik tahmini ve konumlandırma (yerelleştirme) yapar.
8.2 - Geleneksel Hareketten Yapı Oluşturma (SfM) algoritmalarının başarısız olduğu, özellik eşleştirme hataları ve gürültüye yatkınlık gibi "anormal" kopma durumlarını tek bir uçtan uca modelle aşar.
8.3 - Çıktı olarak güven haritaları üreterek, şeffaf nesneler veya gökyüzü gibi iyi tanımlanmamış zorlu (anormal) piksellerin ağırlığını düşürür ve tespitte güvenilir bölgeleri önceliklendirir.

## 9. Makale - WinCLIP: Zero-/Few-Shot Anomaly Classification and Segmentation
9.1 - WinCLIP, görsel denetim süreçlerindeki zorlukları çözmek için görev-özel eğitim veya etiketleme gerektirmeyen sıfır-atışlı ve az-atışlı anomali sınıflandırma ile konumlandırma modelidir.
9.2 - Sadece normal görüntülerin kullanıldığı ve anomali verisinin yetersiz olduğu durumlarda, önceden eğitilmiş vizyon-dil modellerinin (CLIP) gücünden yararlanır.
9.3 - Anormal durumları ve normalliği daha iyi tanımlayabilmek için "hasarlı", "kusurlu" gibi durum sözcükleri ve "görsel denetim için fotoğraf" gibi çeşitli metin şablonlarından oluşan kompozisyonel bir bilgi istemi (prompt) topluluğu kullanır.
9.4 - Sıfır-atışlı (zero-shot) anomali segmentasyonunda piksel düzeyinde doğru sonuçlar elde edebilmek için, görüntü üzerinde kayan pencereler (sliding windows) yardımıyla çok ölçekli yoğun görsel özellikler çıkarır.
9.5 - Ağ, anomali skorlarını pencere (window), yama (patch) ve görüntü düzeyindeki (image-level) farklı ölçekli özelliklerden harmonik ortalama yöntemiyle birleştirerek anomali konumlandırma haritası üretir.
9.6 - Az-normal-atışlı (few-normal-shot) ayarında çalışan WinCLIP+, mevcut normal referans görüntülerinden elde edilen görsel bağlam bilgisini de sürece dahil eder.
9.7 - WinCLIP+, referans ilişkilendirme modülü ile çok ölçekli özellik haritalarındaki normal verileri hafızasında tutarak, sorgu görüntüsüyle kosinüs benzerliği üzerinden doğrudan görsel anomali skoru hesaplar.
9.8 - Yöntem, dile dayalı (language-guided) sıfır-atışlı anomali skorları ile referans görüntülere dayalı görsel anomali skorlarını birleştirerek birbirini tamamlayıcı bir konumlandırma haritası sunar.
9.9 - MVTec-AD veri setinde hiçbir ek ayarlama yapılmadan sıfır-atışlı anomali sınıflandırmasında %91.8, konumlandırma (segmentasyon) görevinde ise %85.1 AUROC performansı göstermiştir.
9.10 - Sadece bir adet normal görüntünün kullanıldığı (1-shot) senaryoda ise sınıflandırma performansı %93.1'e, segmentasyon performansı %95.2'ye çıkarak mevcut en iyi yöntemleri büyük farkla geride bırakmıştır.
9.11 - Mantıksal anomaliler (eksik parça vb.) gibi sadece dille tanımlanması zor olan yapısal kusurların tespiti, referans görüntüler kullanılarak WinCLIP+ ile başarılı bir şekilde gerçekleştirilebilmektedir.
9.12 - Genel CLIP modelinden farklı olarak, WinCLIP anomali tespiti görevinde dilin sadece nesne ismini değil, nesnenin fiziksel "durumunu" belirlemede ne kadar kritik bir önceliklendirme aracı olduğunu kanıtlamıştır.

## 10. Makale - Geometric Context Transformer for Streaming 3D Reconstruction (LingBot-Map)
10.1 - LingBot-Map, sürekli bir video akışından eş zamanlı kamera pozisyonu tespiti (lokalizasyon) ve yoğun 3B nokta bulutu haritalaması yapan, Geometrik Bağlam Transformatörü (GCT) tabanlı ileri beslemeli bir modeldir.
10.2 - Yöntem, 3B akış konumlandırmasındaki en büyük zorluk olan "seçici bağlam yönetimi" problemini (kompakt durum ile uzun vadeli tutarlılık arasındaki denge) uçtan uca öğrenilebilen bir dikkat mekanizmasıyla çözer.
10.3 - Geometrik Bağlam Dikkat (GCA) modülü, SLAM (Eşzamanlı Konumlandırma ve Haritalama) sistemlerinden esinlenerek yapılandırılmış üç tamamlayıcı bağlamı yönetir.
10.4 - "Çapa Bağlamı" (Anchor Context), sistemin başlangıcında mutlak bir ölçek ve tutarlı bir koordinat sistemi temeli oluşturarak sistemin uzaysal olarak hizalanmasını sağlar.
10.5 - "Yerel Poz-Referans Penceresi", ağın en son gözlemlenen karelerdeki yoğun görsel özellikleri tutmasına olanak tanıyarak doğru yerel geometri ve göreceli poz tespitine imkan verir.
10.6 - "Yörünge Hafızası", tüm gözlem geçmişini çok daha az yer kaplayan, sıkıştırılmış kare başına belirteçlere (token) dönüştürerek global tutarlılık ve kayma (drift) düzeltmesi işlevi görür.
10.7 - Yörünge hafızasındaki tokenlere entegre edilen video zamansal konum kodlamaları (Video RoPE), global yörünge üzerine bir zaman sıralaması dayatarak uzun menzilli hataların düzeltilmesine yardımcı olur.
10.8 - Nedensel (causal) dikkatin doğrusal büyümesinin aksine, GCA'nın yapılandırılmış bağlamı sayesinde kare başına bellek ve işlem maliyeti büyük ölçüde sabit kalarak 10.000 kareyi aşan uzun dizilerde stabil konumlandırma sunar.
10.9 - LingBot-Map, 518x378 çözünürlüklü girişler kullanılarak standart bir GPU üzerinde saniyede yaklaşık 20 kare (FPS) hızında, gerçek zamanlı 3B konumlandırma ve haritalama gerçekleştirebilir.
10.10 - Optimizasyon tabanlı geleneksel paket ayarlaması (bundle adjustment) gibi işlemlere ihtiyaç duymadan, ileri beslemeli tek bir ağ akışıyla kameranın mutlak pozunu ve derinlik haritasını tahmin eder.
10.11 - Çok uzun yörüngeli sekanslar için geliştirilen "Görsel Odometri (VO) Modu", girişleri yerel pencerelere ayırır ve her pencereyi Sim(3) hizalaması ile birleştirerek sınırsız uzunluktaki alanlarda konumlandırma yapar.
10.12 - Yöntem, ağın bellek kullanımını sınırlandırmak ve yörünge takibini iyileştirmek için, optik akış büyüklüğüne göre devreye giren adaptif bir anahtar kare (keyframe) seçim stratejisi kullanır.
10.13 - Eğitim aşamasında uzun dizi optimizasyonunun kararlılığını sağlamak amacıyla, eğitim görünümlerinin sayısının adım adım artırıldığı aşamalı (progressive) bir müfredat stratejisi uygulanmıştır.
10.14 - Çok sayıda kare kullanıldığında GPU bellek sınırını aşmamak için Ulysses bağlam paralelliği stratejisi devreye sokularak görüntülerin birden fazla GPU üzerinde verimli şekilde işlenmesi sağlanmıştır.
10.15 - Kayıp fonksiyonu; derinlik kaybı, mutlak poz kaybı ve yerel pencere içerisindeki yörünge tutarlılığını sağlamlaştıran göreceli poz kaybı (rotasyon ve çeviri hatası) olmak üzere üç temel geometrik kısıtlamayı birleştirir.
10.16 - LingBot-Map, Oxford Spires, ETH3D ve 7-Scenes gibi zorlu veri setlerinde hem mevcut akış tabanlı yöntemleri hem de çevrimdışı 3B konumlandırma algoritmalarını doğruluk ve çalışma hızı bakımından büyük farkla geride bırakmıştır.

 ### Makale Linkleri
 1. FastFlow: Denetimsiz Anomali Tespiti ve Konumlandırma - https://arxiv.org/abs/2111.07677
 
 2. MVTec Anomali Tespiti Veri Kümesi: Kapsamlı Gerçek Dünya Verileri - https://www.researchgate.net/publication/348278659_The_MVTec_Anomaly_Detection_Dataset_A_Comprehensive_Real-World_Dataset_for_Unsupervised_Anomaly_Detection 
 Dataset (MVTec) - https://www.mvtec.com/research-teaching/datasets

 3. PaDiM: Anomali Tespiti ve Konumlandırması için Yama Dağıtım Modelleme Çerçevesi - https://arxiv.org/abs/2011.08785

 4. SimpleNet: Görüntü Anomali Tespiti ve Konumlandırması için Basit Bir Ağ - https://arxiv.org/abs/2303.15140 
 Github Repo- https://github.com/DonaldRR/SimpleNet/tree/main 

5. Sıfır Atışlı Sahne Değişikliği Algılama (Zero-Shot Scene Change Detection) - https://github.com/kyusik-cho/ZSSCD

6. RMMDet: Yol Kenarı Çok Tipli ve Çok Gruplu Sensör Algılama - https://arxiv.org/abs/2305.02203 
Github Repo - https://github.com/OrangeSodahub/RMMDet

7. ChangeFormer: Transformatör Tabanlı Bir Siamese Ağı - https://github.com/wgcban/ChangeFormer 

8. DUSt3R: Geometrik 3D Görüntüleme Kolaylaştırıldı - https://arxiv.org/abs/2312.14132 
Proje Sayfası: https://europe.naverlabs.com/research/publications/dust3r-geometric-3d-vision-made-easy/

9. WinCLIP: Zero-/Few-Shot Anomaly Classification and Segmentation - https://arxiv.org/abs/2303.14814

10. LingBot-Map: Geometric Context Transformer for Streaming 3D Reconstruction - https://arxiv.org/abs/2604.14141 
Github Repo - https://github.com/robbyant/lingbot-map 
Proje Sayfası: https://technology.robbyant.com/lingbot-map