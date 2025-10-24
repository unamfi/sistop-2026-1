import threading
import time
import random
import os

# --- 1. CONFIGURACIÓN Y ESTADO GLOBAL ---

# Número de autos que participarán en la simulación
NUM_AUTOS = 10

# Nombres de los cuadrantes para una salida más clara
# Asignamos IDs fijos que representan nuestra jerarquía (0 < 1 < 2 < 3)
CUADRANTES_IDS = {"NE": 0, "NO": 1, "SO": 2, "SE": 3}
CUADRANTES_NOMBRES = {v: k for k, v in CUADRANTES_IDS.items()} # Invertir para fácil búsqueda

# Definición de las rutas: Origen -> Destino -> [Lista de cuadrantes necesarios]
# Nota: Las listas NO están ordenadas aquí a propósito. El orden se fuerza en el código.
RUTAS = {
    "Norte": {
        "Sur":    [CUADRANTES_IDS["NO"], CUADRANTES_IDS["SO"]], # Seguir de frente
        "Este":   [CUADRANTES_IDS["NO"], CUADRANTES_IDS["SO"], CUADRANTES_IDS["SE"]], # Izquierda
        "Oeste":  [CUADRANTES_IDS["NO"]] # Derecha
    },
    "Sur": {
        "Norte":  [CUADRANTES_IDS["SE"], CUADRANTES_IDS["NE"]], # Seguir de frente
        "Oeste":  [CUADRANTES_IDS["SE"], CUADRANTES_IDS["NE"], CUADRANTES_IDS["NO"]], # Izquierda
        "Este":   [CUADRANTES_IDS["SE"]] # Derecha
    },
    "Este": {
        "Oeste":  [CUADRANTES_IDS["NE"], CUADRANTES_IDS["NO"]], # Seguir de frente
        "Sur":    [CUADRANTES_IDS["NE"], CUADRANTES_IDS["NO"], CUADRANTES_IDS["SO"]], # Izquierda
        "Norte":  [CUADRANTES_IDS["NE"]] # Derecha
    },
    "Oeste": {
        "Este":   [CUADRANTES_IDS["SO"], CUADRANTES_IDS["SE"]], # Seguir de frente
        "Norte":  [CUADRANTES_IDS["SO"], CUADRANTES_IDS["SE"], CUADRANTES_IDS["NE"]], # Izquierda
        "Sur":    [CUADRANTES_IDS["SO"]] # Derecha
    }
}

# Un mutex por cada cuadrante, en orden jerárquico.
mutex_cuadrantes = [threading.Lock() for _ in range(4)]

# Mutex para sincronizar la escritura en la terminal y la actualización del estado
mutex_pantalla = threading.Lock()

# Estado visual de la intersección. Se llenará con el ID del auto o ' '
estado_interseccion = [' ' for _ in range(4)]

# --- 2. FUNCIÓN DE VISUALIZACIÓN ---

def dibujar_interseccion():
    """Limpia la pantalla y dibuja el estado actual de la intersección."""
    # os.system('cls' if os.name == 'nt' else 'clear') # Descomentar para limpiar pantalla
    """Dibuja el estado actual de la intersección."""
    # Centramos los IDs de los autos en un espacio de 3 caracteres para que se vea ordenado
    no = f"{estado_interseccion[CUADRANTES_IDS['NO']]:^3}"
    ne = f"{estado_interseccion[CUADRANTES_IDS['NE']]:^3}"
    so = f"{estado_interseccion[CUADRANTES_IDS['SO']]:^3}"
    se = f"{estado_interseccion[CUADRANTES_IDS['SE']]:^3}"
    
    print("--- ESTADO DE LA INTERSECCIÓN ---")
    print(f"       Norte↑")
    print(f" ╔═══════╦═══════╗")
    print(f" ║  {no}  ║  {ne}  ║")
    print(f"O║═══════╬═══════║E")
    print(f" ║  {so}  ║  {se}  ║")
    print(f" ╚═══════╩═══════╝")
    print(f"       Sur↓")
    print("-" * 35)

# --- 3. LÓGICA DEL HILO (AUTO) ---

def auto(id_auto):
    """Función que será ejecutada por cada hilo. Simula un auto cruzando."""
    
    # Seleccionar origen y destino aleatorios
    origen = random.choice(list(RUTAS.keys()))
    destino = random.choice(list(RUTAS[origen].keys()))
    
    with mutex_pantalla:
        print(f"Auto {id_auto}: Llega desde el {origen} para ir al {destino}.")
        
    # Obtener la lista de cuadrantes necesarios para la ruta
    cuadrantes_necesarios = RUTAS[origen][destino]
    
    # --- PASO CLAVE ANTI-DEADLOCK ---
    # Se ordena la lista de cuadrantes necesarios por su ID jerárquico (0, 1, 2, 3).
    # Esto asegura que todos los hilos intenten adquirir los locks en el mismo orden.
    cuadrantes_ordenados = sorted(cuadrantes_necesarios)
    
    with mutex_pantalla:
        nombres_cuadrantes = [CUADRANTES_NOMBRES[c] for c in cuadrantes_ordenados]
        print(f"Auto {id_auto}: Necesita los cuadrantes en orden de bloqueo: {nombres_cuadrantes}")

    # Adquirir todos los locks en el orden jerárquico
    for cid in cuadrantes_ordenados:
        mutex_cuadrantes[cid].acquire()
        
        # Actualizar estado y visualizar
        with mutex_pantalla:
            print(f"Auto {id_auto}: Lock adquirido para cuadrante {CUADRANTES_NOMBRES[cid]}.")
            estado_interseccion[cid] = id_auto
            dibujar_interseccion()
        
        # Simular tiempo de movimiento
        time.sleep(random.uniform(0.5, 1.0))
        
    # --- SECCIÓN CRÍTICA ---
    with mutex_pantalla:
        print(f"Auto {id_auto}: ¡Cruce completado! Liberando recursos...")
    # --- FIN DE LA SECCIÓN CRÍTICA ---

    # Liberar los locks (en orden inverso por buena práctica)
    for cid in reversed(cuadrantes_ordenados):
        # Actualizar estado y visualizar
        with mutex_pantalla:
            estado_interseccion[cid] = ' '
            print(f"Auto {id_auto}: Lock liberado para cuadrante {CUADRANTES_NOMBRES[cid]}.")
            dibujar_interseccion()
        
        mutex_cuadrantes[cid].release()
        time.sleep(random.uniform(0.2, 0.5))

# --- 4. FUNCIÓN PRINCIPAL ---

def main():
    """Función principal de la simulación."""
    hilos = []
    print("Iniciando la simulación de la Intersección de Caminos...")
    dibujar_interseccion()
    
    # Crear y lanzar todos los hilos (autos)
    for i in range(NUM_AUTOS):
        # Damos un pequeño desfase a la llegada de cada auto
        time.sleep(random.uniform(0.1, 0.5))
        hilo = threading.Thread(target=auto, args=(i,))
        hilos.append(hilo)
        hilo.start()
        
    # Esperar a que todos los hilos terminen
    for hilo in hilos:
        hilo.join()
        
    print("¡Simulación finalizada! Todos los autos han cruzado.")

if __name__ == "__main__":
    main()
