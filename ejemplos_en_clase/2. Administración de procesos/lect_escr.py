#!/usr/bin/python3
#
# Implementación del problema de los "Lectores y Escritores"
from threading import Thread, Semaphore
from time import sleep
from random import random
from colorama import Fore,init

init()

LECTORES = 40
ESCRITORES = 3
pizarron = ''
mut_pizarron = Semaphore(1)
num_lectores = 0
mut_lectores = Semaphore(1)
torniquete = Semaphore(1)

def lector(yo):
    global pizarron, num_lectores
    while True:
        torniquete.acquire()
        torniquete.release()

        with mut_lectores:
            num_lectores += 1
            if num_lectores == 1:
                mut_pizarron.acquire()
            print(Fore.GREEN, f'L{yo} entra.')

        print(Fore.GREEN, f'L{yo} leo {pizarron}. Somos {num_lectores}')
        sleep(random())

        with mut_lectores:
            num_lectores -= 1
            if num_lectores == 0:
                mut_pizarron.release()
            print(Fore.GREEN, f'L{yo} se va.')

def escritor(yo):
    global pizarron
    while True:
        torniquete.acquire()
        mut_pizarron.acquire()
        print(Fore.RED, f'E{yo} modifica el pizarrón')
        sleep(random())
        pizarron = f'E{yo} --- {random()}'
        mut_pizarron.release()
        torniquete.release()
        print(Fore.RED, f'E{yo} terminó con sus cambios.')
        

#print(Fore.WHITE + f'Iniciando sistema con {PRODUCTORES} productores y {CONSUMIDORES} consumidores')
for i in range(LECTORES):
   Thread(target=lector, args=[i]).start()
for i in range(ESCRITORES):
   Thread(target=escritor, args=[i]).start()

while True:
    sleep(1)
    print(Fore.CYAN + f'Pizarrón: {pizarron}')
