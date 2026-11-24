> **Kısım II · Temeller.** Sayılar, bellek, yazmaçlar, yığın ve araçlar. Exploit'e geçmeden önce bunları kendi ekranında görmüş olman gerekiyor.


# Bölüm 02: Sayılar ve baytlar

## Bu bölümde

gdb'de durduğun her an ekran `0x00007ffff7de3bfc`, `0x41414141`, `0x28` gibi sayılarla dolu. Bu sayılar sana bir şey anlatmıyorsa, ekrana bakmak bir duvara bakmak gibidir. Bu bölümde o duvarı okunabilir hale getireceğiz: bir sayının kaç bayt olduğunu, belleğe hangi sırayla yazıldığını ve bir programa bayt bayt nasıl gönderileceğini öğreneceksin. Kitabın geri kalanında bunları bildiğini varsayacağız.

**Ön koşullar:** Bölüm 0'daki laboratuvar kurulumu. Matematik olarak dört işlem yeterli.

**Bu bölümün sonunda:**

- Bir hex sayının kaç bayt olduğunu basamaklarını sayarak söyleyebileceksin.
- Bir sayının bellekte hangi bayt sırasıyla durduğunu kâğıt üstünde yazabileceksin.
- gdb'nin `x` komutuyla aynı belleği bayt, 4 bayt ve 8 bayt olarak okuyup üç çıktıyı birbiriyle ilişkilendirebileceksin.
- Klavyede olmayan baytları içeren bir girdiyi üç farklı yolla oluşturup `xxd` ile doğrulayabileceksin.

## Sezgi: kutular ve etiketler

Belleği, tek sıra halinde dizilmiş, her biri numaralı milyarlarca küçük kutu gibi düşün. Her kutuya 0 ile 255 arasında tek bir sayı sığar. Bu sayıya **bayt**, kutunun numarasına **adres** diyoruz.

Daha büyük bir sayı, örneğin 4 milyar gibi bir sayı saklamak istediğinde tek kutu yetmez. Sayıyı parçalara bölüp yan yana dört kutuya koyarsın. Burada bir soru ortaya çıkıyor: sayının hangi parçası soldaki kutuya, hangisi sağdakine gidecek? Bölümün yarısı bu sorunun cevabı.

Benzetmenin bozulduğu yer şu: gerçek bellekte kutular "boş" olmaz. Her kutuda mutlaka bir değer vardır, sen yazmadıysan daha önce başka biri yazmıştır. gdb'de "boş" sandığın yerlerde tuhaf sayılar görmenin sebebi bu.

## Onaltılık sistem

Günlük hayatta 10 rakam kullanırız: 0'dan 9'a. Onaltılıkta 16 rakam vardır: `0 1 2 3 4 5 6 7 8 9 a b c d e f`. `a` 10, `f` 15 demek. Bir sayının onaltılık yazıldığını göstermek için başına `0x` koyarız.

Neden onaltılık? Çünkü bir onaltılık basamak tam olarak 4 bite karşılık gelir. İki basamak 8 bit, yani tam bir bayttır. Onluk sistemde böyle bir eşleşme yoktur: 255 sayısı bir bayta sığar ama 3 basamaklıdır, 256 ise sığmaz ama yine 3 basamaklıdır. Onaltılıkta bir baytın en büyük değeri `0xff`'dir ve her zaman 2 basamaktır. Kısacası onaltılık, belleğin kendi diline en yakın gösterim.

```text
hex      0x41          0x4142          0x41424344          0x4142434445464748
basamak  2             4               8                   16
bayt     1 (byte)      2 (word)        4 (dword)           8 (qword)
```

Buradan çıkan kural kitabın en çok kullanılan kuralı: **basamak sayısının yarısı, bayt sayısıdır.**

Python'u hesap makinesi olarak kullan. Terminalde `python3` yazıp etkileşimli kullanabilir ya da tek satırlık komutlar verebilirsin:

```bash
python3 -c "print(hex(0x41), chr(0x41), ord('A'), hex(ord('a')))"
```

```text
0x41 A 65 0x61
```

- `hex(...)` bir sayıyı onaltılık yazar.
- `chr(0x41)`, `0x41` değerinin harf karşılığını verir: `A`.
- `ord('A')` bunun tersi: `A`'nın sayı değeri 65, yani `0x41`.

