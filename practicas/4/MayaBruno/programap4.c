#include <stdio.h>
#include <unistd.h>   
#include <sys/wait.h> 

int main() {
    pid_t pid = fork();  // Crear un nuevo proceso

    if (pid < 0) {
        perror("fork");
        return 1;
    }
    else if (pid == 0) {
        printf("Soy el hijo. Mi PID es %d\n", getpid());
    }
    else {
        printf("Soy el padre. Mi PID es %d y mi hijo es %d\n", getpid(), pid);
        wait(NULL); 
        printf("El hijo ha terminado.\n");
    }

    return 0;
}
