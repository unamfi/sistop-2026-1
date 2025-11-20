import copy
import random

class Process:
    """
    Clase para representar un proceso con sus métricas.
    Usamos copy.deepcopy para asegurarnos de que cada simulador
    recibe una copia "limpia" de los procesos.
    """
    def __init__(self, p_id, arrival, duration):
        self.id = p_id
        self.arrival_time = arrival
        self.duration = duration
        
        # Atributos para la simulación
        self.time_remaining = duration
        self_duration = 0 # Para SPN/PSPN
        
        # Atributos para métricas
        self.finish_time = 0
        self.start_time = -1 # -1 significa que nunca ha empezado
        self.wait_time = 0

    def __repr__(self):
        # Una forma bonita de imprimir el proceso
        return f"[id:{self.id} arr:{self.arrival_time} dur:{self.duration}]"

def calculate_metrics(original_processes, finished_processes):
    """
    Calcula las métricas T, E, y P promedio para una lista de procesos terminados.
    """
    total_t = 0
    total_e = 0
    total_p = 0
    
    # Mapeamos los datos originales para fácil acceso
    original_map = {p.id: p for p in original_processes}
    
    for p in finished_processes:
        original = original_map[p.id]
        
        # T (Tiempo de Respuesta): Tiempo total desde que llega hasta que termina
        T = p.finish_time - original.arrival_time
        
        # E (Tiempo en Espera): Tiempo de respuesta menos el tiempo que realmente usó
        E = T - original.duration
        
        # P (Proporción de Penalización): Qué tanto de su tiempo fue espera
        P = T / original.duration
        
        total_t += T
        total_e += E
        total_p += P
        
    num_proc = len(finished_processes)
    if num_proc == 0:
        return 0, 0, 0
        
    return (total_t / num_proc, 
            total_e / num_proc, 
            total_p / num_proc)

def simulate_fcfs(processes_data):
    """
    Simula el algoritmo First Come, First Serve (FCFS).
    """
    # Usamos copy.deepcopy para no modificar la lista original
    processes = copy.deepcopy(processes_data)
    
    current_time = 0
    visual_log = ""
    ready_queue = []
    finished_processes = []
    running_process = None
    
    # Ordenamos los procesos por tiempo de llegada
    processes.sort(key=lambda p: p.arrival_time)
    
    process_index = 0 # Para saber cuál es el siguiente proceso en llegar
    
    # El bucle principal del simulador. Continúa hasta que todos los procesos terminan.
    while len(finished_processes) < len(processes):
        
        # 1. AGREGAR NUEVOS PROCESOS A LA COLA DE LISTOS
        # Revisa si han llegado nuevos procesos en este "tick"
        while (process_index < len(processes) and 
               processes[process_index].arrival_time <= current_time):
            
            ready_queue.append(processes[process_index])
            process_index += 1
            
        # 2. DECIDIR QUÉ PROCESO EJECUTAR (LÓGICA DEL PLANIFICADOR)
        # Si no hay un proceso corriendo Y hay procesos en la cola...
        if running_process is None and len(ready_queue) > 0:
            # ...sacamos el siguiente de la cola (FCFS es FIFO, así que el [0])
            running_process = ready_queue.pop(0)
            if running_process.start_time == -1:
                running_process.start_time = current_time
        
        # 3. EJECUTAR EL "TICK" DE TIEMPO
        if running_process is not None:
            # Hay un proceso corriendo
            visual_log += running_process.id
            running_process.time_remaining -= 1
            
            # Revisar si el proceso terminó
            if running_process.time_remaining <= 0:
                running_process.finish_time = current_time + 1
                finished_processes.append(running_process)
                running_process = None
                
                
        else:
            # No hay nada corriendo (ni en la cola de listos)
            # Esto es un "HUECO"
            visual_log += "-"
            
        # 4. AVANZAR EL RELOJ
        current_time += 1
        
        # Condición de seguridad para evitar bucles infinitos
        if current_time > 1000:
            print("ERROR: Simulación demasiado larga, posible bucle infinito.")
            break
    print("\n--- Simulación FCFS ---")
    avg_t_fcfs, avg_e_fcfs, avg_p_fcfs = calculate_metrics(processes_data, finished_processes)
    print(f"{visual_log}")
    print(f"FCFS: T={avg_t_fcfs:.1f}, E={avg_e_fcfs:.1f}, P={avg_p_fcfs:.2f}")


