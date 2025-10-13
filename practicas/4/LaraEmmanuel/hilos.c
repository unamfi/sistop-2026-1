#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>

#define NUM_HILOS 5

// Función que ejecutarán los hilos
void* hilo_funcion(void* arg) {
	int id = *(int*)arg;
	printf("Hilo %d: Hola desde el hilo!\n", id);
	printf("Hilo %d: Saliendo...\n", id);
	pthread_exit(NULL);
}

int main() {
    pthread_t hilos[NUM_HILOS];
    int ids[NUM_HILOS];
    int i;
    
    printf("Main: Creando %d hilos...\n", NUM_HILOS);
    
    // Crear los hilos
    for (i = 0; i < NUM_HILOS; i++) {
        ids[i] = i + 1;
        if (pthread_create(&hilos[i], NULL, hilo_funcion, &ids[i]) != 0) {
            perror("Error al crear el hilo");
            return 1;
        }
    }
    
    printf("Main: Esperando que los hilos terminen...\n");
    
    // Esperar a que todos los hilos terminen
    for (i = 0; i < NUM_HILOS; i++) {
        if (pthread_join(hilos[i], NULL) != 0) {
            perror("Error al esperar el hilo");
            return 1;
        }
    }
    
    printf("Main: Todos los hilos han terminado.\n");
    return 0;
}
