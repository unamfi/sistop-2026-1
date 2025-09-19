#include <iostream>
#include <windows.h>

DWORD WINAPI tarea(LPVOID lpParam) {
    int id = *(int*)lpParam;
    std::cout << "Hilo " << id << ": estoy corriendo en paralelo\n";
    Sleep(1000); // Pausa de 1 segundo
    std::cout << "Hilo " << id << ": terminé mi trabajo\n";
    return 0;
}

int main() {
    DWORD tid1, tid2;
    HANDLE h1, h2;
    int id1 = 1, id2 = 2;

    // Crear los hilos
    h1 = CreateThread(NULL, 0, tarea, &id1, 0, &tid1);
    h2 = CreateThread(NULL, 0, tarea, &id2, 0, &tid2);

    std::cout << "Proceso principal: esperando a los hilos...\n";

    // Esperar a que los hilos terminen
    WaitForSingleObject(h1, INFINITE);
    WaitForSingleObject(h2, INFINITE);

    std::cout << "Proceso principal: todos los hilos terminaron.\n";

    // Liberar recursos
    CloseHandle(h1);
    CloseHandle(h2);

    return 0;
}
