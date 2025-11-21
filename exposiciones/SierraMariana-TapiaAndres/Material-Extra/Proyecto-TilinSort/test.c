#include <stdio.h>
#include <omp.h>
#include <stdlib.h>
/////////////////////////////////////////////////////////////////////////////////////////////////
void TilinSortSerialP(int arr[], int length) {
    int fin = length - 1;
    int n = 0;
    int flag;

    while (n < fin) {
        int i = n + 1;
        int k = fin;
        flag = 1;
        while (flag) {
            if (arr[n] >= arr[k]) {
                int temp = arr[n];
                arr[n] = arr[k];
                arr[k] = temp;
            }
            if (arr[n] >= arr[i]) {
                int temp = arr[n];
                arr[n] = arr[i];
                arr[i] = temp;
            }

            if (i == k || k == i + 1) {
                flag = 0;
            }
            k--;
            i++;
        }
        n++;
    }
}
/////////////////////////////////////////////////////////////////////////////////////////////////
void TilinSortParallel(int Arr[], int size) {
    int mid = size / 2;
    int L[mid];
    int R[size - mid];

    #pragma omp parallel for
    for (int i = 0; i < mid; i++) {
        L[i] = Arr[i];
    }

    #pragma omp parallel for
    for (int j = mid; j < size; j++) {
        R[j - mid] = Arr[j];
    }

    // Llamada a TilinSortSerial para ordenar cada subarreglo en paralelo
    #pragma omp parallel sections
    {
        #pragma omp section
        {
            TilinSortSerialP(L, mid);
        }

        #pragma omp section
        {
            TilinSortSerialP(R, size - mid);
        }
    }

    int i = 0;
    int j = 0;
    int k = 0;

    // Combinar los subarreglos ordenados
    while (i < mid && j < size - mid) {
        if (L[i] <= R[j]) {
            Arr[k] = L[i];
            i++;
        } else {
            Arr[k] = R[j];
            j++;
        }
        k++;
    }

    // Copiar los elementos restantes de L[], si los hay
    while (i < mid) {
        Arr[k] = L[i];
        i++;
        k++;
    }

    // Copiar los elementos restantes de R[], si los hay
    while (j < size - mid) {
        Arr[k] = R[j];
        j++;
        k++;
    }
}
/////////////////////////////////////////////////////////////////////////////////////////////////
void TilinSortParallelTask(int Arr[], int size) {
    int mid = size / 2;
    int L[mid];
    int R[size - mid];

    // Copiar elementos a L y R en paralelo
    #pragma omp parallel for
    for (int i = 0; i < size; i++) {
        if (i < mid) {
            L[i] = Arr[i];
        } else {
            R[i - mid] = Arr[i];
        }
    }

    // Ordenar subarreglos en paralelo usando tareas
    #pragma omp parallel
    {
        #pragma omp single nowait
        {
            #pragma omp task
            {
                TilinSortSerialP(L, mid);
            }
            #pragma omp task
            {
                TilinSortSerialP(R, size - mid);
            }
        }
    }

    int i = 0;
    int j = 0;
    int k = 0;

    // Combinar los subarreglos ordenados
    while (i < mid && j < size - mid) {
        if (L[i] <= R[j]) {
            Arr[k] = L[i];
            i++;
        } else {
            Arr[k] = R[j];
            j++;
        }
        k++;
    }

    // Copiar los elementos restantes de L[], si los hay
    while (i < mid) {
        Arr[k] = L[i];
        i++;
        k++;
    }

    // Copiar los elementos restantes de R[], si los hay
    while (j < size - mid) {
        Arr[k] = R[j];
        j++;
        k++;
    }
}
/////////////////////////////////////////////////////////////////////////////////////////////////
int main() {
    int elementos = 10;
    int Arr[elementos];
    int AuxArr[elementos];

    for (int i = 0; i < elementos; i++) {
        AuxArr[i] = rand() % 2000;
        //AuxArr[i] = elementos-i;
        //AuxArr[i] = i+1;
    }

    printf("Arr unsorted: [");
    for (int j = 0; j < elementos; j++) {
        printf("%d,", AuxArr[j]);
    }

    //TilinSortSerialP(AuxArr, elementos);
    //TilinSortParallel(AuxArr, elementos);
    TilinSortParallelTask(AuxArr, elementos);

    printf("]\n  Sorted Arr: [");
    for (int j = 0; j < elementos; j++) {
        printf("%d,", AuxArr[j]);
    }
    printf("]\n\n");

    return 0;
}
