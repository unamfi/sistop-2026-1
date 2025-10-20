import threading
import time
import random

NUM_ALUMNOS = 5  
NUM_SILLAS = 3   
MAX_PREGUNTAS = 2 

# Semaforos, mutex y multiplex
sillas = threading.Semaphore(NUM_SILLAS)
profesor_listo = threading.Semaphore(0)
alumno_listo = threading.Semaphore(0)
mutex = threading.Lock()
alumnos_esperando = 0

def profesor():
    global alumnos_esperando
    
    print("El profesor abre su cubículo")
    while True:
        print("El profesor no tiene a quién atender y se va a mimir 😴")
        
        profesor_listo.acquire()
        print("El profesor se despierta por un alumno 😠")
        
        while True:
            mutex.acquire() 
            if alumnos_esperando == 0:
                # Si ya no hay nadie, sale del ciclo para volver a dormir.
                mutex.release()
                break
            # Llama al siguiente alumno para que haga su pregunta.
            print("Profesor: 'Pase el siguiente...")
            alumno_listo.release()

            print("El profesor está resolviendo una duda 🤔")
            mutex.release() 
            time.sleep(random.uniform(1, 2))            

def alumno(id_alumno):

    global alumnos_esperando
    num_preguntas = random.randint(1, MAX_PREGUNTAS)

    print(f"\nAlumno {id_alumno} llega. Tiene {num_preguntas} preguntas 🤔")    
    # Intenta tomar una silla, si no hay se bloquea el hilo
    sillas.acquire()
    
    print(f"Alumno {id_alumno} encontró una silla y entró ✅")
    
    # Modifica la variable alumnos_esperando de forma segura con el mutex
    mutex.acquire()
    alumnos_esperando += 1
    mutex.release()
    
    # Bucle para hacer todas sus preguntas
    while num_preguntas > 0:
        # Avisa al profesor que hay alguien listo
        profesor_listo.release()
        # Espera su turno para ser atendido
        alumno_listo.acquire()
        print(f"\nAlumno {id_alumno} está haciendo una pregunta 🙋")
        time.sleep(random.uniform(0.5, 1)) 
        num_preguntas -= 1
        print(f"Alumno {id_alumno}: '¡Gracias!'. Le quedan {num_preguntas} preguntas")

    # Se resolvieron sus dudas y se va 
    mutex.acquire()
    alumnos_esperando -= 1
    mutex.release()
    
    # Libera la silla que estaba ocupando si ya no le quedaron dudas 
    sillas.release()
    print(f"Alumno {id_alumno} terminó y se va 👋\n")

if __name__ == "__main__":
    # Se marca como 'daemon' para que termine cuando el programa principal termine.
    hilo_profesor = threading.Thread(target=profesor)
    hilo_profesor.daemon = True #Linea para terminar el programa 
    hilo_profesor.start()
    
    # Crear y lanzar los hilos de los alumnos
    hilos_alumnos = []
    for i in range(NUM_ALUMNOS):
        hilo = threading.Thread(target=alumno, args=(i + 1,))
        hilos_alumnos.append(hilo)
        hilo.start()
        # Alumnos que van llegando aleatoriamente 
        time.sleep(random.uniform(0, 1))

    # Esperar a que todos los alumnos terminen para imprimir lo de abajo de que ya fueron atendidos
    for hilo in hilos_alumnos:
        hilo.join()
    print("\nTodos los alumnos han sido atendidos. El horario de atención ha terminado 😎")
