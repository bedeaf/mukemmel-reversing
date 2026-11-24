/* e04_rop: NX acik. Argumanli win() icin ROP. Kanarya/PIE yok. */
#include <stdio.h>
#include <unistd.h>

/* hediye: "pop rdi; ret" parcasi */
__asm__(".globl gadget\ngadget:\n pop %rdi\n ret\n");

void win(unsigned long key)
{
    if (key == 0xdeadbeefcafef00dUL)
        puts("tebrikler: dogru anahtarla win() calisti!");
    else
        printf("win() calisti ama anahtar yanlis: 0x%lx\n", key);
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
