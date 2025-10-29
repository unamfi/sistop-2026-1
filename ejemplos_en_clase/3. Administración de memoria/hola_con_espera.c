#include <stdio.h>
#include <stdlib.h>

int total = 5;

int main() {
  int num;
  int *otro;
  otro = malloc(sizeof(int));
  
  printf("Este es un programa sencillo, trivial, y hasta aburrido\n");
  printf("¿Qué número nos gusta?\n");
  scanf("%d", &num);
  for (int i=0; i<total; i++)
    printf("%d ", num);
  printf("\n\n");
  free(otro);
}
