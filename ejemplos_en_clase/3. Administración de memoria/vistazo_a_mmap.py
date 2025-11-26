#!/usr/bin/python3
import mmap
import os
filename = '../../proyectos/2/fiunamfs.img'

fh = open(filename, 'r+')
fs = mmap.mmap(fh.fileno(), 0)

while True:
    print('¿A partir de dónde quieres leer 100 bytes?')
    base = int(input())
    print(fs[base:base+100])
