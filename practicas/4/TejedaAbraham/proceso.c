#include <stdio.h>
#include <time.h>

int main(void) {
    // 1) Mostrar salida en terminal
    printf("SO: registro de ejecucion iniciado\n");

    // 2) Generar un archivo autoderivado por USO del programa
    FILE *f = fopen("salida.registro", "a");
    if (!f) {
        perror("No pude abrir salida.registro");
        return 1;
    }

    time_t t = time(NULL);
    struct tm *tm = localtime(&t);
    char stamp[64];
    strftime(stamp, sizeof(stamp), "%Y-%m-%d %H:%M:%S", tm);

    fprintf(f, "[%s] Hola desde proceso.c (PID simulado)\n", stamp);
    fclose(f);

    // 3) Mensaje final (con salto de línea correcto)
    printf("SO: registro escrito en salida.registro\n");
    return 0;
}
