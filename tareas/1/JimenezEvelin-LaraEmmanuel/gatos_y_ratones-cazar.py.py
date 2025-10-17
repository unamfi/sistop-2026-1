"""
Simulación concurrente: Comedor de Gatos y Ratones
(Reglas cumplidas sin azar + sin deadlocks en Condition)
"""

import threading as th
import time
import random

def ts():
    return time.strftime("%H:%M:%S")

# ============================================================
# Clase principal: Comedor
# ============================================================

class Comedor:
    def __init__(self, gatos, ratones, platos):
        self.gatos = gatos
        self.ratones = ratones

        # Contador de platos (un recurso compartido) 
        self.platos_sem = th.Semaphore(platos)

        # Sincronización global
        self.mutex = th.Lock()
        self.cond = th.Condition(self.mutex)

        # Estado
        self.gatos_activos = 0
        self.ratones_activos = 0
        self.esperando_gatos = 0
        self.esperando_ratones = 0

        # Turno actual: 'gatos' | 'ratones' | None
        self.turno = None

        # Vida de ratones
        self.ratones_vivos = [True] * ratones

    # ==================== GATOS ====================
    def gato_entra(self, id_gato: int):
        with self.cond:
            self.esperando_gatos += 1

            # Si hay ratones esperando, congelamos la entrada de más gatos
            if self.esperando_ratones > 0:
                self.turno = 'ratones'

            # Espera mientras haya ratones comiendo o el turno sea de ratones
            while (self.ratones_activos > 0 or
                   (self.turno == 'ratones' and self.esperando_ratones > 0)):
                self.cond.wait()

            self.esperando_gatos -= 1

            # No bloquear el semáforo con el candado tomado: usar intento no bloqueante
            while not self.platos_sem.acquire(blocking=False):
                self.cond.wait()

            self.gatos_activos += 1
            if self.turno is None:
                self.turno = 'gatos'

            print(f"[{ts()}] 🐱 Gato {id_gato} empieza a comer.")

    def gato_sale(self, id_gato: int):
        with self.cond:
            self.gatos_activos -= 1
            self.platos_sem.release()
            print(f"[{ts()}] 🐱 Gato {id_gato} terminó de comer.")

            if self.gatos_activos == 0:
                self.turno = 'ratones' if self.esperando_ratones > 0 else None
            self.cond.notify_all()

    # ==================== RATONES ====================
    def raton_entra(self, id_raton: int) -> bool:
        with self.cond:
            if not self.ratones_vivos[id_raton]:
                return False

            self.esperando_ratones += 1

            # Si hay gatos esperando, congelamos la entrada de más ratones
            if self.esperando_gatos > 0:
                self.turno = 'gatos'

            # Regla clave: si hay gatos comiendo y un ratón intenta empezar,
            # el gato lo ve y lo come inmediatamente (sin tomar plato).
            if self.gatos_activos > 0:
                print(f"[{ts()}] 💀🐭 Ratón {id_raton} fue visto y cazado por un gato.")
                self.ratones_vivos[id_raton] = False
                self.esperando_ratones -= 1
                # No aumenta ratones_activos ni toma plato
                self.cond.notify_all()
                return False

            # Si no hay gatos activos, puede intentar tomar plato
            while (self.turno == 'gatos' and self.esperando_gatos > 0):
                self.cond.wait()

            # Intento no bloqueante para no retener el candado
            while not self.platos_sem.acquire(blocking=False):
                self.cond.wait()

            self.esperando_ratones -= 1
            self.ratones_activos += 1
            if self.turno is None:
                self.turno = 'ratones'

            print(f"[{ts()}] 🐭 Ratón {id_raton} empieza a comer.")
            return True

    def raton_sale(self, id_raton: int):
        with self.cond:
            if not self.ratones_vivos[id_raton]:
                return
            self.ratones_activos -= 1
            self.platos_sem.release()
            print(f"[{ts()}] 🐭 Ratón {id_raton} terminó de comer.")

            if self.ratones_activos == 0:
                self.turno = 'gatos' if self.esperando_gatos > 0 else None
            self.cond.notify_all()

# ============================================================
# Ciclo de vida de los animales
# ============================================================

def vida_gato(id_gato, comedor: Comedor, fin: float):
    while time.time() < fin:
        time.sleep(random.uniform(0.6, 1.5))  # pensando
        comedor.gato_entra(id_gato)
        time.sleep(random.uniform(0.8, 1.8))  # comiendo
        comedor.gato_sale(id_gato)

def vida_raton(id_raton, comedor: Comedor, fin: float):
    while time.time() < fin:
        time.sleep(random.uniform(0.5, 1.3))  # explorando
        if not comedor.raton_entra(id_raton):
            print(f"[{ts()}] 🕳️ Ratón {id_raton} desaparece del comedor.")
            break
        time.sleep(random.uniform(0.5, 1.0))  # comiendo
        comedor.raton_sale(id_raton)

# ============================================================
# Simulación principal
# ============================================================

def simular(k_gatos=3, l_ratones=5, m_platos=2, duracion=20, seed=7):
    random.seed(seed)
    print(f"\nIniciando simulación: {k_gatos} gatos, {l_ratones} ratones, {m_platos} platos")
    print("=" * 55)

    comedor = Comedor(k_gatos, l_ratones, m_platos)
    fin = time.time() + duracion

    hilos = []
    for i in range(k_gatos):
        t = th.Thread(target=vida_gato, args=(i, comedor, fin), daemon=True)
        t.start(); hilos.append(t)

    for j in range(l_ratones):
        t = th.Thread(target=vida_raton, args=(j, comedor, fin), daemon=True)
        t.start(); hilos.append(t)

    for t in hilos:
        t.join(timeout=duracion + 2)

    print("=" * 55)
    print(f"[{ts()}] Simulación terminada.")
    vivos = sum(comedor.ratones_vivos)
    print(f"Ratones sobrevivientes: {vivos}/{l_ratones}")

if __name__ == "__main__":
    simular()