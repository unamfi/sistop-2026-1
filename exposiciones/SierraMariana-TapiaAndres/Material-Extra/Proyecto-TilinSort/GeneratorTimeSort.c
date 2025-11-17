#include <stdio.h>
#include <omp.h>
/////////////////////////////////////////////////////////////////////////////////////////////////
void TilinSortSerialP(int Arr[], int length) {
    int fin = length - 1;
    int n = 0;
    int flag;
    while (n < fin) {
        int i = n + 1;
        int k = fin;
        flag = 1;

        while (flag) {
            if (Arr[n] >= Arr[k]) {
                int temp = Arr[n];
                Arr[n] = Arr[k];
                Arr[k] = temp;
            }
            if (Arr[n] >= Arr[i]) {
                int temp = Arr[n];
                Arr[n] = Arr[i];
                Arr[i] = temp;
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
////////////////////////////////////////////////////////////////////////////////////////////////////////

/////////////////////////////////////////////////////////////////////////////////////////////////
void TilinSortSerial(int arr[], int length, FILE *file) {
    int fin = length - 1;
    int n = 0;
    int flag;

    double start_time = omp_get_wtime();  // Medir el tiempo al inicio de la iteración
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
    double end_time = omp_get_wtime();  // Medir el tiempo al final de la iteración
    double elapsed_time = end_time - start_time;

    fprintf(file, "%d, %f\n", n, elapsed_time);  // Guardar en el archivo CSV
}
/////////////////////////////////////////////////////////////////////////////////////////////////
void TilinSortParallel(int Arr[], int size, FILE *file) {
    int mid = size / 2;
    int L[mid];
    int R[size - mid];
    double start_time, end_time, elapsed_time;

    start_time = omp_get_wtime();  // Medir el tiempo al inicio de la iteración

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

    end_time = omp_get_wtime();  // Medir el tiempo al final de la iteración
    elapsed_time = end_time - start_time;

    fprintf(file, "%d, %f\n", size, elapsed_time);  // Guardar en el archivo CSV
}
/////////////////////////////////////////////////////////////////////////////////////////////////
void TilinSortParallelTask(int Arr[], int size, FILE *file) {
    int mid = size / 2;
    int L[mid];
    int R[size - mid];
    double start_time, end_time, elapsed_time;

    start_time = omp_get_wtime();

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

    end_time = omp_get_wtime();
    elapsed_time = end_time - start_time;

    fprintf(file, "%d, %f\n", size, elapsed_time);
}
/////////////////////////////////////////////////////////////////////////////////////////////////
int main() {
    int elementos = 20000;
    int Arr[elementos];

    FILE *serial_file = fopen("SerialExecuteTime.csv", "w");
    if (serial_file == NULL) {
        perror("Error al abrir el archivo para la versión serial");
        return 1;
    }

    fprintf(serial_file, "Iteracion, Tiempo\n");

    for (int i = 0; i < elementos; i++) {
        for (int q = 0; q <= i; q++) {
            Arr[q] = elementos - q;
        }
        Arr[i] = elementos - i;
        TilinSortSerial(Arr, i + 1, serial_file);
    }

    fclose(serial_file); 
/////////////////////////////////////////////////////////////////////////////////////////////////
/*     FILE *parallel_file = fopen("ParallelExecuteTime.csv", "w");
    if (parallel_file == NULL) {
        perror("Error al abrir el archivo para la versión paralelizada");
        return 1;
    }

    fprintf(parallel_file, "Iteracion, Tiempo\n");

    for (int i = 0; i < elementos; i++) {
        for (int q = 0; q <= i; q++) {
            Arr[q] = elementos - q;
        }
        Arr[i] = elementos - i;
        TilinSortParallel(Arr, i + 1, parallel_file);
    }

    fclose(parallel_file); */
/////////////////////////////////////////////////////////////////////////////////////////////////
/*     FILE *parallel_task_file = fopen("ParallelTaskExecuteTime.csv", "w");
    if (parallel_task_file == NULL) {
        perror("Error al abrir el archivo para la versión paralelizada con tareas");
        return 1;
    }

    fprintf(parallel_task_file, "Iteracion, Tiempo\n");

    for (int i = 0; i < elementos; i++) {
        for (int q = 0; q <= i; q++) {
            Arr[q] = elementos - q;
        }
        Arr[i] = elementos - i;
        TilinSortParallelTask(Arr, i + 1, parallel_task_file);
    }
    fclose(parallel_task_file);  */
/////////////////////////////////////////////////////////////////////////////////////////////////
    return 0;
}