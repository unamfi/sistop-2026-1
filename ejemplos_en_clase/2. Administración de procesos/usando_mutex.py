#!/usr/bin/python3
from time import sleep
from threading import Thread, Lock

identificadores = [',', '.', '!', '@', '#', '$', '%']
mut = Lock()
res = ''

def vida_del_hilo(ident):
    global res
    while True:
        mut.acquire()
        for i in range(3):
            res = res + ident
            sleep(0.3)
        mut.release()

def hilo_monitor():
    global res
    while True:
        sleep(5)
        print('Formándome...')
        mut.acquire()
        print(res)
        res = ''
        mut.release()

for ident in identificadores:
    Thread(target=vida_del_hilo, args=[ident]).start()
hilo_monitor()

