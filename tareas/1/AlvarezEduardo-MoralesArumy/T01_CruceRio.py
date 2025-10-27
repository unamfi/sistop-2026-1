# Problema de sincronización. El cruce del río 
# Alvarez Salgado Eduardo Antonio y Morales Castillo Arumy Lizeth

import threading
import time
import random

mutex = threading.Semaphore(1)
sem_hackers = threading.Semaphore(0)
sem_serfs = threading.Semaphore(0)

num_abordando = 0
num_hackers = 0
num_serfs = 0

# Contadores del grupo actual
hackers_abordando = 0
serfs_abordando = 0

def desarrollador_llega(tipo):
    global num_hackers, num_serfs, num_abordando, hackers_abordando, serfs_abordando

    mutex.acquire()
    if tipo == "hacker":
        num_hackers += 1
        print("Hacker espera para abordar.")
    else:
        num_serfs += 1
        print("Serf espera para abordar.")

    # Combinaciones permitidas
    if num_hackers == 4:
        for _ in range(4):
            sem_hackers.release()
        num_hackers = 0
        hackers_abordando, serfs_abordando = 4, 0
        print('---- 4 Hackers están listos para abordar. ----')
    elif num_serfs == 4:
        for _ in range(4):
            sem_serfs.release()
        num_serfs = 0
        hackers_abordando, serfs_abordando = 0, 4
        print('---- 4 Serfs están listos para abordar. ----')
    elif num_hackers == 2 and num_serfs == 2:
        sem_hackers.release(); sem_hackers.release()
        sem_serfs.release(); sem_serfs.release()
        num_hackers = 0
        num_serfs = 0
        hackers_abordando, serfs_abordando = 2, 2
        print('---- 2 Hackers y 2 Serfs están listos para abordar. ----')
    else:
        mutex.release()

    # Abordaje
    if tipo == "hacker":
        sem_hackers.acquire()
        print("Hacker aborda la balsa.")
    else:
        sem_serfs.acquire()
        print("Serf aborda la balsa.")

    num_abordando += 1
    if num_abordando == 4:
        print("---- 4 desarrolladores a bordo. ¡Comienza el viaje! ----")
        time.sleep(1)
        print(f"---- La balsa logró curzar el río con "
              f"{hackers_abordando} Hackers y {serfs_abordando} Serfs. ----")
        num_abordando = 0
        hackers_abordando = 0
        serfs_abordando = 0
        mutex.release()


# --- Generación de desarrolladores aleatorios ---
while True:
    if random.randint(0, 1) == 0:
        threading.Thread(target=desarrollador_llega, args=("hacker",)).start()
    else:
        threading.Thread(target=desarrollador_llega, args=("serf",)).start()

    time.sleep(0.3)
