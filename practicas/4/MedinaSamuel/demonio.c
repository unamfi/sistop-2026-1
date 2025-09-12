#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/stat.h>

int main() {
    pid_t pid;

    
    pid = fork();
    if (pid < 0) exit(EXIT_FAILURE); 
    if (pid > 0) exit(EXIT_SUCCESS); 
    
    if (setsid() < 0) exit(EXIT_FAILURE);

    
    pid = fork();
    if (pid < 0) exit(EXIT_FAILURE);
    if (pid > 0) exit(EXIT_SUCCESS);

    
    //chdir("/");

    

    
    FILE *pid_file = fopen("demonio.pid", "w");
    if (pid_file != NULL) {
        fprintf(pid_file, "%d\\n", getpid());
        fclose(pid_file);
    }

    
    while (1) {
        sleep(10); 
    }

    return 0;
}