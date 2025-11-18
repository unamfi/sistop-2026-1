# Tarea 04 - Tapia, Sierra

## Uso

```bash
python3 Tarea02.py
# O:
chmod +x Tarea02.py
./Tarea02.py
```

## Planificadores

- **FCFS**: First-Come First-Served (el que llega primero se ejecuta)
- **RR1**: Round-Robin con quantum=1
- **RR4**: Round-Robin con quantum=4
- **SPN**: Shortest Process Next (elige el más corto)
- **FB**: Feedback (colas múltiples con prioridades)
- **SRR**: Shortest-Remaining Round-Robin (elige el de menor tiempo restante)

## Métricas

- **T**: Tiempo de retorno promedio
- **E**: Tiempo de espera promedio
- **P**: Penalización promedio

## Ejemplo de salida

```
--- Ronda 1 (seed=100) ---
Procs: A:0,t=5, B:3,t=2, C:5,t=1, D:9,t=3, E:11,t=7 (tot:18)
FCFS: T=10.20, E=6.60, P=2.83
AAAAABBC-DDDEEEEEEE
RR1: T=13.00, E=9.40, P=3.61
ABABABCCDEDEABDEDEEEEEE
RR4: T=10.20, E=6.60, P=2.83
AAAAABBC-DDDEEEEEEE
SPN: T=8.40, E=4.80, P=2.33
AAAAABBCDDDEEEEEEEE
FB: T=11.80, E=8.20, P=3.28
ABABABCCDEABDEDEEDEEEEE
SRR: T=9.20, E=5.60, P=2.56
AAAAACBBDDDEEEEEEEE
```

En la terminal se agregan colores por cada proceso para diferenciar correctamente cada proceso
## Interpretación

- Cada letra representa una unidad de tiempo ejecutando ese proceso
- `-` = CPU sin ejecuciones (no hay nadie listo para ejecutar)

## Cómo funciona

```python
Proceso(nombre='A', llegada=0, rafaga=5)
```
- **nombre**: Identificador del proceso (A, B, C...)
- **llegada**: En qué momento llega el proceso
- **rafaga**: Cuánto tiempo de CPU necesita

### Flujo
1. **Genera/recibe procesos** con sus tiempos de llegada y ráfagas
2. **Ejecuta cada planificador** con los mismos procesos
3. **Registra el timeline** (qué proceso ejecuta en cada momento)
4. **Calcula métricas** por cada planificador:
   - **T** (turnaround): tiempo total desde que llega hasta que termina
   - **E** (espera): tiempo que pasó esperando en cola
   - **P** (penalización): T/ráfaga (cuánto más tardó de lo mínimo)

## Detalles técnicos

### namedtuple
Usamos `namedtuple` para crear procesos de forma simple:
```python
Proceso = namedtuple('Proceso', ['nombre', 'llegada', 'rafaga'])
p = Proceso('A', 0, 5)
print(p.nombre)  # 'A' (más legible que p[0])
```
