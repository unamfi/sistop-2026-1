from . import utils as utils

# Constantes de las entries según la especificación
TYPE_FILE = b'.'[0]
TYPE_FREE = b'-'[0]
EMPTY_NAME = b'--------------'

class DirectoryEntry:
  def __init__(self, raw=None):
    if raw:
      self.parse(raw)
    else:
      self.type = TYPE_FREE
      self.name = EMPTY_NAME
      self.start_cluster = 0
      self.size = 0
      self.created = b'0' * 14
      self.modified = b'0' * 14
      self.raw = None
      
  def parse(self, raw):
    self.raw = raw
    self.type = raw[0]
    self.name = raw[1:15]
    self.start_cluster = utils.read_u32_le(raw[16:20])
    self.size = utils.read_u32_le(raw[20:24])
    self.created = raw[24:38]
    self.modified = raw[38:52]
    
  def as_bytes(self):
    info_bytes = bytearray(64)
    info_bytes[0] = self.type
    
    name = self.name
    if isinstance(name, str):
      name = name.encode('ascii')
      
    name = name[:14]
    info_bytes[1:1+len(name)] = name
    info_bytes[16:20] = utils.write_u32_le(self.start_cluster)
    info_bytes[20:24] = utils.write_u32_le(self.size)
    
    created = self.created if isinstance(self.created, (bytes, bytearray)) else str(self.created).encode('ascii')
    info_bytes[24:38] = created[:14].ljust(14, b'\x00')
    
    modified = self.modified if isinstance(self.modified, (bytes, bytearray)) else str(self.modified).encode('ascii')
    info_bytes[38:52] = modified[:14].ljust(14, b'\x00')
    
    return bytes(info_bytes)
  
  def __str__(self):
    name_str = self.name if isinstance(self.name, str) else self.name.decode('ascii')
    created_str = self.created if isinstance(self.created, str) else self.created.decode('ascii')
    modified_str = self.modified if isinstance(self.modified, str) else self.modified.decode('ascii')
    return f"Name: {name_str}\tcreated: {utils.parse_timestamp(created_str)}\tmodified: {utils.parse_timestamp(modified_str)}"
    
  def is_empty(self):
    return self.name == EMPTY_NAME
  