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
