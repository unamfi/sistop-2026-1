import random

class Proceso:
    def __init__(self, nombre, llegada, tiempo):
        self.nombre = nombre
        self.llegada = llegada
        self.tiempo = tiempo
        self.tiempo_restante = tiempo
        self.tiempo_finalizacion = 0

def fcfs(procesos):
    procesos = sorted(procesos, key=lambda p: p.llegada)
    tiempo_actual = 0
    esquema = ""
    
    for p in procesos:
        if tiempo_actual < p.llegada:
            esquema += '-' * (p.llegada - tiempo_actual)
            tiempo_actual = p.llegada
        
        esquema += p.nombre * p.tiempo
        tiempo_actual += p.tiempo
        p.tiempo_finalizacion = tiempo_actual
    
    return calcular_metricas(procesos, esquema)

def rr(procesos, quantum):
    procesos_copia = []
    for p in procesos:
        nuevo_p = Proceso(p.nombre, p.llegada, p.tiempo)
        procesos_copia.append(nuevo_p)
    
    procesos_copia = sorted(procesos_copia, key=lambda p: p.llegada)
    
    cola = []
    tiempo_actual = 0
    esquema = ""
    indice = 0
    completados = 0
    
    while completados < len(procesos_copia):
        while indice < len(procesos_copia) and procesos_copia[indice].llegada <= tiempo_actual:
            cola.append(procesos_copia[indice])
            indice += 1
        
        if not cola:
            esquema += '-'
            tiempo_actual += 1
            continue
        
        p_actual = cola.pop(0)
        
        tiempo_ejec = min(quantum, p_actual.tiempo_restante)
        esquema += p_actual.nombre * tiempo_ejec
        tiempo_actual += tiempo_ejec
        p_actual.tiempo_restante -= tiempo_ejec
        
        while indice < len(procesos_copia) and procesos_copia[indice].llegada <= tiempo_actual:
            cola.append(procesos_copia[indice])
            indice += 1
        
        if p_actual.tiempo_restante > 0:
            cola.append(p_actual)
        else:
            p_actual.tiempo_finalizacion = tiempo_actual
            completados += 1
    
    return calcular_metricas(procesos_copia, esquema)

def spn(procesos):
    procesos_copia = []
    for p in procesos:
        nuevo_p = Proceso(p.nombre, p.llegada, p.tiempo)
        procesos_copia.append(nuevo_p)
    
    procesos_copia = sorted(procesos_copia, key=lambda p: p.llegada)
    
    ready = []
    tiempo_actual = 0
    esquema = ""
    indice = 0
    completados = 0
    
    while completados < len(procesos_copia):
        while indice < len(procesos_copia) and procesos_copia[indice].llegada <= tiempo_actual:
            ready.append(procesos_copia[indice])
            indice += 1
        
        if not ready:
            esquema += '-'
            tiempo_actual += 1
            continue
                
        mas_corto = ready[0]
        for p in ready:
            if p.tiempo_restante < mas_corto.tiempo_restante:
                mas_corto = p
        
        ready = [p for p in ready if p != mas_corto]
        
        esquema += mas_corto.nombre * mas_corto.tiempo_restante
        tiempo_actual += mas_corto.tiempo_restante
        mas_corto.tiempo_finalizacion = tiempo_actual
        mas_corto.tiempo_restante = 0
        completados += 1
        
        while indice < len(procesos_copia) and procesos_copia[indice].llegada <= tiempo_actual:
            ready.append(procesos_copia[indice])
            indice += 1
    
    return calcular_metricas(procesos_copia, esquema)

def calcular_metricas(procesos, esquema):
    T = sum(p.tiempo_finalizacion - p.llegada for p in procesos) / len(procesos)
    
    E = sum(p.tiempo_finalizacion - p.llegada - p.tiempo for p in procesos) / len(procesos)
    
    P = sum((p.tiempo_finalizacion - p.llegada) / p.tiempo for p in procesos) / len(procesos)
    
    return T, E, P, esquema

def generar_procesos():
    procesos = []
    nombres = "ABCDE"
    
    for i in range(5):
        nombre = nombres[i]
        llegada = random.randint(0, 10)
        tiempo = random.randint(1, 6)
        procesos.append(Proceso(nombre, llegada, tiempo))
    
    return procesos

def main():
    random.seed(32)
    
    for ronda in range(5):
        print("- Ronda " + str(ronda + 1) + ":")
        
        procesos = generar_procesos()
        print("  Procesos:", end=" ")
        for i, p in enumerate(procesos):
            if i > 0:
                print("; ", end="")
            print(p.nombre + ":" + str(p.llegada) + ",t=" + str(p.tiempo), end="")
        print()
        
        # FCFS
        T, E, P, esquema_fcfs = fcfs(procesos)
        print("  FCFS: T=" + str(round(T, 1)) + ", E=" + str(round(E, 1)) + ", P=" + str(round(P, 2)))
        
        # RR1
        T, E, P, esquema_rr1 = rr(procesos, 1)
        print("  RR1: T=" + str(round(T, 1)) + ", E=" + str(round(E, 1)) + ", P=" + str(round(P, 2)))
        
        # RR4
        T, E, P, esquema_rr4 = rr(procesos, 4)
        print("  RR4: T=" + str(round(T, 1)) + ", E=" + str(round(E, 1)) + ", P=" + str(round(P, 2)))
        
        # SPN
        T, E, P, esquema_spn = spn(procesos)
        print("  SPN: T=" + str(round(T, 1)) + ", E=" + str(round(E, 1)) + ", P=" + str(round(P, 2)))
        
        print("  Esquemas:")
        print("    FCFS: " + esquema_fcfs)
        print("    RR1:  " + esquema_rr1)
        print("    RR4:  " + esquema_rr4)
        print("    SPN:  " + esquema_spn)
        print()

if __name__ == "__main__":
    main()