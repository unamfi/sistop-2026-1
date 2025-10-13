#!/usr/bin/python3
#
# ¿Por qué TOCTTOU?
# Son las siglas de "Time Of Check To Time Of Use", una
# vulnerabilidad derivada de que ocurra cierto tiempo entre
# una verificación y la acción correspondiente
import os

# (...)
filename = '/tmp/archivo.txt'
datos = os.fstat(filename)

# (...hago algunas otras cosas)

if datos.uid == os.getuid:
### Debería ser:
### if os.fstat(filename).uid == os.getuid:
    procesa_datos(filename)
else:
    print("Lo siento, el archivo no es tuyo!")
    exit(1)
