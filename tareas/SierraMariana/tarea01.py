#!/usr/bin/python3

import random
import threading
import time

# Variables compartidas
num_hackers = 0
num_serfs = 0
cruces_realizados = 0
retirados = 0  # Contador de desarrolladores que no pudieron cruzar
mutex_cruces = threading.Lock()

# Semáforos para sincronización
mutex = threading.Semaphore(1)
hackers_queue = threading.Semaphore(0)
serfs_queue = threading.Semaphore(0)
balsa_lista = threading.Semaphore(0)

# Configuración
global TOTAL_DESARROLLADORES
CAPACIDAD_BALSA = 4
TIEMPO_CRUCE = 2
DELAY_VISUAL = 0.1  # Delay para mejorar legibilidad
TIMEOUT_ESPERA = 3  # Timeout para detectar deadlock


def imprimir_estado():
    print(f"[Estado] Esperando: {num_hackers} hackers, {num_serfs} serfs")


def hacker(id):
    """Proceso de un hacker que quiere cruzar el río"""
    global num_hackers, num_serfs, cruces_realizados, retirados

    # Simulamos la llegada aleatoria
    time.sleep(random.uniform(0.1, 1.0))

    print(f"Hacker {id} llega a la orilla")
    time.sleep(DELAY_VISUAL)

    mutex.acquire()
    num_hackers += 1
    imprimir_estado()
    time.sleep(DELAY_VISUAL)

    # Decidir si puede formar un grupo
    es_capitan = False
    tipo_grupo = None

    # Opción 1: 4 hackers
    if num_hackers >= 4:
        es_capitan = True
        tipo_grupo = "[4 Hackers]"
        num_hackers -= 4
        # Despertar a 3 hackers más
        for _ in range(3):
            hackers_queue.release()

    # Opción 2: 2 hackers y 2 serfs (grupo mixto)
    elif num_hackers >= 2 and num_serfs >= 2:
        es_capitan = True
        tipo_grupo = "[2 Hackers y 2 Serfs]"
        num_hackers -= 2
        num_serfs -= 2
        # Despertar a 1 hacker y 2 serfs
        hackers_queue.release()
        serfs_queue.release()
        serfs_queue.release()

    if es_capitan:
        print(f"Hacker {id} forma grupo tipo {tipo_grupo}")
        time.sleep(DELAY_VISUAL)
        mutex.release()

        # Esperar a que todos aborden
        for _ in range(3):
            balsa_lista.acquire()

        # ¡Zarpar!
        with mutex_cruces:
            cruces_realizados += 1
            num_cruce = cruces_realizados

        print(f"\n{'=' * 60}")
        print(f"CRUCE #{num_cruce} - Tipo: {tipo_grupo} - VIAJANDO")
        print(f"{'=' * 60}\n")
        time.sleep(DELAY_VISUAL)

        time.sleep(TIEMPO_CRUCE)

        print(f"Cruce #{num_cruce} completado exitosamente\n")
        time.sleep(DELAY_VISUAL)
    else:
        # Esperar a que se forme un grupo
        mutex.release()
        print(f"Hacker {id} espera en la cola...")
        time.sleep(DELAY_VISUAL)

        # Intentar adquirir con timeout
        if hackers_queue.acquire(timeout=TIMEOUT_ESPERA):
            # Notificar que estoy listo para abordar
            balsa_lista.release()
            print(f"Hacker {id} aborda la balsa")
            time.sleep(DELAY_VISUAL)
        else:
            # Timeout alcanzado - no se formó grupo
            mutex.acquire()
            num_hackers -= 1  # Ya no estoy esperando
            retirados += 1  # Contar como retirado
            print(f"Hacker {id} se retira (timeout - no hay grupo posible)")
            imprimir_estado()
            mutex.release()


