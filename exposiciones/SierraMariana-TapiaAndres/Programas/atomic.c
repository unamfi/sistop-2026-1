#include <stdio.h>
#include <omp.h>

int main() {
    int contador = 0;

    #pragma omp parallel for
    for (int i = 0; i < 1000; i++) {
      #pragma omp atomic
      contador++;
    }
    printf("Valor final: %d\n", contador);
    return 0;
}
