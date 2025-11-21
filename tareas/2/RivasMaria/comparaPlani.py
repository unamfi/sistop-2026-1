import random

class Proceso:
    def __init__(self, nombre, inicio, duracion):
        self.nombre = nombre
        self.inicio = inicio
        self.duracion = duracion
        self.restante = duracion
        self.fin = 0

def carga(n=5, max_tiempo=15): #Lista con los procesos aleatorios 
    procesos = []
    for i in range(n):
        inicio = random.randint(0, max_tiempo)
        duracion = random.randint(2, 7)
        procesos.append(Proceso(chr(65+i), inicio, duracion))
    procesos.sort(key=lambda p: p.inicio)
    return procesos

def calculos(procesos):
    T, E, P = 0, 0, 0
    for p in procesos:
        t = p.fin - p.inicio      # Tiempo total
        e = t - p.duracion        # Tiempo de espera
        T += t
        E += e
        P += t / p.duracion
    n = len(procesos)
    return round(T/n, 2), round(E/n, 2), round(P/n, 2)

def fcfs(procesos):
    tiempo = 0
    secuencia = []
    for p in procesos:
        if tiempo < p.inicio:
            secuencia.extend("-" * (p.inicio - tiempo))
            tiempo = p.inicio
        secuencia.extend(p.nombre * p.duracion)
        tiempo += p.duracion
        p.fin = tiempo
    return secuencia

def spn(procesos):
    tiempo = 0
    secuencia = []
    lista = procesos.copy()
    completados = []
    while lista:
        disponibles = [p for p in lista if p.inicio <= tiempo]
        if not disponibles:
            secuencia.append("-")
            tiempo += 1
            continue
        p = min(disponibles, key=lambda x: x.duracion)
        secuencia.extend(p.nombre * p.duracion)
        tiempo += p.duracion
        p.fin = tiempo
        completados.append(p)
        lista.remove(p)
    return secuencia

def rr(procesos, quantum):
    tiempo = 0
    secuencia = []
    lista = procesos.copy()
    cola = []
    completados = []
    while lista or cola:
        cola += [p for p in lista if p.inicio <= tiempo]
        lista = [p for p in lista if p.inicio > tiempo]
        if not cola:
            secuencia.append("-")
            tiempo += 1
            continue
        p = cola.pop(0)
        ejecutar = min(quantum, p.restante)
        for _ in range(ejecutar):
            secuencia.append(p.nombre)
            tiempo += 1
            p.restante -= 1
            for nuevo in [x for x in lista if x.inicio == tiempo]:
                cola.append(nuevo)
            lista = [x for x in lista if x.inicio > tiempo]
        if p.restante == 0:
            p.fin = tiempo
            completados.append(p)
        else:
            cola.append(p)
    return secuencia

def imprimR(alg, procesos, secuencia):
    T, E, P = calculos(procesos)
    print(f"  {alg}: T={T}, E={E}, P={P} ")
    print(f"  {''.join(secuencia)}")

def copiar(procesos): #Copia de los procesos para darsela a cada algoritmo y q no sean distintos
    return [Proceso(p.nombre, p.inicio, p.duracion) for p in procesos]

def main():
    random.seed()

    print("\n- Carga aleatoria:")
    procesos = carga(5) 
    valores = [f"{p.nombre}: {p.inicio}, t={p.duracion}" for p in procesos]
    total = sum(p.duracion for p in procesos)
    print("  " + "; ".join(valores) + f" (tot:{total})")

    fcfsP = copiar(procesos)
    rr1P = copiar(procesos)
    rr4P = copiar(procesos)
    spnP = copiar(procesos)

    fcfsS = fcfs(fcfsP)
    rr1S = rr(rr1P, 1)
    rr4S = rr(rr4P, 4)
    spnS = spn(spnP)

    imprimR("\nFCFS", fcfsP, fcfsS)
    imprimR("\nRR1", rr1P, rr1S)
    imprimR("\nRR4", rr4P, rr4S)
    imprimR("\nSPN", spnP, spnS)

if __name__ == "__main__":
    main()


