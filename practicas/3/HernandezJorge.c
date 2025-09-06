#include <stdio.h>

int main() {
    char nombre[50]; // Declara un array de caracteres para guardar el nombre.

    printf("Por favor, ingresa tu nombre: "); // Le pide al usuario que ingrese su nombre.
    scanf("%s", nombre); // Lee el nombre ingresado por el usuario y lo guarda en la variable `nombre`.

    printf("Hola, %s", nombre); // Imprime el saludo usando el nombre que el usuario introdujo.

    return 0;
}