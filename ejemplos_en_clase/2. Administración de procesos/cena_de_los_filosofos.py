#!/usr/bin/python3
import threading
import time
import random
from colorama import Fore, init

init()

NUM_FILOSOFOS = 5
colores = [Fore.GREEN, Fore.RED, Fore.YELLOW, Fore.BLUE, Fore.CYAN]

palillos = [ threading.Semaphore(1) for i in range(NUM_FILOSOFOS) ]

# mut_palillos = threading.Semaphore( NUM_FILOSOFOS-1 )
# Solución 1: multiplex a NUM_FILOSOFOS-1
# Solución 2: Los pares son zurdos, los impares son diestros

def filosofo(yo):
    while(True):
        piensa(yo)
        levanta_palillos(yo)
        come(yo)

def piensa(yo):
    global colores
    print(colores[yo-1], f'{yo} piensa.....   🤔')

def levanta_palillos(yo):
    global colores
    print(colores[yo-1], f'{yo} tengo hambre 😋')

    # mut_palillos.acquire()
    # palillos[(yo-1) % NUM_FILOSOFOS].acquire()
    # print(colores[yo-1], f'{yo} levanta el palillo izquierdo 🥢🫲')

    # palillos[(yo) % NUM_FILOSOFOS].acquire()
    # print(colores[yo-1], f'{yo} levanta el palillo derecho 🥢🫱')
    # mut_palillos.release()

    if (yo % 2 == 0):
        p1 = palillos[(yo-1) % NUM_FILOSOFOS]
        p1_s = 'izquierdo 🥢🫲'
        p2 = palillos[yo % NUM_FILOSOFOS]
        p2_s = 'derecho 🥢🫱'
    else:
        p2 = palillos[(yo-1) % NUM_FILOSOFOS]
        p2_s = 'izquierdo 🥢🫲'
        p1 = palillos[yo % NUM_FILOSOFOS]
        p1_s = 'derecho 🥢🫱'

    p1.acquire()
    print(colores[yo-1], f'{yo} levanta el palillo {p1_s}')

    p2.acquire()
    print(colores[yo-1], f'{yo} levanta el palillo {p2_s}')




def come(yo):
    global colores
    print(colores[yo-1], f'{yo} come 🍚🍙')
    print(colores[yo-1], f'{yo} satisfecho. 😋')
    palillos[(yo-1) % NUM_FILOSOFOS].release()
    palillos[(yo) % NUM_FILOSOFOS].release()

for i in range(NUM_FILOSOFOS):
    threading.Thread(target = filosofo, args = [i]).start()
