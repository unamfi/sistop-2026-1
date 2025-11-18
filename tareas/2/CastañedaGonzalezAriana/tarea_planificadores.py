import random
import string
from collections import deque, namedtuple
from copy import deepcopy
import statistics

# Definimos la estructura de un proceso
Proceso = namedtuple("Proceso", ["nombre", "llegada", "rafaga"])

def generar_ronda(min_proc=4, max_proc=6, max_llegada=12, max_rafaga=7):
    """Genera una lista de procesos con tiempos de llegada y ráfagas aleatorias."""
    n = random.randint(min_proc, max_proc)
    llegadas = sorted(random.randint(0, max_llegada) for _ in range(n))
    procesos = []
    for i, l in enumerate(llegadas):
        r = random.randint(1, max_rafaga)
        procesos.append(Proceso(string.ascii_uppercase[i], l, r))
    return procesos

def calcular_metricas(procesos, tiempos_final):
    """Calcula T, E y P a partir de los tiempos de finalización."""
    T_list, E_list, P_list = [], [], []
    for p in procesos:
        F = tiempos_final[p.nombre]
        T = F - p.llegada      # Tiempo de retorno
        E = T - p.rafaga       # Tiempo de espera
        P = T / p.rafaga       # Penalización
        T_list.append(T)
        E_list.append(E)
        P_list.append(P)
    return (round(statistics.mean(T_list), 2),
            round(statistics.mean(E_list), 2),
            round(statistics.mean(P_list), 2))

# ------------------- Planificadores -------------------

def fcfs(procesos):
    """First Come First Served (primero en llegar, primero en atender)"""
    procesos = sorted(procesos, key=lambda p: p.llegada)
    tiempo, gantt, finalizados = 0, [], {}
    while len(finalizados) < len(procesos):
        listos = [p for p in procesos if p.llegada <= tiempo and p.nombre not in finalizados]
        if not listos:
            futuros = [p.llegada for p in procesos if p.nombre not in finalizados]
            if not futuros:
                break
            siguiente = min(futuros)
            gantt.extend(['-'] * (siguiente - tiempo))
            tiempo = siguiente
            continue
        actual = listos[0]
        for _ in range(actual.rafaga):
            gantt.append(actual.nombre)
            tiempo += 1
        finalizados[actual.nombre] = tiempo
    return finalizados, ''.join(gantt)

def round_robin(procesos, quantum):
    """Round Robin con quantum"""
    cola = deque()
    tiempo, gantt = 0, []
    restantes = {p.nombre: p.rafaga for p in procesos}
    finalizados, llegados = {}, set()
    while len(finalizados) < len(procesos):
        for p in procesos:
            if p.llegada <= tiempo and p.nombre not in llegados:
                cola.append(p.nombre)
                llegados.add(p.nombre)
        if cola:
            actual = cola.popleft()
            ejecutar = min(quantum, restantes[actual])
            for _ in range(ejecutar):
                for p in procesos:
                    if p.llegada == tiempo and p.nombre not in llegados:
                        cola.append(p.nombre)
                        llegados.add(p.nombre)
                gantt.append(actual)
                restantes[actual] -= 1
                tiempo += 1
            if restantes[actual] == 0:
                finalizados[actual] = tiempo
            else:
                cola.append(actual)
        else:
            gantt.append('-')
            tiempo += 1
    return finalizados, ''.join(gantt)

def spn(procesos):
    """Shortest Process Next (el que tenga menor ráfaga primero)"""
    tiempo, gantt, finalizados = 0, [], {}
    while len(finalizados) < len(procesos):
        listos = [p for p in procesos if p.llegada <= tiempo and p.nombre not in finalizados]
        if not listos:
            gantt.append('-')
            tiempo += 1
            continue
        actual = min(listos, key=lambda p: (p.rafaga, p.llegada, p.nombre))
        for _ in range(actual.rafaga):
            gantt.append(actual.nombre)
            tiempo += 1
        finalizados[actual.nombre] = tiempo
    return finalizados, ''.join(gantt)

