#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void main() {
  /* char *cadena; */
  /* cadena = malloc(15 * sizeof(char)); */
  char cadena[15];
  printf("¿Y cuál quieres que sea la cadena?\n");
  scanf("%s", cadena);
  printf("Tu cadena es: «%s»\n", cadena);
}



///   strcat  → strncat / strlcat
///   strcpy  → strncpy / strlcpy
///   strstr  → strnstr / strlstr
