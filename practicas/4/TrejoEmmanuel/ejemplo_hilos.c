#include <stdio.h>
#include <pthread.h>

void* ejemploHilos(void* arg) {
    int id = *((int*)arg);
    printf("Hilo %d ejecutándose\n", id);
    return NULL;
}

int main() {
    pthread_t hilo;
    int id = 1;
    
    pthread_create(&hilo, NULL, ejemploHilos, &id);
    pthread_join(hilo, NULL);
    
    printf("Programa terminado\n");
    return 0;
}
