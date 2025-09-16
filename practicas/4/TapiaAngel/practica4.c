#include <stdio.h>
#include <omp.h>

int main() {
    #pragma omp parallel num_threads(4) 
    {
        int thread_id = omp_get_thread_num();
        int num_threads = omp_get_num_threads();   
        printf("Hola desde el hilo %d de un total de %d hilos.\n", thread_id, num_threads);
        if (thread_id == 0) {
            printf("Soy el hilo principal.\n");
        }
    }

    return 0;
}