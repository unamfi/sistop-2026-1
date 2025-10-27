import threading as th
import time
import random

def ts():
    return time.strftime("%H:%M:%S")

class ComedorGatosRatones:
    """
    Reglas que implementa:
    - Sólo un animal por plato (semáforo por plato).
    - Nunca comen gatos y ratones al mismo tiempo (platos juntos => se ven).
    - Alternancia por tandas: cuando termina una tanda, si hay espera de la otra
      especie, se cede el turno para evitar inanición.
    """
    def __init__(self, k_gatos, l_ratones, m_platos):
        self.k_gatos = k_gatos
        self.l_ratones = l_ratones
        self.m_platos = m_platos

        # Un semáforo por plato (1 = libre, 0 = ocupado)
        self.platos_sem = [th.Semaphore(1) for _ in range(m_platos)]

        # Estado global
        self.mutex = th.Lock()
        self.cond = th.Condition(self.mutex)

        self.activos_gatos = 0
        self.activos_ratones = 0
        self.esperando_gatos = 0
        self.esperando_ratones = 0
        self.platos_libres = m_platos

        # Turno actual: 'gatos' | 'ratones' | None
        self.turno = None

    # --------------- Gestión de platos (interno) ---------------
    def _reservar_plato(self):
        """Intenta tomar un plato libre (no bloqueante)."""
        for i, sem in enumerate(self.platos_sem):
            if sem.acquire(blocking=False):
                return i
        return None

    def _liberar_plato(self, plato_id: int):
        self.platos_sem[plato_id].release()

    # -------------------- Entrada / salida: GATO --------------------
    def gato_quiere_comer(self, id_gato: int) -> int:
        with self.cond:
            self.esperando_gatos += 1

            # Congela entrada si hay ratones esperando (para alternar tandas)
            if self.esperando_ratones > 0:
                self.turno = 'ratones'

            # Espera mientras haya ratones activos o turno de ratones
            while (self.activos_ratones > 0 or
                   (self.turno == 'ratones' and self.esperando_ratones > 0) or
                   self.platos_libres == 0):
                self.cond.wait()  

            self.esperando_gatos -= 1

            # Reserva un plato
            plato = self._reservar_plato()
            while plato is None:
                self.cond.wait()
                plato = self._reservar_plato()

            # Estado de tanda
            self.activos_gatos += 1
            self.platos_libres -= 1
            if self.turno is None:
                self.turno = 'gatos'

            print(f"[{ts()}] 🐱 Gato {id_gato} empieza en plato {plato}. Platos libres: {self.platos_libres}")
            return plato

    def gato_termina(self, id_gato: int, plato_id: int):
        with self.cond:
            self._liberar_plato(plato_id)
            self.activos_gatos -= 1
            self.platos_libres += 1
            print(f"[{ts()}] 🐱 Gato {id_gato} terminó en plato {plato_id}. Platos libres: {self.platos_libres}")

            # Si fue el último de su tanda, ceder turno si hay ratones esperando
            if self.activos_gatos == 0:
                if self.esperando_ratones > 0:
                    self.turno = 'ratones'
                else:
                    self.turno = None
            self.cond.notify_all()

    # -------------------- Entrada / salida: RATÓN -------------------
    def raton_quiere_comer(self, id_raton: int) -> int:
        with self.cond:
            self.esperando_ratones += 1

            # Congela entrada si hay gatos esperando (para alternar tandas)
            if self.esperando_gatos > 0:
                self.turno = 'gatos'

            while (self.activos_gatos > 0 or
                   (self.turno == 'gatos' and self.esperando_gatos > 0) or
                   self.platos_libres == 0):
                self.cond.wait()    

            self.esperando_ratones -= 1

            plato = self._reservar_plato()
            while plato is None:
                self.cond.wait()
                plato = self._reservar_plato()

            self.activos_ratones += 1
            self.platos_libres -= 1
            if self.turno is None:
                self.turno = 'ratones'

            print(f"[{ts()}] 🐭 Ratón {id_raton} empieza en plato {plato}. Platos libres: {self.platos_libres}")
            return plato
    
    def raton_termina(self, id_raton: int, plato_id: int):
        with self.cond:
            self._liberar_plato(plato_id)
            self.activos_ratones -= 1
            self.platos_libres += 1
            print(f"[{ts()}] 🐭 Ratón {id_raton} terminó en plato {plato_id}. Platos libres: {self.platos_libres}")

            if self.activos_ratones == 0:
                if self.esperando_gatos > 0:
                    self.turno = 'gatos'
                else:
                    self.turno = None
            self.cond.notify_all()

# ====================== Hilos de animales ======================
def vida_gato(gid: int, comedor: ComedorGatosRatones, fin: float):
    while time.time() < fin:
        time.sleep(random.uniform(0.6, 1.8))  # “pensar”
        plato = comedor.gato_quiere_comer(gid)
        time.sleep(random.uniform(0.8, 2.2))  # “comer”
        comedor.gato_termina(gid, plato)

def vida_raton(rid: int, comedor: ComedorGatosRatones, fin: float):
    while time.time() < fin:
        time.sleep(random.uniform(0.4, 1.6))  # “explorar”
        plato = comedor.raton_quiere_comer(rid)
        time.sleep(random.uniform(0.5, 1.2))  # “comer en sigilo”
        comedor.raton_termina(rid, plato)

# ====================== Simulación principal ======================
def simular(k_gatos=3, l_ratones=5, m_platos=2, tiempo_simulacion=15, seed=7):
    random.seed(seed)
    print(f"Iniciando simulación: {k_gatos} gatos, {l_ratones} ratones, {m_platos} platos")
    print("=" * 60)

    comedor = ComedorGatosRatones(k_gatos, l_ratones, m_platos) 
    fin = time.time() + tiempo_simulacion
    
    hilos = []
    for i in range (k_gatos):
        t = th.Thread(target=vida_gato, args=(i, comedor, fin), daemon=True)
        t.start(); hilos.append(t)

    for j in range(l_ratones):
        t = th.Thread(target=vida_raton, args=(j, comedor, fin), daemon=True)
        t.start(); hilos.append(t)

    for t in hilos:
        t.join(timeout=tiempo_simulacion + 2)

    print("=" * 60)
    print(f"[{ts()}] Simulación terminada.")

if __name__ == "__main__":
    simular(k_gatos = 3, l_ratones = 5, m_platos = 2, tiempo_simulacion= 20)