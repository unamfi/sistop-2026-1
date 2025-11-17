from modules.filesystem import FileSystem

def main():
  fs = FileSystem('C:/Users/alons/Desktop/sistop-2026-1/proyectos/2/AvilaAlonso-MedinaSamuel/fiunamfs.img')
  fs.list_entries()
  fs.write_file_from_host("C:/Users/alons/Downloads/create-a-python-script.webp", "python.webp")
  fs.list_entries()
  
if __name__ == '__main__':
  main()
  