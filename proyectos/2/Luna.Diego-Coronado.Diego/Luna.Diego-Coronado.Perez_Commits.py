import os
import struct
import threading
import time
from datetime import datetime


TAMANO_DISQUETE = 1440 * 1024
TAMANO_SECTOR = 512
TAMANO_CLUSTER_DEFECTO = 1024  
TAMANO_ENTRADA = 64
SUPERBLOQUE_CLUSTER = 0

CLUSTERS_DIRECTORIO_DEFECTO = 4 
NOMBRE_SISTEMA_ARCHIVOS = 'FiUnamFS'

VERSION_SISTEMA = '26-1'  
ARCHIVO_IMAGEN = 'fiunamfs.img'


archivo_mutex = threading.Lock() 

FILE_MARK = b'\x2d'             

EMPTY_MARK = b'\x2f'            

EMPTY_NAME_MARKER = b'.' * 14 


def CLEAR():
    os.system('cls' if os.name == 'nt' else 'clear')

def pausa():
    input("\n\tPresione Enter para continuar...")

def menuMainImp():
    print("\n\t----------------------------------------------")
    print(f"\t      Sistema de Archivos {NOMBRE_SISTEMA_ARCHIVOS} v{VERSION_SISTEMA}")
    print("\t----------------------------------------------")
    print("\t1. Listar directorio")
    print("\t2. Copiar archivo desde FiUnamFS al sistema (PC)")
    print("\t3. Copiar archivo desde el sistema (PC) a FiUnamFS")
    print("\t4. Eliminar archivo en FiUnamFS")
    print("\t5. Salir")
    print("\t----------------------------------------------")

def listarDirectorioImp():
    print("\n\t" + "-"*105)
    print("\t {:<5} {:<15} | {:<10} | {:<15} | {:<18} | {:<18}".format(
        "Tipo", "Nombre", "Tamaño", "Cluster Ini", "Fecha Creación", "Fecha Modif"))
    print("\t" + "-"*105)