def feedback(procesos):
    """Feedback multinivel con 3 colas: RR(1), RR(2), FCFS"""
    tiempo, gantt, finalizados = 0, [], {}
    Q0, Q1, Q2 = deque(), deque(), deque()
    restantes = {p.nombre: p.rafaga for p in procesos}
    llegados = set()
    while len(finalizados) < len(procesos):
        for p in procesos:
            if p.llegada <= tiempo and p.nombre not in llegados:
                Q0.append(p.nombre)
                llegados.add(p.nombre)

        if Q0:
            actual = Q0.popleft()
            gantt.append(actual)
            restantes[actual] -= 1
            tiempo += 1
            if restantes[actual] == 0:
                finalizados[actual] = tiempo
            else:
                Q1.append(actual)
        elif Q1:
            actual = Q1.popleft()
            for _ in range(2):
                for p in procesos:
                    if p.llegada == tiempo and p.nombre not in llegados:
                        Q0.append(p.nombre)
                        llegados.add(p.nombre)
                gantt.append(actual)
                restantes[actual] -= 1
                tiempo += 1
                if restantes[actual] == 0:
                    finalizados[actual] = tiempo
                    break
            else:
                Q2.append(actual)
        elif Q2:
            actual = Q2.popleft()
            while restantes[actual] > 0:
                for p in procesos:
                    if p.llegada == tiempo and p.nombre not in llegados:
                        Q0.append(p.nombre)
                        llegados.add(p.nombre)
                gantt.append(actual)
                restantes[actual] -= 1
                tiempo += 1
            finalizados[actual] = tiempo
        else:
            gantt.append('-')
            tiempo += 1
    return finalizados, ''.join(gantt)

def srr(procesos, quantum_base=2):
    """Selfish Round Robin: los nuevos procesos cortan al principio"""
    tiempo, gantt, finalizados = 0, [], {}
    cola = deque()
    restantes = {p.nombre: p.rafaga for p in procesos}
    llegados = set()
    while len(finalizados) < len(procesos):
        for p in procesos:
            if p.llegada == tiempo and p.nombre not in llegados:
                cola.appendleft(p.nombre)
                llegados.add(p.nombre)

        if cola:
            actual = cola.popleft()
            for _ in range(quantum_base):
                gantt.append(actual)
                restantes[actual] -= 1
                tiempo += 1
                for p in procesos:
                    if p.llegada == tiempo and p.nombre not in llegados:
                        cola.appendleft(p.nombre)
                        llegados.add(p.nombre)
                if restantes[actual] == 0:
                    finalizados[actual] = tiempo
                    break
            else:
                cola.append(actual)
        else:
            gantt.append('-')
            tiempo += 1
    return finalizados, ''.join(gantt)

# ------------------- Impresión -------------------

def imprimir_ronda(i, procesos, simulaciones):
    print(f"\n- Ronda {i + 1}:")
    info = '; '.join(f"{p.nombre}: {p.llegada}, t={p.rafaga}" for p in procesos)
    print(f"  {info}  (tot:{sum(p.rafaga for p in procesos)})")
    for nombre, (finales, gantt) in simulaciones.items():
        T, E, P = calcular_metricas(procesos, finales)
        print(f"  {nombre}: T={T}, E={E}, P={P}")
        print(f"  {gantt}")

# ------------------- Principal -------------------

def ejecutar_rondas(cantidad=5, semilla=None):
    if semilla is not None:
        random.seed(semilla)
    for i in range(cantidad):
        procesos = generar_ronda()
        simulaciones = {
            "FCFS": fcfs(deepcopy(procesos)),
            "RR1":  round_robin(deepcopy(procesos), 1),
            "RR4":  round_robin(deepcopy(procesos), 4),
            "SPN":  spn(deepcopy(procesos)),
            "FB":   feedback(deepcopy(procesos)),
            "SRR":  srr(deepcopy(procesos))
        }
        imprimir_ronda(i, procesos, simulaciones)

if __name__ == "__main__":
    print("Comparación de mecanismos de planificación de procesos\n")
    ejecutar_rondas(cantidad=5, semilla=None)

