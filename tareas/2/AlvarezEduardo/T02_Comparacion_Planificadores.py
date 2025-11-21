# Tarea 02. Comparación de Planificadores
# Alvarez Salgado Eduardo Antonio
import random
from collections import deque

# Genera una lista de procesos con llegadas y ráfagas aleatorias.
def crear_procesos(num_de_procesos = 5, max_burst = 5, max_gap = 6):
    procesos_id = [chr(ord('A') + i) for i in range(num_de_procesos)] # Los procesos son identificados con las letras del abecedario.
    tiempo_llegada = 0
    procesos = []
    for nombre in procesos_id:
        dur = random.randint(1, max_burst)
        procesos.append((nombre, tiempo_llegada, dur))
        tiempo_llegada += random.randint(0, max_gap)
    return procesos

def duracion_total(procesos):
    return sum(p[2] for p in procesos)

def formato_procesos(procesos):
    partes = [f"{p[0]}: {p[1]}, t={p[2]}" for p in procesos]
    return "; ".join(partes) + f" (tot:{duracion_total(procesos)})"

# Cálculo de métricas de desempeño T, E y P a partir de los tiempos de finalización.
def calcular_metricas(procesos, fin_por_indice):
    n = len(procesos)
    lleg = [p[1] for p in procesos]
    dur  = [p[2] for p in procesos]
    T = [fin_por_indice[i] - lleg[i] for i in range(n)]
    E = [T[i] - dur[i] for i in range(n)]
    P = [T[i] / dur[i] for i in range(n)]
    return sum(T)/n, sum(E)/n, sum(P)/n

def imprimir_metricas(nombre, avgT, avgE, avgP):
    print(f"{nombre}: T={avgT:.2f}, E={avgE:.2f}, P={avgP:.2f}")

# Planificador FCFS: First Come, First Served
def FCFS(procesos):
    cola = sorted(procesos, key=lambda x: x[1])  # Se ordenan por llegada
    idx  = {p[0]: i for i, p in enumerate(procesos)}

    tiempo = 0
    salida = []
    fin = [None] * len(procesos)

    for nombre, tiempo_llegada, dur in cola:
        while tiempo < tiempo_llegada:
            salida.append('-')   # Si el proceso aún no llega, hay un "hueco".
            tiempo += 1
        for _ in range(dur):
            salida.append(nombre)
            tiempo += 1
        fin[idx[nombre]] = tiempo

    avgT, avgE, avgP = calcular_metricas(procesos, fin)
    imprimir_metricas("FCFS", avgT, avgE, avgP)
    print("".join(salida))


# Planificador Round Robin (genérico con quantum)
def RR(procesos, quantum, etiqueta):
    n = len(procesos)
    procesos_id = [p[0] for p in procesos]
    lleg    = [p[1] for p in procesos]
    restante     = [p[2] for p in procesos]
    fin     = [None] * n

    tiempo = 0
    salida = []
    ready = deque()
    liberado = [False] * n

    for i in range(n):
        if lleg[i] <= 0 and restante[i] > 0 and not liberado[i]:
            ready.append(i); liberado[i] = True

    while any(r > 0 for r in restante):
        if not ready:
            salida.append('-'); tiempo += 1 #Huecos
            for i in range(n):
                if not liberado[i] and lleg[i] <= tiempo and restante[i] > 0:
                    ready.append(i); liberado[i] = True
            continue

        i = ready.popleft()
        run = min(quantum, restante[i])

        for _ in range(run):
            salida.append(procesos_id[i])
            tiempo += 1
            restante[i] -= 1
            for j in range(n):
                if not liberado[j] and lleg[j] <= tiempo and restante[j] > 0:
                    ready.append(j); liberado[j] = True
            if restante[i] == 0: break

        if restante[i] == 0:
            fin[i] = tiempo
        else:
            ready.append(i)

    avgT, avgE, avgP = calcular_metricas(procesos, fin)
    imprimir_metricas(etiqueta, avgT, avgE, avgP)
    print("".join(salida))

# Variantes de Round Robin con quantum 1 y 4
def RR1(procesos): RR(procesos, 1, "RR1")
def RR4(procesos): RR(procesos, 4, "RR4")

# Planificador SPN: Shortest Process Nex
def SPN(procesos):
    n = len(procesos)
    procesos_id = [p[0] for p in procesos]
    lleg    = [p[1] for p in procesos]
    dur     = [p[2] for p in procesos]
    fin     = [None] * n
    hecho   = [False] * n

    tiempo = 0
    salida = []

    while not all(hecho):
        cand = [i for i in range(n) if not hecho[i] and lleg[i] <= tiempo]
        if not cand:
            salida.append('-'); tiempo += 1; continue
        i = min(cand, key=lambda k: dur[k])
        for _ in range(dur[i]):
            salida.append(procesos_id[i]); tiempo += 1
        fin[i] = tiempo; hecho[i] = True

    avgT, avgE, avgP = calcular_metricas(procesos, fin)
    imprimir_metricas("SPN", avgT, avgE, avgP)
    print("".join(salida))

# MFQ: Multilevel Feedback Queue.
def MFQ(procesos, quantums):
    n = len(procesos)
    procesos_id = [p[0] for p in procesos]
    lleg    = [p[1] for p in procesos]
    restante     = [p[2] for p in procesos]
    fin     = [None] * n

    colas = [deque() for _ in quantums]
    liberado = [False] * n

    tiempo = 0
    salida = []

    for i in range(n):
        if lleg[i] <= 0 and restante[i] > 0 and not liberado[i]:
            colas[0].append(i); liberado[i] = True

    def hay_listos(): return any(colas[l] for l in range(len(colas)))

    while any(r > 0 for r in restante):
        if not hay_listos():
            salida.append('-'); tiempo += 1
            for i in range(n):
                if not liberado[i] and lleg[i] <= tiempo and restante[i] > 0:
                    colas[0].append(i); liberado[i] = True
            continue

        nivel = next(l for l in range(len(colas)) if colas[l])
        i = colas[nivel].popleft()
        q = quantums[nivel]
        run = min(q, restante[i])

        for _ in range(run):
            salida.append(procesos_id[i]); tiempo += 1; restante[i] -= 1
            for j in range(n):
                if not liberado[j] and lleg[j] <= tiempo and restante[j] > 0:
                    colas[0].append(j); liberado[j] = True
            if restante[i] == 0: break

        if restante[i] == 0:
            fin[i] = tiempo
        else:
            siguiente = nivel + 1 if nivel + 1 < len(colas) else nivel
            colas[siguiente].append(i)

    avgT, avgE, avgP = calcular_metricas(procesos, fin)
    imprimir_metricas("MFQ", avgT, avgE, avgP)
    print("".join(salida))

# Ejecución de 5 rondas
if __name__ == "__main__":
    RONDAS = 5
    for r in range(1, RONDAS + 1):
        procesos = crear_procesos(num_de_procesos=5, max_burst=5, max_gap=6)
        print(f"\n- Ronda {r}:")
        print("  " + formato_procesos(procesos))
        FCFS(procesos)
        RR1(procesos)
        RR4(procesos)
        SPN(procesos)
        MFQ(procesos, quantums=[1, 2, 4])