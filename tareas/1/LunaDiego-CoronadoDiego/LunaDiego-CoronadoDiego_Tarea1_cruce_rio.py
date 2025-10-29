"""
Simulación del problema de sincronización:
------------------------------------------
'El cruce del río' con desarrolladores de Linux (hackers)
y de Microsoft (serfs). Se usa sincronización con semáforos
y se añaden colores en consola para distinguirlos.

Reglas:
- En la balsa caben exactamente 4 personas.
- No puede haber 3 hackers y 1 serf (ni viceversa).
- Pueden cruzar:
    * 4 hackers
    * 4 serfs
    * 2 hackers + 2 serfs
- Los demás deben esperar el siguiente viaje para subir a la balsa.
"""


import threading
import random
import time
from colorama import Fore, Style, init

# Inicializar colorama
init(autoreset=True)

# Variables globales compartidas
hackers = 0
serfs = 0

# Semáforos
mutex = threading.Semaphore(1)   # Control de acceso a las variables compartidas
balsa = threading.Semaphore(0)   # Control de los que suben a la balsa

# Capacidad de la balsa
PERSONAS_POR_BALSA = 4

def persona_llega(id_persona, tipo):
    """
    Función que simula la llegada de una persona (hacker o serf) al río.
    Evalúa si hay una combinación válida para que la balsa cruce.
    """

    global hackers, serfs

    # Controlar acceso concurrente
    with mutex:
        if tipo == "hacker":
            hackers += 1
            print(Fore.CYAN + f"Hacker {id_persona} espera para subir a la balsa" + Style.RESET_ALL)
        else:
            serfs += 1
            print(Fore.YELLOW + f"Serf {id_persona} espera para subir a la balsa" + Style.RESET_ALL)

        # Combinaciones válidas para zarpar
        if hackers >= 2 and serfs >= 2:
            print(Fore.GREEN + "🚤 Se reúnen 2 hackers y 2 serfs, suben a la balsa y viajan 🌊\n" + Style.RESET_ALL)
            for _ in range(PERSONAS_POR_BALSA):
                balsa.release()
            hackers -= 2
            serfs -= 2

        elif hackers >= 4:
            print(Fore.CYAN + "🚤 Se reúnen 4 hackers, suben a la balsa y viajan 🌊\n" + Style.RESET_ALL)
            for _ in range(PERSONAS_POR_BALSA):
                balsa.release()
            hackers -= 4

        elif serfs >= 4:
            print(Fore.YELLOW + "🚤 Se reúnen 4 serfs, suben a la balsa y viajan 🌊\n" + Style.RESET_ALL)
            for _ in range(PERSONAS_POR_BALSA):
                balsa.release()
            serfs -= 4

    # Esperar turno para subir (si no se liberó balsa, queda esperando)
    balsa.acquire()


def main():
    """
    Crea los hilos que simulan la llegada aleatoria de hackers y serfs.
    """
    threads = []

    print(Fore.BLUE + Style.BRIGHT + "\n=== 🌊 Simulación del Cruce del Río 🌊 ===\n" + Style.RESET_ALL)

    # Crear y lanzar hilos (serfs o hackers llegando)
    for i in range(1, 101):
        tipo = random.choice(["hacker", "serf"])
        t = threading.Thread(target=persona_llega, args=(i, tipo))
        threads.append(t)
        t.start()
        time.sleep(random.uniform(1, 1))  # Llegadas con retardo aleatorio

    # Esperar a que todos los hilos terminen
    for t in threads:
        t.join()

    print(Fore.MAGENTA + "\n🏁 Se acabaron los viajes 😢.\n" + Style.RESET_ALL)


if __name__ == "__main__":
    main()
