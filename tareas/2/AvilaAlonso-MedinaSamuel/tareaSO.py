# Medina Villa Samuel-----320249538
# Ávila Martínez Alonso-----320237988
# Tarea 2: Ejercicio de comparación de planificadores


import random

# Estructura para guardar info de cada proceso
class Proceso:
    def __init__(self, nombre, llegada, rafaga):
        self.nombre = nombre
        self.llegada = llegada  
        self.rafaga = rafaga  
        self.falta = rafaga  # cuanto le queda
        self.fin = 0  
        self.espera = 0 
        self.retorno = 0 

# Genera procesos random para probar
def crear_procesos(num):
    lista = []
    for i in range(num):
        nom = chr(65 + i)  # A, B, C...
        llega = random.randint(0, 12)  
        dur = random.randint(2, 7)   
        lista.append(Proceso(nom, llega, dur))
    return lista

# Clona la lista para no modificar la original
def duplicar_procesos(procesos):
    nueva_lista = []
    for p in procesos:
        nueva_lista.append(Proceso(p.nombre, p.llegada, p.rafaga))
    return nueva_lista

# FCFS - primero en llegar primero en ser atendido
def fcfs(procesos):
    procesos.sort(key=lambda p: p.llegada)
    t = 0  # tiempo del sistema
    resultado = ""
    
    for p in procesos:
        # esperar si el proceso no ha llegado
        if t < p.llegada:
            t = p.llegada
        
        resultado += p.nombre * p.rafaga
        t += p.rafaga
        
        # calcular metricas
        p.fin = t
        p.retorno = p.fin - p.llegada
        p.espera = p.retorno - p.rafaga
    
    return procesos, resultado

# SPN - ejecuta primero el mas corto de los disponibles
def spn(procesos):
    procesos.sort(key=lambda p: p.llegada)
    listos = []  # procesos que ya llegaron
    finalizados = []
    t = 0
    resultado = ""

    while len(finalizados) < len(procesos):
        # meter a listos los que ya llegaron
        i = 0
        while i < len(procesos):
            if procesos[i].llegada <= t and procesos[i] not in finalizados:
                if procesos[i] not in listos:
                    listos.append(procesos[i])
            i += 1
        
        if len(listos) > 0:
            # buscar el mas corto
            mas_corto = listos[0]
            for proceso in listos:
                if proceso.rafaga < mas_corto.rafaga:
                    mas_corto = proceso
            
            listos.remove(mas_corto)
            resultado += mas_corto.nombre * mas_corto.rafaga
            t += mas_corto.rafaga
            
            mas_corto.fin = t
            mas_corto.retorno = mas_corto.fin - mas_corto.llegada
            mas_corto.espera = mas_corto.retorno - mas_corto.rafaga
            finalizados.append(mas_corto)
        else:
            # nadie listo, avanzar tiempo
            t += 1
    
    return finalizados, resultado

# Round Robin - cada proceso ejecuta su turno de quantum
def round_robin(procesos, quantum):
    procesos.sort(key=lambda p: p.llegada)
    
    # copiar para trabajar con tiempo restante
    cola = []
    for p in procesos:
        cola.append(p)
    
    t = 0
    finalizados = []
    resultado = ""
    
    while len(cola) > 0:
        actual = cola.pop(0)
        
        # si no ha llegado, esperar
        if actual.llegada > t:
            t = actual.llegada
        
        # ejecutar quantum o lo que quede
        if actual.falta > quantum:
            resultado += actual.nombre * quantum
            t += quantum
            actual.falta -= quantum
            cola.append(actual)  # regresa a la cola
        else:
            # termina
            resultado += actual.nombre * actual.falta
            t += actual.falta
            actual.falta = 0
            
            actual.fin = t
            actual.retorno = actual.fin - actual.llegada
            actual.espera = actual.retorno - actual.rafaga
            finalizados.append(actual)
    
    return finalizados, resultado

# Obtiene promedios de las metricas
def sacar_promedios(procesos):
    suma_T = 0
    suma_E = 0
    suma_P = 0
    
    for p in procesos:
        suma_T += p.retorno
        suma_E += p.espera
        suma_P += p.retorno / p.rafaga
    
    cantidad = len(procesos)
    return suma_T/cantidad, suma_E/cantidad, suma_P/cantidad

def main():
    rondas = 5  
    num_procesos = 5 

    for r in range(1, rondas + 1):
        print(f"\n--- Ronda {r} ---")

        # crear procesos random
        procesos = crear_procesos(num_procesos)
        
        # ordenar para mostrar
        procesos.sort(key=lambda x: x.llegada)

        # mostrar info de procesos
        info = []
        for p in procesos:
            info.append(f"{p.nombre}: {p.llegada}, t={p.rafaga}")
        
        print("; ".join(info))

        # probar algoritmos
        
        # FCFS
        res_fcfs, sec_fcfs = fcfs(duplicar_procesos(procesos))
        t, e, p = sacar_promedios(res_fcfs)
        print(f"FCFS: T={t:.2f}, E={e:.2f}, P={p:.2f}")
        print(sec_fcfs)

        # SPN
        res_spn, sec_spn = spn(duplicar_procesos(procesos))
        t, e, p = sacar_promedios(res_spn)
        print(f"SPN: T={t:.2f}, E={e:.2f}, P={p:.2f}")
        print(sec_spn)

        # RR quantum 1
        res_rr1, sec_rr1 = round_robin(duplicar_procesos(procesos), 1)
        t, e, p = sacar_promedios(res_rr1)
        print(f"RR1: T={t:.2f}, E={e:.2f}, P={p:.2f}")
        print(sec_rr1)

        # RR quantum 4
        res_rr4, sec_rr4 = round_robin(duplicar_procesos(procesos), 4)
        t, e, p = sacar_promedios(res_rr4)
        print(f"RR4: T={t:.2f}, E={e:.2f}, P={p:.2f}")
        print(sec_rr4)

if __name__ == "__main__":
    main()