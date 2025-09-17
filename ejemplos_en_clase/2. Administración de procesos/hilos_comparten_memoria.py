#!/usr/bin/python3
from threading import Thread
import time
var = '.'

def altera():
    global var
    caracteres = ['.', ',', '!', '@', '_', '-']
    while True:
        for c in caracteres:
            var = c
            time.sleep(5)

def monitorea():
    while True:
        print(var)
        time.sleep(1)

Thread(target=altera).start()
Thread(target=monitorea).start()
