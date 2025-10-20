# Tejeda Vaca Abraham. Ejercicios de sincronización: Cruce del rio.

import threading as th
import random
import time
import argparse

# =========================
# Parámetros por defecto
# =========================
PERSONAS_POR_BALSA = 4  # Regla del problema: la balsa sólo zarpa con 4

class CruceDelRio:
    """
    Reglas del problema:
      - Sólo zarpan grupos de 4.
      - Grupos válidos: 2H+2S, 4H o 4S (¡prohibido 3+1!).
    Sincronización usada:
      - mutex para contadores y armado del grupo (región crítica)
      - dos semáforos (filas) para otorgar cupos por tipo
      - Barrier(4, action=...) para asegurar 4 a bordo y un único zarpe atómico
    Fairness simple:
      - Se prefiere 2H+2S si es posible; si no, 4 del mismo bando.
    """

    def __init__(self):
        # MUTEX:
        # Protege la región crítica donde se actualizan contadores de espera
        # y se decide/“publica” el siguiente grupo.
        self.mutex = th.Lock()

        # BARRERA:
        # Se dispara cuando 4 hilos llaman a wait(). La "action" se ejecuta
        # exactamente UNA vez por viaje (zarpe + llegada).
        self.barrera = th.Barrier(
            PERSONAS_POR_BALSA,
            action=self._accion_de_zarpe
        )

        # CONTADORES COMPARTIDOS (protegidos por self.mutex)
        self.hackers_esperando = 0
        self.serfs_esperando = 0

        # SEMÁFOROS (FILAS):
        # Cada release() “abre” un lugar de abordaje para ese tipo.
        # Cada acquire() consume un lugar (impide que suban más de los permitidos).
        self.fila_hackers = th.Semaphore(0)
        self.fila_serfs = th.Semaphore(0)

        # ESTADO DEL VIAJE ACTUAL:
        # Un lock separado evita condiciones de carrera al imprimir/leer el manifiesto.
        self.viaje_mutex = th.Lock()
        self.viaje_id = 0
        self.manifiesto_actual = "----"

    # ------------------------
    # Lógica de armado de grupo
    # ------------------------
    def _formar_grupo_bajo_mutex(self):
        """
        *** REGIÓN CRÍTICA ***
        PRE: self.mutex tomado.
        Toma una decisión global (atómica) del siguiente grupo que subirá:
          - decide cuántos H y cuántos S (según reglas/fairness)
          - publica lugares con semáforos (release)
          - registra el manifiesto (para imprimirlo al zarpar)
        Devuelve el manifiesto (str) si armó grupo; None si aún no hay suficiente gente.
        """
        liberar_h = liberar_s = 0

        # 1) Preferimos MEZCLA 2H+2S si hay suficientes
        if self.hackers_esperando >= 2 and self.serfs_esperando >= 2:
            liberar_h, liberar_s = 2, 2
            self.hackers_esperando -= 2
            self.serfs_esperando -= 2

        # 2) Si no se puede mezclar, permitimos 4 del MISMO bando
        elif self.hackers_esperando >= 4:
            liberar_h = 4
            self.hackers_esperando -= 4

        elif self.serfs_esperando >= 4:
            liberar_s = 4
            self.serfs_esperando -= 4

        else:
            return None  # Aún no hay un grupo válido de 4 → salir sin liberar nada

        # Manifiesto legible para el reporte del viaje
        manifiesto = (f"{liberar_h}H + {liberar_s}S"
                      if liberar_h and liberar_s
                      else (f"{liberar_h}H" if liberar_h else f"{liberar_s}S"))

        # PUBLICACIÓN DE CUPOS (SEMÁFOROS):
        # Cada release permite que UN hilo del tipo correspondiente “aborde”.
        for _ in range(liberar_h):
            self.fila_hackers.release()
        for _ in range(liberar_s):
            self.fila_serfs.release()

        # Guardamos el manifiesto del viaje de forma segura (viaje_mutex)
        with self.viaje_mutex:
            self.viaje_id += 1
            self.manifiesto_actual = manifiesto

        return manifiesto

    # ------------------------
    # Acción de la barrera (zarpe)
    # ------------------------
    def _accion_de_zarpe(self):
        """
        *** PUNTO DE SINCRONIZACIÓN GLOBAL ***
        Esta función la ejecuta EXACTAMENTE UN hilo cuando llegan los 4 a la barrera.
        Lee el manifiesto y simula el cruce (sleep controlado).
        """
        with self.viaje_mutex:
            manifiesto = self.manifiesto_actual
            vid = self.viaje_id

        print(f"🚣  Viaje #{vid}: Zarpa la balsa con {manifiesto}")
        time.sleep(0.10)  # Control de tiempos: duración del cruce (no busy-wait)
        print(f"✅  Viaje #{vid}: Llegaron a la otra orilla.\n")

    # ------------------------
    # Rutina de cada persona (hilo)
    # ------------------------
    def persona(self, idp: int, tipo: str):
        """
        Modelo de hilo:
          1) Llega a la orilla (log)
          2) Entra a REGIÓN CRÍTICA (mutex) para:
             - incrementarse en el contador del tipo
             - intentar armar grupo (si hay quorum) → publicar cupos
          3) Espera su turno en el SEMÁFORO de su tipo (acquire)
          4) Aborda (pequeño sleep)
          5) Espera en la BARRERA (se van juntos los 4)
        """
        # 1) Llega (log informativo – NO es sincronización)
        print(f"[{time.strftime('%H:%M:%S')}] {tipo} {idp:02d} llega a la orilla.")

        # 2) REGIÓN CRÍTICA: modificar contadores + posible armado del grupo
        with self.mutex:
            if tipo == "H":
                self.hackers_esperando += 1
            else:
                self.serfs_esperando += 1

            # Si hay quorum, publicar cupos de abordaje (vía semáforos)
            _ = self._formar_grupo_bajo_mutex()

        # 3) Esperar permiso de abordaje según el TIPO (SEMÁFORO)
        if tipo == "H":
            self.fila_hackers.acquire()
        else:
            self.fila_serfs.acquire()

        # 4) Abordar (sleep corto para observar interleaving sin consumir CPU)
        print(f"    {tipo} {idp:02d} aborda.")
        time.sleep(0.04)  # Control de tiempos: abordaje

        # 5) PUNTO DE ENCUENTRO: los 4 pasan la barrera y se dispara el zarpe
        self.barrera.wait()

