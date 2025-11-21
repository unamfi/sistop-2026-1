#include <stdio.h>
#include <omp.h>

int main() {
    #pragma omp parallel num_threads(4)
    {
      printf("Primera parte\n");
      #pragma omp barrier
      printf("Segunda parte\n");
    }
    return 0;
}
