::part Kısım I | Binary Ninja'yı tanımak | Ekranın haritası, görünümler, gezinme ve not alma.

# Bu kılavuz hakkında

Bu kılavuz, Vector 35'in resmi Binary Ninja belgelerine (docs.binary.ninja, 6.x) bakarak yazıldı ama onun çevirisi değil. Resmi kılavuz her düğmeyi anlatır. Bu kılavuz ise exploit ve crackme çalışırken gerçekten kullanacağın kısımları anlatıyor, ve her şeyi `~/cracks` içindeki örnek programlar üzerinde gösteriyor.

Ekran görüntülerinin hepsi bu makinedeki Binary Ninja'dan alındı: **Binary Ninja Free 6.0.10905**, senin ayarlarınla. Kırmızı çerçeveler ve numaralar, metinde bahsedilen yerleri gösteriyor. Görüntünün altındaki numaralı liste, her çerçevenin ne olduğunu söylüyor.

Açmak için:

```cmd
binaryninja ~/cracks/e01_admin
```

Senin ayar dosyan (`~/.binaryninja/settings.json`) üç şeyi değiştirmiş:

```out
"ui.view.graph.preferred": true,
"ui.view.graph.il": "HighLevelIL",
"rendering.format.scopingStyle": "braces"
```

Bir fonksiyona girdiğinde varsayılan olarak **grafik görünümü** açılıyor, kod seviyesi **HLIL**, ve HLIL süslü parantezlerle gösteriliyor. Kılavuzdaki görüntüler bu ayarlarla alındı.

# İlk açılış

Binary Ninja'yı her açtığında önce bir karşılama penceresi gelir. Senin sürümün ücretsiz (Free) sürüm: x86, x64, ARMv7 ve ARM64 programlarını açabilir, ticari olmayan kullanım içindir. `Start`'a bas ve geç.

{{img:welcome.png|Binary Ninja Free karşılama penceresi.}}

İlk açılışta bir de **"Enable WARP Network Access?"** diye bir soru gelebilir. WARP, fonksiyonları bilinen kütüphane fonksiyonlarıyla eşleştirmek için Vector 35'in sunucusuna bağlanan bir özellik. Analiz ettiğin programla ilgili bilgiyi dışarı göndermek istemiyorsan **No** de. Bu kılavuzun hiçbir yerinde gerekmiyor, ve istersen sonradan Settings'ten açabilirsin.

Dosya açılınca Binary Ninja hemen analize başlar. Fonksiyonları bulur, assembly'ye çevirir, ara dillere (IL) yükseltir ve sonunda C'ye benzer bir çıktı üretir. Küçük programlarda bu bir saniye sürer. Büyük programlarda beklemen gerekmez: bir fonksiyona tıkladığında Binary Ninja önce onu analiz eder.

Analiz veritabanını (`.bndb`) `Ctrl+S` ile kaydedersin. Verdiğin isimler, yorumlar, tipler bu dosyada durur, program dosyası değişmez. Sekme başlığında dosya adının yanında `●` görüyorsan kaydedilmemiş değişikliğin var demektir.

# Ekranın haritası