def serf(id):
    """Proceso de un serf que quiere cruzar el río"""
    global num_hackers, num_serfs, cruces_realizados, retirados

    # Simular llegada aleatoria
    time.sleep(random.uniform(0.1, 1.0))

    print(f"Serf {id} llega a la orilla")
    time.sleep(DELAY_VISUAL)

    mutex.acquire()
    num_serfs += 1
    imprimir_estado()
    time.sleep(DELAY_VISUAL)

    # Decidir si puede formar un grupo
    es_capitan = False
    tipo_grupo = None

    # Opción 1: 4 serfs
    if num_serfs >= 4:
        es_capitan = True
        tipo_grupo = "[4 Serfs]"
        num_serfs -= 4
        # Despertar a 3 serfs más
        for _ in range(3):
            serfs_queue.release()

    # Opción 2: 2 hackers y 2 serfs (grupo mixto)
    elif num_hackers >= 2 and num_serfs >= 2:
        es_capitan = True
        tipo_grupo = "[2 Hackers y 2 Serfs]"
        num_hackers -= 2
        num_serfs -= 2
        # Despertar a 2 hackers y 1 serf
        hackers_queue.release()
        hackers_queue.release()
        serfs_queue.release()

    if es_capitan:
        print(f"Serf {id} forma grupo tipo {tipo_grupo}")
        time.sleep(DELAY_VISUAL)
        mutex.release()

        # Esperar a que todos aborden
        for _ in range(3):
            balsa_lista.acquire()

        # ¡Zarpar!
        with mutex_cruces:
            cruces_realizados += 1
            num_cruce = cruces_realizados

        print(f"\n{'=' * 60}")
        print(f"CRUCE #{num_cruce} - Tipo: {tipo_grupo} - VIAJANDO")
        print(f"{'=' * 60}\n")
        time.sleep(DELAY_VISUAL)

        time.sleep(TIEMPO_CRUCE)

        print(f"Cruce #{num_cruce} completado exitosamente\n")
        time.sleep(DELAY_VISUAL)

    else:
        # Esperar a que se forme un grupo
        mutex.release()
        print(f"Serf {id} espera en la cola...")
        time.sleep(DELAY_VISUAL)

        # Intentar adquirir con timeout
        if serfs_queue.acquire(timeout=TIMEOUT_ESPERA):
            # Notificar que estoy listo para abordar
            balsa_lista.release()
            print(f"Serf {id} aborda la balsa")
            time.sleep(DELAY_VISUAL)
        else:
            # Timeout alcanzado - no se formó grupo
            mutex.acquire()
            num_serfs -= 1  # Ya no estoy esperando
            retirados += 1  # Contar como retirado
            print(f"Serf {id} se retira (timeout - no hay grupo posible)")
            imprimir_estado()
            mutex.release()


def main():
    print(f"\n{'=' * 60}")
    print(" SIMULACION: EL CRUCE DEL RIO ")
    print(f"{'=' * 60}\n")
    print("Reglas:")
    print("  - La balsa necesita exactamente 4 personas (Sí no, la balsa se volca)")
    print(
        "  - Suponemos que si son menos de 4 hay personas en la balsa, no podrían cruzar"
    )
    print(
        "  - Combinaciones validas: [4 Hakers y 0 Serfs, 0 Hackers y 4 Serfs, o 2 Hackers y 2 Serfs]\n"
    )
    print("Condición del usuario:")
    TOTAL_DESARROLLADORES = int(
        input(
            "Conociendo las reglas ingrese el número de desarrolladores que desea invitar: "
        )
    )
    print(f"\n{'-' * 60}\n")

    threads = []

    # Creamos a los desarrolladores de forma random
    for i in range(TOTAL_DESARROLLADORES):
        if random.random() < 0.5:
            t = threading.Thread(target=hacker, args=(i,), name=f"Hacker-{i}")
        else:
            t = threading.Thread(target=serf, args=(i,), name=f"Serf-{i}")
        threads.append(t)
        t.start()

    # Esperar a que todos terminen
    for t in threads:
        t.join()

    # Estadísticas finales
    print(f"\n{'=' * 60}")
    print("RESULTADO FINAL")
    print(f"{'=' * 60}")
    print(f"Total de desarrolladores invitados: {TOTAL_DESARROLLADORES}")
    print(f"Viajes realizados: {cruces_realizados}")
    print(f"Cantidad de desarrolladores que cruzaron: {cruces_realizados * 4}")
    print(f"Cantidad de desarrolladores que NO cruzaron: {retirados}\n")

    # Comprobación de la cantidad total de desarrolladores que cruzaron

    if retirados > 0:
        print(f"\n{retirados} desarrollador(es) no pudieron cruzar")
        print(f"(No se formaron grupos validos con los restantes)")
    else:
        print(f"\nTodos cruzaron exitosamente!")

    print(f"\n{'=' * 60}\n")


if __name__ == "__main__":
    main()
