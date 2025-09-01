#include <stdio.h>

int main() {
    char user[120];
    printf("Cúal es tu nombre: ");
    fgets(user, sizeof(user), stdin);

    printf("Hola %s", user);
    return 0;
}

