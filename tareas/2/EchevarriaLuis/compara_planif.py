import math
import random

class Proceso:
    """
    Define un proceso con sus tiempos y métricas.
    Usamos propiedades para calcular T, E y P automáticamente.
    """
    def __init__(self, id, llegada, rafaga_total):
        self.id = id
        self.llegada = llegada
        self.rafaga_total = rafaga_total  # t
        
        # Estos se calcularán durante la simulación
        self.tiempo_inicio = -1
        self.tiempo_fin = -1
        self.rafaga_restante = rafaga_total
        
        # --- AÑADIDO PARA FB ---
        self.prioridad = 0         # El proceso inicia en la cola de más alta prioridad (0)
        self.cuantico_gastado = 0  # Contador para el cuántum actual

    @property
    def T(self):
        """ Tiempo de Retorno (Turnaround) """
        return self.tiempo_fin - self.llegada

    @property
    def E(self):
        """ Tiempo de Espera (Wait) """
        return self.T - self.rafaga_total

    @property
    def P(self):
        """ Proporción de Penalización (Penalty Ratio) """
        # Evitar división por cero si la ráfaga es 0
        return self.T / self.rafaga_total if self.rafaga_total > 0 else 0

    def __repr__(self):
        """ Representación para imprimir el objeto """
        return f"[id={self.id}, t_llegada={self.llegada}, t_rafaga={self.rafaga_total}]"

def calcular_metricas_promedio(procesos_terminados):
    """
    Calcula el promedio de T, E y P para una lista de procesos terminados.
    """
    total_procesos = len(procesos_terminados)
    if total_procesos == 0:
        return 0, 0, 0

    T_total = sum(p.T for p in procesos_terminados)
    E_total = sum(p.E for p in procesos_terminados)
    P_total = sum(p.P for p in procesos_terminados)

    T_prom = T_total / total_procesos
    E_prom = E_total / total_procesos
    P_prom = P_total / total_procesos

    return T_prom, E_prom, P_prom

def print_ronda(procesos):
    """ Función auxiliar para imprimir la carga aleatoria generada. """
    desc = "; ".join([f"{p.id}: {p.llegada}, t={p.rafaga_total}" for p in procesos])
    tot = sum(p.rafaga_total for p in procesos)
    print(f"  {desc} (tot:{tot})")

def generar_ronda_aleatoria(num_procesos=5):
    """ 
    Genera una lista de procesos aleatorios, asegurando que 
    los tiempos de llegada sean secuenciales.
    """
    procesos = []
    tiempo_llegada_actual = 0
    ids = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H'] # Para hasta 8 procesos
    
    for i in range(num_procesos):
        # El nuevo proceso llega 0, 1, 2 o 3 unidades después del anterior
        llegada = tiempo_llegada_actual + random.randint(0, 3)
        rafaga = random.randint(1, 8) # Ráfagas de 1 a 8
        
        procesos.append(Proceso(ids[i], llegada, rafaga))
        
        # El próximo proceso debe llegar *después* de este
        tiempo_llegada_actual = llegada 
        
    return procesos

def simular_fcfs(procesos_entrada):
    """
    Simulador para First-Come, First-Served (FCFS).
    Maneja "huecos" en el tiempo.
    """
    # Creamos copias para no modificar la lista original
    # y ordenamos por tiempo de llegada (clave para FCFS)
    cola_listos = sorted([Proceso(p.id, p.llegada, p.rafaga_total) for p in procesos_entrada], 
                         key=lambda p: p.llegada)
    
    procesos_terminados = []
    esquema_visual = ""
    tiempo_actual = 0
    
    while cola_listos:
        proceso_actual = cola_listos.pop(0) # Saca el primero de la cola

        # --- MANEJO DE HUECOS ---
        # Si el procesador está libre y el proceso aún no ha llegado,
        # adelantamos el tiempo y marcamos el hueco.
        if tiempo_actual < proceso_actual.llegada:
            hueco = proceso_actual.llegada - tiempo_actual
            esquema_visual += "-" * hueco
            tiempo_actual = proceso_actual.llegada
        
        # --- EJECUCIÓN DEL PROCESO ---
        proceso_actual.tiempo_inicio = tiempo_actual
        tiempo_actual += proceso_actual.rafaga_total
        proceso_actual.tiempo_fin = tiempo_actual
        
        # Añadimos al esquema visual
        esquema_visual += proceso_actual.id * proceso_actual.rafaga_total
        
        # Guardamos el proceso terminado
        procesos_terminados.append(proceso_actual)
        
    # Calculamos métricas finales
    T_prom, E_prom, P_prom = calcular_metricas_promedio(procesos_terminados)
    
    print(f"  FCFS: T={T_prom:.1f}, E={E_prom:.1f}, P={P_prom:.2f}")
    print(f"  {esquema_visual}")

