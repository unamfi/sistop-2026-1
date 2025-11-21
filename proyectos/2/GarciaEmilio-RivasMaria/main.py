import struct
import threading
import os
import time
import datetime
import queue

"""
En este codigo se hizo el proyecto 2. Se utilizo OOP para la estructura y jefe trabajador con colas.
Las clases son:
    - File_system: Esta es la clase que nos maneja fiunamfs.img . Este el jefe
    - Mover: Esta es la clase que maneja a los cambios de archivos de fiunamfs.img y nuestro sistema. Este es el trabajador
    - Cluster: Esta clase se utiliza para manejar los clusters. No se uso mucho ya que no hay operaciones que suceden a su nivel
    - File: Basicamente lo mismo que los clusters pero para los archivos
"""

class File_system:
    def __init__(self, sys_dump):
        self.sys_dump = open(sys_dump, 'r+b')
        #El candado para sincronizar nuestros hilos
        self.lock = threading.RLock()
        self._get_info()
        self.clusters = []
        self.directory_entries = []
        self.img = self.sys_dump
        self.dir_start = 1024
        self.dir_size = 4 * 1024
        self._load_clusters()
        self.__read_dir__()

    #los datos que conseguimos aqui es la informacion del sistema de archivos directamente en el superbloque
    def _get_info(self):
        self.sys_dump.seek(0)
        superblock = self.sys_dump.read(512)
        self.name = superblock[0:9].decode('ascii', errors='replace').rstrip('\x00')
        self.version = superblock[10:15].decode('ascii', errors='replace').rstrip('\x00')
        self.volume_label = superblock[20:36].decode('ascii', errors='replace').rstrip('\x00')
        self.cluster_size = struct.unpack('<I', superblock[40:44])[0]
        self.dir_clusters = struct.unpack('<I', superblock[45:49])[0]
        self.total_clusters = struct.unpack('<I', superblock[50:54])[0]
    #Cargamos los clusters
    def _load_clusters(self):
        for i in range(self.total_clusters):
            start = i * self.cluster_size
            end = start + self.cluster_size - 1
            cluster = Cluster(start, end, f"Cluster_{i}")
            self.clusters.append(cluster)
    #Se leen los directorios
    def __read_dir__(self):
        self.directory_entries = []
        for cluster in self.clusters:
            cluster.files = []
        
        self.img.seek(self.dir_start)
        data = self.img.read(self.dir_size)
        
        #Se va en bloques de 64 ya que ese es el tamaño de las entradas
        for i in range(0, self.dir_size, 64):
            entry = data[i:i+64]
            if len(entry) < 64:
                break
                
            file_type = entry[0:1].decode('ascii', errors='replace')
            name = entry[1:15].decode('ascii', errors='replace').rstrip('\x00').strip()
            #Nos saltamos los registros vacios
            if (file_type == '/' or 
                name == '...............' or 
                name == '--------------' or 
                name == '' or
                file_type not in ['-', '.']):
                continue
                
            start_cluster = struct.unpack('<I', entry[16:20])[0]
            size = struct.unpack('<I', entry[20:24])[0]
            if start_cluster == 0 or start_cluster >= len(self.clusters) or size == 0:
                continue

            #Conseguimos la info de los clusters
            created = entry[24:38].decode('ascii', errors='replace')
            modified = entry[38:52].decode('ascii', errors='replace')
            
            file_obj = File(file_type, name, size, created)
            file_obj.modified = modified
            file_obj.start_cluster = start_cluster
            
            if start_cluster < len(self.clusters):
                self.clusters[start_cluster].files.append(file_obj)
            
            self.directory_entries.append({
                'name': name,
                'type': file_type,
                'start': start_cluster,
                'size': size,
                'created': created,
                'modified': modified,
                'dir_index': i // 64,
                'file_obj': file_obj
            })

    def __find_entry__(self, name):
        for e in self.directory_entries:
            if e['name'] == name:
                return e
        return None

    #Para cambiar el formato de tiempo a algo que se entiende mejor a humanos
    def _format_date(self, date_str):
        if len(date_str) == 14 and date_str.isdigit():
            return f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]} {date_str[8:10]}:{date_str[10:12]}"
        return date_str

    #Un print con los archivos en el sistema sin tanta info
    def __list_Files__(self):
        result = "=" * 80 + "\n"
        result += "Directorio - FiUnamFS\n"
        result += "=" * 80 + "\n"
        result += f"{'Nombre':<20} {'Tipo':<6} {'Tamaño (bytes)':<12} {'Cluster':<8} {'Creado':<16} {'Modificado':<16}\n"
        result += "-" * 80 + "\n"
        
        for entry in self.directory_entries:
            created_str = self._format_date(entry['created'])
            modified_str = self._format_date(entry['modified'])
            result += f"{entry['name']:<20} {entry['type']:<6} {entry['size']:<12} {entry['start']:<8} {created_str:<16} {modified_str:<16}\n"
        
        result += f"\nNum. de archivos: {len(self.directory_entries)}"
        return result

    #Un print de un archivo con mas info detallada
    def get_detailed_file_info(self, filename):
        entry = self.__find_entry__(filename)
        if not entry:
            return f"Error: No existe '{filename}' en FiUnamFS"
            
        result = "=" * 80 + "\n"
        result += f"Info. Detallada de: {filename}\n"
        result += "=" * 80 + "\n"
        result += f"Nombre: {entry['name']}\n"
        result += f"Tamaño: {entry['size']} bytes ({entry['size'] / 1024:.2f} KB)\n"
        result += f"Principio del Cluster: {entry['start']}\n"
        result += f"Indice del dir.: {entry['dir_index']}\n"
        result += f"Creado: {self._format_date(entry['created'])}\n"
        result += f"Modificado: {self._format_date(entry['modified'])}\n"
        
        #Unos calculos extras por curiosidad
        clusters_needed = (entry['size'] + self.cluster_size - 1) // self.cluster_size
        wasted_space = (clusters_needed * self.cluster_size) - entry['size']
        efficiency = (entry['size'] / (clusters_needed * self.cluster_size)) * 100
        
        result += f"Clusters necesarios: {clusters_needed}\n"
        result += f"Fragmentacion interna: {wasted_space} bytes\n"
        result += f"Eficiencia: {efficiency:.2f}%\n"
        
        if clusters_needed > 0:
            result += f"Donde esta: {entry['start']} - {entry['start'] + clusters_needed - 1}\n"
            result += f"Espacio usado: {clusters_needed * self.cluster_size} bytes\n"
        
        return result

    #Un print sobre el sistema de archivos
    def get_file_system_info(self):
        total_used_space = sum(entry['size'] for entry in self.directory_entries)
        total_capacity = self.total_clusters * self.cluster_size
        
        result = "=" * 80 + "\n"
        result += "Info. del sistema de archivos\n"
        result += "=" * 80 + "\n"
        result += f"Nombre: {self.name}\n"
        result += f"Version: {self.version}\n"
        result += f"Etiqueta del volumen: {self.volume_label}\n"
        result += f"Tamaño del cluster: {self.cluster_size} bytes\n"
        result += f"Num. de dir. de clusters: {self.dir_clusters}\n"
        result += f"Archivos en el sistema: {len(self.directory_entries)}\n"
        result += f"Espacio usado: {total_used_space} bytes\n"
        result += f"Espacio libre: {total_capacity - total_used_space} bytes\n"
        result += f"% de uso: {(total_used_space / total_capacity * 100):.2f}%\n"
        
        return result
    #para cerrar el hilo
    def close(self):
        self.sys_dump.close()

