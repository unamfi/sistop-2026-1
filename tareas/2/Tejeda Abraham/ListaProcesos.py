# ===============================
# Tejeda Vaca Abraham. Tarea2 
# ===============================
import random

# ===============================
# Generación de procesos
# ===============================

def Generar_Procesos(num_de_procesos=5):
    nombres_procesos = ['A', 'B', 'C', 'D', 'E', 'F', 'G']
    llegada = 0
    procesos = []
    for i in range(num_de_procesos):
        nombre = nombres_procesos[i]
        duracion = random.randint(1, 5)
        procesos.append([nombre, llegada, duracion])
        llegada += random.randint(0, max(0, duracion - 1))
    return procesos

# ===============================
# Métricas a partir de tiempos de finalización
# ===============================

def Calcular_Metricas_Desde_Final(procesos, tiempos_final):
    # procesos: [[nombre, llegada, duracion], ...]
    # tiempos_final: dict nombre -> tiempo final real
    T = []
    E = []
    P = []
    for nombre, llegada, duracion in procesos:
        fin = tiempos_final[nombre]
        t = fin - llegada
        e = t - duracion
        p = t / duracion
        T.append(t); E.append(e); P.append(p)
    averageT = sum(T) / len(T)
    averageE = sum(E) / len(E)
    averageP = sum(P) / len(P)
    return averageT, averageE, averageP

def Imprimir_Metricas(avgT, avgE, avgP, nombre_algoritmo):
    print(f'{nombre_algoritmo}: T={avgT:.2f}, E={avgE:.2f}, P={avgP:.2f}')

# ===============================
# FCFS
# ===============================

def FCFS(procesos):
    procs = sorted([p[:] for p in procesos], key=lambda x: x[1])
    tiempo = 0
    linea = []
    fin = {}
    for nombre, llegada, duracion in procs:
        if tiempo < llegada:
            linea.extend('i' * (llegada - tiempo))
            tiempo = llegada
        linea.extend(nombre * duracion)
        tiempo += duracion
        fin[nombre] = tiempo
    avgT, avgE, avgP = Calcular_Metricas_Desde_Final(procesos, fin)
    Imprimir_Metricas(avgT, avgE, avgP, 'FCFS')
    print('  ' + ''.join(linea))

# ===============================
# Round Robin genérico 
# ===============================

def RR(procesos, q, etiqueta):
    procs = sorted([p[:] for p in procesos], key=lambda x: x[1])
    n = len(procs)
    restante = {p[0]: p[2] for p in procs}
    llegada = {p[0]: p[1] for p in procs}
    orden = [p[0] for p in procs]
    tiempo = 0
    linea = []
    fin = {}
    i = 0  # índice de próximas llegadas
    lista = []  # lista lista de nombres listos

    def empujar_llegadas(t):
        nonlocal i
        while i < n and procs[i][1] <= t:
            lista.append(procs[i][0])
            i += 1

    while len(fin) < n:
        empujar_llegadas(tiempo)
        if not lista:
            # nadie listo: tiempo ocioso
            linea.append('i')
            tiempo += 1
            continue
        actual = lista.pop(0)
        correr = min(q, restante[actual])
        for _ in range(correr):
            linea.append(actual)
            tiempo += 1
            restante[actual] -= 1
            empujar_llegadas(tiempo)
            if restante[actual] == 0:
                fin[actual] = tiempo
                break
        if restante[actual] > 0:
            lista.append(actual)

    avgT, avgE, avgP = Calcular_Metricas_Desde_Final(procesos, fin)
    Imprimir_Metricas(avgT, avgE, avgP, etiqueta)
    print('  ' + ''.join(linea))

def RR1(procesos):
    RR(procesos, 1, 'RR1')

def RR4(procesos):
    RR(procesos, 4, 'RR4')

# ===============================
# SPN
# ===============================

def SPN(procesos):
    procs = [p[:] for p in procesos]
    n = len(procs)
    tiempo = 0
    linea = []
    fin = {}
    restantes = {p[0]: p[2] for p in procs}

    # ordenar por llegada para consumir en orden en la "lista de espera"
    procs.sort(key=lambda x: x[1])
    i = 0  # próximas llegadas
    listos = []  # cada item es [nombre, llegada, duracion]

    def empujar_llegadas(t):
        nonlocal i
        while i < n and procs[i][1] <= t:
            listos.append(procs[i][:])
            i += 1

    while len(fin) < n:
        empujar_llegadas(tiempo)
        if not listos:
            linea.append('i')
            tiempo += 1
            continue
        # elegir el más corto de los listos (por duración total)
        listos.sort(key=lambda x: x[2])
        nombre, llegada, duracion = listos.pop(0)
        # correr completo (no expropiativo)
        for _ in range(restantes[nombre]):
            linea.append(nombre)
            tiempo += 1
            empujar_llegadas(tiempo)
        fin[nombre] = tiempo
        restantes[nombre] = 0

    avgT, avgE, avgP = Calcular_Metricas_Desde_Final(procesos, fin)
    Imprimir_Metricas(avgT, avgE, avgP, 'SPN')
    print('  ' + ''.join(linea))

# ===============================
# Multinivel con quantums dados
# ===============================

def MULTINIVEL(procesos, quantums):
    procs = sorted([p[:] for p in procesos], key=lambda x: x[1])
    n = len(procs)
    tiempo = 0
    linea = []
    fin = {}
    restante = {p[0]: p[2] for p in procs}
    i = 0  # próximas llegadas
    colas = [[] for _ in quantums]  # listas de nombres

    def empujar_llegadas(t):
        nonlocal i
        while i < n and procs[i][1] <= t:
            colas[0].append(procs[i][0])
            i += 1

    def hay_listos():
        return any(colas[k] for k in range(len(colas)))

    while len(fin) < n:
        empujar_llegadas(tiempo)
        if not hay_listos():
            linea.append('i')
            tiempo += 1
            continue
        # primer nivel con elementos
        nivel = next(k for k in range(len(colas)) if colas[k])
        nombre = colas[nivel].pop(0)
        q = quantums[nivel]
        correr = min(q, restante[nombre])
        for _ in range(correr):
            linea.append(nombre)
            tiempo += 1
            restante[nombre] -= 1
            empujar_llegadas(tiempo)
            if restante[nombre] == 0:
                fin[nombre] = tiempo
                break
        if restante[nombre] > 0:
            if nivel + 1 < len(colas):
                colas[nivel + 1].append(nombre)
            else:
                colas[nivel].append(nombre)

    avgT, avgE, avgP = Calcular_Metricas_Desde_Final(procesos, fin)
    Imprimir_Metricas(avgT, avgE, avgP, 'MFQ')
    print('  ' + ''.join(linea))

# ===============================
# Ejecución (5 rondas)
# ===============================

if __name__ == '__main__':
    rondas = 5
    for r in range(rondas):
        cola = Generar_Procesos(5)
        total = sum(p[2] for p in cola)
        detalle = '; '.join([f'{p[0]}:{p[1]}, t={p[2]}' for p in cola])
        print(f'\nRonda {r + 1}:')
        print(f'  {detalle} (tot:{total})')
        FCFS(cola)
        RR1(cola)
        RR4(cola)
        SPN(cola)
        MULTINIVEL(cola, [1, 2, 4])