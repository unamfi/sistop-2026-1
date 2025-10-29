#!/usr/bin/env python3
import random
from collections import deque, namedtuple

Proceso = namedtuple("Proceso", ["nombre", "llegada", "rafaga"])


def generar_procesos(semilla, n_min=4, n_max=7, max_llegada=12, max_rafaga=8):
    random.seed(semilla)
    n = random.randint(n_min, n_max)
    llegadas = sorted(random.sample(range(max_llegada + 1), n))
    return [
        Proceso(chr(65 + i), llegadas[i], random.randint(1, max_rafaga))
        for i in range(n)
    ]


def calcular_metricas(finalizacion, procesos):
    T = sum(finalizacion[p.nombre] - p.llegada for p in procesos) / len(procesos)
    E = sum(finalizacion[p.nombre] - p.llegada - p.rafaga for p in procesos) / len(
        procesos
    )
    P = sum((finalizacion[p.nombre] - p.llegada) / p.rafaga for p in procesos) / len(
        procesos
    )
    return T, E, P


def linea_tiempo(registro):
    # Colores ANSI para terminal
    colores = {
        "A": "\033[91m",
        "B": "\033[92m",
        "C": "\033[93m",
        "D": "\033[94m",
        "E": "\033[95m",
        "F": "\033[96m",
        "G": "\033[97m",
    }
    reset = "\033[0m"

    resultado = []
    for c in registro:
        if c is None:
            resultado.append("-")
        else:
            color = colores.get(c, "")
            resultado.append(f"{color}{c}{reset}")
    return "".join(resultado)


# FCFS: First-Come First-Served (el primero que llega, primero se atiende)
def fcfs(procesos):
    tiempo, registro, fin = 0, [], {}
    for p in sorted(procesos, key=lambda x: (x.llegada, x.nombre)):
        # Tiempo ocioso hasta que llegue el proceso
        registro.extend([None] * max(0, p.llegada - tiempo))
        tiempo = max(tiempo, p.llegada)
        # Ejecutar el proceso completo
        registro.extend([p.nombre] * p.rafaga)
        tiempo += p.rafaga
        fin[p.nombre] = tiempo
    return registro, fin


# SPN: Shortest Process Next (el proceso más corto primero, no preemptivo)
def spn(procesos):
    tiempo, registro, fin, terminados = 0, [], {}, set()
    while len(terminados) < len(procesos):
        # Procesos que ya llegaron y no han terminado
        listos = [
            p for p in procesos if p.llegada <= tiempo and p.nombre not in terminados
        ]
        if not listos:
            registro.append(None)
            tiempo += 1
            continue
        # Elegir el de menor ráfaga
        p = min(listos, key=lambda x: (x.rafaga, x.llegada, x.nombre))
        registro.extend([p.nombre] * p.rafaga)
        tiempo += p.rafaga
        fin[p.nombre] = tiempo
        terminados.add(p.nombre)
    return registro, fin


# RR: Round-Robin (turnos circulares con quantum fijo)
def rr(procesos, quantum=1):
    restante = {p.nombre: p.rafaga for p in procesos}
    ordenados = sorted(procesos, key=lambda x: x.llegada)
    indice, tiempo, registro, fin, cola = 0, 0, [], {}, deque()

    while len(fin) < len(procesos):
        # Agregar procesos que llegaron en este momento
        while indice < len(ordenados) and ordenados[indice].llegada <= tiempo:
            cola.append(ordenados[indice].nombre)
            indice += 1

        if not cola:
            registro.append(None)
            tiempo += 1
            continue

        actual = cola.popleft()
        ejecutar = min(quantum, restante[actual])

        # Ejecutar por quantum o lo que quede
        for _ in range(ejecutar):
            registro.append(actual)
            tiempo += 1
            # Revisar llegadas durante ejecución
            while indice < len(ordenados) and ordenados[indice].llegada <= tiempo:
                cola.append(ordenados[indice].nombre)
                indice += 1

        restante[actual] -= ejecutar
        if restante[actual] == 0:
            fin[actual] = tiempo
        else:
            cola.append(actual)  # Volver a la cola

    return registro, fin


