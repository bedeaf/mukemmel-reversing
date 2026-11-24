/* e08_pie: kanarya + PIE + NX + ASLR. Kanarya ve kod adresi sizdir. */
#include <stdio.h>
#include <unistd.h>

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
    read(0, buf, 200);        /* HATA 2: tasma */
}

int main(void)
{
    setvbuf(stdout, NULL, _IONBF, 0);
    vuln();
    puts("normal cikis.");
    return 0;
}
