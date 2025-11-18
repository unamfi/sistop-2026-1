import random


# Planificacion de procesos utilizados: FCFS, RR, SPN


# Función para generar una lista de procesos aleatorios
def generar_procesos():
    procesos = []
    letras = ['A', 'B', 'C', 'D', 'E']
    tiempo_actual = 0
    for letra in letras:
        llegada = tiempo_actual
        duracion = random.randint(2, 6)
        procesos.append((letra, llegada, duracion))
        tiempo_actual += random.randint(0, 3)  
    return procesos


# FCFS (First Come, First Serve)
def fcfs(procesos):
    tiempo = 0
    ejecucion = ""
    tiempos_espera = []
    tiempos_retorno = []

    for nombre, llegada, duracion in procesos:
        if tiempo < llegada:
            tiempo = llegada 
        espera = tiempo - llegada
        tiempos_espera.append(espera)
        tiempo += duracion
        retorno = tiempo - llegada
        tiempos_retorno.append(retorno)
        ejecucion += nombre * duracion

    T = sum(tiempos_retorno) / len(procesos)
    E = sum(tiempos_espera) / len(procesos)
    P = T / (T - E)
    return ejecucion, T, E, P

# Round Robin (RR)
def rr(procesos, quantum):
    cola = []
    tiempo = 0
    ejecucion = ""
    tiempos_restantes = {p[0]: p[2] for p in procesos}
    tiempos_final = {}
    tiempos_espera = {p[0]: 0 for p in procesos}
    procesos_restantes = list(procesos)

    while procesos_restantes or cola:
        # agregamos a la cola los procesos que ya llegaron
        for p in list(procesos_restantes):
            if p[1] <= tiempo:
                cola.append(p)
                procesos_restantes.remove(p)

        if cola:
            proceso = cola.pop(0)
            nombre = proceso[0]
            duracion = min(quantum, tiempos_restantes[nombre])
            ejecucion += nombre * duracion
            tiempo += duracion
            tiempos_restantes[nombre] -= duracion

            # agregamos nuevos procesos que llegaron mientras tanto
            for p in list(procesos_restantes):
                if p[1] <= tiempo and p not in cola:
                    cola.append(p)
                    procesos_restantes.remove(p)

            # si el proceso no ha terminado, se vuelve a poner en la cola
            if tiempos_restantes[nombre] > 0:
                cola.append((nombre, proceso[1], proceso[2]))
            else:
                tiempos_final[nombre] = tiempo
        else:
            tiempo += 1  # si no hay nada que ejecutar, avanzar tiempo

    T = sum(tiempos_final[p[0]] - p[1] for p in procesos) / len(procesos)
    E = sum(tiempos_final[p[0]] - p[1] - p[2] for p in procesos) / len(procesos)
    P = T / (T - E)
    return ejecucion, T, E, P

# SPN (Shortest Process Next)
def spn(procesos):
    tiempo = 0
    ejecucion = ""
    completados = []
    lista_espera = []

    while len(completados) < len(procesos):
        # agregamos procesos que ya llegaron
        for p in procesos:
            if p not in completados and p not in lista_espera and p[1] <= tiempo:
                lista_espera.append(p)
        # si no hay procesos listos, avanzar tiempo
        if not lista_espera:
            tiempo += 1
            continue
        # seleccionar el de menor duración
        lista_espera.sort(key=lambda x: x[2])
        proceso = lista_espera.pop(0)
        nombre, llegada, duracion = proceso
        ejecucion += nombre * duracion
        tiempo += duracion
        completados.append(proceso)

    tiempos_final = {p[0]: 0 for p in procesos}
    tiempo_total = 0
    for p in completados:
        tiempos_final[p[0]] = tiempo_total + p[2]
        tiempo_total += p[2]
    T = sum(tiempos_final[p[0]] - p[1] for p in procesos) / len(procesos)
    E = sum(tiempos_final[p[0]] - p[1] - p[2] for p in procesos) / len(procesos)
    P = T / (T - E)
    return ejecucion, T, E, P


# main
for ronda in range(1, 6):  
    print(f"\n--- Ronda {ronda} ---")
    procesos = generar_procesos()
    print("Procesos generados (nombre, llegada, duración):")
    for p in procesos:
        print(p)
    print()

    # FCFS
    ejec_fcfs, T, E, P = fcfs(procesos)
    print(f"FCFS:  T={T:.2f}, E={E:.2f}, P={P:.2f}")
    print(" ", ejec_fcfs)

    # RR con quantum = 1
    ejec_rr1, T, E, P = rr(procesos, 1)
    print(f"RR1:   T={T:.2f}, E={E:.2f}, P={P:.2f}")
    print(" ", ejec_rr1)

    # RR con quantum = 4
    ejec_rr4, T, E, P = rr(procesos, 4)
    print(f"RR4:   T={T:.2f}, E={E:.2f}, P={P:.2f}")
    print(" ", ejec_rr4)

    # SPN
    ejec_spn, T, E, P = spn(procesos)
    print(f"SPN:   T={T:.2f}, E={E:.2f}, P={P:.2f}")
    print(" ", ejec_spn)