def simular(n_personas=20, semilla=None, p_hacker=0.5):
    """
    Crea y lanza 'n_personas' hilos.
    - p_hacker controla la proporción H/S.
    - semilla permite reproducibilidad.
    - Se introducen sleeps aleatorios para simular tiempos de llegada reales.
    """
    if semilla is not None:
        random.seed(semilla)

    cruce = CruceDelRio()
    hilos = []

    for i in range(1, n_personas + 1):
        # Cada hilo representa una persona independiente (H o S)
        tipo = "H" if random.random() < p_hacker else "S"
        t = th.Thread(target=cruce.persona, args=(i, tipo), daemon=False)
        hilos.append(t)
        t.start()

        # CONTROL DE TIEMPOS DE LLEGADA:
        # Pausa pequeña y aleatoria para simular concurrencia “natural”
        # y evitar que todos lleguen exactamente al mismo tiempo.
        time.sleep(random.uniform(0.01, 0.07))

    # Esperar a que todos los hilos terminen (ejecución FINITA)
    for t in hilos:
        t.join()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cruce del río con semáforos + barrera")
    parser.add_argument("--personas", type=int, default=20, help="Total de personas a simular")
    parser.add_argument("--seed", type=int, default=None, help="Semilla para reproducibilidad")
    parser.add_argument("--p_hacker", type=float, default=0.5, help="Probabilidad de que una persona sea H (0..1)")
    args = parser.parse_args()

    simular(args.personas, args.seed, args.p_hacker)