class Mover(threading.Thread):
    def __init__(self, file_system):
        threading.Thread.__init__(self)
        self.file_system = file_system
        self.input_dir = "input_files"
        self.output_dir = "output_files"
        self.operation_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.running = True
        self.daemon = True
        self._create_directories()
        self.start()
    #El loop que mantiene vivo al hilo trabajador
    def run(self):
        print("El hilo Mover empieza")
        while self.running:
            try:
                operation, args = self.operation_queue.get(timeout=1.0)
                if operation == "SHUTDOWN":
                    break
                result = self._process_operation(operation, args)
                self.result_queue.put(result)
            except queue.Empty:
                continue
            except Exception as e:
                self.result_queue.put(f"Error hilo mover: {e}")

    #Hace la operacion que se le pide sacada de una cola
    def _process_operation(self, operation, args):
        try:
            if operation == "EXTRACT_FILE":
                return self._extract_file(args['filename'])
            elif operation == "EXTRACT_ALL":
                return self._extract_all_files()
            elif operation == "ADD_FILE":
                return self._add_file(args['filename'])
            elif operation == "DELETE_FILE":
                return self._delete_file(args['filename'])
            else:
                return f"Esa operacion no se tiene registrada: {operation}"
        except Exception as e:
            return f"Error hilo mover: {e}"

    #Crea los dirs. donde se van a tener los archivos de afuera. Aqui se pondria cambiar por una direccion 
    #en nuestro sistema pero estaba mas sencillo mantenerlo en una carpeta de esta forma no teniendo que copiar la direccion
    def _create_directories(self):
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

    def _extract_file(self, filename):
        entry = self.file_system.__find_entry__(filename)
        if not entry:
            return f"Error: No se encontro '{filename}' en FiUnamFS"

        try:
            #Se consigue donde esta posicionado el archivo en el sistema de archivos y lo lee
            file_position = entry['start'] * self.file_system.cluster_size
            self.file_system.sys_dump.seek(file_position)
            file_data = self.file_system.sys_dump.read(entry['size'])
        except Exception as e:
            return f"Error en el hilo mover: {e}"

        try:
            #Lo escribe afuera en output_files
            output_path = os.path.join(self.output_dir, filename)
            with open(output_path, 'wb') as output_file:
                output_file.write(file_data)
            return f"Se copio '{filename}' a {output_path}"
        except Exception as e:
            return f"Error en hilo mover al copiar: {e}"

    # Es basicamente el metodo de arriba pero en loop y saca todo
    def _extract_all_files(self):
        if not self.file_system.directory_entries:
            return "No hay archivos en el sistema"

        success_count = 0
        results = []
        
        for entry in self.file_system.directory_entries:
            result = self._extract_file(entry['name'])
            if "Successfully" in result:
                success_count += 1
                results.append(f"{entry['name']}")
            else:
                results.append(f"{entry['name']}: {result}")
        
        return f"Se copiaron: {success_count}/{len(self.file_system.directory_entries)} archivos\n" + "\n".join(results)

    def _add_file(self, filename):
        input_path = os.path.join(self.input_dir, filename)
        
        if not os.path.exists(input_path):
            return f"Error: '{filename}' no esta en la carpeta {self.input_dir}"
        
        if self.file_system.__find_entry__(filename):
            return f"Error: '{filename}' ya existe"
        
        #Se checa si el archivo si cabe en el sistema
        file_size = os.path.getsize(input_path)
        total_capacity = self.file_system.total_clusters * self.file_system.cluster_size
        current_used = sum(entry['size'] for entry in self.file_system.directory_entries)
        
        if file_size > (total_capacity - current_used):
            return f"Error: '{filename}' es demasiado grande, ({file_size} bytes)"
        
        #Busca los clusters (completos) para meter el archivo
        clusters_needed = (file_size + self.file_system.cluster_size - 1) // self.file_system.cluster_size
        free_clusters = self._find_free_clusters(clusters_needed)
        if not free_clusters:
            return f"Error: NO hay espacio continuo que pueda contener a '{filename}'"
        
        #Encuentra los directorios libres
        dir_entry_offset = self._find_free_directory_entry()
        if dir_entry_offset is None:
            return "Error: No hay espacio en el directorio"
        
        try:
            with open(input_path, 'rb') as input_file:
                file_data = input_file.read()
        except Exception as e:
            return f"Error en el hilo mover: {e}"
        
        #Se crea el cluster y se meter el archivo
        start_cluster = free_clusters[0]
        bytes_written = 0
        for i, cluster_num in enumerate(free_clusters):
            cluster_position = cluster_num * self.file_system.cluster_size
            self.file_system.sys_dump.seek(cluster_position)
            chunk_size = min(self.file_system.cluster_size, len(file_data) - bytes_written)
            self.file_system.sys_dump.write(file_data[bytes_written:bytes_written + chunk_size])
            bytes_written += chunk_size
        
        #Se crea la entrada en el directorio
        now = datetime.datetime.now()
        created_str = now.strftime("%Y%m%d%H%M%S")
        
        entry_data = bytearray(64)
        entry_data[0:1] = b'-'
        name_bytes = filename[:14].ljust(14, '\x00').encode('ascii')
        entry_data[1:15] = name_bytes
        entry_data[16:20] = struct.pack('<I', start_cluster)
        entry_data[20:24] = struct.pack('<I', file_size)
        entry_data[24:38] = created_str.encode('ascii')
        entry_data[38:52] = created_str.encode('ascii')
        
        dir_entry_position = self.file_system.dir_start + dir_entry_offset
        self.file_system.sys_dump.seek(dir_entry_position)
        self.file_system.sys_dump.write(entry_data)
        self.file_system.sys_dump.flush()
        
        #Se recarga el directorio para reflejar los cambios
        self.file_system.__read_dir__()
        
        return f"Se copio'{filename}' a FiUnamFS (tamaño: {file_size} bytes, clusters: {clusters_needed})"

    def _delete_file(self, filename):
        entry = self.file_system.__find_entry__(filename)
        if not entry:
            return f"Error: '{filename}' no esta en FiUnamFS"

        #En el dir se borra. No borramos los datos en el cluster ya que como no esta registrado sera sobreescrito
        #Esto hace la implementacion mas sencilla pero crea problemas de seguridad
        dir_entry_position = self.file_system.dir_start + (entry['dir_index'] * 64)
        
        deleted_entry = bytearray(64)
        deleted_entry[0:1] = b'/'
        deleted_entry[1:15] = b'.' * 14
        
        self.file_system.sys_dump.seek(dir_entry_position)
        self.file_system.sys_dump.write(deleted_entry)
        self.file_system.sys_dump.flush()
        
        self.file_system.__read_dir__()
        
        return f"Se borro '{filename}' de FiUnamFS (Se liberaron {entry['size']} bytes)"

    def _find_free_clusters(self, clusters_needed):
        used_clusters = set()
        for entry in self.file_system.directory_entries:
            file_clusters = (entry['size'] + self.file_system.cluster_size - 1) // self.file_system.cluster_size
            for i in range(file_clusters):
                used_clusters.add(entry['start'] + i)
        
        free_clusters = []
        for cluster_num in range(5, self.file_system.total_clusters):
            if cluster_num not in used_clusters:
                free_clusters.append(cluster_num)
                if len(free_clusters) >= clusters_needed:
                    return free_clusters[:clusters_needed]
            else:
                free_clusters = []
        
        return None

    def _find_free_directory_entry(self):
        self.file_system.sys_dump.seek(self.file_system.dir_start)
        directory_data = self.file_system.sys_dump.read(self.file_system.dir_size)
        
        for i in range(0, self.file_system.dir_size, 64):
            entry = directory_data[i:i+64]
            file_type = entry[0:1]
            name_raw = entry[1:15]
            
            if file_type == b'\x00' and all(b == 0 for b in name_raw):
                return i
        
        return None

    #Metodos para meter instrucciones a la cola
    def extract_file(self, filename):
        self.operation_queue.put(("EXTRACT_FILE", {"filename": filename}))
        return self._wait_for_result()

    def extract_all_files(self):
        self.operation_queue.put(("EXTRACT_ALL", {}))
        return self._wait_for_result()

    def add_file(self, filename):
        self.operation_queue.put(("ADD_FILE", {"filename": filename}))
        return self._wait_for_result()

    def delete_file(self, filename):
        self.operation_queue.put(("DELETE_FILE", {"filename": filename}))
        return self._wait_for_result()

    def _wait_for_result(self, timeout=30):
        try:
            result = self.result_queue.get(timeout=timeout)
            return result
        except queue.Empty:
            return "Error: La operacion ya tomo mucho tiempo"

    def list_input_files(self):
        if not os.path.exists(self.input_dir):
            return "La carpeta input_files no existe"
        
        files = os.listdir(self.input_dir)
        if not files:
            return "No hay archivos"
        
        result = "Los archivos son:\n"
        for file in files:
            file_path = os.path.join(self.input_dir, file)
            file_size = os.path.getsize(file_path)
            result += f"  {file} ({file_size} bytes)\n"
        
        return result

    def list_output_files(self):
        if not os.path.exists(self.output_dir):
            return "La carpeta output_files no existe"
        
        files = os.listdir(self.output_dir)
        if not files:
            return "No hay archivos en la carpeta"
        
        result = "Los archivos son:\n"
        for file in files:
            file_path = os.path.join(self.output_dir, file)
            file_size = os.path.getsize(file_path)
            result += f"  {file} ({file_size} bytes)\n"
        
        return result
    #Para el hilo trabajador / mover
    def stop(self):
        self.running = False
        self.operation_queue.put(("SHUTDOWN", {}))

