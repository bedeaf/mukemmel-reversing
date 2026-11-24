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