Bu eşleşmeyi ezberle: **`A` = `0x41`**. Exploit yazanlar dolgu için neredeyse her zaman `A` kullanır, çünkü ekranda `0x4141414141414141` gördüğün an "burası benim yazdığım yer" diye tanırsın.

Onluk ile onaltılık arasında gidip gelmen gerekecek. İki yönü de Python yapar:

```bash
python3 -c "print(0x28, hex(40), 0x20 + 8, hex(0x80 + 8))"
```

```text
40 0x28 40 0x88
```

Bu dört sayı, kitapta tekrar tekrar karşına çıkacak mesafelerden. `0x20 + 8` bir buffer'dan dönüş adresine olan uzaklık, `0x88` başka bir programdaki aynı uzaklık. Şimdilik sadece Python'un iki gösterim arasında nasıl çevirdiğine dikkat et.

## Boyutların isimleri

| Boyut | İsim | hex basamak | gdb harfi | C'deki karşılığı | Binary Ninja'da |
|---|---|---|---|---|---|
| 1 bayt | byte | 2 | `b` | `char` | `char`, `uint8_t` |
| 2 bayt | word | 4 | `h` | `short` | `int16_t` |
| 4 bayt | dword | 8 | `w` | `int`, `unsigned int` | `int32_t` |
| 8 bayt | qword | 16 | `g` | `long`, her türlü işaretçi | `int64_t`, `void*` |

İsimlerin tarihi bir kalıntısı var: Intel'in eski 16 bitlik işlemcilerinde "word" 2 bayttı, isim de öyle kaldı. "dword" (double word) 4, "qword" (quad word) 8 bayt. 64 bitlik bir işlemcide çalışırken bu isimlerin mantıksız görünmesi normal.

Assembly'de bellekle çalışan her komut boyutu da yazar:

```nasm
mov    DWORD PTR [rbp-0x10],0x0     ; rbp-0x10 adresine 4 baytlık 0 yaz
mov    BYTE PTR [rbp+rax-0x50],0x0  ; tek bir bayta 0 yaz
mov    rax,QWORD PTR [rbp-0x8]      ; rbp-0x8 adresindeki 8 baytı rax'e oku
```

`DWORD PTR` gördüğünde aklına "burada 4 baytlık bir şey var, büyük ihtimalle bir `int`" gelsin. Bu küçük alışkanlık, bir C değişkeninin assembly'deki karşılığını bulmanın en hızlı yolu.

## Baştaki sıfırlar

`0x401166` ile `0x0000000000401166` **aynı sayıdır.** Baştaki sıfırlar değeri değiştirmez, sadece sayının durduğu kutunun ne kadar büyük olduğunu gösterir. gdb'nin `p/x` komutu baştaki sıfırları atar, `x/gx` ise 8 baytın hepsini gösterir. Bir değeri iki komutla karşılaştırırken bu farkı unutursan, aynı sayıya bakıp farklı sanabilirsin.

## Little-endian: bu bölümün asıl konusu

4 baytlık `0x41424344` sayısını belleğe yazmamız gerekiyor. Dört kutu var: `adres+0`, `adres+1`, `adres+2`, `adres+3`. Sayının hangi baytı hangi kutuya gider?

İki seçenek var ve ikisi de dünyada kullanılıyor:

- **Big-endian:** sayının büyük ucu önce. Kâğıda yazdığımız gibi: `41 42 43 44`. Ağ protokolleri ve bazı eski işlemciler böyle yapar.
- **Little-endian:** sayının küçük ucu önce. `44 43 42 41`. **x86 böyle yapar.** ARM işlemciler de pratikte hep böyle çalışır.

```text
sayı:     0x 41 42 43 44
             ── ── ── ──
             │  │  │  └── en küçük bayt (sayının sağ ucu)
             │  │  └───── 
             │  └────────
             └─────────── en büyük bayt (sayının sol ucu)

bellek:   adres+0  adres+1  adres+2  adres+3
          ┌───────┬────────┬────────┬────────┐
          │  44   │   43   │   42   │   41   │
          └───────┴────────┴────────┴────────┘
             D        C        B        A
```

Bir tarih benzetmesi işe yarayabilir. Türkiye'de tarihi `24.11.2026` diye yazarız: en küçük birim (gün) önce, en büyüğü (yıl) sonra. Little-endian da sayıları böyle yazar. Benzetme şurada bozuluyor: tarihte parçaların içindeki rakamları ters çevirmeyiz, little-endian ise bayt sırasını çevirir ama her baytın kendi içindeki iki basamağı aynı kalır. `0x44` bellekte yine `44`'tür, `44`'ün tersi olan `0x44` değil.

