# Kitaptaki örnek programları bin/ klasörüne derler.
# Kullanım: make        (hepsini derle)
#           make clean  (bin/ klasörünü sil)

SRC := ornekler/src
BIN := bin
BASE := -O0 -fcf-protection=none

all: $(BIN)/e01_admin $(BIN)/e02_win $(BIN)/e03_shell $(BIN)/e03_sc.bin $(BIN)/e04_rop \
     $(BIN)/e05_libc $(BIN)/e06_fmt $(BIN)/e07_canary $(BIN)/e08_pie $(BIN)/e09_full

$(BIN):
	mkdir -p $(BIN)

# Kısım III: hiçbir koruma yok
$(BIN)/e01_admin $(BIN)/e02_win $(BIN)/e03_shell: $(BIN)/%: $(SRC)/%.c | $(BIN)
	gcc $(BASE) -fno-stack-protector -no-pie -z execstack -o $@ $<

$(BIN)/e03_sc.bin: $(SRC)/e03_sc.asm | $(BIN)
	nasm -f bin $< -o $@

# NX açık
$(BIN)/e04_rop $(BIN)/e05_libc: $(BIN)/%: $(SRC)/%.c | $(BIN)
	gcc $(BASE) -fno-stack-protector -no-pie -o $@ $<

# format string
$(BIN)/e06_fmt: $(SRC)/e06_fmt.c | $(BIN)
	gcc $(BASE) -fno-stack-protector -no-pie -Wno-format-security -o $@ $<

# canary
$(BIN)/e07_canary: $(SRC)/e07_canary.c | $(BIN)
	gcc $(BASE) -fstack-protector-all -no-pie -Wno-format-security -o $@ $<

# canary + PIE
$(BIN)/e08_pie: $(SRC)/e08_pie.c | $(BIN)
	gcc $(BASE) -fstack-protector-all -pie -fPIE -Wno-format-security -o $@ $<

# hepsi + Full RELRO
$(BIN)/e09_full: $(SRC)/e09_full.c | $(BIN)
	gcc $(BASE) -fstack-protector-all -pie -fPIE -Wno-format-security -Wl,-z,relro,-z,now -o $@ $<

clean:
	rm -rf $(BIN)

.PHONY: all clean
