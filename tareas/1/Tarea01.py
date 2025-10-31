import threading
import time
import random

secciones_interseccion = [threading.Semaphore(1) for _ in range(4)]

#Funcion auxiliar para el intercambio
def intercambia(A, j):
    aux = A[j]
    A[j] = A[j-1]
    A[j-1] = aux

#Algoritmo de ordenamiento Bubblesort para las secciones de la interseccion de cada hilo
def bubblesort(A,n):
    k = 0
    for i in range((n),1,-1):
        for j in range((n-1),0,-1):
            k+=1
            if(A[j]<A[j-1]):
                intercambia(A, j)
    return A

#Logica detras del movimiento de cada coche
def movimiento_coche(id_coche, carril_origen, movimiento):
    
    print(f"Llega coche {id_coche} del carril {carril_origen}, quiere ir a {movimiento}")

    ruta = []
    #Opciones
    #Recto
    if movimiento == 0: 
        ruta.extend([carril_origen, (carril_origen + 1) % 4])
    # Derecha
    elif movimiento == 1: 
        ruta.append(carril_origen)
    # Izquierda
    elif movimiento == 2: 
        ruta.extend([carril_origen, (carril_origen + 1) % 4, (carril_origen + 2) % 4])

    n1 = len(ruta)
    parte = bubblesort(ruta,n1)

    
    for i in parte:
        secciones_interseccion[i].acquire()

    print(f"- El coche {id_coche} esta cruzando...")
    time.sleep(random.uniform(0.5, 1.5))
    print(f"- El coche {id_coche} termino de cruzar.")

    #liberar las secciones tomadas
    for i in reversed(parte):
        secciones_interseccion[i].release()


def generador_coches():
    contador_coches = 0
    while 1 < 2:
        
        origen = random.randint(0, 3)
        ruta = random.randint(0, 2)
        
        hilo = threading.Thread(target=movimiento_coche, args=(contador_coches, origen, ruta))
        hilo.start()

        contador_coches += 1
        time.sleep(random.uniform(0.2, 1.9))

generador_coches()