def simulate_rr(processes_data, quantum):
    # Usamos copy.deepcopy para no modificar la lista original
    processes = copy.deepcopy(processes_data)
    
    current_time = 0
    visual_log = ""
    ready_queue = []
    finished_processes = []
    running_process = None
    contador_tick = 0

    # Ordenamos los procesos por tiempo de llegada
    processes.sort(key=lambda p: p.arrival_time)
    
    process_index = 0 # Para saber cuál es el siguiente proceso en llegar
    
    # El bucle principal del simulador. Continúa hasta que todos los procesos terminan.
    while len(finished_processes) < len(processes):
        
        # 1. AGREGAR NUEVOS PROCESOS A LA COLA DE LISTOS
        # Revisa si han llegado nuevos procesos en este "tick"
        while (process_index < len(processes) and 
               processes[process_index].arrival_time <= current_time):
            
            ready_queue.append(processes[process_index])
            process_index += 1
            
        # 2. DECIDIR QUÉ PROCESO EJECUTAR (LÓGICA DEL PLANIFICADOR)
        # Si no hay un proceso corriendo Y hay procesos en la cola...
        if running_process is None and len(ready_queue) > 0:
            # ...sacamos el siguiente de la cola (FCFS es FIFO, así que el [0])
            running_process = ready_queue.pop(0)
            contador_tick = 0
            if running_process.start_time == -1:
                running_process.start_time = current_time
        
        # 3. EJECUTAR EL "TICK" DE TIEMPO
        if running_process is not None:
            # Hay un proceso corriendo
            visual_log += running_process.id
            running_process.time_remaining -= 1
            
            contador_tick += 1
            
            # Revisar si el proceso terminó
            if running_process.time_remaining <= 0:
                running_process.finish_time = current_time + 1
                finished_processes.append(running_process)
                running_process = None
            elif(contador_tick == quantum):
                # ¡Se acabó el tiempo! Lo mandamos al final de la fila
                ready_queue.append(running_process)
                # Dejamos la CPU libre
                running_process = None
        else:
            # No hay nada corriendo (ni en la cola de listos)
            # Esto es un "HUECO"
            visual_log += "-"
            
        # 4. AVANZAR EL RELOJ
        current_time += 1

        # Condición de seguridad para evitar bucles infinitos
        if current_time > 1000:
            print("ERROR: Simulación demasiado larga, posible bucle infinito.")
            break
    
    print(f"\n--- Simulación RR quantum {quantum}---")
    # Calcular métricas para RR
    avg_t_rr, avg_e_rr, avg_p_rr = calculate_metrics(processes_data, finished_processes)
    print(f"{visual_log}")
    print(f"RR{quantum}: T={avg_t_rr:.1f}, E={avg_e_rr:.1f}, P={avg_p_rr:.2f}")

def BuscarMenor(A):
    menor = A[0].duration
    indice_menor = 0

    for i in range(1, len(A)):
        if A[i].duration < menor:
            menor = A[i].duration
            indice_menor = i
    return indice_menor

def simulate_spn(processes_data):
    
    # Usamos copy.deepcopy para no modificar la lista original
    processes = copy.deepcopy(processes_data)
    
    current_time = 0
    visual_log = ""
    ready_queue = []
    finished_processes = []
    running_process = None
    
    # Ordenamos los procesos por tiempo de llegada
    processes.sort(key=lambda p: p.arrival_time)
    
    process_index = 0 # Para saber cuál es el siguiente proceso en llegar
    
    # El bucle principal del simulador. Continúa hasta que todos los procesos terminan.
    while len(finished_processes) < len(processes):
        
        # 1. AGREGAR NUEVOS PROCESOS A LA COLA DE LISTOS
        # Revisa si han llegado nuevos procesos en este "tick"
        while (process_index < len(processes) and 
               processes[process_index].arrival_time <= current_time):
            
            ready_queue.append(processes[process_index])
            process_index += 1
            
        # 2. DECIDIR QUÉ PROCESO EJECUTAR (LÓGICA DEL PLANIFICADOR)
        # Si no hay un proceso corriendo Y hay procesos en la cola...
        if running_process is None and len(ready_queue) > 0:
            # ...sacamos el siguiente de la cola (FCFS es FIFO, así que el [0])
            indice_menor = BuscarMenor(ready_queue)
            running_process = ready_queue.pop(indice_menor)
            if running_process.start_time == -1:
                running_process.start_time = current_time
        
        # 3. EJECUTAR EL "TICK" DE TIEMPO
        if running_process is not None:
            # Hay un proceso corriendo
            visual_log += running_process.id
            running_process.time_remaining -= 1
            
            # Revisar si el proceso terminó
            if running_process.time_remaining <= 0:
                running_process.finish_time = current_time + 1
                finished_processes.append(running_process)
                running_process = None
                
                
        else:
            # No hay nada corriendo (ni en la cola de listos)
            # Esto es un "HUECO"
            visual_log += "-"
            
        # 4. AVANZAR EL RELOJ
        current_time += 1
        
        # Condición de seguridad para evitar bucles infinitos
        if current_time > 1000:
            print("ERROR: Simulación demasiado larga, posible bucle infinito.")
            break

    print("\n--- Simulación SPN ---")
    avg_t_spn, avg_e_spn, avg_p_spn = calculate_metrics(processes_data, finished_processes)
    print(f"{visual_log}")
    print(f"SPN: T={avg_t_spn:.1f}, E={avg_e_spn:.1f}, P={avg_p_spn:.2f}\n")    


