#!/usr/bin/python3
#
# ¡Juego de catorrazos multijugador!

import threading
from time import sleep
from random import random

jugadores = 5
tot_hilos = 15
multiplex = threading.Semaphore(jugadores)
activos = []
mut_activos = threading.Semaphore(1)

def jugador(yo):
    global activos
    fuerza = 5
    print(f"{' ' * yo}J={yo} F={fuerza}")
    while True:
        multiplex.acquire()
        with mut_activos:
            activos.append(yo)
        sleep(random())
        for i in range(4):
            print(f"{' ' * yo}J={yo} dentro!")
            if random() > 0.5:
                fuerza += 1
            else:
                fuerza -= 1
            if fuerza < 1:
                with mut_activos:
                    activos.release(yo)
                multiplex.release()
                print(f"{' ' * yo}J={yo} ARRRGGGHHHHH!")
                return 0
            print(f"{' ' * yo}J={yo} Sigo, F={fuerza}")
        with mut_activos:
            activos.release(yo)
        multiplex.release()

for i in range(tot_hilos):
    threading.Thread(target=jugador, args=[i]).start()

while True:
    print(f'****** Hilos activos: {activos}')
    sleep(0.5)
