# Home Assistant Nöbetçi Eczane

İstanbul Eczacı Odası'nın güncel web servisini kullanarak İstanbul ve Yalova'daki nöbetçi eczaneleri Home Assistant'a ekler.

## Ne oluşturur?

- Her aktif eczane için bir `geo_location` entity'si. Entity durumu, Home Assistant ev konumuna kuş uçuşu mesafedir.
- Entity niteliklerinde telefon (`phone` ve `phone_e164`), adres, yol tarifi notu, koordinatlar, nöbet bitişi, il ve ilçe bilgileri.
- Standart Home Assistant haritasında yeşil eczane işaretçisi.
- Cihaz sayfasındaki **Tanılayıcı** bölümünde il, ana ilçe, yarıçap ve güncelleme aralığı kontrolleri ile **Son başarılı kontrol** sensörü.
- **Nöbetçi Eczane Card**: ilk üç eczaneyi gösterir, tıklanınca tümünü mesafeye göre sıralar; arama ve Google Maps düğmeleri sunar.

Nöbet sona erdiğinde veya yarıçap/il/ilçe ayarı değiştiğinde artık sonuçlarda bulunmayan konum entity'leri hem Home Assistant state listesinden hem entity registry'den otomatik kaldırılır; yeni eczaneler otomatik eklenir. Temizlik ilk yüklemede ve her başarılı veri güncellemesinde çalışır. Varsayılan yenileme aralığı 30 dakikadır ve entegrasyon seçeneklerinden 15–360 dakika arasında değiştirilebilir.

Entegrasyon resmî harita verisini tek istekte alır, Home Assistant ev koordinatına göre seçilen yarıçap içinde yerel olarak filtreler ve mesafeye göre sıralar. Bu nedenle seçilen ilçenin sınırının hemen dışındaki daha yakın bir nöbetçi eczane de listelenir. İlçe seçimi kart gruplaması için kullanılır; sonuçlar yalnızca ilçe sınırına hapsedilmez.

## Kurulum

1. `custom_components/nobetci_eczane` klasörünü Home Assistant içindeki `/config/custom_components/` klasörüne kopyalayın.
2. Home Assistant'ı yeniden başlatın.
3. **Ayarlar → Cihazlar ve Hizmetler → Entegrasyon Ekle → Nöbetçi Eczane** yolunu açın.
4. İl, ana ilçe, arama yarıçapı ve güncelleme aralığını seçin.

Daha sonra entegrasyonun cihaz sayfasındaki **Tanılayıcı** bölümünden il, ana ilçe, yarıçap ve güncelleme aralığının tamamını değiştirebilirsiniz. Mesafe hesabının merkezi Home Assistant'taki ev konumudur.

## Haritada gösterme

Standart Home Assistant harita kartı, `nobetci_eczane` kaynağındaki tüm aktif konumları doğrudan gösterebilir:

```yaml
type: map
auto_fit: true
entities:
  - zone.home
geo_location_sources:
  - nobetci_eczane
```

Birden fazla ilçe eklediyseniz aynı kaynak altındaki eczaneler aynı haritada görünür.

## Özel kart

Entegrasyon kart dosyasını şu adreste sunar ve Lovelace kaynağını otomatik kaydeder:

```text
/nobetci_eczane/nobetci-eczane-card.js?v=0.5.5
```

Home Assistant yeniden başladıktan sonra kart seçicide **Nöbetçi Eczane Card** adıyla görünür. İsterseniz YAML ile de ekleyebilirsiniz:

```yaml
type: custom:nobetci-eczane-card
source: nobetci_eczane
district: Çekmeköy
title: Çekmeköy Nöbetçi Eczaneler
show_address: true
show_distance: true
show_directions: true
show_source: true
max_items: 3
```

`district` isteğe bağlıdır. Verildiğinde o yapılandırmaya ait yarıçap sonuçlarını gösterir; sonuçlar arasında komşu ilçe eczaneleri bulunabilir. Kaldırıldığında `nobetci_eczane` kaynağındaki tüm yapılandırmalar tek kartta listelenir. Kart entity adına bağımlı değildir; nöbet listesi değiştiğinde yeni `geo_location` entity'lerini otomatik bulur. Başlık altında son güncelleme, yarıçap ve sonuç sayısı gösterilir. İlk `max_items` kayıt görünür; başlığa veya **Tümünü göster** düğmesine basılınca listenin tamamı açılır. Bütün sonuçlar mesafeye göre sıralanır. Her eczanede telefon düğmesi ile `mdi:directions` ikonlu navigasyon control button bulunur; Android'de varsayılan `geo:` işleyicisi, Apple cihazlarda sistem harita bağlantısı ve masaüstünde web haritası açılır.

## Neden Tile yerine geo_location ve özel kart?

Tile kart sabit bir entity kimliği bekler. Nöbetçi eczaneler ise nöbet değişiminde oluşup kaybolduğu için Harita kartındaki `geo_location_sources` filtresi bu veri modeline daha uygundur. Liste, telefon ve yol tarifi işlemleri için özel kart kullanılabilir.

## 0.1.x sürümünden yükseltme

Yükseltme sırasında eski **Nöbetçi eczaneler** ve **En yakın nöbetçi eczane** özet sensörleri entity registry'den kaldırılır. Kart kaynağı entegrasyon tarafından otomatik kaydedilir ve sürüm yükseltmelerinde güncellenir. Panolardaki eski sensör tabanlı kart yapılandırmasını yukarıdaki `source` tabanlı yapılandırmayla değiştirin.

## Geliştirme ve npm build

Kartın düzenlenebilir kaynağı `src/nobetci-eczane-card.js` dosyasındadır. `custom_components/nobetci_eczane/static/` altındaki dosya build çıktısıdır; doğrudan düzenlemeyin.

```bash
npm ci
npm run build
```

Geliştirme sırasında değişiklikleri otomatik derlemek için:

```bash
npm run dev
```

Kart testleriyle birlikte temiz bir production build almak için:

```bash
npm test
```

Build işlemi esbuild kullanır, sürümü `package.json` içinden karta enjekte eder ve Home Assistant'ın sunduğu static dosyayı minify eder.

## Kaynak ve sınırlamalar

- Kaynak: [İstanbul Eczacı Odası Nöbetçi Eczane Uygulaması](https://www.istanbuleczaciodasi.org.tr/nobetci-eczane/)
- Desteklenen iller: İstanbul ve Yalova.
- Servis belgelenmiş genel amaçlı bir API değildir; resmî web arayüzünün kullandığı JSON yanıtı okunur.
- Mesafe, Home Assistant ev koordinatından eczaneye kuş uçuşu hesaplanır; yol mesafesi değildir.
- Koordinatı bulunmayan bir kayıt harita/konum entity'si olarak oluşturulamaz.
- Kaynağa yük bindirmemek için varsayılan yenileme aralığı 30, izin verilen en düşük değer 15 dakikadır.
- Yapılandırmalar aynı istemciyi ve kısa süreli önbelleği paylaşır; eşzamanlı güncellemeler tek kaynak isteğinde birleştirilir.
- İstemci kendisini Home Assistant entegrasyonu olarak tanıtır, oturumu ve doğrulama anahtarını yeniden kullanır, kaynak reddederse el sıkışmayı yalnızca bir kez yeniler. CAPTCHA veya anti-bot mekanizmalarını aşmaya çalışmaz.
