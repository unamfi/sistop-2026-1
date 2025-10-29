
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

"""
Comparador de planificadores de CPU para tareas de SO.
Algoritmos: FCFS/FIFO, RR(q), SPN (SJF no expropiativo), FB (MLFQ), SRR (Round Robin egoísta).
Incluye:
  - Generación de cargas aleatorias con huecos (tiempos de llegada arbitrarios).
  - Métricas promedio: T (turnaround), E (espera), P (penalización = T/servicio).
  - Esquema visual (Gantt textual) por algoritmo.

Uso rápido (en notebook/Colab):
  from compara_planif import run_demo
  run_demo(seed=42)

Uso como script (terminal):
  python compara_planif.py --rondas 2 --proc-min 4 --proc-max 6 --tmax 8 --seed 123 --no-gantt
"""

from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional, Callable
import random
import string
import math
import argparse

# -----------------------------
# Modelo de proceso
# -----------------------------
@dataclass
class Proc:
    name: str
    arrival: int   # tiempo de llegada
    service: int   # ráfaga total
    remain: int = field(init=False)
    start_time: Optional[int] = None
    finish_time: Optional[int] = None

    def __post_init__(self):
        self.remain = int(self.service)

    # helpers de métricas
    @property
    def T(self) -> int:
        assert self.finish_time is not None
        return self.finish_time - self.arrival

    @property
    def E(self) -> int:
        return self.T - self.service

    @property
    def P(self) -> float:
        return self.T / float(self.service)


# -----------------------------
# Utilidades
# -----------------------------
def clone_procs(base: List[Proc]) -> List[Proc]:
    """Copia fría (reseteada) de procesos para simular múltiples algoritmos sobre la misma carga."""
    out = []
    for p in base:
        q = Proc(p.name, p.arrival, p.service)
        out.append(q)
    return out

def metrics(procs: List[Proc]) -> Tuple[float, float, float]:
    T = sum(p.T for p in procs) / len(procs)
    E = sum(p.E for p in procs) / len(procs)
    P = sum(p.P for p in procs) / len(procs)
    return (T, E, P)

def format_metrics(T: float, E: float, P: float) -> str:
    return f"T={T:.1f}, E={E:.1f}, P={P:.2f}"

