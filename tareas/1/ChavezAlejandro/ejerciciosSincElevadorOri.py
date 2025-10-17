import threading
import time
import random

num_pisos = 5
cap_maxima = 5
num_usuarios = 12 #Se puede ajustar

piso_actual = 0 #El elevador empieza en el piso 0
direccion = 1  #Empieza subiendo (1) y puede cambiar a bajando (-1)
capacidad = threading.Semaphore(cap_maxima)
mutex_estado = threading.Lock()
cond_pisos = [threading.Condition() for _ in range(num_pisos)]
usuarios_en_elevador = []

#Elevador
def elevador():
    global piso_actual, direccion
    while True:
        time.sleep(1.5)
        with mutex_estado: #El usuario se mueve de piso
            piso_actual += direccion
            if piso_actual == num_pisos - 1:
                direccion = -1
            elif piso_actual == 0:
                direccion = 1

            print(f"\n🚪 Elevador llegó al piso {piso_actual} (dir: {'↑' if direccion==1 else '↓'})")
            cond_pisos[piso_actual].notify_all() #Se notifica a los usuarios esperando en este piso

#Usuarios
def usuario(id, origen, destino):
    global piso_actual
    cond = cond_pisos[origen]
    with cond:
        print(f"👤 Usuario {id} espera en piso {origen} para ir a {destino}")
        cond.wait_for(lambda: piso_actual == origen)

    capacidad.acquire() #El usuario intenta subirse
    print(f"🚶 Usuario {id} abordó en piso {origen}")
    usuarios_en_elevador.append((id, destino))

    while True:
        time.sleep(0.5)
        with mutex_estado:
            if piso_actual == destino:
                print(f"🏁 Usuario {id} bajó en piso {destino}")
                usuarios_en_elevador.remove((id, destino))
                capacidad.release()
                break

#Se crean los hilos
threading.Thread(target=elevador, daemon=True).start()

for i in range(num_usuarios):
    origen = random.randint(0, num_pisos-1)
    destino = random.randint(0, num_pisos-1)
    while destino == origen:
        destino = random.randint(0, num_pisos-1)
    threading.Thread(target=usuario, args=(i, origen, destino), daemon=True).start()
    time.sleep(0.3)

#Para que no se detenga
while True:
    time.sleep(2)