def simular_rr(procesos_entrada, quantum):
    """
    Simulador para Round Robin (RR) con un quantum dado.
    """
    # Creamos copias para no modificar la lista original
    procesos_por_llegar = sorted(
        [Proceso(p.id, p.llegada, p.rafaga_total) for p in procesos_entrada],
        key=lambda p: p.llegada
    )
    
    procesos_terminados = []
    cola_listos = []
    esquema_visual = ""
    tiempo_actual = 0
    proceso_en_ejecucion = None
    tiempo_cuantico_actual = 0
    
    n_procesos = len(procesos_entrada)

    while True: # Bucle infinito que se rompe con lógica interna
        
        # 1. Mover procesos de "por_llegar" a "cola_listos" si ya es su tiempo
        while procesos_por_llegar and procesos_por_llegar[0].llegada <= tiempo_actual:
            cola_listos.append(procesos_por_llegar.pop(0))
            
        # 2. Manejar el proceso en ejecución (si hay uno)
        if proceso_en_ejecucion:
            proceso_en_ejecucion.rafaga_restante -= 1
            tiempo_cuantico_actual += 1
            
            # Comprobar si el proceso terminó
            if proceso_en_ejecucion.rafaga_restante == 0:
                proceso_en_ejecucion.tiempo_fin = tiempo_actual + 1
                procesos_terminados.append(proceso_en_ejecucion)
                proceso_en_ejecucion = None
                tiempo_cuantico_actual = 0
            # Comprobar si el cuántum expiró
            elif tiempo_cuantico_actual == quantum:
                cola_listos.append(proceso_en_ejecucion) # Re-encolar al final
                proceso_en_ejecucion = None
                tiempo_cuantico_actual = 0

        # 3. Asignar CPU si está libre
        if proceso_en_ejecucion is None:
            if cola_listos:
                proceso_en_ejecucion = cola_listos.pop(0) # Saca el siguiente
                
                # Si es la primera vez que se ejecuta, marca su inicio
                if proceso_en_ejecucion.tiempo_inicio == -1:
                    proceso_en_ejecucion.tiempo_inicio = tiempo_actual
                
                # Reiniciamos el cuántum para este proceso
                tiempo_cuantico_actual = 0

        # 4. Condición de salida: si NO hay proceso en ejecución,
        # NO hay procesos en cola, y NO hay procesos por llegar, TERMINAMOS.
        if proceso_en_ejecucion is None and not cola_listos and not procesos_por_llegar:
            break

        # 5. Construir el esquema visual
        if proceso_en_ejecucion:
            esquema_visual += proceso_en_ejecucion.id
        else:
            esquema_visual += "-" # Hueco
        
        # 6. Avanzar el tiempo
        tiempo_actual += 1
        
    # Calculamos métricas finales
    T_prom, E_prom, P_prom = calcular_metricas_promedio(procesos_terminados)
    
    print(f"  RR{quantum}: T={T_prom:.1f}, E={E_prom:.1f}, P={P_prom:.2f}")
    print(f"  {esquema_visual}")

