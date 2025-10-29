import random
import io
from collections import deque
import copy

# Clase para el Proceso 
class Process:
    def __init__(self, id, arrival, burst):
        self.id = id
        self.arrival_time = arrival
        self.burst_time = burst
        self.time_remaining = burst
        
        # Variables para el calculo de los estadisticos
        self.start_time = -1  
        self.finish_time = -1 
        self.wait_time = 0    # Tiempo total en la cola de listos

    def __repr__(self):
        # Facilita la impresión de la carga inicial
        return f"{self.id}: {self.arrival_time}, t={self.burst_time}"

# Genera la carga aleatoria para los procesos tomando en cuenta que puede haber huecos 
def generate_load(num_processes=5):
    processes = []
    current_arrival = 0
    names = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for i in range(num_processes):
        arrival = current_arrival
        burst = random.randint(2, 8) # Duración de 2 a 8 ticks
        processes.append(Process(names[i], arrival, burst))
        
        # El siguiente proceso llegará un poco después
        current_arrival += random.randint(0, 4)
        
    return processes

# Calcula los parametros estadisticos
def calculate_stats(finished_processes):
    """
    T = Tiempo de Retorno
    E = Tiempo de Espera
    R = Tiempo de Respuesta
    P = Tiempo de Retorno Normalizado
    """
    # Inicializamos variables totales
    total_T = 0
    total_E = 0
    total_R = 0
    total_P = 0
    num = len(finished_processes)
    
    if num == 0:
        return {"T": 0, "E": 0, "R": 0, "P": 0}
    # P representa el proceso
    for p in finished_processes:
        T = p.finish_time - p.arrival_time
        E = p.wait_time
        R = p.start_time - p.arrival_time
        P = T / p.burst_time # Retorno / Duración
        
        total_T += T
        total_E += E
        total_R += R
        total_P += P
        
    return {
        "T": total_T / num,
        "E": total_E / num,
        "R": total_R / num,
        "P": total_P / num
    }

# Algoritmos de Planificación
# Firs come first serve
def fcfs(processes_orig):
    # Copiamos la lista para no modificar la original
    processes = copy.deepcopy(processes_orig)
    
    time = 0
    gantt = ""
    ready_queue = deque()
    # Procesos que aún no han llegado, ordenados por llegada
    pending = sorted(processes, key=lambda p: p.arrival_time)
    finished = []
    running_process = None
    
    # El bucle principal se ejecuta mientras haya trabajo por hacer
    while pending or ready_queue or running_process:
        
        # 1. Mover procesos de pendientes a listos si ya llegaron
        while pending and pending[0].arrival_time <= time:
            ready_queue.append(pending.pop(0))
        
        # 2. Decidir que ejecutar cuando el CPU esta libre
        if running_process is None:
            if ready_queue:
                # Tomar el siguiente de la cola FCFS
                running_process = ready_queue.popleft()
                if running_process.start_time == -1:
                    running_process.start_time = time
            else:
                if pending: # Si no hay listos, pero faltan por llegar 
                    gantt += "_" #Con esta linea se maneja el proceso "vacio" o que hubo espacio entre procesos
                    time += 1
                    continue
                else:
                    break # No hay nada corriendo, nada en espera, nada por llegar. Terminamos.

        # 3. "Tick" del procesador
        gantt += running_process.id
        running_process.time_remaining -= 1
        
        # 4. Actualizar espera de los que están en la cola de listos
        for p in ready_queue:
            p.wait_time += 1

        # 5. Comprobar si el proceso terminó
        if running_process.time_remaining == 0:
            running_process.finish_time = time + 1
            finished.append(running_process)
            running_process = None           
        time += 1 
    return calculate_stats(finished), gantt

#Shortest process next
def spn(processes_orig):
    processes = copy.deepcopy(processes_orig)
    time = 0
    gantt = ""
    ready_queue = [] # Usamos lista para poder buscar el más corto
    pending = sorted(processes, key=lambda p: p.arrival_time)
    finished = []
    running_process = None
    
    while pending or ready_queue or running_process:
        
        # 1. Mover procesos de pendientes a listos
        while pending and pending[0].arrival_time <= time:
            ready_queue.append(pending.pop(0))
        
        # 2. Decidir qué ejecutar 
        if running_process is None:
            if ready_queue:
                ready_queue.sort(key=lambda p: p.burst_time)
                # Tomar el más corto
                running_process = ready_queue.pop(0) 
                
                if running_process.start_time == -1:
                    running_process.start_time = time
            else:
                if pending:
                    gantt += "_" #Con esta linea se maneja el proceso "vacio" o que hubo espacio entre procesos
                    time += 1
                    continue
                else:
                    break 

        # 3. "Tick"
        gantt += running_process.id
        running_process.time_remaining -= 1
        
        # 4. Actualizar espera
        for p in ready_queue:
            p.wait_time += 1

        # 5. Comprobar si terminó (no apropiativo)
        if running_process.time_remaining == 0:
            running_process.finish_time = time + 1
            finished.append(running_process)
            running_process = None 
        time += 1

    return calculate_stats(finished), gantt

