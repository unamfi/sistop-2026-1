#include <stdio.h>
#include <omp.h>

int main() {
    #pragma omp parallel
    {
        #pragma omp sections
        {
            #pragma omp section
            {
                printf("Sección 1 ejecutada por el hilo %d\n", omp_get_thread_num());
            }

            #pragma omp section
            {
                printf("Sección 2 ejecutada por el hilo %d\n", omp_get_thread_num());
            }
        }
    }
    return 0;
}
