#@author: Jose Eduardo Martinez Garcia
#@date: 27/10/25

#>>>> LIBRERIAS <<<<
from random import randint as rint
from collections import deque as dq

#>>>> CLASES <<<<
class Proceso:
    def __init__(self, nomProc, Quantumllegada, duracion):
        self.nombre = nomProc
        self.llegada = Quantumllegada
        self.duracion = duracion
        self.duracionRestante = duracion

#>>>> FUNCIONES <<<<
# Genera una lista de procesos con tiempos de llegada y duraciones aleatorias        
def generarProcesos(numProc):
    procesos = []
    tiempo_actual = 0
    for i in range(numProc):
        duracion = rint(1, 7)
        procesos.append(Proceso(chr(65 + i), tiempo_actual, duracion))
        tiempo_actual += rint(1, 7)
    return procesos    

# *****PLANIFICADORES*****

#Planificador FCFS(First come first served)/FIFO(First in first out)
def fcfs(procesos):
    resultado = []
    tiempos_servido = []
    tiempo_actual = 0
    for proceso in procesos:
        if tiempo_actual < proceso.llegada:
            tiempo_actual = proceso.llegada
        tiempo_actual += proceso.duracion
        resultado.extend([proceso.nombre] * proceso.duracion)
        tiempos_servido.append(tiempo_actual)
    return resultado, tiempos_servido

#Planificador RR(Round Robin) con quantum variable 
def rr(procesos, quantum):
    resultado = []
    tiempos_servido = {}
    tiempo_actual = 0
    cola = dq([p for p in procesos 
        if p.llegada <= tiempo_actual])
    espera = dq([p for p in procesos
        if p.llegada > tiempo_actual])
    
    while cola or espera:
        if not cola and espera:
            tiempo_actual = espera[0].llegada
            cola.append(espera.popleft())
        
        proceso = cola.popleft()
        ejecutado = min(proceso.duracionRestante, quantum)
        proceso.duracionRestante -= ejecutado
        resultado.extend([proceso.nombre] * ejecutado)
        tiempo_actual += ejecutado
        
        if proceso.duracionRestante == 0:
            tiempos_servido[proceso.nombre] = tiempo_actual
        else:
            cola.append(proceso)
        while espera and espera[0].llegada <= tiempo_actual:
            cola.append(espera.popleft())
    return resultado, [tiempos_servido[p.nombre] for p in procesos]

#Planificador SPN(Shortest Process Next), el proceso mas corto siguiente
def spn(procesos):
    resultado = []
    tiempos_servido = []
    tiempo_actual = 0
    cola = sorted(procesos, key=lambda p: (p.llegada, p.duracion))
    
    while cola:
        disponibles = [p for p in cola if p.llegada <= tiempo_actual]
        if not disponibles:
            tiempo_actual = cola[0].llegada
            continue
        proceso = min(disponibles, key=lambda p: p.duracion)
        cola.remove(proceso)
        tiempo_actual += proceso.duracion
        resultado.extend([proceso.nombre] * proceso.duracion)
        tiempos_servido.append(tiempo_actual)
        
    return resultado, tiempos_servido

#*****METRICAS DE RENDIMIENTO*****
def metricas(tiempos, procesos):
    n = len(procesos)
    T = sum([t - p.llegada for t, p in zip(tiempos, procesos)])/n
    E = sum([t - p.llegada - p.duracion for t, p in zip(tiempos, procesos)])/n 
    P = sum([t / p.duracion for t, p in zip(tiempos, procesos)])/n
    return T, E, P

#*****ESQUEMA VISUAL Y RESULTADOS*****
def esquemaVisual(resultado, planificador):
    print(f"\nEsquema visual de {planificador}:\n")
    tiempo = 0
    linea = ""
    for nombre in resultado:
        linea += f"|{nombre}"
        tiempo += 1
    linea += "|"
    print(linea)

    print("\n")
    
#*****RONDAS DE EJECUCION*****
def printRonda(ronda):
    numProc = 5
    print(f"\n--- RONDA {ronda} ---")
    procesos = generarProcesos(numProc)
    for proceso in procesos:
        print(f"{proceso.nombre}: llegada={proceso.llegada}, duracion={proceso.duracion}")
    
    
    fcfs_resultado, fcfs_tiempos = fcfs(procesos[:])
    fcfs_metricas = metricas(fcfs_tiempos, procesos)
    esquemaVisual(fcfs_resultado, "FCFS")
    print(f"FCFS -> T={fcfs_metricas[0]:.2f}, E={fcfs_metricas[1]:.2f}, P={fcfs_metricas[2]:.2f}")
    
    rrQ1_resultado, rrQ1_tiempos = rr([Proceso(p.nombre, p.llegada, p.duracion) for p in procesos], quantum=1)
    rrQ1_metricas = metricas(rrQ1_tiempos, procesos)
    esquemaVisual(rrQ1_resultado, "RR (Quantum=1)")
    print(f"RR (Quantum=1) -> T={rrQ1_metricas[0]:.2f}, E={rrQ1_metricas[1]:.2f}, P={rrQ1_metricas[2]:.2f}")
    
    rrQ4_resultado, rrQ4_tiempos = rr([Proceso(p.nombre, p.llegada, p.duracion) for p in procesos], quantum=4)
    rrQ4_metricas = metricas(rrQ4_tiempos, procesos)
    esquemaVisual(rrQ4_resultado, "RR (Quantum=4)")
    print(f"RR (Quantum=4) -> T={rrQ4_metricas[0]:.2f}, E={rrQ4_metricas[1]:.2f}, P={rrQ4_metricas[2]:.2f}")
    
    spn_resultado, spn_tiempos = spn(procesos[:])
    spn_metricas = metricas(spn_tiempos, procesos)
    esquemaVisual(spn_resultado, "SPN")
    print(f"SPN -> T={spn_metricas[0]:.2f}, E={spn_metricas[1]:.2f}, P={spn_metricas[2]:.2f}")
    
#*****MAIN*****
def main():
    for ronda in range(1, 6):
        printRonda(ronda)
        
if __name__ == "__main__":
    main()