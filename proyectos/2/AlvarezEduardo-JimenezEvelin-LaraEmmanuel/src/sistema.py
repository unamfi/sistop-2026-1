#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sistema.py
Programa principal: menú de interacción con la imagen FiUnamFS.

Este archivo orquesta:
- La creación del objeto FiUnamFS
- El estado compartido entre hilos
- El hilo monitor
- El menú interactivo en consola (modo texto)
"""

import sys

from estado import EstadoFS
from fiunamfs import FiUnamFS
from monitor import iniciar_hilo_monitoreo


def menu():
    """
    Menú interactivo en consola para operar sobre una imagen FiUnamFS.

    Opciones:
    1) Listar directorio
    2) Copiar archivo desde FiUnamFS → local
    3) Copiar archivo desde local → FiUnamFS
    4) Eliminar archivo en FiUnamFS
    5) Salir
    """
    # Permitir pasar el nombre de la imagen por línea de comandos.
    # Si no se pasa, se usa 'fiunamfs.img' por defecto.
    if len(sys.argv) >= 2:
        imagen = sys.argv[1]
    else:
        imagen = "fiunamfs.img"

    # Creamos el estado compartido y la instancia de FiUnamFS.
    estado = EstadoFS()
    fs = FiUnamFS(imagen, estado)

    # Hilo de monitoreo concurrente (corre en segundo plano).
    iniciar_hilo_monitoreo(fs)

    # Bucle principal del menú interactivo.
    while True:
        print("\n=== MENÚ FIUNAMFS ===")
        print("1) Listar directorio")
        print("2) Copiar archivo desde FiUnamFS")
        print("3) Copiar archivo hacia FiUnamFS")
        print("4) Eliminar archivo")
        print("5) Salir")

        # Leemos opción del usuario.
        op = input("> ")

        if op == "1":
            # Listar todas las entradas de directorio no vacías.
            print("\nIdx Nombre           Cluster Tamaño Creación        Modificación")
            print("--- --------------- ------- ------- --------------- ---------------")
            entries = fs.leer_directorio()
            for i, e in enumerate(entries):
                if not e.is_empty():
                    # Alineamos columnas para que el listado sea legible.
                    print(
                        f"{i:<3} {e.name:<15} {e.start:<7} {e.size:<7} "
                        f"{e.created:<15} {e.modified:<15}"
                    )

        elif op == "2":
            # Copiar archivo desde la imagen FiUnamFS al sistema local.
            origen = input("Nombre en FiUnamFS: ")
            destino = input("Salida local: ")
            fs.copiar_desde(origen, destino)

        elif op == "3":
            # Copiar archivo desde el sistema local a la imagen FiUnamFS.
            arch = input("Archivo local origen: ")
            nombre = input("Nombre en FiUnamFS: ")
            fs.copiar_hacia(arch, nombre)

        elif op == "4":
            # Eliminar (marcar como libre) una entrada en el directorio.
            nombre = input("Nombre a eliminar: ")
            fs.eliminar(nombre)

        elif op == "5":
            # Salir del menú y finalizar el programa principal.
            print("Saliendo...")
            break

        else:
            # Opción no reconocida.
            print("[ERROR] Opción inválida.")


if __name__ == "__main__":
    menu()