#include <stdio.h>
#include <unistd.h>

int main() {
i    int pid = fork();

    if (pid == 0) {
        printf("Tu mataste a mi padre piiipipi\n");
    } else {
        printf("YO SOY TU PADREEE\n");
    }

    return 0;
}

