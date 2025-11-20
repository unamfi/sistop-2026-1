import sys

class Proceso:
    def __init__(self, identificador, momento_llegada, tiempo_servicio):
        self.identificador = identificador       
        self.momento_llegada = momento_llegada   
        self.tiempo_servicio = tiempo_servicio   
        self.momento_finalizacion = 0          
        self.servicio_original = tiempo_servicio 

    def restablecer(self):
        #Devuelve el estado del proceso a sus valores iniciales
        self.tiempo_servicio = self.servicio_original
        self.momento_finalizacion = 0

# Imprimir las métricas de rendimiento (T, E, P)
def reportar_resultados (esquema_nombre, T_prom, E_prom, P_prom):
    print("")
    print("{}: T={}, E={}, P={}".format(esquema_nombre, T_prom, E_prom, P_prom))
    

# Función que calcula y muestra las métricas para cualquier algoritmo
def obtener_metricas(esquema, procesos_terminados):
    T, E, P = [], [], []
    for proceso in procesos_terminados:
        tiempo_retorno = proceso.momento_finalizacion - proceso.momento_llegada
        tiempo_espera = tiempo_retorno - proceso.servicio_original
        
        if proceso.servicio_original > 0:
            penalizacion = tiempo_retorno / proceso.servicio_original
        else:
            penalizacion = 0
            
        T.append(tiempo_retorno)
        E.append(tiempo_espera)
        P.append(penalizacion)
        
    obtener_metricas_T_prom = sum(T) / len(T)
    obtener_metricas_E_prom = sum(E) / len(E)
    obtener_metricas_P_prom = sum(P) / len(P)
    
    reportar_resultados (esquema, obtener_metricas_T_prom, obtener_metricas_E_prom, obtener_metricas_P_prom)


# Algoritmo Shortest Process Next (SPN)
def SPN(lista_procesos):
    procesos_completados = []
    tiempo_actual = 0
    
    
    cola_activos = [] 
    
    while any(p.tiempo_servicio > 0 for p in lista_procesos): 
        
        for p in lista_procesos:
            if p.momento_llegada <= tiempo_actual and p.tiempo_servicio > 0 and p not in cola_activos:
                cola_activos.append(p)
        
        if cola_activos:
            proceso_elegido = min(cola_activos, key=lambda p: p.tiempo_servicio)
            
            while proceso_elegido.tiempo_servicio != 0:
                proceso_elegido.tiempo_servicio -= 1
                tiempo_actual += 1
                print(proceso_elegido.identificador, end ="")
                
            proceso_elegido.momento_finalizacion = tiempo_actual
            procesos_completados.append(proceso_elegido)
            cola_activos.remove(proceso_elegido)
        else:
            tiempo_actual += 1
            
    obtener_metricas("SPN", lista_procesos)

# Algoritmo First Come First Serve (FCFS)
def FCFS(lista_procesos):
    tiempo_actual = 0
    procesos_completados = []
    
    for proceso in lista_procesos:
        
        if proceso.momento_llegada > tiempo_actual:
            tiempo_actual = proceso.momento_llegada
            
        while proceso.tiempo_servicio != 0:
            proceso.tiempo_servicio -= 1
            tiempo_actual += 1
            print(proceso.identificador, end ="")
            
        proceso.momento_finalizacion = tiempo_actual
        procesos_completados.append(proceso)
    
    obtener_metricas("FCFS", procesos_completados)


# Algoritmo RR4
def RR4(lista_procesos):
    tiempo_actual = 0
    quantum = 4
    
    while any(p.tiempo_servicio > 0 for p in lista_procesos):
        for proceso in lista_procesos:
            contador_ejecucion = 0
            
            if proceso.momento_llegada <= tiempo_actual and proceso.tiempo_servicio > 0:
                
                while (contador_ejecucion < quantum and proceso.tiempo_servicio > 0):
                    proceso.tiempo_servicio -= 1
                    tiempo_actual += 1
                    print(proceso.identificador, end ="")
                    contador_ejecucion += 1
                    
                    if proceso.tiempo_servicio == 0 and proceso.momento_finalizacion == 0:
                        proceso.momento_finalizacion = tiempo_actual
        
        if not any(p.momento_llegada <= tiempo_actual and p.tiempo_servicio > 0 for p in lista_procesos):
            tiempo_actual += 1
            
    obtener_metricas("RR4", lista_procesos)