# --- PUNTO DE ENTRADA PRINCIPAL ---
if __name__ == "__main__":

    print("-----\tEJEMPLOS DE EJECUCION PRIMER EJEMPLO\t-----\n")

    #"""
    primera_ronda_data = [
        Process(p_id='A', arrival=0, duration=3),
        Process(p_id='B', arrival=1, duration=5),
        Process(p_id='C', arrival=3, duration=2),
        Process(p_id='D', arrival=9, duration=5),
        Process(p_id='E', arrival=12, duration=5),
    ]
    #"""

    total_time = sum(p.duration for p in primera_ronda_data)
    print("Iniciando simulación...")
    print(f"Procesos: {primera_ronda_data} (tot:{total_time})")

    # --- SIMULACIÓN FCFS ---
    simulate_fcfs(primera_ronda_data)

    # --- SIMULACIÓN RR (Quantum 1) ---
    simulate_rr(primera_ronda_data, quantum=1)

    # --- SIMULACIÓN RR (Quantum 4) ---
    simulate_rr(primera_ronda_data, quantum=4)

    # --- SIMULACIÓN SPN ---
    simulate_spn(primera_ronda_data)

    print("\n\n\n-----\tEJEMPLOS DE EJECUCION CON HUECOS\t-----\n")
    ronda_data_huecos = [
        Process(p_id='A', arrival=0, duration=2),
        Process(p_id='B', arrival=1, duration=5),
        Process(p_id='C', arrival=8, duration=3),
        Process(p_id='D', arrival=9, duration=4),
    ]
    # --- SIMULACIÓN FCFS ---
    simulate_fcfs(ronda_data_huecos)

    # --- SIMULACIÓN RR (Quantum 1) ---
    simulate_rr(ronda_data_huecos, quantum=1)
    
    # --- SIMULACIÓN RR (Quantum 4) ---
    simulate_rr(ronda_data_huecos, quantum=4)

    # --- SIMULACIÓN SPN ---
    simulate_spn(ronda_data_huecos)

    print("\n\n\n-----\tEJEMPLOS DE EJECUCION CON CARGAS ALEATORIAS\t-----\n")
    
    for i in range(0,5):
        print(f"\n\nIteracion {i}")
        arrival_aleatorio = []
        ac_ac = 0
        for i in range(0,5):
            x_xd = random.randint(0,6)
            ac_ac +=x_xd
            arrival_aleatorio.append(ac_ac)
        p_id_conjunto =['A','B','C','D','E']
        conjunto_aleatorio = []
        for i in range(0,5):
            duration_random = random.randint(1,6)
            conjunto_aleatorio.append(Process(p_id=p_id_conjunto[i], arrival=arrival_aleatorio[i], duration=duration_random))
            duration_random = 0 

        total_time = sum(p.duration for p in conjunto_aleatorio)
        print(f"\nProcesos: {conjunto_aleatorio} (tot:{total_time})")

        # --- SIMULACIÓN FCFS ---
        simulate_fcfs(conjunto_aleatorio)

        # --- SIMULACIÓN RR (Quantum 1) ---
        simulate_rr(conjunto_aleatorio, quantum=1)

        # --- SIMULACIÓN RR (Quantum 4) ---
        simulate_rr(conjunto_aleatorio, quantum=4)

        # --- SIMULACIÓN SPN ---
        simulate_spn(conjunto_aleatorio)