# Round robin
def rr(processes_orig, quantum=1):
    processes = copy.deepcopy(processes_orig)
    time = 0
    gantt = ""
    ready_queue = deque()
    pending = sorted(processes, key=lambda p: p.arrival_time)
    finished = []
    running_process = None
    current_quantum_slice = 0 # Contador para el quantum
    
    while pending or ready_queue or running_process:
        
        # 1. Mover procesos pendientes a listos
        while pending and pending[0].arrival_time <= time:
            ready_queue.append(pending.pop(0))

        # 2. Decidir
        if running_process is None:
            if ready_queue:
                running_process = ready_queue.popleft()
                if running_process.start_time == -1:
                    running_process.start_time = time
                current_quantum_slice = 0 # Reiniciar contador de quantum
            else:
                if pending:
                    gantt += "_"
                    time += 1
                    continue
                else:
                    break

        # 3. Tick
        gantt += running_process.id
        running_process.time_remaining -= 1
        current_quantum_slice += 1

        # 4. Actualizar espera
        for p in ready_queue:
            p.wait_time += 1

        # 5. Comprobar fin del proceso o del Quantum
        if running_process.time_remaining == 0:
            # Fin proceso
            running_process.finish_time = time + 1
            finished.append(running_process)
            running_process = None
        elif current_quantum_slice == quantum:
            # Fin de Quantum
            # IMPORTANTE: Los que llegan ahora se añaden antes que el proceso que desalojaremos
            while pending and pending[0].arrival_time <= (time + 1):
                 ready_queue.append(pending.pop(0))
                 
            # Devolver el proceso al final de la cola
            ready_queue.append(running_process)
            running_process = None    
        time += 1
    return calculate_stats(finished), gantt

def fb(processes_orig):
    processes = copy.deepcopy(processes_orig)
    time = 0
    gantt = ""
    # Tres colas de listos, una por nivel
    queues = [deque(), deque(), deque()] # Q0, Q1, Q2
    quantum_config = [1, 4, float('inf')] # Infinito para FCFS en Q2 o sea la de menor prioridad
    
    pending = sorted(processes, key=lambda p: p.arrival_time)
    finished = []
    running_process = None
    current_quantum_slice = 0
    current_queue_level = -1
    
    while pending or queues[0] or queues[1] or queues[2] or running_process:
        
        # 1. Mover procesos de 'pendientes' a 'Q0' (más alta en prioridad)
        while pending and pending[0].arrival_time <= time:
            new_proc = pending.pop(0)
            
            # Apropiación, en caso que llegue un proceso de prioridad más alta
            if running_process and current_queue_level > 0:
                # Se desaloja y vuelve al inicio de su cola
                queues[current_queue_level].appendleft(running_process)
                running_process = None # Forzar al planificador a reevaluar
            queues[0].append(new_proc) # El nuevo siempre entra a Q0

        # 2. Decidir qué ejecutar
        if running_process is None:
            # Buscar en colas, por prioridad (Q0 > Q1 > Q2)
            if queues[0]:
                running_process = queues[0].popleft()
                current_queue_level = 0
            elif queues[1]:
                running_process = queues[1].popleft()
                current_queue_level = 1
            elif queues[2]:
                running_process = queues[2].popleft()
                current_queue_level = 2
            else:
                if pending:
                    gantt += "_" #Con esta linea se maneja el proceso "vacio" o que hubo espacio entre procesos
                    time += 1
                    continue
                else:
                    break 
                    
            if running_process.start_time == -1:
                running_process.start_time = time
            current_quantum_slice = 0 # Reiniciar contador

        # 3. Tick
        gantt += running_process.id
        running_process.time_remaining -= 1
        current_quantum_slice += 1

        # 4. Actualizar espera en TODAS las colas
        for q_level in range(len(queues)):
            if q_level != current_queue_level: # No contar al que corre
                for p in queues[q_level]:
                    p.wait_time += 1

        # 5. Comprobar eventos
        quantum_for_level = quantum_config[current_queue_level]
        
        if running_process.time_remaining == 0:
            # Proceso terminó
            running_process.finish_time = time + 1
            finished.append(running_process)
            running_process = None
        elif current_quantum_slice == quantum_for_level:
            # Fin de Quantum (para Q0 o Q1)
            # Decidir a qué cola va el proceso
            next_level = min(current_queue_level + 1, 2)
            
            # Manejar llegadas antes de mover el proceso
            while pending and pending[0].arrival_time <= (time + 1):
                 new_proc_during_slice = pending.pop(0)
                 if current_queue_level > 0: 
                     queues[next_level].append(running_process) # Poner el actual en su sig. cola
                     running_process = None
                 queues[0].append(new_proc_during_slice)
            
            if running_process: # Si no fue desalojado por una llegada
                queues[next_level].append(running_process)
                running_process = None
        time += 1        
    return calculate_stats(finished), gantt

# Main para ejecutar todo
def main():
    num_rondas = 5
    for i in range(num_rondas):
        print("-" * 15)
        print(f"Ronda {i+1}")
        print("-" * 15)
        load = generate_load(5)
    
        # Imprimir la carga generada
        total_burst = sum(p.burst_time for p in load)
        carga_str = "; ".join(map(str, load))
        print(f"  {carga_str} (tot:{total_burst})\n")
        
        # Diccionario para almacenar los algoritmos y sus argumentos
        algoritmos = {
            "FCFS": (fcfs, {}),
            "SPN ": (spn, {}),
            "RR1 ": (rr, {"quantum": 1}),
            "RR4 ": (rr, {"quantum": 4}),
            "FB  ": (fb, {})
        }
        
        for name, (func, kwargs) in algoritmos.items():
            # Ejecutar la simulación
            stats, gantt = func(load, **kwargs)
            
            # Imprimir resultados.
            print(f"  {name}: T={stats['T']:.2f}, E={stats['E']:.2f}, P={stats['P']:.2f} (R={stats['R']:.2f})")
            print(f"  {gantt}\n")
        print("")

if __name__ == "__main__":
    main()