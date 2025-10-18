# Simulación: El Cruce del Río

**Integrantes del equipo**
- Sierra García Mariana
- Tapia García Andrés

## Tabla de Contenidos
- [Descripción del Problema](#descripción-del-problema)
- [Requerimientos](#requerimientos)
- [Uso](#uso)
- [Cómo Funciona](#cómo-funciona)
- [Estrategia de Sincronización](#estrategia-de-sincronización)
- [Estructura del Código](#estructura-del-código)

## Descripción del Problema

Para el desarrollo de esta tarea elegimos el problema de sincronización "El Cruce del Río". En este problema se plantea una situación en la que desarrolladores de dos grupos distintos (hackers de Linux y serfs de Microsoft) intentan abordar una balsa para cruzar un río, pero deben hacerlo respetando un conjunto de restricciones de convivencia y equilibrio entre los grupos.

### Reglas del Problema

1. **Capacidad exacta**: La balsa debe llevar exactamente 4 personas
2. **Evitar peleas**: Solo se permiten las siguientes combinaciones:
   - 4 hackers y 0 serfs
   - 0 hackers y 4 serfs
   - 2 hackers y 2 serfs (grupo mixto)
3. **Prohibido**: Combinaciones 3-1 (tres de un tipo y uno del otro) causan peleas
4. **Seguridad**: Con menos de 4 personas, la balsa volcaría
5. **Retorno automático**: La balsa regresa sola después de cada cruce

### Objetivos de Sincronización

- Evitar condiciones de carrera (race conditions)
- Prevenir bloqueos mutuos (deadlocks)
- Evitar inanición (starvation)
- Garantizar formación correcta de grupos
- Coordinar múltiples hilos concurrentes

## Requerimientos

### Verificar Python
Abre una terminal y verifica que tienes Python 3 instalado:
```bash
python3 --version
```

Deberías ver algo como: `Python 3.8.10` (o superior)

### Dar permisos de ejecución (Linux/macOS)
```bash
chmod +x cruce_rio.py
```

## Uso

### Ejecución Básica
```bash
python3 cruce_rio.py
```

### Ejecución con Shebang (Linux/macOS)
```bash
./cruce_rio.py
```

### Ejecución en Windows
```cmd
python cruce_rio.py
```

### ¿Qué verás?

Al ejecutar el programa, verás:
1. **Banner inicial** con las reglas
2. **Solicitud de entrada**: El programa pedirá el número de desarrolladores
3. **Mensajes en tiempo real** de:
   - Llegada de desarrolladores
   - Estado actual (cuántos esperan)
   - Formación de grupos
   - Cruces de la balsa
   - Retiros por timeout (si ocurren)
4. **Estadísticas finales** al terminar

## Cómo Funciona

### Flujo General del Programa
```
1. INICIALIZACIÓN
   - Usuario ingresa número de desarrolladores
   - Se crean N desarrolladores (aleatorio H/S)
   - Cada uno es un hilo independiente

2. LLEGADA A LA ORILLA
   - Desarrollador llega (tiempo aleatorio)
   - Se registra (incrementa contador)
   - Muestra estado del sistema

3. DECISIÓN DE GRUPO
   ¿Hay 4+ de mi tipo?        → Formar grupo homogéneo
   ¿Hay 2+ de cada tipo?      → Formar grupo mixto
   ¿No se puede formar grupo? → Esperar en cola

4. FORMAR GRUPO (quien decide)
   - Decrementa contadores
   - Despierta a otros 3 desarrolladores
   - Todos abordan la balsa

5. ESPERA CON TIMEOUT
   - Si no se forma grupo en 3 segundos
   - El desarrollador se retira
   - Se registra como "no cruzó"

6. CRUCE
   - Los 4 se sincronizan
   - La balsa zarpa
   - Simula tiempo de cruce (2 segundos)
   - Llegan al otro lado

7. ESTADÍSTICAS FINALES
   - Total de desarrolladores invitados
   - Viajes realizados
   - Personas que cruzaron
   - Personas que se retiraron (no cruzaron)
```

### Algoritmo Detallado

#### Para Hackers:
```python
1. Llegar a la orilla
2. Adquirir mutex (acceso exclusivo a contadores)
3. Incrementar num_hackers
4. Evaluar opciones:
   SI num_hackers >= 4:
      - Formar grupo de 4 hackers
      - Despertar 3 hackers más
      - Coordinar cruce
   SI NO, SI num_hackers >= 2 Y num_serfs >= 2:
      - Formar grupo mixto (2H + 2S)
      - Despertar 1 hacker y 2 serfs
      - Coordinar cruce
   SI NO:
      - Liberar mutex
      - Dormir en cola de hackers
      - Esperar señal para abordar (con timeout de 3s)
      - SI timeout: retirarse y decrementar contador
5. Cruzar el río (si abordó exitosamente)
```

#### Para Serfs:
```python
1. Llegar a la orilla
2. Adquirir mutex (acceso exclusivo a contadores)
3. Incrementar num_serfs
4. Evaluar opciones:
   SI num_serfs >= 4:
      - Formar grupo de 4 serfs
      - Despertar 3 serfs más
      - Coordinar cruce
   SI NO, SI num_hackers >= 2 Y num_serfs >= 2:
      - Formar grupo mixto (2H + 2S)
      - Despertar 2 hackers y 1 serf
      - Coordinar cruce
   SI NO:
      - Liberar mutex
      - Dormir en cola de serfs
      - Esperar señal para abordar (con timeout de 3s)
      - SI timeout: retirarse y decrementar contador
5. Cruzar el río (si abordó exitosamente)
```

## Estrategia de Sincronización

### Primitivas Utilizadas

#### 1. **Mutex Principal (Semáforo Binario)**
```python
mutex = threading.Semaphore(1)
```
- **Propósito**: Proteger el acceso a variables compartidas
- **Protege**: `num_hackers`, `num_serfs`
- **Patrón**: Exclusión mutua básica

#### 2. **Mutex para Cruces (Lock)**
```python
mutex_cruces = threading.Lock()
```
- **Propósito**: Proteger el contador de cruces realizados
- **Protege**: `cruces_realizados`
- **Patrón**: Exclusión mutua para estadísticas

#### 3. **Colas de Espera**
```python
hackers_queue = threading.Semaphore(0)
serfs_queue = threading.Semaphore(0)
```
- **Propósito**: Mantener desarrolladores dormidos hasta que puedan abordar
- **Patrón**: Señalización (signaling) con timeout
- **Funcionamiento**:
  - Valor 0 = desarrollador bloqueado
  - `release()` = despertar a un desarrollador
  - `acquire(timeout=3)` = esperar máximo 3 segundos

#### 4. **Sincronización de Abordaje**
```python
balsa_lista = threading.Semaphore(0)
```
- **Propósito**: Coordinar que los 4 desarrolladores aborden antes de zarpar
- **Patrón**: Barrera (barrier) simplificada
- **Funcionamiento**:
  - Cada desarrollador hace `release()` al abordar
  - El organizador hace `acquire()` 3 veces (espera a los otros 3)

### Prevención de Problemas Clásicos

#### Condiciones de Carrera → Mutex
- **Problema**: Dos hilos modifican `num_hackers` simultáneamente
- **Solución**: Todo acceso a contadores está protegido por `mutex`

#### Bloqueo Mutuo → Orden de Adquisición + Timeout
- **Problema**: Desarrolladores esperan indefinidamente sin formar grupos
- **Solución 1**: Solo un hilo puede tomar decisiones (quien adquiere mutex primero)
- **Solución 2**: Timeout de 3 segundos permite retiro si no hay grupo posible
- **Garantía**: Un hilo decrementa contadores y despierta a otros atómicamente

#### Inanición → Grupos Mixtos + Timeout
- **Problema**: Un tipo espera indefinidamente por falta del otro tipo
- **Solución 1**: Se priorizan grupos mixtos (2-2) cuando hay disponibilidad
- **Solución 2**: Timeout permite que desarrolladores se retiren si no hay suficientes del otro tipo
- **Nota**: Si solo hay de un tipo suficiente, formarán grupos homogéneos

#### Deadlock → Detección y Recuperación
- **Problema**: Situaciones donde no se pueden formar más grupos válidos
- **Solución**: Sistema de timeout que detecta cuando no hay progreso
- **Resultado**: Desarrolladores restantes se retiran ordenadamente

## Estructura del Código
```
cruce_rio.py
│
├── Variables Globales
│   ├── num_hackers (int)          # Hackers esperando
│   ├── num_serfs (int)            # Serfs esperando
│   ├── cruces_realizados (int)    # Contador de cruces
│   └── retirados (int)            # Desarrolladores que no cruzaron
│
├── Semáforos y Locks
│   ├── mutex                      # Protege variables compartidas
│   ├── mutex_cruces               # Protege contador de cruces
│   ├── hackers_queue              # Cola de hackers esperando
│   ├── serfs_queue                # Cola de serfs esperando
│   └── balsa_lista                # Sincroniza abordaje
│
├── Configuración
│   ├── CAPACIDAD_BALSA = 4        # Capacidad de la balsa
│   ├── TIEMPO_CRUCE = 2           # Segundos de cruce
│   ├── DELAY_VISUAL = 0.5         # Delay para legibilidad
│   └── TIMEOUT_ESPERA = 3         # Timeout para detección
│
├── Funciones
│   ├── imprimir_estado()          # Muestra estado actual
│   ├── hacker(id)                 # Proceso de un hacker
│   ├── serf(id)                   # Proceso de un serf
│   └── main()                     # Función principal
│
└── Punto de Entrada
    └── if __name__ == "__main__"
```

### Descripción de Funciones Principales

#### `imprimir_estado()`
```python
def imprimir_estado():
    """Muestra cuántos desarrolladores están esperando"""
```
- Imprime: "Esperando: X hackers, Y serfs"
- Se llama cada vez que alguien llega o se retira

#### `hacker(id)` y `serf(id)`
```python
def hacker(id):
    """Lógica completa de un hacker que quiere cruzar"""
```
- **Parámetro**: `id` - Identificador único
- **Comportamiento**:
  1. Espera tiempo aleatorio (simula llegada)
  2. Se registra
  3. Decide si formar grupo o esperar
  4. Si espera: intenta abordar con timeout de 3s
  5. Si timeout: se retira y registra como no cruzado
  6. Si aborda: cruza el río
- **Diferencia**: Igual lógica, diferentes colas y mensajes

#### `main()`
```python
def main():
    """Inicializa y ejecuta la simulación completa"""
```
- Muestra banner inicial con reglas
- Solicita número de desarrolladores al usuario
- Crea hilos (mezcla aleatoria de hackers/serfs)
- Espera a que todos terminen
- Muestra estadísticas finales detalladas
