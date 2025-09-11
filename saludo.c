#include <stdio.h>

int main() {
    char nombre[50];
    printf("Escribe tu nombre: ");
    scanf("%s", nombre);
    printf("¡Hola %s!\n", nombre);
    return 0;
}