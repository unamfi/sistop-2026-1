# Implementación del problema del "Servidor Web" con patrón Jefe-Trabajador
from threading import Thread, Semaphore
from time import sleep
from random import random, randint
from colorama import Fore, init

init()
NUM_TRABAJADORES = 5
peticiones_pendientes = []
mutex_peticiones = Semaphore(1)
sem_hay_peticiones = Semaphore(0)
sem_trabajador_disponible = Semaphore(NUM_TRABAJADORES)
contador_peticiones = 0

def trabajador(id):
    """Hilo trabajador que procesa peticiones"""
    global peticiones_pendientes
    print(Fore.CYAN + f'T{id}: Iniciando')
    
    while True:
        # Dormir esperando peticiones
        sem_hay_peticiones.acquire()
        
        # Tomar una petición de la lista
        with mutex_peticiones:
            if peticiones_pendientes:
                peticion = peticiones_pendientes.pop(0)
            else:
                continue
        
        # Procesar la petición
        print(Fore.GREEN + f'T{id}: Procesando petición {peticion["id"]} - {peticion["tipo"]} {peticion["recurso"]}')
        sleep(peticion["tiempo"])
        print(Fore.GREEN + f'T{id}: Terminé petición {peticion["id"]}')
        
        # Indicar que estoy disponible nuevamente
        sem_trabajador_disponible.release()

def jefe():
    """Proceso jefe que recibe conexiones y las asigna"""
    global contador_peticiones
    print(Fore.MAGENTA + f'JEFE: Servidor iniciado con {NUM_TRABAJADORES} trabajadores')
    
    while True:
        # Simular llegada de nueva conexión
        sleep(random() * 2)
        
        # Esperar a que haya un trabajador disponible
        sem_trabajador_disponible.acquire()
        
        # Crear petición
        contador_peticiones += 1
        tipos = ['GET', 'POST', 'PUT', 'DELETE']
        recursos = ['/index.html', '/api/datos', '/imagen.jpg', '/style.css']
        
        peticion = {
            'id': contador_peticiones,
            'tipo': tipos[randint(0, 3)],
            'recurso': recursos[randint(0, 3)],
            'tiempo': random() * 2
        }
        
        print(Fore.MAGENTA + f'JEFE: Nueva conexión #{contador_peticiones} - {peticion["tipo"]} {peticion["recurso"]}')
        
        # Agregar petición a la lista compartida
        with mutex_peticiones:
            peticiones_pendientes.append(peticion)
        
        # Despertar a un trabajador
        sem_hay_peticiones.release()
        print(Fore.MAGENTA + f'JEFE: Asignando petición #{contador_peticiones} a trabajador')

# Iniciar trabajadores
print(Fore.WHITE + f'Iniciando servidor web con {NUM_TRABAJADORES} trabajadores')
for i in range(NUM_TRABAJADORES):
    Thread(target=trabajador, args=[i]).start()

# Iniciar jefe
Thread(target=jefe).start()

# Mantener el programa corriendo
while True:
    sleep(5)
    with mutex_peticiones:
        print(Fore.YELLOW + f'Estado: {len(peticiones_pendientes)} peticiones en cola')