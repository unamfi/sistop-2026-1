#!/usr/bin/python3
import threading
from time import sleep

sem = threading.Semaphore(0)

def prepara_conexion():
    print('* Preparando conexión')
    sleep(1)
    print('* Conexión preparada')
    sem.release()

def envia_datos():
    print('- Calculando datos')
    sleep(0.2)
    print('- Datos listos. ¡A mandarlos!')
    sem.acquire()
    print('- Datos enviados. ¡Ya terminamos!')

threading.Thread(target=prepara_conexion).start()
threading.Thread(target=envia_datos).start()
