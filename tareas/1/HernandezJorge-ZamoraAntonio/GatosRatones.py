import threading
import time
import random
from colorama import Fore, init

init()

# Parámetros iniciales (se pueden modificar de acuerdo al número de gatos, ratones y platos deseados)
NUM_GATOS = 5
NUM_RATONES = 15
NUM_PLATOS = 5

print(Fore.YELLOW + f'HAY {NUM_GATOS} GATOS 🐱')
print(Fore.CYAN + f'HAY {NUM_RATONES} RATONES 🐭')
print(Fore.WHITE + f'HAY {NUM_PLATOS} PLATOS 🍽️\n')

# Semáforo y mutex 
platos = threading.Semaphore(NUM_PLATOS)
mutex = threading.Lock()

# Contadores de gatos y ratones comiendo
gatos_comiendo = 0
ratones_comiendo = 0

def gato(id):
    global gatos_comiendo, ratones_comiendo

    while True:
        time.sleep(random.uniform(1, 2))  # Llega un gato a intentar comer en un plato

        platos.acquire()
        with mutex:
            gatos_comiendo += 1
        print(Fore.YELLOW + f'🐱 Gato {id} está comiendo. [Gatos comiendo: {gatos_comiendo}]')

        # Gato come un rato
        time.sleep(random.uniform(1, 2))

        with mutex:
            gatos_comiendo -= 1
        platos.release()

        print(Fore.YELLOW + f'🐱 Gato {id} terminó de comer.')
        time.sleep(random.uniform(1.5, 2))  # El Gato {id} termina de comer y descansa un poco

def raton(id):
    global gatos_comiendo, ratones_comiendo

    while True:
        time.sleep(random.uniform(0.5, 1))  # Llega un ratón a intentar comer en un plato

        with mutex:
            if gatos_comiendo > 0: # Si hay al menos un gato comiendo, se come al ratón para mantener las apariencias
                print(Fore.RED + f'💀🐭 Ratón {id} intentó comer y fue devorado por un gato 💀')
                return  # El ratón muere y termina el hilo

        # Si no hay gatos comiendo, puede comer con total tranquilidad
        platos.acquire()
        with mutex:
            ratones_comiendo += 1
        print(Fore.CYAN + f'🐭 Ratón {id} está comiendo. [Ratones comiendo: {ratones_comiendo}]')

        # Ratón come un rato
        time.sleep(random.uniform(0.8, 1.5))

        with mutex:
            ratones_comiendo -= 1
        platos.release()
        print(Fore.CYAN + f'🐭 Ratón {id} terminó de comer.')

        time.sleep(random.uniform(0.5, 1))  # El Ratón {id} termina de comer y descansa un poco

# Crear hilos
hilos = []
for i in range(NUM_GATOS):
    hilo = threading.Thread(target=gato, args=(i + 1,))
    hilos.append(hilo)
    hilo.start()

for i in range(NUM_RATONES):
    hilo = threading.Thread(target=raton, args=(i + 1,))
    hilos.append(hilo)
    hilo.start()

# Mantener programa activo
for hilo in hilos:
    hilo.join()