Bunun pratikteki anlamı: bir programa `0x41424344` sayısını girdi olarak vermek istersen, klavyeden `ABCD` değil **`DCBA`** yazarsın. Bölüm 7'deki ilk exploit tam olarak bu.

Python'da `struct.pack` çevirmeyi senin yerine yapar. `<` işareti "little-endian", `I` "4 baytlık işaretsiz sayı", `Q` "8 baytlık işaretsiz sayı" demek:

```bash
python3 -c 'import struct; print(struct.pack("<I", 0x41424344))'
```

```text
b'DCBA'
```

pwntools'ta aynı işin kısayolları var: `p32` 4 bayt, `p64` 8 bayt paketler. Tersini, yani baytlardan sayı çıkarmayı da `u32` ve `u64` yapar:

```python
from pwn import p32, p64, u64
print(p32(0x41424344), p64(0x401166))
print(hex(u64(b"\x66\x11\x40\x00\x00\x00\x00\x00")))
print(b"A"*4 + p32(0xdeadbeef))
```

```text
b'DCBA' b'f\x11@\x00\x00\x00\x00\x00'
0x401166
b'AAAA\xef\xbe\xad\xde'
```

İlk satırın ikinci yarısı yeni başlayanların çoğunu şaşırtır. `p64(0x401166)` sekiz bayt üretti: `66 11 40 00 00 00 00 00`. Ama Python bazı baytları harf olarak gösteriyor: `0x66` bir harfe karşılık geldiği için `f`, `0x40` için `@`. Yani `b'f\x11@\x00...'` gösterimi aslında `66 11 40 00 ...` demek. Python bir baytı yazdırılabilir bir harfe denk gelirse harf olarak, gelmezse `\x..` olarak gösterir. Şüpheye düştüğünde `.hex()` ile bak:

```bash
python3 -c 'from pwn import p64; print(p64(0x401166).hex(" "))'
```

```text
66 11 40 00 00 00 00 00
```

## Uygulama: aynı belleğe üç farklı gözle bakmak

Şimdi little-endian'ı canlı bir programda göreceğiz. Bölüm 7'deki `e01_admin` programını kullanacağız. Programın ne yaptığını şimdilik bilmen gerekmiyor, sadece bir girdiyi belleğe nasıl koyduğuna bakacağız.

**Adım 1: Girdiyi bir dosyaya yaz.** 20 tane `A`:

```bash
printf 'AAAAAAAAAAAAAAAAAAAA' > /tmp/a20
xxd /tmp/a20
```

`xxd` dosyadaki baytları onaltılık gösterir. 20 tane `41` görmelisin.

**Adım 2: Programı gdb'de, girdiyi okuduktan hemen sonra durdur.** `0x4011ad` adresi, programın `read` çağrısından hemen sonraki komut. Bu adresi nasıl bulduğumuzu Bölüm 7'de göreceksin.

```bash
pwndbg -q ~/cracks/e01_admin
b *0x4011ad
r < /tmp/a20
```

`r < /tmp/a20`, programı başlatır ve klavye yerine dosyayı girdi olarak verir.

