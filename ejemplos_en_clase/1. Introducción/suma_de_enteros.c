#include <stdio.h>
void main() {
  int a = 5;
  int b = 10;
  int c = 0;
  for (int i = 1; i < b; i++)
    c = c + a;
  printf("Mi resultado es: %d\n", c);
}
