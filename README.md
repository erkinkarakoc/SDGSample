# Binek / kamyon sentetik veri laboratuvarı

Blender + Python ile 100 yol kamerası görüntüsü, görünür bounding box, semantic segmentation ve instance segmentation üretir. Araç modelleri lisanslı kaynaklardan alınmıştır; sahne kurulumu, randomization ve etiket üretimi Python ile yapılır.

**Bu bir veri üreticisidir.** Gerçek fotoğraftan otomobil/kamyon tahmini yapan eğitilmiş bir model içermez. Model eğitimi ve gerçek veride değerlendirme ayrı aşamadır.

## Tamamlanan üretim

- 100 RGB görüntü, 100 semantic maske, 100 instance maske.
- 398 görünür nesne: 201 binek otomobil, 197 kamyon.
- 80 train / 10 validation / 10 test; sahne grupları ayrık.
- Disk üzerindeki 100 örneğin doğrulaması: **PASS** (`outputs/vehicle_dataset/validation_report.json`).
- Dört etiket birim testi ve gerçek Cycles örtülme regresyonu geçti.
- `--resume` testi tamamlanmış örnekleri yeniden render etmeden bitirdi.
- Eski `first_render` örneği kaldırıldı.

## Çıktıyı inceleme

Üretim tamamlandığında `outputs/vehicle_dataset/preview.html` dosyasını tarayıcıda aç. Örnekler arasında gezin, kutuları ve renkli sınıf maskesini açıp kapat. Renkli overlay yalnızca inceleme içindir; eğitim maskeleri sayısal ID PNG dosyalarıdır.

| Çıktı | Anlamı |
|---|---|
| `images/000000.png` | 1024 × 576 RGB, Cycles, 32 samples, denoising |
| `semantic/000000.png` | 8-bit grayscale; 0 background, 1 car, 2 truck |
| `instance/000000.png` | 16-bit grayscale; 0 background, her araç için ayrı ID |
| `labels/000000.txt` | YOLO detection; 0 car, 1 truck; normalize cx cy w h |
| `metadata/000000.json` | Seed, sınıflar, pozlar, kamera K/transform, görünür kutular, alanlar, RLE maskeler, dosya/kod hash'leri |
| `annotations/coco.json` | COCO xywh kutuları ve kayıpsız uncompressed RLE segmentasyonları |
| `annotations/train.json`, `val.json`, `test.json` | Ayrı COCO alt kümeleri |
| `dataset.yaml` ve split `.txt` dosyaları | YOLO detection veri kümesi tanımı |
| `validation_report.json` | Diskteki gerçek dosyalara uygulanan doğrulama raporu |
| `example_scene.blend` | İlk örneği Blender'da incelemek için sahne |

YOLO **detection** export edilir. Segmentation eğitiminde semantic/instance maskelerini veya COCO RLE'yi kullan. COCO tüketicisinin uncompressed RLE desteğini kontrol et; poligon dönüşümü yapılmadığı için delikler ve ayrı görünen parçalar korunur.

Veri kümesini başka bir klasöre taşırsan `dataset.yaml` içindeki `path` değerini güncelle. COCO `file_name` alanları veri kümesi köküne göredir.

## Çalıştırma

Proje klasöründe PowerShell; Blender 3.4.1 ile doğrulandı:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 3.4\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/generate.py
```

Tek örnek denemesi:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 3.4\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/generate.py -- --count 1 --output outputs/quality_check
```

Kesilen üretime devam etme:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 3.4\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python scripts/generate.py -- --resume
```

Resume, config/asset/kod hash'leri ve gerekli dosyalar eşleşiyorsa o örneği atlar. Config değiştirilmiş bir klasöre resume uygulanmaz; yeni çıktı klasörü kullan. Resume olmadan çalıştırmak çıktı dosyalarını yeniler. Mevcut split tasarımı 100 örnek / 10 sahne grubu içindir.

Doğrulama (Blender'ın NumPy paketi kullanılır; pip kurulumu gerekmez):

```powershell
& 'C:\Program Files\Blender Foundation\Blender 3.4\3.4\python\bin\python.exe' scripts/test_labels.py
& 'C:\Program Files\Blender Foundation\Blender 3.4\3.4\python\bin\python.exe' scripts/validate_dataset.py outputs/vehicle_dataset
```

Gerçek render üzerinden örtülme regresyonu:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 3.4\blender.exe' --background --factory-startup --disable-autoexec --python-exit-code 1 --python tests/render_mask_check.py
```

## Modüller

```text
config/dataset.json
        ↓
asset_manager.py  → Kaynak mesh'leri değerlendir, statik geometriye çevir, metreye ölçekle
scene_builder.py  → Sahne grubu, yola uygun yerleşim, renk/kamera/güneş çeşitliliği
renderer.py       → Aynı render'dan RGB ve IndexOB
labels.py         → Instance → semantic → görünür bbox / alan / RLE
exporter.py       → PNG / COCO / YOLO / metadata / tarayıcı görünümü
validate_dataset.py → Diskteki çıktıların çapraz kontrolü
```

`generate.py` modülleri yönetir. Sahne üretimi ile anotasyon üretimi ayrıdır. Seçim durumundan bağımsız veri API'si tercih edilir; render/kayıt için `bpy.ops` kullanılır.

## Etiket sözleşmesi