# SRR: Shortest-Remaining Round-Robin (elige el de menor tiempo restante)
def srr(procesos, quantum=1):
    restante = {
        p.nombre: {"llegada": p.llegada, "restante": p.rafaga} for p in procesos
    }
    tiempo, registro, fin = 0, [], {}

    while len(fin) < len(procesos):
        # Procesos listos que aún no terminan
        listos = [
            n
            for n, datos in restante.items()
            if datos["llegada"] <= tiempo and datos["restante"] > 0
        ]
        if not listos:
            registro.append(None)
            tiempo += 1
            continue

        # Elegir el que tiene menor tiempo restante
        actual = min(
            listos, key=lambda n: (restante[n]["restante"], restante[n]["llegada"], n)
        )
        ejecutar = min(quantum, restante[actual]["restante"])

        registro.extend([actual] * ejecutar)
        tiempo += ejecutar
        restante[actual]["restante"] -= ejecutar

        if restante[actual]["restante"] == 0:
            fin[actual] = tiempo

    return registro, fin


# FB: Feedback (colas múltiples con quantum creciente, penaliza procesos largos)
def fb(procesos, quantums=(1, 2, 4)):
    restante = {
        p.nombre: {"llegada": p.llegada, "restante": p.rafaga} for p in procesos
    }
    ordenados = sorted(procesos, key=lambda x: x.llegada)
    indice, tiempo, registro, fin = 0, 0, [], {}
    colas = [deque() for _ in range(len(quantums) + 1)]  # Última cola es FCFS

    while len(fin) < len(procesos):
        # Nuevos procesos siempre van a la cola de mayor prioridad (0)
        while indice < len(ordenados) and ordenados[indice].llegada <= tiempo:
            colas[0].append(ordenados[indice].nombre)
            indice += 1

        # Buscar la cola no vacía de mayor prioridad
        nivel = next((i for i, q in enumerate(colas) if q), None)
        if nivel is None:
            registro.append(None)
            tiempo += 1
            continue

        actual = colas[nivel].popleft()
        # En la última cola se ejecuta hasta terminar
        ejecutar = (
            min(quantums[nivel], restante[actual]["restante"])
            if nivel < len(quantums)
            else restante[actual]["restante"]
        )

        for _ in range(ejecutar):
            registro.append(actual)
            tiempo += 1
            while indice < len(ordenados) and ordenados[indice].llegada <= tiempo:
                colas[0].append(ordenados[indice].nombre)
                indice += 1

        restante[actual]["restante"] -= ejecutar
        if restante[actual]["restante"] == 0:
            fin[actual] = tiempo
        else:
            # Baja de prioridad (siguiente cola)
            colas[min(nivel + 1, len(colas) - 1)].append(actual)

    return registro, fin


def comparar(procesos, mostrar_linea=True):
    planificadores = [
        ("FCFS", fcfs),
        ("RR1", lambda p: rr(p, 1)),
        ("RR4", lambda p: rr(p, 4)),
        ("SPN", spn),
        ("FB", fb),
        ("SRR", lambda p: srr(p, 1)),
    ]

    print(
        f"Procesos: {', '.join(f'{p.nombre}:{p.llegada},t={p.rafaga}' for p in procesos)} (total:{sum(p.rafaga for p in procesos)})"
    )

    for nombre, funcion in planificadores:
        registro, fin = funcion(procesos)
        T, E, P = calcular_metricas(fin, procesos)
        print(f"{nombre}: T={T:.2f}, E={E:.2f}, P={P:.2f}")
        if mostrar_linea:
            print(linea_tiempo(registro))
    print()


if __name__ == "__main__":
    for i in range(5):
        print(f"--- Ronda {i + 1} (semilla={100 + i}) ---")
        comparar(generar_procesos(100 + i))