def simular_spn(procesos_entrada):
    """
    Simulador para Shortest Process Next (SPN) (No apropiativo).
    Maneja "huecos".
    """
    # Creamos copias para no modificar la lista original
    procesos_por_llegar = sorted(
        [Proceso(p.id, p.llegada, p.rafaga_total) for p in procesos_entrada],
        key=lambda p: p.llegada
    )
    
    procesos_terminados = []
    cola_listos = []
    esquema_visual = ""
    tiempo_actual = 0
    
    n_procesos = len(procesos_entrada)

    while len(procesos_terminados) < n_procesos:
        
        # 1. Mover procesos de "por_llegar" a "cola_listos" si ya es su tiempo
        while procesos_por_llegar and procesos_por_llegar[0].llegada <= tiempo_actual:
            cola_listos.append(procesos_por_llegar.pop(0))

        # 2. Asignar CPU si está libre
        if cola_listos:
            # --- CLAVE DE SPN ---
            # Ordena la cola de listos por ráfaga más corta
            cola_listos.sort(key=lambda p: p.rafaga_total)
            
            proceso_actual = cola_listos.pop(0) # Saca el más corto
            
            # --- EJECUCIÓN NO APROPIATIVA ---
            # Como es no apropiativo, se ejecuta de una sola vez
            
            # Si es la primera vez, marca el inicio
            if proceso_actual.tiempo_inicio == -1:
                proceso_actual.tiempo_inicio = tiempo_actual
                
            tiempo_ejecucion = proceso_actual.rafaga_total
            tiempo_actual += tiempo_ejecucion
            proceso_actual.tiempo_fin = tiempo_actual
            
            esquema_visual += proceso_actual.id * tiempo_ejecucion
            
            procesos_terminados.append(proceso_actual)

        else:
            # No hay procesos listos. O hay un hueco o terminamos.
            if procesos_por_llegar:
                # Hay un HUECO. Adelantamos el tiempo hasta el próximo proceso.
                proxima_llegada = procesos_por_llegar[0].llegada
                huecos = proxima_llegada - tiempo_actual
                esquema_visual += "-" * huecos
                tiempo_actual = proxima_llegada
            else:
                # No hay procesos listos ni por llegar. Terminamos.
                break

    # Calculamos métricas finales
    T_prom, E_prom, P_prom = calcular_metricas_promedio(procesos_terminados)
    
    print(f"  SPN: T={T_prom:.1f}, E={E_prom:.1f}, P={P_prom:.2f}")
    print(f"  {esquema_visual}")

