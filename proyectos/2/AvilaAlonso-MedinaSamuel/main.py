from modules.filesystem import FileSystem

def main():
  fs = FileSystem('C:/Users/alons/Desktop/sistop-2026-1/proyectos/2/AvilaAlonso-MedinaSamuel/fiunamfs.img')
  fs.list_entries()
  fs.read_file_to_host('logo.png', 'C:/Users/alons/Desktop/sistop-2026-1/proyectos/2/AvilaAlonso-MedinaSamuel/logo.png')
  
if __name__ == '__main__':
  main()