import struct
from datetime import datetime

def read_u32_le(b_number):
  return struct.unpack('<I', b_number)[0]

def write_u32_le(number):
  return struct.pack('<I', number)

def get_now_timestamp():
  return datetime.utcnow().strftime('%Y%m%d%H%M%S')

def parse_timestamp(timestamp):
  timestamp = timestamp.strip()
  if len(timestamp) != 14 or not timestamp.isdigit():
    raise ValueError(f"Invalid timestamp: {timestamp}")
  
  year = timestamp[0:4]
  month = timestamp[4:6]
  day = timestamp[6:8]
  hour = timestamp[8:10]
  minute = timestamp[10:12]
  second = timestamp[12:14]
  
  return f"{year}-{month}-{day} {hour}:{minute}:{second}"
  