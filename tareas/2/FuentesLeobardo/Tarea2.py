import random
from collections import deque

# Clase para representar un proceso

class Proceso:
    def __init__(self, nombre, llegada, duracion):
        self.nombre = nombre
        self.llegada = llegada
        self.duracion = duracion
        self.restante = duracion
        self.comienzo = None
        self.fin = None
        self.nivel = 0  # para los algoritmos de colas múltiples (FB y SRR)


# Algoritmo Primero llegado, primero servido (FCFS)

def fcfs(lista):
    tiempo = 0
    gantt = []
    for p in sorted(lista, key=lambda x: x.llegada):
        if tiempo < p.llegada:
            gantt.append("-" * (p.llegada - tiempo))
            tiempo = p.llegada
        p.comienzo = tiempo
        gantt.append(p.nombre * p.duracion)
        tiempo += p.duracion
        p.fin = tiempo
    return mostrar_resultado(lista, gantt, "FCFS")


# Algoritmo Ronda (Round Robin)

def rr(lista, quantum):
    tiempo = 0
    gantt = []
    cola = deque()
    procesos = sorted(lista, key=lambda x: x.llegada)
    i = 0

    while cola or i < len(procesos):
        while i < len(procesos) and procesos[i].llegada <= tiempo:
            cola.append(procesos[i])
            i += 1

        if not cola:
            gantt.append("-")
            tiempo += 1
            continue

        p = cola.popleft()
        if p.comienzo is None:
            p.comienzo = tiempo

        ejecutar = min(quantum, p.restante)
        gantt.append(p.nombre * ejecutar)
        tiempo += ejecutar
        p.restante -= ejecutar

        while i < len(procesos) and procesos[i].llegada <= tiempo:
            cola.append(procesos[i])
            i += 1

        if p.restante > 0:
            cola.append(p)
        else:
            p.fin = tiempo

    return mostrar_resultado(lista, gantt, f"RR{quantum}")


# Algoritmo El proceso más corto a continuación (SPN)

def spn(lista):
    tiempo = 0
    gantt = []
    pendientes = lista[:]
    listos = []

    while pendientes or listos:
        listos += [p for p in pendientes if p.llegada <= tiempo]
        pendientes = [p for p in pendientes if p.llegada > tiempo]

        if not listos:
            gantt.append("-")
            tiempo += 1
            continue

        listos.sort(key=lambda x: x.duracion)
        p = listos.pop(0)
        if p.comienzo is None:
            p.comienzo = tiempo

        gantt.append(p.nombre * p.duracion)
        tiempo += p.duracion
        p.fin = tiempo

    return mostrar_resultado(lista, gantt, "SPN")


# Algoritmo Retroalimentación multinivel (FB)

def fb(lista, niveles=3, quantum_base=1):
    tiempo = 0
    gantt = []
    procesos = sorted(lista, key=lambda x: x.llegada)
    colas = [deque() for _ in range(niveles)]
    i = 0

    while any(colas) or i < len(procesos):
        # Agregar procesos nuevos
        while i < len(procesos) and procesos[i].llegada <= tiempo:
            colas[0].append(procesos[i])
            i += 1

        # Buscar la primera cola no vacía
        nivel_actual = next((n for n in range(niveles) if colas[n]), None)
        if nivel_actual is None:
            gantt.append("-")
            tiempo += 1
            continue

        p = colas[nivel_actual].popleft()
        if p.comienzo is None:
            p.comienzo = tiempo

        quantum = quantum_base * (2 ** nivel_actual)
        ejecutar = min(quantum, p.restante)
        gantt.append(p.nombre * ejecutar)
        tiempo += ejecutar
        p.restante -= ejecutar

        # Agregar procesos que llegan mientras se ejecuta
        while i < len(procesos) and procesos[i].llegada <= tiempo:
            colas[0].append(procesos[i])
            i += 1

        if p.restante > 0:
            if nivel_actual < niveles - 1:
                p.nivel = nivel_actual + 1
                colas[p.nivel].append(p)
            else:
                colas[nivel_actual].append(p)
        else:
            p.fin = tiempo

    return mostrar_resultado(lista, gantt, "FB")


# Algoritmo Ronda egoísta (SRR)

def srr(lista, quantum=2):
    tiempo = 0
    gantt = []
    procesos = sorted(lista, key=lambda x: x.llegada)
    cola = deque()
    i = 0

    while cola or i < len(procesos):
        while i < len(procesos) and procesos[i].llegada <= tiempo:
            procesos[i].nivel = 0  # prioridad inicial
            cola.append(procesos[i])
            i += 1

        if not cola:
            gantt.append("-")
            tiempo += 1
            continue

        # Ordenar por prioridad (nivel más bajo = más egoísta)
        cola = deque(sorted(list(cola), key=lambda p: p.nivel))
        p = cola.popleft()
        if p.comienzo is None:
            p.comienzo = tiempo

        ejecutar = min(quantum, p.restante)
        gantt.append(p.nombre * ejecutar)
        tiempo += ejecutar
        p.restante -= ejecutar

        # Aumentar el “egoísmo” de los demás
        for q in cola:
            q.nivel += 1

        while i < len(procesos) and procesos[i].llegada <= tiempo:
            procesos[i].nivel = 0
            cola.append(procesos[i])
            i += 1

        if p.restante > 0:
            cola.append(p)
        else:
            p.fin = tiempo

    return mostrar_resultado(lista, gantt, "SRR")


# Función para calcular métricas y mostrar resultados

def mostrar_resultado(lista, gantt, nombre):
    T, E, P = [], [], []

    for p in lista:
        t_total = p.fin - p.llegada
        espera = t_total - p.duracion
        T.append(t_total)
        E.append(espera)
        P.append(t_total / p.duracion)

    print(f"  {nombre}: T={sum(T)/len(T):.1f}, E={sum(E)/len(E):.1f}, P={sum(P)/len(P):.2f}")
    print("   ", "".join(gantt))
    return {"algoritmo": nombre, "T": T, "E": E, "P": P}


# Genera una lista de procesos aleatorios

def generar_procesos():
    n = 5
    llegada = 0
    lista = []
    for i in range(n):
        llegada += random.randint(0, 4)  # se permiten huecos
        duracion = random.randint(2, 6)
        lista.append(Proceso(chr(65 + i), llegada, duracion))
    return lista


def main():
    random.seed()
    print("Simulación de algoritmos de planificación\n")

    for ronda in range(1, 6):
        print(f"- Ronda {ronda}:")
        procesos = generar_procesos()
        texto = "; ".join([f"{p.nombre}: {p.llegada}, t={p.duracion}" for p in procesos])
        total = sum(p.duracion for p in procesos)
        print(f"  {texto}  (tot:{total})")

        # Ejecutar los algoritmos con copias nuevas
        fcfs([Proceso(p.nombre, p.llegada, p.duracion) for p in procesos])
        rr([Proceso(p.nombre, p.llegada, p.duracion) for p in procesos], 1)
        rr([Proceso(p.nombre, p.llegada, p.duracion) for p in procesos], 4)
        spn([Proceso(p.nombre, p.llegada, p.duracion) for p in procesos])
        fb([Proceso(p.nombre, p.llegada, p.duracion) for p in procesos])
        srr([Proceso(p.nombre, p.llegada, p.duracion) for p in procesos])

        print()  # separación entre rondas


if __name__ == "__main__":
    main()