{{img:e01_map.png|Binary Ninja'nın ana ekranı, e01_admin açıkken.}}

| | Bölge | Ne var |
|---|---|---|
| **A** | Symbols paneli | Programdaki bütün fonksiyonlar ve adresleri. `main`'e, `win`'e buradan gidersin. |
| **B** | Cross References paneli | İmlecin üstünde durduğu şeyi kim kullanıyor. İmleç her hareket ettiğinde güncellenir. |
| **C** | Ana panel | Kodun kendisi. Üstteki çubuktan düzen (`Graph`/`Linear`) ve seviye (`High Level IL`, `Disassembly`...) seçilir. |
| **D** | Sağ kenar çubuğu | Variables `(x)`, Stack (katmanlar simgesi), Strings (`99`), Find (büyüteç), History (saat), Pinned Cross References (raptiye). |
| **E** | Menü çubuğu | File, Edit, View, Analysis, Debugger... |
| **F** | Durum çubuğu | Uyarı sayısı, platform (`linux-x86_64`), imlecin adresi, dosya kilidi. |
| **G** | Sol kenar çubuğu | Symbols, Types `{T}`, Tags, Memory Map, Debugger ve diğer paneller. |

Kenar çubuğundaki bir simgeye tıklayınca o panel açılır, tekrar tıklayınca kapanır. Aynı bölgede bir anda tek panel görünür. `Shift` ile tıklarsan ikisi birden açık kalır. Simgeleri sürükleyip başka kenara taşıyabilirsin. Sağ tıklayıp "Floating" dersen panel ayrı bir pencereye çıkar.

Bir adrese **orta tuşla** (tekerlek) tıklarsan o adres ana panelin yanında yeni bir bölmede açılır. `main` ile `vuln`'ü yan yana görmek için kullanışlı.

# Görünümler

Aynı kodu iki ayrı eksende değiştirebilirsin. İkisini karıştırma.

**Düzen:** kod alt alta bir liste mi (**Linear**), kutular ve oklar mı (**Graph**)? `Space` ile geçersin.

**Seviye:** Disassembly, LLIL, MLIL, HLIL ya da Pseudo C. Ana panelin üstündeki ikinci açılır menüden seçersin. `i` sırayla dolaşır. `Tab` (ya da `F5`) bulunduğun yerde HLIL ile Disassembly arasında gidip gelir.

| Seviye | Ne |
|---|---|
| Disassembly | `objdump`'taki gerçek komutlar |
| LLIL | Her komutun ne yaptığı açıkça yazılmış hali. Yazmaçlar duruyor. |
| MLIL | Yazmaçlar ve yığın gitmiş, yerine değişkenler gelmiş |
| HLIL | `if`, `while`, fonksiyon çağrıları. C'ye en yakın hal. |
| Pseudo C | HLIL'in C sözdizimine biraz daha benzetilmiş hali |

## Graph + HLIL: senin varsayılanın

{{img:e01_hlil_graph.png|e01_admin'in main fonksiyonu, Graph düzeninde HLIL.}}

1. Symbols panelinde `main` seçili. Adres sütununda `0x401156` (sütun dar olduğu için sonu kesik görünüyor).
2. Düzen `Graph`, seviye `High Level IL`. İkisini buradan değiştirebilirsin.
3. `read(0, &var_28, 0x40)`: girdi `var_28`'e okunuyor, boyutu `0x40` = 64.
4. `if (var_18 != 0x41424344)`: programın kararı. Bu kutudan iki ok çıkıyor. **Yeşil** ok koşul doğruysa, **kırmızı** ok yanlışsa gidilen yol. Yeşil ok "yetkin yok"a, kırmızı ok "hos geldin admin!"e gidiyor.
5. Durum çubuğunda imlecin adresi: `0x401156`, yani `main`'in başı.

Grafik görünümünde bir koşulun hangi kutuya gittiğini görmek, bir crackme'de "doğru şifre" yolunu bulmanın en hızlı yolu. `w` grafiği ekrana sığdırır, `Ctrl` + tekerlek yakınlaştırır.

## Disassembly: adresler ve offset'ler

`Tab`'a basınca aynı yer assembly olarak açılır:

{{img:e01_disasm.png|Aynı main, Disassembly seviyesinde.}}

1. Seviye artık `Disassembly`.
2. `lea rax, [rbp-0x20 {var_28}]`: buffer'ın adresi hesaplanıyor. Binary Ninja, `[rbp-0x20]`'nin yanına süslü parantez içinde değişkenin adını yazmış. **Assembly'deki `[rbp-0x20]` ile HLIL'deki `var_28` aynı şey.** Bu bağlantıyı Bölüm 8'de kullanacağız.
3. `mov eax, dword [rbp-0x10 {var_18}]`: karşılaştırılan değişken, `[rbp-0x10]`.
4. `cmp eax, 0x41424344` ve ardından `jne`: kararın assembly hali.

Adres, offset ya da komut baytı lazım olduğunda Disassembly'ye geç. Bir gdb kesme noktası için adresi buradan alırsın: `read` çağrısı `0x4011a8`'de.

## Linear: her şey alt alta

`Space` grafiği listeye çevirir:

{{img:e01_linear.png|Linear düzende HLIL. Fonksiyonlar ve bölümler alt alta.}}

1. Düzen `Linear`.
2. `main`'in gövdesi. Her satırın solunda adresi var.
3. `if` ve `else` bu düzende iç içe girintili gösteriliyor. Grafikte ise ayrı kutulardaydı.

Linear düzende fonksiyonların arasındaki veri, bölüm başlıkları (`.text`, `.fini`...) ve tanımlanmamış baytlar da görünür. Global değişkenlere, metinlere ya da GOT tablosuna bakmak istediğinde Linear'a geç. Grafikte bir veriye çift tıklarsan Binary Ninja seni kendisi Linear'a götürür.

# Gezinme

Temel kural: **gitmek istediğin şeye çift tıkla.** Fonksiyon adı, adres, okun ucu, değişken, hepsi çalışır.

| Tuş | İş |
|---|---|
| `Esc` | Geri |
| `Ctrl+[` / `Ctrl+]` | Geri / ileri |
| `g` | Adrese git. `main`, `0x4011a8`, `vuln+52` gibi ifadeler kabul eder. Sayılar varsayılan olarak onaltılık. |
| `Ctrl+P` | Komut paleti: Binary Ninja'nın yapabildiği her işi adıyla ara |
| `Ctrl+Shift+P` | Her şeyde ara: komutlar, fonksiyonlar, tipler, metinler |

## Komut paletini hesap makinesi olarak kullanmak

`Ctrl+Shift+P` ile açılan paletin başına `=` yazarsan, yazdığın ifadeyi hesaplar:

{{img:palette2.png|Ctrl+Shift+P, =0x28-0x18 ifadesini hesaplıyor.}}

1. Yazılan ifade: `=0x28-0x18`. Sağda mod olarak `Expression` yazıyor.
2. Sonuç: `0x10`. Bölüm 9'da göreceğin `name` ile `admin` arasındaki mesafe.

Dikkat: düz `Ctrl+P` sadece komut arar (başına `>` koyar) ve `=` ifadesini hesaplamaz. Bunu bu makinede denedik. Hesap için `Ctrl+Shift+P` kullan.

## Çapraz referanslar

Bir şeyin üstüne gelip `x`'e basınca, onu kullanan her yer listelenir. Binary Ninja'nın sana en çok vakit kazandıracak özelliği bu.

{{img:xref_read.png|Symbols'te read seçiliyken x'e basıldı.}}

1. Symbols panelinde `read` seçili.
2. Altta **Pinned Cross References** paneli açıldı. İlk satır: `main`'in `0x4011a8` adresinde `read(0, &name, 0x40)` çağrısı. Programda girdi okunan tek yer burası.
3. İkinci satır `0x404010`: `read`'in GOT kutusu. Bu bir **veri** referansı. Program `read`'i bu kutudaki adres üzerinden çağırıyor (exploit kitabı Bölüm 14).

`x` ile açılan liste sabittir (pinned), başka bir yere tıklasan da kaybolmaz. Soldaki Cross References paneli ise imleç nereye giderse ona göre değişir. Bir sonraki referansa `Alt+x`, öncekine `Alt+Shift+x` ile geçersin. Liste uzunsa üstteki `Filter`'a tıklayıp kod/veri/değişken diye süzebilirsin.

Kullanım örnekleri:

- **`read`, `gets`, `strcpy` üstünde `x`**: girdi okunan ve kopyalanan her yer.
- **Bir metnin üstünde `x`**: o metni yazdıran kod. Crackme'de "Wrong password"dan geriye gitmenin yolu.
- **Bir değişkenin üstünde `x`**: o değişkenin okunduğu ve yazıldığı her satır.

## Strings paneli

{{img:strings2.png|Strings paneli.}}

1. Sağ kenar çubuğundaki `99` simgesi Strings panelini açar.
2. Arama kutusu. Yazdıkça süzer. Sağdaki `.*` düğmesi düzenli ifadeyi açar, `Aa` büyük/küçük harf duyarlılığını.
3. Her metnin adresi, türü, uzunluğu ve kaç yerden kullanıldığı (`Refs`). Bir metne çift tıklayınca adresine gidersin, orada `x` ile onu kullanan koda geçersin.

# Not almak: isim, tip, yorum

Bir programı anlamak, onu kendi kelimelerinle yeniden yazmak demek. Binary Ninja'da üç tuşla:

| Tuş | İş |
|---|---|
| `n` | İsim ver: fonksiyon, değişken, adres |
| `y` | Tip ver: `int`, `char[16]`, `struct user*` |
| `;` | Yorum ekle |

## İsim vermek

Bir değişkenin üstüne tıkla ve `n`'ye bas:

{{img:dlg_rename.png|var_28'in üstünde n'ye basıldı.}}

1. Seçili değişken: `var_28`.
2. İsim penceresi: "Enter variable name". Yeni ismi yaz, `Enter`.

`var_28` → `name`, `var_18` → `admin` yaptığımızda HLIL'in her yerinde isimler değişti: `read(0, &name, 0x40)`, `if (admin != 0x41424344)`. Disassembly'deki `[rbp-0x20 {var_28}]` de `{name}` oldu.

## Tip vermek

Aynı değişkenin üstünde `y`:

{{img:dlg_type.png|y ile tip penceresi. Binary Ninja tipi void olarak tahmin etmiş.}}

1. "Type for variable name" penceresi. Binary Ninja bu değişkenin tipini `void` sanmış. Buraya `char name[16]` yazdık.

Sonuç bir sonraki bölümde, Stack panelinin görüntüsünde.

Bir alışkanlık önerisi: **anladığın her şeye hemen isim ver.** `sub_401156` yerine `check_password`, `var_18` yerine `admin`. Yarım saat sonra koda döndüğünde nerede kaldığını hatırlamanın tek güvenilir yolu bu.

Önemli bir yeri sonra bulmak için ona etiket koy (sağ tık → Tag). Yaptığın her değişiklik **History** panelinde (sağ kenarda saat simgesi) durur. Oradan herhangi bir noktaya geri dönebilirsin. `Ctrl+Z` de çalışır.

# Veri ve tipler

Linear görünümde bir adresin üstüne gelip şu tuşlarla ne olduğunu söylersin:

| Tuş | Burayı ne yapar |
|---|---|
| `1` `2` `4` `8` | O kadar baytlık bir tamsayı |
| `d` | Tamsayı boyutları arasında sırayla geçer |
| `a` | İlk null bayta kadar bir metin |
| `o` | Bir işaretçi |
| `*` | Dizi |
| `-` / `0` | İşaretli/işaretsiz, onaltılık/onluk |
| `r` | Tek bir ASCII karakter |
| `s` | Struct oluşturmaya çalışır |
| `u` | Tanımı kaldırır |
| `p` | Burada bir fonksiyon başlat |

`p` önemli: Binary Ninja bazen bir fonksiyonu kaçırır, örneğin sadece bir işaretçi tablosundan çağrılan bir fonksiyonu. Kodun başladığı yere gidip `p`'ye basarsın.

Bir struct tanımlamak için `t` ile tip görünümüne geç, sağ tık ile yeni tip oluştur ve C sözdizimiyle yaz:

```c
struct user {
    char name[16];
    uint32_t admin;
};
```

Sonra değişkene dönüp `y` ile tipini `struct user` yaparsın. `*(rax + 0x10)` gibi ifadeler `user->admin` olur.
