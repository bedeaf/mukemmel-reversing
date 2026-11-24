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
