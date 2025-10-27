
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Comparador de planificación de procesos.
Algoritmos: FCFS, SPN (SJF no expropiativo), RR q=1, RR q=4, SRR (Ronda egoísta)*

*SRR implementado como una variante de Round Robin que favorece procesos nuevos:
  - Quantum base q=1.
  - En su primera vez, un proceso recibe un 'bonus' de 2q y se inserta al frente.
  - Luego opera con q normal en cola FIFO (evita inanición).

Formato de salida inspirado en las capturas: para cada ronda se imprime
la carga, las métricas promedio (T, E, P) y la línea visual (Gantt con letras).
"""
import argparse
import random
import string
from dataclasses import dataclass
from typing import List, Tuple, Dict

@dataclass
class Proceso:
    nombre: str
    llegada: int
    rafaga: int

# -------------- Utilidades comunes --------------
def describir_carga(procs: List[Proceso]) -> Tuple[str, int]:
    partes = []
    total_t = 0
    for p in procs:
        partes.append(f"{p.nombre}: {p.llegada}, t={p.rafaga}")
        total_t += p.rafaga
    return "; ".join(partes), total_t

def procs_from_params(n: int, tmin: int, tmax: int, gapmax: int, rng: random.Random) -> List[Proceso]:
    nombres = list(string.ascii_uppercase)[:n]
    llegadas = [0]
    t = 0
    for _ in range(1, n):
        t += rng.randint(0, gapmax)
        llegadas.append(t)
    res = []
    for i, nom in enumerate(nombres):
        res.append(Proceso(nom, llegadas[i], rng.randint(tmin, tmax)))
    return res

def metrics_from_completion(procs: List[Proceso], completion: Dict[str, int]) -> Tuple[float, float, float]:
    T_sum = E_sum = P_sum = 0.0
    for p in procs:
        fin = completion[p.nombre]
        T = fin - p.llegada
        E = T - p.rafaga
        P = T / p.rafaga
        T_sum += T; E_sum += E; P_sum += P
    n = len(procs)
    return T_sum/n, E_sum/n, P_sum/n

# -------------- FCFS --------------
def fcfs(procs: List[Proceso]):
    orden = sorted(procs, key=lambda x: (x.llegada, x.nombre))
    t = 0
    line = []
    completion = {}
    for p in orden:
        if t < p.llegada:
            t = p.llegada  # ociosidad no impresa
        t_ini = t
        t_fin = t_ini + p.rafaga
        line.append(p.nombre * p.rafaga)
        completion[p.nombre] = t_fin
        t = t_fin
    T,E,P = metrics_from_completion(procs, completion)
    return T,E,P, "".join(line)

# -------------- SPN (SJF no expropiativo) --------------
def spn(procs: List[Proceso]):
    restantes = {p.nombre: p.rafaga for p in procs}
    llegada = {p.nombre: p.llegada for p in procs}
    byname = {p.nombre: p for p in procs}
    completado = {}
    t = 0
    line = []
    listos = []
    # eventos ordenados por llegada
    nombres_orden_llegada = [p.nombre for p in sorted(procs, key=lambda x: (x.llegada, x.nombre))]
    idx_arr = 0
    while len(completado) < len(procs):
        # encolar procesos que ya llegaron
        while idx_arr < len(nombres_orden_llegada) and llegada[nombres_orden_llegada[idx_arr]] <= t:
            nom = nombres_orden_llegada[idx_arr]
            listos.append(nom)
            idx_arr += 1
        if not listos:
            # saltar a próxima llegada
            if idx_arr < len(nombres_orden_llegada):
                t = llegada[nombres_orden_llegada[idx_arr]]
                continue
        # elegir el de menor ráfaga total (no restante), en empates alfabético
        candidato = min(listos, key=lambda nm: (byname[nm].rafaga, nm))
        listos.remove(candidato)
        # correr entero (no expropiativo)
        q = restantes[candidato]
        line.append(candidato * q)
        t += q
        completado[candidato] = t
    T,E,P = metrics_from_completion(procs, completado)
    return T,E,P, "".join(line)

# -------------- Round Robin genérico --------------
def rr(procs: List[Proceso], quantum: int):
    restantes = {p.nombre: p.rafaga for p in procs}
    llegada = {p.nombre: p.llegada for p in procs}
    completion = {}
    t = 0
    line = []
    # cola de listos
    orden_llegada = sorted(procs, key=lambda x: (x.llegada, x.nombre))
    idx_arr = 0
    cola = []
    while len(completion) < len(procs):
        while idx_arr < len(orden_llegada) and orden_llegada[idx_arr].llegada <= t:
            cola.append(orden_llegada[idx_arr].nombre)
            idx_arr += 1
        if not cola:
            if idx_arr < len(orden_llegada):
                t = orden_llegada[idx_arr].llegada
                continue
        actual = cola.pop(0)
        q = min(quantum, restantes[actual])
        line.append(actual * q)
        t += q
        restantes[actual] -= q
        while idx_arr < len(orden_llegada) and orden_llegada[idx_arr].llegada <= t:
            cola.append(orden_llegada[idx_arr].nombre)
            idx_arr += 1
        if restantes[actual] > 0:
            cola.append(actual)
        else:
            completion[actual] = t
    T,E,P = metrics_from_completion(procs, completion)
    return T,E,P, "".join(line)

# -------------- SRR (Ronda egoísta, variante) --------------
def srr(procs: List[Proceso], q_base: int = 1, bonus_factor: int = 2):
    restantes = {p.nombre: p.rafaga for p in procs}
    llegada = {p.nombre: p.llegada for p in procs}
    completion = {}
    t = 0
    line = []
    orden_llegada = sorted(procs, key=lambda x: (x.llegada, x.nombre))
    idx_arr = 0
    cola = []
    first_time = {p.nombre: True for p in procs}
    while len(completion) < len(procs):
        # nuevos al FRENTE en su primera aparición
        while idx_arr < len(orden_llegada) and orden_llegada[idx_arr].llegada <= t:
            cola.insert(0, orden_llegada[idx_arr].nombre)
            idx_arr += 1
        if not cola:
            if idx_arr < len(orden_llegada):
                t = orden_llegada[idx_arr].llegada
                continue
        actual = cola.pop(0)
        q = q_base * (bonus_factor if first_time[actual] else 1)
        q = min(q, restantes[actual])
        line.append(actual * q)
        t += q
        restantes[actual] -= q
        # llegadas durante el tramo -> al frente (primera vez)
        while idx_arr < len(orden_llegada) and orden_llegada[idx_arr].llegada <= t:
            cola.insert(0, orden_llegada[idx_arr].nombre)
            idx_arr += 1
        if restantes[actual] > 0:
            first_time[actual] = False
            cola.append(actual)
        else:
            completion[actual] = t
            first_time[actual] = False
    T,E,P = metrics_from_completion(procs, completion)
    return T,E,P, "".join(line)

# -------------- Main --------------
def main():
    ap = argparse.ArgumentParser(description="Comparador: FCFS, SPN, RR(q=1,q=4), SRR")
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--nproc", type=int, default=5)
    ap.add_argument("--tmin", type=int, default=2)
    ap.add_argument("--tmax", type=int, default=7)
    ap.add_argument("--gapmax", type=int, default=4)
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()
    rng = random.Random(args.seed)

    print("$ ./compara_planif")
    etiquetas = ["Primera", "Segunda", "Tercera", "Cuarta", "Quinta"]
    for r in range(1, args.runs + 1):
        carga = procs_from_params(args.nproc, args.tmin, args.tmax, args.gapmax, rng)
        desc, tot = describir_carga(carga)
        pref = etiquetas[r-1] if (r-1) < len(etiquetas) else f"Ronda {r}"
        print(f"- {pref} ronda:")
        print(f"  {desc} (tot:{tot})\n")

        T,E,P,g = fcfs(carga)
        print(f"  FCFS: T={T:.1f}, E={E:.1f}, P={P:.2f}")
        print(f"  {g}\n")

        T,E,P,g = spn(carga)
        print(f"  SPN:  T={T:.1f}, E={E:.1f}, P={P:.2f}")
        print(f"  {g}\n")

        T,E,P,g = rr(carga, quantum=1)
        print(f"  RR1:  T={T:.1f}, E={E:.1f}, P={P:.2f}")
        print(f"  {g}\n")

        T,E,P,g = rr(carga, quantum=4)
        print(f"  RR4:  T={T:.1f}, E={E:.1f}, P={P:.2f}")
        print(f"  {g}\n")

        T,E,P,g = srr(carga, q_base=1, bonus_factor=2)
        print(f"  SRR:  T={T:.1f}, E={E:.1f}, P={P:.2f}")
        print(f"  {g}\n")

if __name__ == "__main__":
    main()
