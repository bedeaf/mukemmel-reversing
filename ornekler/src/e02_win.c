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
