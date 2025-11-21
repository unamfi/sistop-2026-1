#include <stdio.h>
#include <omp.h>

int main() {
    int suma=0;
    #pragma omp parallel for reduction(+:suma)
    for (int i=0;i<100000;i++)
      suma++;
    printf("Suma total: %d\n",suma);
    return 0;
}
