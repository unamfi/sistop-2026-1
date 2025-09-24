#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(void) {
    pid_t pid =fork();
    if (pid < 0) { perror("fork"); exit(1); }

    if (pid == 0) {
        
        printf("[Hijo] PID=%d termina ya\n", getpid());
        _exit(0); // usa _exit para no correr at_exit ni flush extra
    }

    printf("[Padre] PID=%d, hijo=%d (no haré wait por 30s)\n", getpid(), pid);
    sleep(30);
   
    return 0;
}
