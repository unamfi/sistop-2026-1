#include <stdio.h>
#include <omp.h>

int main() {
  #pragma omp parallel num_threads(4)
  {
    printf("Hilo %d de %d\n", omp_get_thread_num(), omp_get_num_threads());
  }
}
