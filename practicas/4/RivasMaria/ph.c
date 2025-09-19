#include <stdio.h>
#include <unistd.h>

int main() {
    int pid = fork();  // Crea un proceso hijo

    if (pid == 0) {
        printf("Mataste a mi padre\n");
    } else {
        printf("YO SOY TU PADREEE\n");
    }

    return 0;
}

