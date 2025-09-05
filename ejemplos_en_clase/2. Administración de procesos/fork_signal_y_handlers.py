#!/usr/bin/python3
import os
import signal

print(f'Mi PID es: {os.getpid()}')
print('¡Vamos a crear un nuevo proceso!')

def handler(signum, frame):
    if signum == signal.SIGCHLD:
        os.waitpid(-1, os.WNOHANG)
        print('Terminé de esperar a un proceso hijo.')
    elif signum == signal.SIGTERM or signum == signal.SIGINT:
        print('¿Creíste que me iría tan fácil? ¡JÁ!')
    elif signum == signal.SIGWINCH:
        print('La pantalla cambió...')

signal.signal(signal.SIGCHLD, handler)
signal.signal(signal.SIGTERM, handler)
signal.signal(signal.SIGINT, handler)
signal.signal(signal.SIGWINCH, handler)

for i in range(5):
    pid = os.fork()

    if pid == 0:
        # Ya se que soy el proceso hijo
        print(f'¡Soy el hijito {os.getpid()}!')
        print(f'Papá se llama {os.getppid()}')
        exit()
    elif pid < 0:
        print('AAAAAHHHHHH!!!! ERRORRRRRR!!!!')
        exit(1)

# Estoy ejecutando el proceso padre
print(f'    Soy el proceso padre, {os.getpid()}')
print(f'    Mi último proceso hijo se llama {pid}')
input("    Dime cuando estés listo para terminar...\n")