**Adım 3: Aynı belleğe üç farklı boyutta bak.** Girdinin yazıldığı yer `rbp-0x20` adresi (bunu da Bölüm 7'de göreceğiz):

```bash
x/20bx $rbp-0x20
x/4gx $rbp-0x20
x/wx $rbp-0x10
```

```text
0x7fffffffd440: 0x41 0x41 0x41 0x41 0x41 0x41 0x41 0x41
0x7fffffffd448: 0x41 0x41 0x41 0x41 0x41 0x41 0x41 0x41
0x7fffffffd450: 0x41 0x41 0x41 0x41

0x7fffffffd440: 0x4141414141414141  0x4141414141414141
0x7fffffffd450: 0x0000000041414141  0x00007ffff7ffdda0

0x7fffffffd450: 0x41414141
```

Komutun biçimi: `x/` + **kaç tane** + **boyut** (`b`, `w`, `g`) + **gösterim** (`x` = onaltılık).

**Adım 4: Çıktıyı oku.**

`x/20bx` baytları tek tek gösteriyor. Tam 20 tane `0x41` var. Her satırın başındaki adres, o satırdaki ilk baytın adresi: ilk satır `...d440`, ikinci satır 8 bayt sonra `...d448`.

`x/4gx` aynı belleği 8'er baytlık sayılar olarak okuyor. Üçüncü sayıya dikkatle bak: `0x0000000041414141`. Bu adreste bellekte sırasıyla `41 41 41 41 00 00 00 00` var. Little-endian kuralıyla, küçük adresteki `41`'ler sayının **sağ** ucuna, sıfırlar sol ucuna düşüyor.

`x/wx` sadece 4 bayt okuyor ve `0x41414141` gösteriyor. Bu dört bayt, girdinin 17. ile 20. baytları. Bölüm 7'de bu dört baytın programın bir değişkenine denk geldiğini göreceksin.

`x/4gx` çıktısındaki son değer `0x00007ffff7ffdda0` senin yazdığın bir şey değil. `x` komutu "şu adresten başlayarak N tane şunu göster" der. Oraya kimin ne yazdığına bakmaz. Sezgi bölümündeki uyarıyı hatırla: bellekte boş kutu yoktur.

## Klavyede olmayan baytları göndermek

`A` gibi harfler kolay. Ama `0x00`, `0xef` ya da `0x0a` gibi baytları nasıl göndereceksin? Üç yol var ve üçü de aynı sonucu verir:

```bash
printf 'AAAA\xef\xbe\xad\xde' | xxd
python3 -c 'import sys; sys.stdout.buffer.write(b"AAAA\xef\xbe\xad\xde")' | xxd
python3 -c 'import sys; from pwn import p32; sys.stdout.buffer.write(b"AAAA"+p32(0xdeadbeef))' | xxd
```

```text
00000000: 4141 4141 efbe adde                      AAAA....
00000000: 4141 4141 efbe adde                      AAAA....
00000000: 4141 4141 efbe adde                      AAAA....
```

`xxd` çıktısının üç sütunu var: soldaki dosya içindeki konum, ortadaki baytlar (ikişerli gruplar halinde), sağdaki ise yazdırılabilir olanların harf karşılığı (olmayanlar `.` olarak). Bir payload'ı programa göndermeden önce **her zaman** `xxd` ile bak. Bu alışkanlık, ileride saatlerce sürecek hata aramalarını dakikalara indirir.

Üç yöntem arasındaki fark kullanım kolaylığı. `printf` kısa ve elle yazılabilen şeyler için iyi. Python, hesaplanması gereken uzun payload'lar için. Üçüncü satırdaki gibi `p32`/`p64` kullanmak ise ileride sayıların hepsinin değişken olduğu exploit'lerde tek makul yol.

## Savunma tarafı

Bu bölümde bir saldırı tekniği yok, ama exploit'lerin neredeyse hepsi burada öğrendiğin bir gerçeğe dayanıyor: program bir sayıyı bellekte bayt bayt tutar ve kimin yazdığını hatırlamaz. Yazılım tarafında bunun tek gerçek savunması, programın bir buffer'a o buffer'ın boyutundan fazla bayt yazmasına hiç izin vermemek. Bunu nasıl yapacağını Bölüm 7'nin savunma kısmında göreceksin. Diğer bütün korumalar (canary, NX, ASLR) yazma işlemi olduktan **sonra** zararı sınırlamaya çalışır.

> [!WARNING]
> **Sık yapılan hatalar**
>
> - **Python'da `print()` ile bayt göndermek.** `print` baytları metne çevirir, sonuna Enter (`\n`) ekler ve `0x80`'den büyük baytları başka baytlara dönüştürür. Bayt göndermek için her zaman `sys.stdout.buffer.write(...)` kullan.
> - **Little-endian'ı unutmak.** Adres `0x401166` ise payload'da `\x40\x11\x66` değil `\x66\x11\x40\x00\x00\x00\x00\x00` olmalı. `p64` kullanırsan bu hatayı yapamazsın.
> - **4 ile 8 baytı karıştırmak.** Bir `int` değişkeni 4 bayttır. Onu `p64` ile ezersen 4 bayt fazladan yazarsın ve yanındaki değişkeni de bozarsın.
> - **`echo` kullanmak.** `echo` da sonuna Enter ekler. `echo -n` bazı kabuklarda çalışır, bazılarında `-n`'yi metin olarak yazar. `printf` her yerde aynı davranır.

## Kontrol soruları

1. `0x7fffffffd440` kaç baytlık bir sayı? Bir adres olarak bellekte kaç bayt yer kaplar?
2. `0x5ca1ab1e` sayısı belleğe hangi bayt sırasıyla yazılır?
3. `p/x` ile `0x401166`, `x/gx` ile `0x0000000000401166` görüyorsun. Aynı değer mi?
4. Bellekte `ef be ad de 00 00 00 00` var. `x/gx` ile okursan ne görürsün?
5. `b'f\x11@\x00'` kaç bayt ve onaltılık olarak nedir?
6. Bir programa `0x0a` baytı içeren bir payload göndermek neden bazen sorun olur?

## Alıştırmalar

1. **Gözlemle.** Uygulamadaki gdb oturumunu tekrar aç. `x/20bx` yerine `x/6wx $rbp-0x20` çalıştır. İlk beş değer neden `0x41414141`? Altıncı değer neden farklı?
2. **Tahmin et, sonra dene.** `/tmp/a20` dosyasını `printf 'ABCDEFGH' > /tmp/a8` ile değiştir. `x/gx $rbp-0x20` komutunun ne göstereceğini önce kâğıda yaz, sonra dene.
3. **Kendin yap.** `0x00007ffff7de3bfc` adresini `p64` ile paketleyen ve baytlarını `.hex(" ")` ile yazdıran bir Python satırı yaz. İlk bayt hangisi, son iki bayt neden `00`?

## Özet

- Bir hex basamağı 4 bit, iki basamak 1 bayt. Basamak sayısının yarısı bayt sayısıdır.
- byte/word/dword/qword = 1/2/4/8 bayt. gdb'de `b`/`h`/`w`/`g`.
- x86 little-endian'dır: sayının en küçük baytı en küçük adrese yazılır.
- `p32`/`p64` sayıları doğru sırada paketler. `u32`/`u64` tersini yapar.
- Bayt göndermek için `printf` ya da `sys.stdout.buffer.write`, kontrol etmek için `xxd`.
- Bellekte boş kutu yoktur. Senin yazmadığın her yerde, daha önce yazılmış bir değer vardır.

Bir sonraki bölümde bu baytların durduğu yerin bir haritasını çıkaracağız: programın kodu, kütüphaneler ve yığın bellekte nerede duruyor?

---
**Kontrol sorularının cevapları**

1. 12 hex basamağı, yani 6 baytlık bir değer. Ama bir adres olarak her zaman 8 bayt yer kaplar, üstteki 2 bayt sıfırdır: `0x00007fffffffd440`.
2. `1e ab a1 5c`.
3. Evet, aynı değer. `p/x` baştaki sıfırları atıyor.
4. `0x00000000deadbeef`.
5. 4 bayt: `66 11 40 00`.
6. `fgets` ve `gets` gibi satır okuyan fonksiyonlar `0x0a`'yı satır sonu kabul edip okumayı orada keser. Payload'ın geri kalanı programa ulaşmaz.

**Bu bölümde geçen yeni terimler:** bayt, adres, onaltılık, byte/word/dword/qword, little-endian, big-endian, ASCII, null bayt.


# Bölüm 03: Bellek haritası

## Bu bölümde

Çalışan bir program belleği tek bir parça olarak kullanmaz. Kod bir yerde, global değişkenler başka bir yerde, kütüphaneler ve yığın bambaşka yerlerde durur. Bu bölümde bu yerleşimin haritasını çıkaracağız. Haritayı bir kere görünce, gdb'de karşına çıkan herhangi bir adrese bakıp onun kod mu, kütüphane mi, yığın mı olduğunu söyleyebileceksin. Bu yetenek, ileride sızan bir adresin işine yarayıp yaramayacağını anlamanın ilk adımı.

**Ön koşullar:** Bölüm 2 (hex ve adresler).

**Bu bölümün sonunda:**

- pwndbg'de `vmmap` çıktısını okuyup her satırın hangi dosyaya ait olduğunu ve izinlerini söyleyebileceksin.
- Bir adresin hangi bölgede olduğunu ilk birkaç basamağına bakarak tahmin edebileceksin.
- ASLR'nin hangi bölgeleri kaydırdığını iki çalıştırmayı karşılaştırarak gösterebileceksin.
- `r-x`, `rw-` ve `rwx` izinlerinin exploit açısından ne anlama geldiğini açıklayabileceksin.

## Sezgi: bir şehir planı

Belleği bir şehir gibi düşün. Programın kodu şehrin merkezinde, adresi hiç değişmeyen eski bir mahallede. libc gibi kütüphaneler şehrin dışında, her gün başka bir yere taşınan bir sanayi sitesinde. Yığın da şehrin en ucunda, aşağı doğru büyüyen bir mahalle. Bir adresi gördüğünde onun hangi mahalleye ait olduğunu sokak isminden anlarsın: `0x40...` ile başlıyorsa merkez, `0x7f...` ile başlıyorsa dışarısı.

Benzetme şurada bozuluyor: gerçek şehirde mahalleler bitişiktir. Bellekte ise mahalleler arasında devasa boşluklar vardır. O boşluklardaki bir adrese erişmeye çalışmak, programın anında çökmesine yol açar.

## Haritayı görmek

pwndbg'de `vmmap` komutu haritayı gösterir. `e02_win`'i başlatıp `vuln` fonksiyonunun başında durduralım:

```bash
pwndbg -q ~/cracks/e02_win
b *vuln
r
vmmap
```

```text
             Start                End Perm     Size  Offset File
          0x400000           0x401000 r--p     1000       0 e02_win
          0x401000           0x402000 r-xp     1000    1000 e02_win
          0x402000           0x403000 r--p     1000    2000 e02_win
          0x403000           0x404000 r--p     1000    2000 e02_win
          0x404000           0x405000 rw-p     1000    3000 e02_win
    0x7ffff7db9000     0x7ffff7de1000 r--p    28000       0 /usr/lib/libc.so.6
    0x7ffff7de1000     0x7ffff7f3a000 r-xp   159000   28000 /usr/lib/libc.so.6
    0x7ffff7f3a000     0x7ffff7f90000 r--p    56000  181000 /usr/lib/libc.so.6
    0x7ffff7f90000     0x7ffff7f94000 r--p     4000  1d6000 /usr/lib/libc.so.6
    0x7ffff7f94000     0x7ffff7f96000 rw-p     2000  1da000 /usr/lib/libc.so.6
    0x7ffff7fc6000     0x7ffff7fc8000 r-xp     2000       0 [vdso]
    0x7ffff7fc8000     0x7ffff7fc9000 r--p     1000       0 /usr/lib/ld-linux-x86-64.so.2
    0x7ffff7fc9000     0x7ffff7ff0000 r-xp    27000    1000 /usr/lib/ld-linux-x86-64.so.2
    ...
    0x7ffffffdd000     0x7ffffffff000 rwxp    22000       0 [stack]
```

Çıktıdaki birkaç satırı kısalttık (`...`). Her satır bir bölgeyi anlatıyor:

| Sütun | Anlamı |
|---|---|
| **Start / End** | Bölgenin başladığı ve bittiği adres. `End` bölgeye dahil değil. |
| **Perm** | İzinler: `r` okunabilir, `w` yazılabilir, `x` çalıştırılabilir. `p` "bu sürece özel kopya" demek, exploit açısından önemsiz. |
| **Size** | Bölgenin boyutu, onaltılık. `1000` = 4096 bayt = bir sayfa. |
| **Offset** | Bölgenin, kaynak dosyanın içinde kaçıncı bayttan başladığı. |
| **File** | Bölgenin hangi dosyadan geldiği. Köşeli parantezliler (`[stack]`, `[vdso]`) dosyadan gelmez, çekirdek oluşturur. |

Bir programın neden tek dosyadan beş ayrı bölge oluşturduğunu merak edebilirsin. Sebep izinler: kodun çalıştırılabilir ama yazılamaz, sabit metinlerin sadece okunabilir, global değişkenlerin ise yazılabilir olması gerekir. İzinler sayfa sayfa verildiği için dosya izin türlerine göre bölünür.

## Mahalleler

| Adres böyle başlıyorsa | Nerede | Ne var |
|---|---|---|
| `0x40....` | Programın kendisi (PIE kapalıyken) | `main`, `win`, senin fonksiyonların, global değişkenler |
| `0x5555 5555 4...` (gdb) / `0x55..`–`0x65..` | Programın kendisi (PIE açıkken) | Aynısı (Bölüm 18) |
| `0x7ffff7....` (gdb) / `0x7...` | Paylaşılan kütüphaneler | libc (`puts`, `system`), dinamik bağlayıcı `ld.so` |
| `0x7ffffff.....` (gdb) / `0x7ffc..`–`0x7fff..` | Yığın | Yerel değişkenler, dönüş adresleri, ortam değişkenleri |

Tablodaki "gdb" sütunu ASLR kapalıyken gördüğün değerler. ASLR açıkken kütüphane ve yığın adresleri her çalıştırmada değişir, ama genelde yine `0x7` ile başlar.

Kitabın başındaki gdb oturumunu hatırlarsan, iki adres görmüştük:

- `0x401116`, `main`'in adresiydi. **Program** mahallesi.
- `0x00007ffff7de3bfc` ise `__libc_start_call_main+124` idi. **libc** mahallesi. Bu tabloya göre ikisini hiçbir araca sormadan ayırt edebilirsin.

## İzinlerin exploit için anlamı

İzinler, bir saldırganın belleğin neresinde ne yapabileceğini belirler:

- **Programın kodu `r-xp`**: okunur ve çalıştırılır ama **yazılamaz**. Kodu değiştiremezsin. Ama içindeki parçaları kullanabilirsin (Bölüm 12).
- **`0x404000` bölgesi `rw-p`**: yazılabilir ama çalıştırılamaz. Global değişkenler burada. Bölüm 14'te göreceğin GOT tablosu da burada ve bu yüzden bazı saldırıların hedefi.
- **Yığın bu programda `rwxp`**: hem yazılabilir hem çalıştırılabilir. Normal bir programda böyle bir bölge olmamalı. `e02_win`, Kısım III'teki diğer örnekler gibi bilerek `-z execstack` ile derlendi. Bölüm 11'de bunu kullanıp yığına kendi kodumuzu koyacağız. Bölüm 12'de NX açılınca yığın `rw-p` olacak ve bu yol kapanacak.

## Uygulama: ASLR'yi gözünle görmek

`ldd` bir programın hangi kütüphanelere bağlı olduğunu ve onları nereye yüklediğini gösterir. Bunu yapmak için programı gerçekten yükler, yani ASLR'nin etkisini de görürüz.

**Adım 1: ASLR açıkken üç kere çalıştır.**

```bash
for i in 1 2 3; do ldd ~/cracks/e02_win | grep libc; done
```

```text
libc.so.6 => /usr/lib/libc.so.6 (0x000078f827114000)
libc.so.6 => /usr/lib/libc.so.6 (0x000075ff994a9000)
libc.so.6 => /usr/lib/libc.so.6 (0x0000769f4c409000)
```

Üç çalıştırma, üç farklı adres.

**Adım 2: ASLR kapalı iki kere çalıştır.**

```bash
for i in 1 2; do setarch -R ldd ~/cracks/e02_win | grep libc; done
```

```text
libc.so.6 => /usr/lib/libc.so.6 (0x00007ffff7db9000)
libc.so.6 => /usr/lib/libc.so.6 (0x00007ffff7db9000)
```

İki çalıştırma, aynı adres. Üstelik bu adres, gdb'deki `vmmap` çıktısındaki libc'nin ilk satırıyla aynı: `0x7ffff7db9000`. gdb'nin her seferinde aynı adresleri göstermesinin sebebi, onun da ASLR'yi kapatarak çalıştırması.

**Adım 3: Değişmeyen kısma dikkat et.** Adım 1'deki üç adrese tekrar bak: `...14000`, `...a9000`, `...09000`. Hepsi `000` ile bitiyor. Bu tesadüf değil. Kütüphaneler her zaman bir sayfanın başına yüklenir ve bir sayfa `0x1000` bayttır. ASLR adresleri sadece sayfa sayfa kaydırabilir, son üç hex basamağı asla değiştiremez. Bu küçük gerçek Bölüm 13'te en güvendiğimiz sağlama yöntemi olacak.

## Savunma tarafı

Bu bölümde iki savunma mekanizmasını iş başında gördün:

- **İzin ayrımı (W^X, "yazılabilir ya da çalıştırılabilir, ikisi birden değil")**: modern derleyiciler ve çekirdek varsayılan olarak hiçbir bölgeyi aynı anda `w` ve `x` yapmaz. `e02_win`'deki `rwxp` yığın, bu korumayı `-z execstack` ile bilerek kapattığımız için var. Gerçek dünyada bir programın `checksec` çıktısında `RWX: Has RWX segments` görmek, ciddi bir uyarı işaretidir.
- **ASLR**: `/proc/sys/kernel/randomize_va_space` değeri 2 olduğunda yığın, kütüphaneler, heap ve (PIE'li programlarda) programın kendisi rastgele yüklenir. 0 değeri ASLR'yi tamamen kapatır. Bunu kendi makinende yapmak, kitaptaki ilk örnekleri kolaylaştırır ama makineni de korumasız bırakır. `setarch -R` aynı işi sadece tek bir program için yapar, o yüzden onu kullanıyoruz.

> [!WARNING]
> **Sık yapılan hatalar**
>
> - **gdb'de bulunan bir adresi gdb dışında kullanmak.** gdb ASLR'yi kapatır. Dışarıda ASLR açıksa o adres geçersizdir. Bölüm 11'de, ASLR kapalıyken bile gdb içi ve dışı yığın adreslerinin neden farklı olduğunu da göreceksin.
> - **`vmmap`'teki `End` adresini bölgenin içinde sanmak.** `0x401000`–`0x402000` bölgesinin son baytı `0x401fff`'dir.
> - **`0x7`'yle başlayan her adresi libc sanmak.** Yığın da, `ld.so` da `0x7` ile başlar. Emin olmak için `vmmap ADRES` ya da `info symbol ADRES` kullan.

## Kontrol soruları

1. `0x401166` adresi `vmmap` çıktısında hangi satırın içinde? O satırın izinleri ne?
2. `0x7ffff7e34110` hangi dosyaya ait?
3. `0x7fffffffd440` hangi bölgede?
4. Bir bölgenin `Size` sütununda `1000` yazıyor. Bu kaç bayt?
5. ASLR açıkken libc'nin adresi değişti. Programın kendi kodu (`0x400000`) neden değişmedi?
6. Taban adreslerinin hep `000` ile bitmesinin sebebi ne?

## Alıştırmalar

1. **Gözlemle.** `e02_win` gdb'de dururken `vmmap libc` ve `vmmap stack` komutlarını dene. `vmmap 0x401166` ne gösteriyor?
2. **Tahmin et, sonra dene.** `e04_rop` NX açık derlendi. Onun `vmmap` çıktısında yığının izinleri ne olacak? Önce tahmin et, sonra bak.
3. **Kendin yap.** `e02_win`'i gdb dışında, `setarch -R` olmadan iki kere başlat (girdi beklerken durur). Başka bir terminalde `grep stack /proc/$(pgrep -n e02_win)/maps` ile yığın adresine bak. İki çalıştırmada aynı mı?

## Özet

- Çalışan bir programın belleği; kod, veri, kütüphaneler ve yığın gibi bölgelere ayrılır. `vmmap` haritayı gösterir.
- Her bölgenin izinleri var: `r`, `w`, `x`. Normal bir programda hiçbir bölge aynı anda `w` ve `x` olmaz.
- PIE kapalı bir programın kodu `0x40...`, kütüphaneler ve yığın `0x7...` ile başlar.
- ASLR kütüphaneleri ve yığını her çalıştırmada kaydırır. `setarch -R` ve gdb ASLR'yi kapatır.
- Kaydırma sayfa (`0x1000`) birimleriyle yapıldığı için taban adresleri hep `000` ile biter.

Sırada işlemcinin kendi içindeki kutular var: yazmaçlar. Bu kutulara bakmadan, haritada nerede olduğumuzu bile bilemeyiz.

---
**Kontrol sorularının cevapları**

1. `0x401000`–`0x402000` satırı, `r-xp`. Programın kodu.
2. libc. `0x7ffff7de1000`–`0x7ffff7f3a000` arasındaki `r-xp` satırına düşüyor, yani libc'nin kodu.
3. Yığın (`[stack]`, `0x7ffffffdd000`–`0x7ffffffff000`).
4. `0x1000` = 4096 bayt, bir sayfa.
5. Program PIE olmadan derlendi. PIE'siz bir program her zaman derlenirken belirlenen adrese yüklenir.
6. Kütüphaneler ve program sayfa başlarına yüklenir. Bir sayfa `0x1000` bayt olduğu için başlangıç adresinin son 12 biti hep sıfırdır.

**Bu bölümde geçen yeni terimler:** bellek bölgesi, izin, sayfa, `vmmap`, ASLR, W^X.

---

[← 00-hazirlik](00-hazirlik.md) · [İçindekiler](README.md) · [02-yazmaclar-ve-yigin →](02-yazmaclar-ve-yigin.md)