def alphabet_names(k: int) -> List[str]:
    letters = list(string.ascii_uppercase)
    out = []
    i = 0
    while len(out) < k:
        if i < len(letters):
            out.append(letters[i])
        else:
            # AA, AB, AC...
            idx = i - len(letters)
            first = letters[idx // len(letters)]
            second = letters[idx % len(letters)]
            out.append(first + second)
        i += 1
    return out

# -----------------------------
# Motor de simulación por ticks
# -----------------------------
def simulate(base_procs: List[Proc],
             scheduler: Callable,
             *, 
             quantum: Optional[int] = None,
             fb_quanta: Tuple[int, ...] = (1, 2, 4)) -> Tuple[List[Proc], str]:
    """
    Ejecuta la simulación por pasos discretos de tiempo (ticks = 1).
    Retorna (procesos_terminados, gantt_textual).
    El 'scheduler' es una función que decide qué proceso ejecutar en el tick actual.
    """
    # clonar procesos para este algoritmo
    procs = clone_procs(base_procs)

    # Reloj y estructuras
    time = 0
    finished = 0
    n = len(procs)
    gantt = []  # lista de símbolos por tick

    # Estados de ejecución gestionados por el scheduler (colas, contadores, etc.)
    state = scheduler("init", procs=procs, quantum=quantum, fb_quanta=fb_quanta)

    # Simulación hasta terminar todos
    while finished < n:
        # añadir llegadas al estado del planificador
        new_arrivals = [p for p in procs if p.arrival == time]
        if new_arrivals:
            scheduler("arrivals", state=state, arrivals=new_arrivals, now=time)

        # pedir al scheduler el siguiente proceso para este tick
        sel: Optional[Proc] = scheduler("select", state=state, now=time)

        if sel is None:
            # CPU ociosa
            gantt.append("-")
            time += 1
            continue

        # Marcar primer arranque si no existía
        if sel.start_time is None:
            sel.start_time = time

        # ejecutar 1 tick
        sel.remain -= 1
        gantt.append(sel.name[0])  # primera letra para el diagrama

        # avisar avance (para RR/FB/SRR y sus contadores de quantum)
        scheduler("tick", state=state, running=sel, now=time)

        time += 1

        # ¿terminó en este tick?
        if sel.remain == 0:
            sel.finish_time = time
            finished += 1
            scheduler("finish", state=state, finished=sel, now=time)

    return procs, "".join(gantt)

# -----------------------------
# Implementaciones de planificadores
# -----------------------------
def sched_fcfs(event, **kwargs):
    """FIFO: cola simple, no expropiativo."""
    if event == "init":
        procs = kwargs["procs"]
        state = {"queue": [], "current": None}
        return state
    state = kwargs["state"]
    if event == "arrivals":
        state["queue"].extend(sorted(kwargs["arrivals"], key=lambda p: p.arrival))
    elif event == "select":
        # si hay alguien ejecutándose (no expropiativo), mantenerlo hasta que termine
        if state.get("current") and state["current"].remain > 0:
            return state["current"]
        # tomar siguiente
        if state["queue"]:
            state["current"] = state["queue"].pop(0)
            return state["current"]
        state["current"] = None
        return None
    elif event == "tick":
        pass
    elif event == "finish":
        state["current"] = None

def sched_spn(event, **kwargs):
    """SPN = SJF no expropiativo: elegir el de menor servicio total entre listos."""
    if event == "init":
        return {"ready": [], "current": None}
    state = kwargs["state"]
    if event == "arrivals":
        state["ready"].extend(kwargs["arrivals"])
    elif event == "select":
        cur = state.get("current")
        if cur and cur.remain > 0:
            return cur
        if not state["ready"]:
            state["current"] = None
            return None
        # elegir por 'service' original (no por remain)
        state["ready"].sort(key=lambda p: p.service)
        state["current"] = state["ready"].pop(0)
        return state["current"]
    elif event == "tick":
        pass
    elif event == "finish":
        state["current"] = None

def sched_rr(event, **kwargs):
    """RR con quantum configurable."""
    if event == "init":
        return {"ready": [], "q": kwargs["quantum"], "qleft": 0, "current": None}
    state = kwargs["state"]
    if event == "arrivals":
        state["ready"].extend(kwargs["arrivals"])
    elif event == "select":
        cur = state.get("current")
        if cur and cur.remain > 0 and state["qleft"] > 0:
            return cur
        # cambio de contexto
        if cur and cur.remain > 0:
            state["ready"].append(cur)
        if state["ready"]:
            state["current"] = state["ready"].pop(0)
            state["qleft"] = state["q"]
            return state["current"]
        state["current"] = None
        return None
    elif event == "tick":
        state["qleft"] -= 1
    elif event == "finish":
        state["current"] = None
        state["qleft"] = 0

def sched_fb(event, **kwargs):
    """MLFQ (Feedback multinivel) con cuantums crecientes por nivel (e.g., 1,2,4)."""
    if event == "init":
        quanta = list(kwargs.get("fb_quanta", (1,2,4)))
        return {"levels": [[] for _ in quanta], "quanta": quanta, "qleft": 0, "level": None, "current": None}
    st = kwargs["state"]
    if event == "arrivals":
        for p in kwargs["arrivals"]:
            st["levels"][0].append(p)  # nuevos al nivel más alto
    elif event == "select":
        cur = st.get("current")
        if cur and cur.remain > 0 and st["qleft"] > 0:
            return cur
        # democión si agotó quantum (y no terminó)
        if cur and cur.remain > 0:
            lvl = st["level"]
            nxt = min(lvl + 1, len(st["levels"]) - 1)
            st["levels"][nxt].append(cur)
        # elegir más alta prioridad no vacía
        for i, q in enumerate(st["quanta"]):
            if st["levels"][i]:
                st["current"] = st["levels"][i].pop(0)
                st["level"] = i
                st["qleft"] = q
                return st["current"]
        st["current"] = None
        st["level"] = None
        st["qleft"] = 0
        return None
    elif event == "tick":
        st["qleft"] -= 1
    elif event == "finish":
        st["current"] = None
        st["qleft"] = 0
        st["level"] = None

def sched_srr(event, **kwargs):
    """
    RR egoísta (prioriza 'nuevos').
    Dos colas: NEW (cuántum=1) y OLD (cuántum=Qold=4 por defecto).
    Siempre servimos NEW; si está vacía, servimos OLD.
    Cuando llega un proceso, entra a NEW; si agota su quantum en NEW y no termina, pasa a OLD.
    """
    if event == "init":
        return {"new": [], "old": [], "qleft": 0, "current": None, "where": None, "Qold": 4}
    st = kwargs["state"]
    if event == "arrivals":
        st["new"].extend(kwargs["arrivals"])
    elif event == "select":
        cur = st.get("current")
        if cur and cur.remain > 0 and st["qleft"] > 0:
            return cur
        # Si el actual agotó quantum y no terminó, reencolar
        if cur and cur.remain > 0:
            if st["where"] == "new":
                st["old"].append(cur)  # tras primera rebanada, pasa a OLD
            else:
                st["old"].append(cur)
        # prioridad NEW
        if st["new"]:
            st["current"] = st["new"].pop(0)
            st["where"] = "new"
            st["qleft"] = 1
            return st["current"]
        if st["old"]:
            st["current"] = st["old"].pop(0)
            st["where"] = "old"
            st["qleft"] = st["Qold"]
            return st["current"]
        st["current"] = None
        st["where"] = None
        st["qleft"] = 0
        return None
    elif event == "tick":
        st["qleft"] -= 1
    elif event == "finish":
        st["current"] = None
        st["where"] = None
        st["qleft"] = 0

# -----------------------------
# Generador de cargas
# -----------------------------
def gen_workload(n: int, tmax: int, smin: int = 1, smax: int = 10, *, with_gaps: bool = True, rng: random.Random = random) -> List[Proc]:
    """
    Genera 'n' procesos con llegada uniforme en [0, tmax] (si with_gaps=True) o en 0.. (sin huecos si False).
    Duraciones uniformes en [smin, smax].
    """
    names = alphabet_names(n)
    if with_gaps:
        arrivals = [rng.randint(0, tmax) for _ in range(n)]
    else:
        arrivals = [0]*n
    services = [rng.randint(smin, smax) for _ in range(n)]
    procs = [Proc(name=nm, arrival=a, service=s) for nm, a, s in zip(names, arrivals, services)]
    return sorted(procs, key=lambda p: (p.arrival, p.name))

def describe_workload(procs: List[Proc]) -> str:
    parts = [f"{p.name}: a={p.arrival}, t={p.service}" for p in procs]
    total = sum(p.service for p in procs)
    return " | ".join(parts) + f"   (tot:{total})"

# -----------------------------
# Ejecutor por rondas
# -----------------------------
ALGOS = {
    "FCFS": (sched_fcfs, {}),
    "RR1":  (sched_rr, {"quantum": 1}),
    "RR4":  (sched_rr, {"quantum": 4}),
    "SPN":  (sched_spn, {}),
    "FB":   (sched_fb, {"fb_quanta": (1,2,4)}),
    "SRR":  (sched_srr, {}),
}

def run_round(procs: List[Proc], *, show_gantt: bool = True) -> str:
    lines = []
    for name, (sched, params) in ALGOS.items():
        sim_procs, gantt = simulate(procs, sched, **params)
        T,E,P = metrics(sim_procs)
        lines.append(f"{name}: {format_metrics(T,E,P)}")
        if show_gantt:
            lines.append(gantt)
    return "\n".join(lines)

def run_experiment(rondas: int = 2, proc_min: int = 3, proc_max: int = 7, tmax: int = 8, seed: Optional[int] = None, show_gantt: bool = True) -> None:
    rng = random.Random(seed)
    for r in range(1, rondas+1):
        n = rng.randint(proc_min, proc_max)
        wl = gen_workload(n, tmax=tmax, rng=rng, with_gaps=True)
        print(f"- Ronda {r}:")
        print(" " + describe_workload(wl))
        print(run_round(wl, show_gantt=show_gantt))
        print()

# -----------------------------
# Interfaz principal
# -----------------------------
def run_demo(seed: int = 42):
    print("Demostración rápida con 2 rondas...")
    run_experiment(rondas=2, proc_min=4, proc_max=6, tmax=8, seed=seed, show_gantt=True)

def main():
    ap = argparse.ArgumentParser(description="Comparación de planificadores de CPU (FCFS, RR, SPN, FB, SRR)")
    ap.add_argument("--rondas", type=int, default=2)
    ap.add_argument("--proc-min", type=int, default=3)
    ap.add_argument("--proc-max", type=int, default=7)
    ap.add_argument("--tmax", type=int, default=8, help="máximo tiempo de llegada (genera huecos)")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--no-gantt", action="store_true", help="no mostrar el esquema visual")
    args = ap.parse_args()

    run_experiment(rondas=args.rondas,
                   proc_min=args.proc_min,
                   proc_max=args.proc_max,
                   tmax=args.tmax,
                   seed=args.seed,
                   show_gantt=not args.no_gantt)

if __name__ == "__main__":
    main()
