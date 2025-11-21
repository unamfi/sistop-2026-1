import os
from . import utils as utils
from .directory_entry import DirectoryEntry

# Constantes del sistema de archivos según la especificación
SECTOR_SIZE = 512
CLUSTER_SECTORS = 2
CLUSTER_SIZE = SECTOR_SIZE * CLUSTER_SECTORS
FS_NAME = "FiUnamFS"
FS_VERSION = "26-1"
DIR_START_CLUSTER = 1
DIR_CLUSTERS = 3
DIR_ENTRY_SIZE = 64
DIR_ENTRIES = (DIR_CLUSTERS * CLUSTER_SIZE) // DIR_ENTRY_SIZE

class FileSystem:
  def __init__(self, img_path):
    self.img_path = img_path
    self._load_superblock()
    self._load_directory()
    
  def _load_superblock(self):
    with open(self.img_path, 'rb') as file_system:
      file_system.seek(0)
      super_block = file_system.read(CLUSTER_SIZE)
      
      name = super_block[0:9].rstrip(b'\x00').decode('ascii')
      version = super_block[10:15].rstrip(b'\x00').decode('ascii')
      label = super_block[20:36].rstrip(b'\x00').decode('ascii')
      cluster_size = utils.read_u32_le(super_block[40:44])
      reserved_directory_clusters = utils.read_u32_le(super_block[45:49])
      total_clusters = utils.read_u32_le(super_block[50:54])
            
      if name != FS_NAME or version != FS_VERSION:
        raise RuntimeError(f'El sistema de archivos no es válido, los datos encontrados son:\nnombre: {name}\nversión: {version}')
      
      self.super_block_data = {
        'name': name,
        'version': version,
        'label': label,
        'cluster_size': cluster_size,
        'reserved_directory_clusters': reserved_directory_clusters,
        'total_clusters': total_clusters
      }
      
      self.directory_offset = DIR_START_CLUSTER * cluster_size
      self.directory_size = reserved_directory_clusters * cluster_size
      self.data_start_cluster = DIR_START_CLUSTER + reserved_directory_clusters
      self.cluster_size = cluster_size
      self.total_clusters = total_clusters
      
  def _load_directory(self):
    with open(self.img_path, 'rb') as file_system:
      file_system.seek(self.directory_offset)
      raw = file_system.read(self.directory_size)
    
    self.entries = []
    for i in range(0, len(raw), DIR_ENTRY_SIZE):
      entry_chunk = raw[i:i+DIR_ENTRY_SIZE]
      entry = DirectoryEntry(entry_chunk)
      self.entries.append(entry)
      
  def list_entries(self):
    for entry in self.entries:
      if not entry.is_empty():
        print(entry)
        
  def find_entry(self, fname):
    for entry in self.entries:
      if entry.get_name_str() == fname:
        return entry
      
    return None
  
  def read_file_to_host(self, fname, outpath):
    entry = self.find_entry(fname)
    if not entry:
      raise FileNotFoundError(fname)
    
    start = entry.start_cluster * self.cluster_size
    size = entry.size
    with open(self.img_path, 'rb') as file_system:
      file_system.seek(start)
      data = file_system.read(size)
      
      with open(outpath, 'wb') as out_dir:
        out_dir.write(data)
        
  def _occupied_cluster_ranges(self):
    ranges = []
    for entry in self.entries:
      if entry.is_empty() or entry.size == 0:
        continue
      
      clusters_occupied = (entry.size + self.cluster_size - 1) // self.cluster_size
      ranges.append((entry.start_cluster, entry.start_cluster + clusters_occupied))
      
    ranges.sort()
    return ranges
        
  def _find_free_contiguous(self, clusters_needed):
    occupied = self._occupied_cluster_ranges()
    cur = self.data_start_cluster
    end = self.total_clusters
    
    merged = []
    for cluster_start, cluster_end in occupied:
      if cluster_end <= cur:
        continue
      if not merged:
        merged.append([cluster_start, cluster_end])
      else:
        if cluster_start <= merged[-1][1]:
          merged[-1][1] = max(merged[-1][1], cluster_end)
        else:
          merged.append([cluster_start, cluster_end])
          
    for cluster_start, cluster_end in merged:
      if cluster_start - cur >= clusters_needed:
        return cur
      cur = max(cur, cluster_end)
      
    if end - cur >= clusters_needed:
      return cur
    
    return None
  
  def _update_directory(self):
    with open(self.img_path, 'r+b') as file_system:
      file_system.seek(self.directory_offset)
      out = bytearray()
      for entry in self.entries:
        out.extend(entry.as_bytes())
        
      out = out[:self.directory_size].ljust(self.directory_size, b'\x00')
      file_system.write(out)
        
  def write_file_from_host(self, fpath, remote_name = None):  
    with open(fpath, 'rb') as file:
      data = file.read()
      
    size = len(data)
    clusters_needed = (size + self.cluster_size - 1) // self.cluster_size
    
    free_idx = None
    for idx, entry in enumerate(self.entries):
      if entry.is_empty():
        free_idx = idx
        break
      
    if not free_idx:
      raise RuntimeError("No hay entradas libres en el directorio")
    
    start_cluster = self._find_free_contiguous(clusters_needed)
    if not start_cluster:
      raise RuntimeError("No hay espacio contiguo suficiente para copiar el archivo")
    
    with open(self.img_path, 'r+b') as file_system:
      file_system.seek(start_cluster * self.cluster_size)
      file_system.write(data)
      
    entry = self.entries[free_idx]
    new_name = remote_name if remote_name else os.path.basename(fpath)
    entry.init_entry(new_name, start_cluster, size)
    
    self._update_directory()
  
  def delete_file(self, fname):
    entry = self.find_entry(fname)
    if not entry:
      raise FileNotFoundError(fname)
    
    entry.delete_entry()
    self._update_directory()