- Her aracın gövde, tekerlek, ayna ve diğer parçaları aynı `pass_index` değerini taşır.
- Cycles `IndexOB` çıktısı 32-bit EXR'den okunur; tam sayı kontrolünden sonra uint16 instance PNG'ye yazılır.
- Background = 0. Aynı sınıftaki iki araç semantic maskede aynı, instance maskede farklı ID taşır.
- Kutular **görünür maskenin** min/max piksel koordinatlarından çıkarılır. Tamamen örtülü veya kadraj dışındaki nesneye kutu verilmez; metadata'da görünmeyen ID kaydedilir.
- Origin sol üsttedir; `xmax` ve `ymax` hariç üst sınırlardır. Tek pikselin genişliği/yüksekliği 1'dir.
- RGB kenarları antialiasing içerir; IndexOB sert tam sayı maskesidir. Karışık RGB sınır pikselleri ile maskenin sert sınırı birebir renk eşitliği ifade etmez.
- Camlara opak, yansıtıcı dış yüzey materyali uygulanır. Transparan cam arkasındaki nesneleri etiketleme bu pilotun kapsamı dışındadır.
- Motion blur, depth of field ve lens distortion kullanılmaz. Kamera K, yatay sensor fit ve kare piksel varsayımına göredir. Blender kamera uzayı -Z ileri, +Y yukarıdır; CV extrinsic koordinatlarıyla karıştırma.
- Gölgeler, asfalt ve binalar background'dır. Yalnızca iki araç sınıfı segment edilir.

Blender'ın [render pass belgesi](https://docs.blender.org/manual/id/3.0/render/layers/passes.html), Object Index pass'in antialiasing içermediğini açıklar. Bu özellik tam sayı etiket sözleşmesinin bilinçli parçasıdır.

## Çeşitlilik ve ayırma

- Her görüntüde 3–5 araç; her iki sınıf en az 64 görünür piksel ile temsil edilir.
- Araçlar iki şeritte çakışmayan yerleşim yuvalarına atanır; küçük konum/yön değişimleri uygulanır.
- Her iki sınıf aynı renk paletini kullanır. Kamyonun kaynak yüzey dokuları korunarak renk varyasyonu yapılır.
- Kamera yüksekliği, uzaklığı, odak uzaklığı; güneş yüksekliği, yönü ve exposure değişir.
- 10 çevre grubu × 10 örnek: ilk 8 grup train (80), 1 grup val (10), 1 grup test (10).
- Aynı çevre grubu farklı split'lere dağılmaz. **Araç asset'leri bütün split'lerde ortaktır**; bu test yeni araç modellerine veya gerçek dünyaya genelleme testi değildir.
- Sabit seed, aynı kod/asset/Blender ortamında sahne parametrelerini yeniden üretir. Farklı sürüm/donanımlarda bit düzeyinde aynı render garanti edilmez.

Render/denoising ve sayısal yuvarlama nedeniyle RGB piksel düzeyinde çok küçük farklar oluşabilir. Tekrarlanabilirlik kontrolünde config, seed, kod/asset hash'leri, kamera/nesne pozları ve etiket maskelerini birlikte değerlendir.

## Kalite ve sınırlar

Gerçek 3B araç geometrisi, materyaller, fizik tabanlı ışık ve render'dan türetilen etiketlerle hazırlanmış bir **pilot sentetik veri kümesidir**. Ancak 100 örnek ve sınıf başına bir kaynak model, üretim ortamında yüksek doğruluk iddiası için yeterli değildir.

Otomobil varlığı spor coupe; kamyon varlığı altı tekerlekli Pinzgauer hafif yük aracıdır. Bu araç pilotun `truck` taksonomisine dahil edilmiştir; standart sivil ağır yük kamyonlarını temsil etmez. Çevre prosedürel ve basitleştirilmiştir. Kamuflaj/yüzey karakteri sınıfa özgü kestirme ipucu olabilir. Gündüz, kuru ve düz yol kapsamı vardır. Negatif görüntüler, gece/yağmur, farklı araç modelleri ve gerçek kamera değerlendirmesi sonraki genişleme alanlarıdır.

Doğrulama raporu etiket tutarlılığını denetler; foto-gerçekçilik sertifikası veya gerçek dünyada ML başarısı değildir.

## Mülakatta anlatım

“Config ve seed ile yol sahneleri oluşturuyorum. Her aracı alt mesh'lerinden bağımsız tek bir instance olarak tanımlıyorum. RGB ile aynı render'dan nesne kimliklerini alıp semantic ve instance maskeleri üretiyorum. Bounding box'ları görünür maskeden çıkardığım için kutu, alan ve segmentasyon aynı piksel kümesini ifade ediyor. COCO/YOLO çıktılarını otomatik kontrol ediyor, split'leri sahne grubu bazında ayırıyorum. Sınırlı asset çeşitliliğinin gerçek dünyaya genelleme kanıtı olmadığını ayrıca belirtiyorum.”

## Varlık kaynakları

Kaynaklar, yazarlar ve lisanslar [assets/README.md](assets/README.md) içinde. Kamyonun Royalty Free koşulları kaynak asset dağıtımını sınırlar; orijinal dosyaları herkese açık bir model paketi olarak yeniden dağıtma. Mülakatta üretilen görüntüler, etiketler ve kendi kodun üzerinden sunum yapabilirsin.
