import struct
import threading

class File_system:
    def __init__(self, sys_dump):
        self.sys_dump = open(sys_dump, 'r+b')
        self.lock = threading.Lock()
        self._get_info()
        self.clusters = []
        self.directory_entries = []
        self.img = self.sys_dump
        self.dir_start = 1024
        self.dir_size = 4 * 1024

    def _get_info(self):
        self.sys_dump.seek(0)
        superblock = self.sys_dump.read(512)
        self.name = superblock[0:9].decode('ascii', errors='replace').rstrip('\x00')
        self.version = superblock[10:15].decode('ascii', errors='replace').rstrip('\x00')
        volume_label = superblock[20:36].decode('ascii', errors='replace').rstrip('\x00')

    def __str__(self):
         return f"The file system has the following information: {self.name} {self.version}"

    def __read_dir__(self):
        with self.lock:
            self.directory_entries = []  # lista de dicts
            self.img.seek(self.dir_start)
            data = self.img.read(self.dir_size)
            for i in range(0, self.dir_size, 64):
                entry = data[i:i+64]
                if len(entry) < 64: #Si quedan menos de 64 bytes ya no es valida la entrada
                    break
                file_type = entry[0:1].decode('ascii', errors='replace')
                name = entry[1:15].decode('ascii', errors='replace').rstrip('\x00').strip()

                #Si quedan entradas vacias o no usadas se omiten o se saltan
                if file_type == '/' or name == '...............':  # vacío según especificación
                    continue
                start_cluster = struct.unpack('<I', entry[16:20])[0]
                size = struct.unpack('<I', entry[20:24])[0]
                created = entry[24:38].decode('ascii', errors='replace')
                modified = entry[38:52].decode('ascii', errors='replace')
                self.directory_entries.append({
                    'name': name,
                    'type': file_type,
                    'start': start_cluster,
                    'size': size,
                    'created': created,
                    'modified': modified,
                    'dir_index': i // 64
                    })

    def __find_entry__(self, name):
      for e in self.directory_entries:
         if e['name'] == name:
            return e
      return None

    def __list_Files__(self):
        self.__read_dir__()
        for entry in self.directory_entries:
            print(f"{entry['name']}  {entry['size']} bytes  cluster {entry['start']}")


class Cluster:
    def __init__(self, start, end, name):
        self.start = start
        self.end = end
        self.name = name
        self.files = []

class File:
    def __init__(self, type, name, size, date):
        self.type = type
        self.name = name
        self.size = size
        self.date = date
        self.left_over_size = 0

if __name__ == "__main__":
    file_system = File_system('fiunamfs.img')
    print(file_system)
    file_system.__list_Files__()
    file_system.sys_dump.close()