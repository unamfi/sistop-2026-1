#!/usr/bin/python3
#
# Implementación del problema de los "Productores y Consumidores"
from threading import Thread, Semaphore
from time import sleep
from random import random
from colorama import Fore,init

init()

MAX_OBJETOS = 5
PRODUCTORES = 10
CONSUMIDORES = 10
cinta = []
mutex_cinta = Semaphore(1)
num_objetos = Semaphore(0)
cinta_llena = Semaphore(MAX_OBJETOS)

def productor(yo):
    global cinta
    print(Fore.GREEN + f'P{yo}: Iniciando')
    while True:
        sleep(random())
        obj = random()
        print(Fore.GREEN + f'P{yo}: Generé {obj}')
        cinta_llena.acquire()
        with mutex_cinta:
            cinta.append(obj)
        num_objetos.release()

def consumidor(yo):
    global cinta
    print(Fore.YELLOW + f'C{yo}: Iniciando')
    while True:
        num_objetos.acquire()
        with mutex_cinta:
            obj = cinta.pop()
        cinta_llena.release()
        print(Fore.YELLOW + f'C{yo}: Obtuve {obj}')
        sleep(random())

print(Fore.WHITE + f'Iniciando sistema con {PRODUCTORES} productores y {CONSUMIDORES} consumidores')
for i in range(PRODUCTORES):
    Thread(target=productor, args=[i]).start()
for i in range(CONSUMIDORES):
    Thread(target=consumidor, args=[i]).start()

while True:
    sleep(1)
    print(Fore.CYAN + f'Cinta: {len(cinta)} objetos')
