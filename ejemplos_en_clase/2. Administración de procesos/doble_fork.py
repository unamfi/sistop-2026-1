#!/usr/bin/python3
import os
import time

pid = os.fork()

if pid > 0:
    print(f'Mi ({os.getpid()}) trabajo aquí está cumplido. ¡Cháu!')
    exit(0)

# Nos olvidamos de ese PID, ya no me importa
pid = os.fork()
if pid == 0:
    while True:
#        print(f'Mi PID es {os.getpid()}, el PID de mi padre es {os.getppid()}')
        time.sleep(1)

exit(0)
