#include <stdio.h>
#include <omp.h>

int main() {
    int contador = 0;
    omp_set_num_threads(4); // Se puede fijar el número de hilos si se desea
    #pragma omp parallel for
        for (int i = 0; i < 10; i++) {   // puse 10 para que no llene la salida
            #pragma omp critical
            {
                contador++;
                printf("Hilo %d incrementó el contador a %d (iteración %d)\n",
                       omp_get_thread_num(), contador, i);
            }
        }
    printf("Valor final del contador = %d\n", contador);
    return 0;
}