class Cluster:
    def __init__(self, start, end, name):
        self.start = start
        self.end = end
        self.name = name
        self.files = []

    def __str__(self):
        return f"{self.name}: {len(self.files)} files, {self.start:,}-{self.end:,} bytes"

class File:
    def __init__(self, file_type, name, size, created_date):
        self.type = file_type
        self.name = name
        self.size = size
        self.created = created_date
        self.modified = None
        self.start_cluster = None

    def __str__(self):
        return f"{self.name} ({self.size} bytes, cluster {self.start_cluster})"

if __name__ == "__main__":
    print("Sistema de archivos: FiUnamFS")
    print("=" * 50)
    
    file_system = File_system('fiunamfs.img')
    mover = Mover(file_system)
    
    try:
        while True:
            print("\n=== MENU ===")
            print("1. Info de sistema")
            print("2. Dirs. del sistema")
            print("3. Info detallada de un archivo")
            print("4. Copiar un archivo hacia nuestro sistema")
            print("5. Copiar todos los archivos a nuestro sistema") 
            print("6. Agregar un archvio a fiunamfs")
            print("7. Borrar un archivo de fiunamfs")
            print("8. Archivos en input files")
            print("9. Archivos en output files")
            print("10. Salir")
            
            choice = input("\nSeleciona!: ").strip()
            
            if choice == "1":
                print(file_system.get_file_system_info())
            elif choice == "2":
                print(file_system.__list_Files__())
            elif choice == "3":
                filename = input("Nombre del archivo: ")
                print(file_system.get_detailed_file_info(filename))
            elif choice == "4":
                filename = input("Nombre del archivo: ")
                result = mover.extract_file(filename)
                print(result)
            elif choice == "5":
                result = mover.extract_all_files()
                print(result)
            elif choice == "6":
                filename = input("Nombre del archivo: ")
                result = mover.add_file(filename)
                print(result)
            elif choice == "7":
                filename = input("Nombre del archivo: ")
                result = mover.delete_file(filename)
                print(result)
            elif choice == "8":
                result = mover.list_input_files()
                print(result)
            elif choice == "9":
                result = mover.list_output_files()
                print(result)
            elif choice == "10":
                break
            else:
                print("Esa opcion no esta considerada")
                
    except KeyboardInterrupt:
        print("\nCerrando...")
    
    finally:
        mover.stop()
        file_system.close()
        mover.join(timeout=2.0)
        print("Se pararon los hilos.")