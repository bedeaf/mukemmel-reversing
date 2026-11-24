# mükemmel-reversing

Türkçe tersine mühendislik ve exploit geliştirme kaynakları. İki kitap ve kitaplardaki her örneğin kaynak kodu ve çalışan exploit'i.

İnternette Türkçe, baştan sona, gerçek çıktılarla ilerleyen bir kaynak bulamadığımız için yazdık. Kitaplardaki her komut Linux x86-64 üzerinde çalıştırıldı ve her çıktı o çalıştırmadan alındı.

## İçerik

| | Ne | Oku |
|---|---|---|
| **Exploit Geliştirme** | Hiç koruması olmayan bir programdan NX, ASLR, canary, PIE ve Full RELRO'nun hepsi açık bir programa kadar dokuz adımda yığın exploit'i. Hex ve little-endian'dan başlıyor, ret2win, shellcode, ROP, ret2libc ve format string üzerinden ilerliyor. | [Web'de](kitap/README.md) · [PDF](pdf/Exploit-Gelistirme.pdf) (156 sayfa) |
| **Binary Ninja Kullanım Kılavuzu** | Binary Ninja'nın arayüzü, görünümler, gezinme, isim ve tip verme, Stack paneli. Kitaptaki örnekler üzerinde, gerçek ekran görüntüleriyle. | [Web'de](binja/README.md) · [PDF](pdf/Binary-Ninja-Kullanim-Kilavuzu.pdf) (31 sayfa) |

Komutları kopyalamak için **web sürümünü** kullan. GitHub her kod bloğunun sağ üstüne bir kopyalama düğmesi koyuyor.

## Örnekleri derlemek

```bash
git clone https://github.com/bedeaf/mukemmel-reversing
cd mukemmel-reversing
make
```

Programlar `bin/` klasörüne derlenir. Exploit'ler `ornekler/exploit/` içinde:

```bash
cd ornekler/exploit
python3 e01_admin_x.py
```

Gerekenler: `gcc`, `nasm`, `python3`, [pwntools](https://github.com/Gallopsled/pwntools), gdb ([pwndbg](https://github.com/pwndbg/pwndbg) önerilir), `ROPgadget`. Binary Ninja kılavuzu için [Binary Ninja Free](https://binary.ninja/free/) yeterli.

| Klasör | İçinde |
|---|---|
| `kitap/` | Exploit Geliştirme kitabı, Markdown |
| `binja/` | Binary Ninja kılavuzu, Markdown ve ekran görüntüleri |
| `pdf/` | İki kitabın PDF'leri |
| `ornekler/src/` | `e01_admin.c` … `e09_full.c`, shellcode (`e03_sc.asm`) |
| `ornekler/exploit/` | Her örneğin çalışan exploit'i |
| `uretim/` | PDF'leri üreten betikler ve kaynak metinler |

## Okumadan önce bil

- **Yollar.** Kitap bir laboratuvar düzeninde yazıldı: metinde geçen `~/cracks/e01_admin` bu depodaki `bin/e01_admin`, `~/.cracks_src/` ise `ornekler/` demek. Kitaptaki çıktılarda görünen `/home/linkola/...` yolları gerçek çıktı oldukları için değiştirilmedi.
- **Sürüm.** Çıktılar şu ortamda alındı: Void Linux, çekirdek 6.18, glibc 2.41, gcc 14.2, pwntools 4.15, Binary Ninja Free 6.0. Senin makinende adresler farklı olacak, mesafeler ve yöntem aynı kalacak.
- **libc'ye bağlı sayılar.** `e05`, `e09` ve kitabın Bölüm 15 ve 19'u, glibc 2.41'e özel offset'ler kullanıyor (`system` = `0x51030`, `__libc_start_call_main+124` = `0x2abfc`). Başka bir libc'de bu sayıları kitapta anlatıldığı gibi kendin ölç.
- **"Merdiven" kutuları.** Kitapta geçen `p01_gate` gibi alıştırmalar yazarın kendi çalışma setinden ve bu depoda yok. Onları geçebilirsin.

## Yasal uyarı

Bu depodaki her teknik, okuyucunun kendi derlediği küçük programlar üzerinde, kendi makinesinde öğrenmesi için yazıldı. Aynı teknikleri izin almadığın sistemlere karşı kullanmak suçtur (Türkiye'de TCK 243 ve 244). Pratik için CTF'ler, [crackmes.one](https://crackmes.one), [pwn.college](https://pwn.college) gibi bunun için yapılmış yerleri kullan.

## Lisans

- Kitapların metni ve ekran görüntüleri: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/deed.tr). Paylaşabilir ve değiştirebilirsin. Kaynak göster ve aynı lisansla paylaş.
- Kod (`ornekler/`, `uretim/`, `Makefile`): [MIT](LICENSE).
- Binary Ninja, Vector 35 Inc.'in ticari markasıdır. Kılavuz, resmi belgelere ([docs.binary.ninja](https://docs.binary.ninja)) bakılarak yazıldı ve resmi değildir.

Hata bulursan ya da bir çıktı senin makinende farklıysa issue aç.
