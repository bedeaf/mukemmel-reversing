/* e06_fmt: format string hatasi. Okuma (%p) ve yazma (%n). */
#include <stdio.h>
#include <unistd.h>

unsigned int hedef = 0;

int main(void)
{
    char buf[128];
    setvbuf(stdout, NULL, _IONBF, 0);
    for (int i = 0; i < 2; i++) {
        printf("mesaj: ");
        int n = read(0, buf, sizeof(buf) - 1);
        if (n <= 0)
            return 1;
        buf[n] = 0;
        printf(buf);          /* HATA: kullanici girdisi format olarak */
        printf("\nhedef = %u\n", hedef);
    }
    if (hedef == 1337)
        puts("tebrikler: hedef degisti!");
    return 0;
}
