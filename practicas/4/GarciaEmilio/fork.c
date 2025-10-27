#include <stdio.h>
#include <sys/types.h>
#include <unistd.h>

int main() {
    printf("Eco\n");
    fflush(stdout);

    for (int i = 0; i < 5; i++) fork();
    printf("...ecooooo...\n");

    return 0;
}