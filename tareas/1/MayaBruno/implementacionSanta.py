# Problema de Santa Claus 

import threading
from threading import Semaphore, Lock, Thread
from time import sleep
from random import random
from colorama import Fore, init

init()

ELFOS = 15
RENOS = 9

renos_listos = 0
elfos_esperando = 0

mut_renos = Lock()
mut_elfos = Lock()

sem_santa = Semaphore(0)

torniquete = Semaphore(1)

multiplex_elfos = Semaphore(3)

elf_atendidos = Semaphore(0)

reno_listo = Semaphore(0)       
reno_fin_viaje = Semaphore(0)   

def santa():
    global renos_listos, elfos_esperando
    print(Fore.CYAN + "Santa: me voy a dormir en el Polo Norte...")
    while True:
        sem_santa.acquire()

        atender_renos = False
        with mut_renos:
            if renos_listos == RENOS:
                atender_renos = True

        if atender_renos:
            print(Fore.CYAN + "Santa: ¡Despierto! Llegaron los 9 renos. Preparando el trineo... HOO! HO! HO!")

            # Enganchar renos
            for _ in range(RENOS):
                reno_listo.release()

            # Viajar
            sleep(0.3 + random())

            # Reiniciar estado y liberar renos del viaje
            with mut_renos:
                renos_listos = 0
            for _ in range(RENOS):
                reno_fin_viaje.release()

            print(Fore.CYAN + "Santa: viaje terminado. Vuelvo a dormir.")
            # Reabrir torniquete para los renos
            torniquete.release()
            continue

        print(Fore.CYAN + "Santa: ¡Despierto! Ayudo a 3 elfos con problemas...")
        sleep(0.2 + random())
        for _ in range(3):
            elf_atendidos.release()
        print(Fore.CYAN + "Santa: terminé de ayudar a los elfos. A dormir de nuevo.")


def reno(yo):
    global renos_listos
    print(Fore.RED + f"R{yo}: me voy de vacaciones al Caribe!!!")
    while True:
        # Vacaciones de los renos
        sleep(3 + random() * 3)   

        # Regreso
        ultimo = False
        with mut_renos:
            renos_listos += 1
            print(Fore.RED + f"R{yo}: ya llegué a chambear. Renos listos = {renos_listos}/{RENOS}")
            if renos_listos == RENOS:
                ultimo = True

        if ultimo:
            # Cerrar torniquete 
            torniquete.acquire()
            print(Fore.RED + "Renos: ¡ya somos los 9! Despertamos a Santa.")
            sem_santa.release()

        #Se enganchan los renos al trineo
        reno_listo.acquire()
        print(Fore.RED + f"R{yo}: ¡enganchado al trineo, a despegar!")

        # Esperar fin de viaje 
        reno_fin_viaje.acquire()
        print(Fore.RED + f"R{yo}: viaje terminado. ¡me voy de vacaciones otra vez! ")
        


def elfo(yo):
    global elfos_esperando
    print(Fore.GREEN + f"E{yo}: a trabajar fabricando juguetes!")
    while True:
        sleep(0.2 + random())
        if random() < 0.45:
            
            torniquete.acquire()
            torniquete.release()

            # Intentar entrar al grupo de 3 elfos que quieren que santa los ayude
            multiplex_elfos.acquire()
            despertar_santa = False
            with mut_elfos:
                elfos_esperando += 1
                print(Fore.GREEN + f"E{yo}: necesito ayuda. Elfos en grupo = {elfos_esperando}/3")
                if elfos_esperando == 3:
                    despertar_santa = True

            if despertar_santa:
                print(Fore.GREEN + "Elfos: somos 3, ¡despertamos a Santa!")
                sem_santa.release()

            # Esperar atención
            elf_atendidos.acquire()

        
            liberar_sala = False
            with mut_elfos:
                elfos_esperando -= 1
                print(Fore.GREEN + f"E{yo}: ya me atendieron; quedan {elfos_esperando} del grupo actual")
                if elfos_esperando == 0:
                    liberar_sala = True

            if liberar_sala:
                for _ in range(3):
                    multiplex_elfos.release()
        else:
            
            pass


Thread(target=santa, daemon=True).start()
for i in range(RENOS):
    Thread(target=reno, args=[i], daemon=True).start()
for i in range(ELFOS):
    Thread(target=elfo, args=[i], daemon=True).start()

while True:
    sleep(1.0)
    with mut_renos, mut_elfos:
        print(Fore.MAGENTA + f"Estado actual: renos_listos={renos_listos}/{RENOS} | elfos_esperando={elfos_esperando}/3")