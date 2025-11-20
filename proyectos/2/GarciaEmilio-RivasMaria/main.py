import struct
import threading
import os

class Mover:
    def __init__(self, file_system):
        self.file_system = file_system
        self.input_dir = "input_files"
        self.output_dir = "output_files"
        self._create_directories()

    def delete_file_from_fs(self, filename):
        entry = self.file_system.__find_entry__(filename)
        if not entry:
            print(f"Error: File '{filename}' not found in FiUnamFS")
            return False

        try:
            dir_entry_position = self.file_system.dir_start + (entry['dir_index'] * 64)
            
            self.file_system.sys_dump.seek(dir_entry_position)
            current_entry = self.file_system.sys_dump.read(64)
            
            deleted_entry = bytearray(64)
            deleted_entry[0:1] = '/'  
            deleted_entry[1:15] = '.' * 14
            
            self.file_system.sys_dump.seek(dir_entry_position)
            self.file_system.sys_dump.write(deleted_entry)
            
            self.file_system.sys_dump.flush()
            
            self.file_system.__read_dir__()
            
            print(f"Successfully deleted '{filename}' from FiUnamFS")
            print(f"  Freed {entry['size']} bytes")
            print(f"  Freed {entry['start']} cluster(s)")
            print(f"  Directory entry {entry['dir_index']} marked as available")
            
            return True
            
        except Exception as e:
            print(f"Error deleting '{filename}' from FiUnamFS: {e}")
            return False

    def _create_directories(self):
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

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

    def add_file_to_fs(self, filename):
        input_path = os.path.join(self.input_dir, filename)
        
        if not os.path.exists(input_path):
            print(f"Error: File '{filename}' not found in {self.input_dir}")
            return False
        
        if self.file_system.__find_entry__(filename):
            print(f"Error: File '{filename}' already exists in FiUnamFS")
            return False
        
        file_size = os.path.getsize(input_path)
        total_capacity = self.file_system.total_clusters * self.file_system.cluster_size
        current_used = sum(entry['size'] for entry in self.file_system.directory_entries)
        
        if file_size > (total_capacity - current_used):
            print(f"Error: File '{filename}' is too large ({file_size} bytes)")
            print(f"Available space: {total_capacity - current_used} bytes")
            return False
        
        clusters_needed = (file_size + self.file_system.cluster_size - 1) // self.file_system.cluster_size
        
        free_clusters = self._find_free_clusters(clusters_needed)
        if not free_clusters:
            print(f"Error: Not enough contiguous free clusters for '{filename}'")
            print(f"Required: {clusters_needed} clusters")
            return False
        
        dir_entry_offset = self._find_free_directory_entry()
        if dir_entry_offset is None:
            print("Error: No free directory entries available")
            return False
        
        try:
            with open(input_path, 'rb') as input_file:
                file_data = input_file.read()
            
            start_cluster = free_clusters[0]
            bytes_written = 0
            
            for i, cluster_num in enumerate(free_clusters):
                cluster_position = cluster_num * self.file_system.cluster_size
                self.file_system.sys_dump.seek(cluster_position)
                
                chunk_size = min(self.file_system.cluster_size, len(file_data) - bytes_written)
                self.file_system.sys_dump.write(file_data[bytes_written:bytes_written + chunk_size])
                bytes_written += chunk_size
            
            import datetime
            now = datetime.datetime.now()
            created_str = now.strftime("%Y%m%d%H%M%S")
            
            entry_data = bytearray(64)
            
            entry_data[0:1] = '-'
            
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
            self.file_system.__read_dir__()
            
            print(f"Successfully added '{filename}' to FiUnamFS")
            print(f"  Size: {file_size} bytes")
            print(f"  Clusters used: {clusters_needed} (starting at cluster {start_cluster})")
            print(f"  Directory entry: {dir_entry_offset // 64}")
            
            return True
            
        except Exception as e:
            print(f"Error adding '{filename}' to FiUnamFS: {e}")
            return False

    def list_input_files(self):
        if not os.path.exists(self.input_dir):
            print("Input directory does not exist")
            return []

        files = os.listdir(self.input_dir)
        if not files:
            print("No files in input directory")
            return []

        print("Files in input directory:")
        for file in files:
            file_path = os.path.join(self.input_dir, file)
            file_size = os.path.getsize(file_path)
            print(f"  {file} ({file_size} bytes)")
        
        return files
    def _create_directories(self):
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

    def extract_file(self, filename):
        entry = self.file_system.__find_entry__(filename)
        if not entry:
            print(f"Error: File '{filename}' not found in FiUnamFS")
            return False

        try:
            cluster_size = self.file_system.cluster_size
            file_position = entry['start'] * cluster_size
            
            self.file_system.sys_dump.seek(file_position)
            file_data = self.file_system.sys_dump.read(entry['size'])
            
            output_path = os.path.join(self.output_dir, filename)
            with open(output_path, 'wb') as output_file:
                output_file.write(file_data)
            
            print(f"Successfully extracted '{filename}' to {output_path}")
            return True
            
        except Exception as e:
            print(f"Error extracting '{filename}': {e}")
            return False

    def extract_all_files(self):
        if not self.file_system.directory_entries:
            print("No files found in FiUnamFS")
            return False

        success_count = 0
        total_files = len(self.file_system.directory_entries)
        
        print(f"Extracting {total_files} files from FiUnamFS...")
        
        for entry in self.file_system.directory_entries:
            if self.extract_file(entry['name']):
                success_count += 1
        
        print(f"Extraction complete: {success_count}/{total_files} files successfully extracted")
        return success_count == total_files

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
        self._load_clusters()
        self.__read_dir__()

    def _get_info(self):
        self.sys_dump.seek(0)
        superblock = self.sys_dump.read(512)
        self.name = superblock[0:9].decode('ascii', errors='replace').rstrip('\x00')
        self.version = superblock[10:15].decode('ascii', errors='replace').rstrip('\x00')
        self.volume_label = superblock[20:36].decode('ascii', errors='replace').rstrip('\x00')
        self.cluster_size = struct.unpack('<I', superblock[40:44])[0]
        self.dir_clusters = struct.unpack('<I', superblock[45:49])[0]
        self.total_clusters = struct.unpack('<I', superblock[50:54])[0]

    def _load_clusters(self):
        for i in range(self.total_clusters):
            start = i * self.cluster_size
            end = start + self.cluster_size - 1
            cluster = Cluster(start, end, f"Cluster_{i}")
            self.clusters.append(cluster)

    def __read_dir__(self):
        with self.lock:
            self.directory_entries = []
            for cluster in self.clusters:
                cluster.files = []
                
            self.img.seek(self.dir_start)
            data = self.img.read(self.dir_size)
            
            for i in range(0, self.dir_size, 64):
                entry = data[i:i+64]
                if len(entry) < 64:
                    break
                    
                file_type = entry[0:1].decode('ascii', errors='replace')
                name = entry[1:15].decode('ascii', errors='replace').rstrip('\x00').strip()

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

    def __list_Files__(self):
        print("=" * 80)
        print("DIRECTORY LISTING")
        print("=" * 80)
        print(f"{'Name':<20} {'Type':<6} {'Size (bytes)':<12} {'Cluster':<8} {'Created':<16} {'Modified':<16}")
        print("-" * 80)
        
        for entry in self.directory_entries:
            created_str = self._format_date(entry['created'])
            modified_str = self._format_date(entry['modified'])
            print(f"{entry['name']:<20} {entry['type']:<6} {entry['size']:<12} {entry['start']:<8} {created_str:<16} {modified_str:<16}")

    def _format_date(self, date_str):
        if len(date_str) == 14 and date_str.isdigit():
            return f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]} {date_str[8:10]}:{date_str[10:12]}"
        return date_str

    def get_file_system_info(self):
        print("=" * 80)
        print("FILE SYSTEM INFORMATION")
        print("=" * 80)
        print(f"File System Name: {self.name}")
        print(f"Version: {self.version}")
        print(f"Volume Label: {self.volume_label}")
        print(f"Cluster Size: {self.cluster_size} bytes")
        print(f"Directory Clusters: {self.dir_clusters}")
        print(f"Total Clusters: {self.total_clusters}")
        print(f"Total Capacity: {self.total_clusters * self.cluster_size / 1024:.1f} KB")
        print(f"Directory Start: {self.dir_start} bytes")
        print(f"Directory Size: {self.dir_size} bytes")
        print(f"Files Found: {len(self.directory_entries)}")
        
        total_used_space = sum(entry['size'] for entry in self.directory_entries)
        total_capacity = self.total_clusters * self.cluster_size
        print(f"Total Used Space: {total_used_space} bytes")
        print(f"Free Space: {total_capacity - total_used_space} bytes")
        print(f"Usage: {(total_used_space / total_capacity * 100):.2f}%")

    def list_files_by_cluster(self):
        print("=" * 80)
        print("FILES BY CLUSTER")
        print("=" * 80)
        
        used_clusters = [cluster for cluster in self.clusters if cluster.files]
        
        if not used_clusters:
            print("No files found in any cluster.")
            return
            
        for cluster in used_clusters:
            print(f"\n{cluster.name}:")
            print(f"  Cluster Range: {cluster.start:,} - {cluster.end:,} bytes")
            print(f"  Files in cluster: {len(cluster.files)}")
            print("  " + "-" * 60)
            
            for file in cluster.files:
                file_size_kb = file.size / 1024
                clusters_needed = (file.size + self.cluster_size - 1) // self.cluster_size
                print(f"      {file.name}")
                print(f"      Size: {file.size:,} bytes ({file_size_kb:.2f} KB)")
                print(f"      Type: {file.type}")
                print(f"      Clusters needed: {clusters_needed}")
                print(f"      Created: {self._format_date(file.created)}")
                print(f"      Modified: {self._format_date(file.modified)}")

    def get_detailed_file_info(self, filename):        
        entry = self.__find_entry__(filename)
        if not entry:
            print(f"File '{filename}' not found.")
            return
            
        print("=" * 80)
        print(f"DETAILED FILE INFORMATION: {filename}")
        print("=" * 80)
        print(f"Name: {entry['name']}")
        #print(f"Type: {entry['type']}")
        print(f"Size: {entry['size']} bytes ({entry['size'] / 1024:.2f} KB)")
        print(f"Start Cluster: {entry['start']}")
        print(f"Directory Index: {entry['dir_index']}")
        print(f"Created: {self._format_date(entry['created'])}")
        print(f"Modified: {self._format_date(entry['modified'])}")
        
        clusters_needed = (entry['size'] + self.cluster_size - 1) // self.cluster_size
        wasted_space = (clusters_needed * self.cluster_size) - entry['size']
        print(f"Clusters Required: {clusters_needed}")
        print(f"Wasted Space (internal fragmentation): {wasted_space} bytes")
        print(f"Efficiency: {(entry['size'] / (clusters_needed * self.cluster_size) * 100):.2f}%")

    def __str__(self):
        return f"FiUnamFS v{self.version} - {self.volume_label} - {len(self.directory_entries)} files"

