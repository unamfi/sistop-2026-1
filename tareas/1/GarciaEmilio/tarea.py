import threading
import time
import random

current_floor = 1
elevator_direction = 1
passengers = []
waiting = {}

elevator_capacity = threading.Semaphore(5)

elevator_lock = threading.Lock()

def elevator():
    global current_floor, elevator_direction
    
    print("El elevador esta en el piso 1")
    
    while True:
        #Esto es lo que se 'tarda' el elevador de moverse de un piso a otro
        time.sleep(2) 
        
        with elevator_lock:
            current_floor += elevator_direction
            
            if current_floor >= 10:
                elevator_direction = -1
            if current_floor <= 1:
                elevator_direction = 1
            
            print(f"El elevador esta en el piso {current_floor}, va para {'arriba' if elevator_direction == 1 else 'abajo'}")
            
            people_exiting = [p for p in passengers if p[1] == current_floor]
            for person in people_exiting:
                passengers.remove(person)
                elevator_capacity.release()
                print(f"El usuario {person[0]} se salio en {current_floor}")
            
            if current_floor in waiting and waiting[current_floor]:
                for user_id, destination in waiting[current_floor][:]:
                    if elevator_capacity.acquire(blocking=False):
                        passengers.append((user_id, destination))
                        waiting[current_floor].remove((user_id, destination))
                        print(f"El usuario {user_id} entro, va para {destination}")
                    else:
                        break
            
            if current_floor in waiting and not waiting[current_floor]:
                del waiting[current_floor]

def user(user_id):
    start_floor = random.randint(1, 10)
    destination = random.randint(1, 10)
    
    while destination == start_floor:
        destination = random.randint(1, 10)
    
    print(f"El usuario {user_id} esta en {start_floor} quiere ir a {destination}")
    
    with elevator_lock:
        if start_floor not in waiting:
            waiting[start_floor] = []
        waiting[start_floor].append((user_id, destination))
    
    while True:
        time.sleep(1)
        with elevator_lock:            
            still_waiting = any(u[0] == user_id for floor in waiting.values() for u in floor)
            still_riding = any(p[0] == user_id for p in passengers)
            
            if not still_waiting and not still_riding:
                print(f"El usuario {user_id} llego a su destino")
                break

def main():
    print("*"*10 + 'Emilio Garcia Riba Tarea' + '*'*10)
        
    elevator_thread = threading.Thread(target=elevator)
    elevator_thread.daemon = True
    elevator_thread.start()
    
    user_threads = []
    for user_id in range(1, 11):
        user_thread = threading.Thread(target=user, args=(user_id,))
        user_thread.daemon = True
        user_thread.start()
        user_threads.append(user_thread)
        time.sleep(random.randint(1, 3))
    
    time.sleep(30)

if __name__ == "__main__":
    main()