def simular_fb(procesos_entrada):
    """
    Simulador para Feedback (FB) / Retroalimentación Multinivel.
    """
    quantums = [1, 2] 
    
    procesos_por_llegar = sorted(
        [Proceso(p.id, p.llegada, p.rafaga_total) for p in procesos_entrada],
        key=lambda p: p.llegada
    )
    
    procesos_terminados = []
    colas = [[], [], []] 
    esquema_visual = ""
    tiempo_actual = 0
    proceso_en_ejecucion = None
    n_procesos = len(procesos_entrada)

    while True: # Bucle infinito que se rompe con lógica interna
        
        # 1. Mover procesos de "por_llegar" a la cola Q0 (mayor prioridad)
        while procesos_por_llegar and procesos_por_llegar[0].llegada <= tiempo_actual:
            nuevo_proceso = procesos_por_llegar.pop(0)
            nuevo_proceso.prioridad = 0 
            colas[0].append(nuevo_proceso)

        # 2. Revisar si hay que hacer PREEMPT (interrupción)
        if proceso_en_ejecucion:
            proceso_de_Q0 = bool(colas[0])
            if proceso_de_Q0 and proceso_en_ejecucion.prioridad > 0:
                p = proceso_en_ejecucion
                p.cuantico_gastado = 0 
                colas[p.prioridad].append(p) 
                proceso_en_ejecucion = None

        # 3. Asignar CPU si está libre
        if proceso_en_ejecucion is None:
            for i in range(len(colas)):
                if colas[i]:
                    proceso_en_ejecucion = colas[i].pop(0)
                    if proceso_en_ejecucion.tiempo_inicio == -1:
                        proceso_en_ejecucion.tiempo_inicio = tiempo_actual
                    break 

        # 4. Condición de salida: si NO hay proceso en ejecución,
        # TODAS las colas están vacías, y NO hay procesos por llegar, TERMINAMOS.
        if (proceso_en_ejecucion is None and 
            all(not cola for cola in colas) and 
            not procesos_por_llegar):
            break

        # 5. Ejecutar un pulso de reloj (si hay proceso) o marcar hueco (si no)
        if proceso_en_ejecucion:
            p = proceso_en_ejecucion
            esquema_visual += p.id
            p.rafaga_restante -= 1
            p.cuantico_gastado += 1
            
            # Comprobar si el proceso TERMINÓ
            if p.rafaga_restante == 0:
                p.tiempo_fin = tiempo_actual + 1
                procesos_terminados.append(p)
                proceso_en_ejecucion = None
                tiempo_actual += 1 # Avanza el tiempo
                continue # Pasa al siguiente ciclo de tiempo

            # Determinar el cuántum para la prioridad actual
            if p.prioridad < len(quantums):
                quantum_actual = quantums[p.prioridad]
            else:
                quantum_actual = float('inf') # Es la cola FCFS (Q2)

            # Comprobar si el CUÁNTUM EXPIRÓ
            if p.cuantico_gastado == quantum_actual:
                p.cuantico_gastado = 0
                if p.prioridad < (len(colas) - 1):
                    p.prioridad += 1 # Democión
                colas[p.prioridad].append(p) # Re-encola (en nueva o misma cola)
                proceso_en_ejecucion = None
        
        else:
            # No hay nada en ejecución
            esquema_visual += "-"
            
        # 6. Avanzar el tiempo
        tiempo_actual += 1
            
    # Calculamos métricas finales
    T_prom, E_prom, P_prom = calcular_metricas_promedio(procesos_terminados)
    
    print(f"  FB (Q={[q for q in quantums]}): T={T_prom:.1f}, E={E_prom:.1f}, P={P_prom:.2f}")
    print(f"  {esquema_visual}")

# --- PROGRAMA PRINCIPAL ---

# 1. Rondas de prueba del profesor
print("--- PRUEBAS DEL PROFESOR ---")

ronda_1 = [
    Proceso('A', 0, 3),
    Proceso('B', 1, 5),
    Proceso('C', 3, 2),
    Proceso('D', 9, 5),
    Proceso('E', 12, 5)
]

ronda_huecos = [
    Proceso('A', 0, 2),
    Proceso('B', 1, 5),
    Proceso('C', 8, 3),
    Proceso('D', 9, 4)
]

print("\n- Primera ronda (ejemplo profe):")
print_ronda(ronda_1)
simular_fcfs(ronda_1)
simular_rr(ronda_1, quantum=1)
simular_rr(ronda_1, quantum=4)
simular_spn(ronda_1)
simular_fb(ronda_1)

print("\n- Segunda ronda (ejemplo 'huecos'):")
print_ronda(ronda_huecos)
simular_fcfs(ronda_huecos)
simular_rr(ronda_huecos, quantum=1)
simular_rr(ronda_huecos, quantum=4)
simular_spn(ronda_huecos)
simular_fb(ronda_huecos)

# 2. Rondas aleatorias para la tarea
print("\n--- 5 EJECUCIONES ALEATORIAS ---")

for i in range(1, 6):
    print(f"\n- Ronda Aleatoria {i}:")
    ronda_aleatoria = generar_ronda_aleatoria(5) # 5 procesos
    print_ronda(ronda_aleatoria)
    
    # Ejecuta todos los simuladores para esta ronda
    simular_fcfs(ronda_aleatoria)
    simular_rr(ronda_aleatoria, quantum=1)
    simular_rr(ronda_aleatoria, quantum=4)
    simular_spn(ronda_aleatoria)
    simular_fb(ronda_aleatoria)