class Cluster:
    def __init__(self, start, end, name):
        self.start = start
        self.end = end
        self.name = name
        self.files = []

    def __str__(self):
        return f"{self.name}: {len(self.files)} files, {self.start:,}-{self.end:,} bytes"

    def add_file(self, file):
        self.files.append(file)

    def remove_file(self, file_name):
        self.files = [f for f in self.files if f.name != file_name]

    def get_detailed_info(self):
        total_file_size = sum(file.size for file in self.files)
        return {
            'name': self.name,
            'file_count': len(self.files),
            'total_size': total_file_size,
            'start': self.start,
            'end': self.end,
            'files': [file.name for file in self.files]
        }

class File:
    def __init__(self, file_type, name, size, created_date):
        self.type = file_type
        self.name = name
        self.size = size
        self.created = created_date
        self.modified = None
        self.start_cluster = None
        self.left_over_size = 0

    def __str__(self):
        return f"{self.name} ({self.size} bytes, cluster {self.start_cluster})"

    def get_info(self):
        return (f"File: {self.name}\n"
                f"Size: {self.size} bytes\n"
                f"Cluster: {self.start_cluster}\n"
                f"Created: {self.created}\n"
                f"Modified: {self.modified}")

if __name__ == "__main__":
    file_system = File_system('fiunamfs.img')
    mover = Mover(file_system)

    mover.add_file_to_fs('hola.txt')
    mover.delete_file_from_fs('hola.txt')
    file_system.list_files_by_cluster()
    mover.extract_all_files()
    
    file_system.sys_dump.close()