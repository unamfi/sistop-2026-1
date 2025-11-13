import struct

class File_system:
    def __init__(self, sys_dump):
        self.sys_dump = open(sys_dump, 'rb')
        self._get_info()
        self.clusters = []
    
    def _get_info(self):
            superblock = self.sys_dump.read(512)
            self.name = superblock[0:8].decode('ascii', errors='replace')
            self.version = superblock[8:16].decode('ascii', errors='replace')
            volume_label = superblock[16:52].decode('ascii', errors='replace')

    def __str__(self):
         return f"The file system has the following information: {self.name} {self.version}"
            
            
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