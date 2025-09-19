#include <stdio.h>
#include <time.h>

int main(void) {
    // Muestra en pantalla que el programa ha iniciado su ejecución
    printf("Iniciando ejecución del programa...\n");

    // Abre (o crea si no existe) el archivo 'salida.registro' en modo append
    FILE *f = fopen("salida.registro", "a");
    if (!f) {
        // Si ocurre un error al abrir el archivo, se muestra el motivo y se sale
        perror("Error: no fue posible abrir el archivo 'salida.registro'");
        return 1;
    }

    // Obtiene la fecha y hora actuales
    time_t t = time(NULL);
    struct tm *tm = localtime(&t);

    // Arreglo para almacenar la marca de tiempo formateada
    char stamp[64];
    strftime(stamp, sizeof(stamp), "%Y-%m-%d %H:%M:%S", tm);

    // Escribe en el archivo la marca de tiempo junto con un mensaje
    fprintf(f, "[%s] Ejecución registrada desde proceso.c\n", stamp);

    // Cierra el archivo para asegurar que los datos se guarden correctamente
    fclose(f);

    // Notifica al usuario en pantalla que el registro se escribió con éxito
    printf("Registro guardado en 'salida.registro'.\n");

    return 0;
}
