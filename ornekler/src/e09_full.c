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
