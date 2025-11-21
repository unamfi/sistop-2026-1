import os
import struct
import threading
import queue
import time

# constantes globales
nombreImagen = "fiunamfs.img"
clusterSize = 1024 #dos sectores de 512 bytes
entradaSize = 64
inicioDirectorio = clusterSize      
directorioSize = 4 * clusterSize  


# colas para comunicar los hilos 
cola_ordenes = queue.Queue()
cola_respuestas = queue.Queue()

# lógica del sist de archivos

def validar_superbloque(f):
    #valida la version 26-1
    f.seek(0)
    # Limpiamos nulos y espacios del nombre
    nombre_fs = f.read(8).decode('ascii', errors='ignore').replace('\x00', '').strip()
    
    f.seek(10)
    
    version = f.read(5).decode('ascii', errors='ignore').replace('\x00', '').strip() 
    
    
    # print(f"DEBUG: Nombre='{repr(nombre_fs)}' Versión='{repr(version)}'")

    # Validación estricta
    if nombre_fs == "FiUnamFS" and version == "26-1":
        return True, f"Sistema detectado: {nombre_fs} Versión {version}"
    else:
        
        return False, f"Error: Se esperaba 'FiUnamFS' v'26-1', se encontró '{nombre_fs}' v'{version}'"

def buscar_entrada_libre(f):
    #Busca un hueco en el directorio para escribir un nuevo archivo
    f.seek(inicioDirectorio)
    for i in range(directorioSize // entradaSize):
        posicion = f.tell()
        entrada = f.read(entradaSize)
        tipo = entrada[0:1]
        # Marco entradda vacía
        
        if tipo == b'-' or tipo == b'/': 
            return posicion
    return None

def hSecundario():
    
    #Hilo secundario que se queda  esperando órdenes de la cola, procesa el archivo y responde.
    
    while True:
        try:
            # Esperar orden del Hilo Principal
            orden = cola_ordenes.get()
            
            if orden['comando'] == 'SALIR':
                cola_ordenes.task_done()
                break

            # Abrimos el archivo solo durante la operación para acceso exclusivo
            if not os.path.exists(nombreImagen):
                 cola_respuestas.put(("ERROR", "No se encuentra el archivo fiunamfs.img"))
                 cola_ordenes.task_done()
                 continue

            with open(nombreImagen, 'r+b') as f:
                
                # Leer superbloque
                if orden['comando'] == 'INFO':
                    valido, msg = validar_superbloque(f)
                    cola_respuestas.put(("OK" if valido else "ERROR", msg))

                # Listar directorio
                elif orden['comando'] == 'LS':
                    lista = []
                    f.seek(inicioDirectorio)
                    for _ in range(directorioSize // entradaSize):
                        entrada = f.read(entradaSize)

                        if entrada[0:1] == b'.': 
                            nombre = entrada[1:15].decode('ascii', errors='ignore').strip()
                            
                            cluster_ini = struct.unpack('<I', entrada[16:20])[0]
                            tamano = struct.unpack('<I', entrada[20:24])[0]
                            lista.append(f"{nombre.ljust(15)} | {tamano} bytes | Cluster {cluster_ini}")
                    cola_respuestas.put(("OK", lista))

                # Copiar a sistema
                elif orden['comando'] == 'GET':
                    nombre_buscado = orden['nombre']
                    encontrado = False
                    f.seek(inicioDirectorio)
                    
                    for _ in range(directorioSize // entradaSize):
                        entrada = f.read(entradaSize)
                        if entrada[0:1] == b'.':
                            nombre_leido = entrada[1:15].decode('ascii', errors='ignore').strip()
                            if nombre_leido == nombre_buscado:
                                
                                cluster_ini = struct.unpack('<I', entrada[16:20])[0]
                                tamano = struct.unpack('<I', entrada[20:24])[0]
                                
                                # Leer datos
                                f.seek(cluster_ini * clusterSize)
                                datos = f.read(tamano)
                                
                                # Escribir en disco local
                                with open(orden['destino'], 'wb') as out:
                                    out.write(datos)
                                
                                cola_respuestas.put(("OK", f"Archivo {nombre_buscado} extraído exitosamente."))
                                encontrado = True
                                break
                    
                    if not encontrado:
                        cola_respuestas.put(("ERROR", "Archivo no encontrado."))

                # copiar a FIUNAMFS (PUT)
                elif orden['comando'] == 'PUT':
                    ruta_origen = orden['origen']
                    nombre_destino = orden['nombre_dest']
                    
                    if not os.path.exists(ruta_origen):
                        cola_respuestas.put(("ERROR", "El archivo origen no existe."))
                    else:
                        tam_archivo = os.path.getsize(ruta_origen)
                        
                        
                        max_cluster_usado = 4 
                        f.seek(inicioDirectorio)
                        pos_directorio_libre = None
                        
                        # Barrido para buscar espacio en directorio y último cluster
                        for _ in range(directorioSize // entradaSize):
                            pos = f.tell()
                            entrada = f.read(entradaSize)
                            if entrada[0:1] == b'.':
                                c_ini = struct.unpack('<I', entrada[16:20])[0]
                                size = struct.unpack('<I', entrada[20:24])[0]
                                clusters_ocupados = (size + clusterSize - 1) // clusterSize
                                if (c_ini + clusters_ocupados) > max_cluster_usado:
                                    max_cluster_usado = c_ini + clusters_ocupados - 1
                            elif (entrada[0:1] == b'-' or entrada[0:1] == b'/') and pos_directorio_libre is None:
                                pos_directorio_libre = pos 

                        if pos_directorio_libre is None:
                            cola_respuestas.put(("ERROR", "Directorio lleno."))
                        else:
                            nuevo_cluster_inicio = max_cluster_usado + 1
                            
                            # Escribir datos
                            with open(ruta_origen, 'rb') as src:
                                f.seek(nuevo_cluster_inicio * clusterSize)
                                f.write(src.read())

                            # Actualizar directorio 
                            f.seek(pos_directorio_libre)
                            
                            nombre_fmt = nombre_destino[:14].ljust(14, ' ').encode('ascii')
                            f.write(b'.') 
                            f.write(nombre_fmt)
                            f.write(b'\x00') 
                            f.write(struct.pack('<I', nuevo_cluster_inicio)) 
                            f.write(struct.pack('<I', tam_archivo)) 
                            f.write(b'20260101000000') 
                            f.write(b'20260101000000') 
                            f.write(b'\x00' * 12)   
                            
                            cola_respuestas.put(("OK", f"Guardado en Cluster {nuevo_cluster_inicio}"))

                # eliminado de datos
                elif orden['comando'] == 'RM':
                    nombre_borrar = orden['nombre']
                    f.seek(inicioDirectorio)
                    borrado = False
                    for _ in range(directorioSize // entradaSize):
                        pos = f.tell()
                        entrada = f.read(entradaSize)
                        if entrada[0:1] == b'.':
                            nombre = entrada[1:15].decode('ascii', errors='ignore').strip()
                            if nombre == nombre_borrar:
                                
                                f.seek(pos)
                                f.write(b'-') 
                                f.write(b'.' * 14) 
                                cola_respuestas.put(("OK", f"Archivo {nombre} eliminado."))
                                borrado = True
                                break
                    if not borrado:
                        cola_respuestas.put(("ERROR", "Archivo no encontrado."))

            cola_ordenes.task_done()
            
        except Exception as e:
            cola_respuestas.put(("ERROR", f"Excepción en worker: {str(e)}"))
            cola_ordenes.task_done()


# --- INTERFAZ DE USUARIO (HILO PRINCIPAL) ---

def menuUsuario():
    print("\n--- Iniciando FiUnamFS ---")
    
    # Arrancar el hilo secundario
    t = threading.Thread(target=hSecundario, daemon=True)
    t.start()
    print("Hilo de Sistema de Archivos: activo")

    while True:
        print("\n" + "="*30)
        print("1. Info Superbloque")
        print("2. Listar Archivos")
        print("3. Copiar HACIA tu PC (Get)")
        print("4. Copiar HACIA FiUnamFS (Put)")
        print("5. Eliminar Archivo")
        print("6. Salir")
        opcion = input("Selecciona una opcion: ")

        if opcion == '1':
            cola_ordenes.put({'comando': 'INFO'})
        
        elif opcion == '2':
            cola_ordenes.put({'comando': 'LS'})
        
        elif opcion == '3':
            nom = input("Nombre archivo en FiUnamFS: ")
            dest = input("Nombre destino en tu PC: ")
            cola_ordenes.put({'comando': 'GET', 'nombre': nom, 'destino': dest})

        elif opcion == '4':
            orig = input("Ruta archivo en tu PC: ")
            nom_dest = input("Nombre para guardar en FiUnamFS: ")
            cola_ordenes.put({'comando': 'PUT', 'origen': orig, 'nombre_dest': nom_dest})

        elif opcion == '5':
            nom = input("Nombre archivo a borrar: ")
            cola_ordenes.put({'comando': 'RM', 'nombre': nom})

        elif opcion == '6':
            cola_ordenes.put({'comando': 'SALIR'})
            print("Cerrando sistema...")
            break
        
        else:
            print("Opción inválida")
            continue

        
        # El hilo principal espera la respuesta del secundario
        print("[Espera] Procesando en hilo secundario...")
        
        try:
            estado, mensaje = cola_respuestas.get(timeout=5) 
            
            if estado == "OK":
                print(f"✅ ÉXITO: {mensaje}")
                if isinstance(mensaje, list): 
                    print("-" * 20)
                    for linea in mensaje:
                        print(linea)
                    print("-" * 20)
            else:
                print(f"❌ ERROR: {mensaje}")
            
        except queue.Empty:
            print("⚠️ ERROR: El hilo del sistema de archivos no respondió a tiempo.")

if __name__ == "__main__":
    
    if not os.path.exists(nombreImagen):
        print(f"AVISO: No se detectó {nombreImagen}. Asegúrate de tener el archivo.")
    
    menuUsuario()