# Algoritmo RR1
def RR1(lista_procesos):
    tiempo_actual = 0
    
    while any(p.tiempo_servicio > 0 for p in lista_procesos):
        for proceso in lista_procesos:
            if proceso.momento_llegada <= tiempo_actual and proceso.tiempo_servicio > 0:
                
                if proceso.tiempo_servicio > 0:
                    proceso.tiempo_servicio -= 1
                    tiempo_actual += 1
                    print(proceso.identificador, end ="")
                    
                    if proceso.tiempo_servicio == 0 and proceso.momento_finalizacion == 0:
                        proceso.momento_finalizacion = tiempo_actual

        if not any(p.momento_llegada <= tiempo_actual and p.tiempo_servicio > 0 for p in lista_procesos):
            tiempo_actual += 1
                        
    obtener_metricas("RR1", lista_procesos)


# Función principal para ejecutar todos los algoritmos en una ronda
def CoordinadorDePruebas(numero_ronda, lista_procesos):
    
    print("Ronda " + str(numero_ronda))
    for proceso in lista_procesos:
        print(str(proceso.identificador) +":"+ str(proceso.momento_llegada) +", T="+ str(proceso.servicio_original), end = '; ')
    print("\n")
    
    
    # Debemos asegurarnos de que el estado sea el correcto antes de cada ejecución.

    # 1. SPN
    SPN(lista_procesos)
    for p in lista_procesos: # Restablecer después de SPN
        p.restablecer() 
    print("")
    
    # 2. RR4
    RR4(lista_procesos)
    for p in lista_procesos: # Restablecer después de RR4
        p.restablecer()
    print("")
    
    # 3. RR1
    RR1(lista_procesos)
    for p in lista_procesos: # Restablecer después de RR1
        p.restablecer()
    print("")

    # 4. FCFS
    FCFS(lista_procesos)
    for p in lista_procesos: # Restablecer después de FCFS 
        p.restablecer()



def configurar_ejecuciones():
    def crear_proceso(identificador, llegada, servicio):
        return Proceso(identificador, llegada, servicio)

    # Conjunto 1
    conjunto1 = [
        crear_proceso('A',0,1), crear_proceso('B',1,2), crear_proceso('C',2,4),
        crear_proceso('D',3,8), crear_proceso('E',4,12)
    ]

    # Conjunto 2
    conjunto2 = [
        crear_proceso('A',0,20), crear_proceso('B',1,1), crear_proceso('C',2,1),
        crear_proceso('D',3,1), crear_proceso('E',4,1)
    ]

    # Conjunto 3
    conjunto3 = [
        crear_proceso('A',0,6), crear_proceso('B',5,5), crear_proceso('C',10,6),
        crear_proceso('D',15,5), crear_proceso('E',20,5)
    ]

    # Conjunto 4
    conjunto4 = [
        crear_proceso('A',0,10), crear_proceso('B',1,1), crear_proceso('C',2,8),
        crear_proceso('D',3,2), crear_proceso('E',4,5)
    ]

    # Conjunto 5 
    conjunto5 = [
        crear_proceso('A',0,2), crear_proceso('B',1,3), crear_proceso('C',2,1),
        crear_proceso('D',3,4), crear_proceso('E',4,5)
    ]

    return [conjunto1, conjunto2, conjunto3, conjunto4, conjunto5]


# Función principal de ejecución
def iniciar_simulacion():
    conjuntos_de_procesos = configurar_ejecuciones()
    
    for index, conjunto in enumerate(conjuntos_de_procesos):
        print("\n<--------------------------------------------------------->\n")
        CoordinadorDePruebas(index+1, conjunto)

# Bloque de ejecución principal
if __name__ == "__main__":
    iniciar_simulacion()