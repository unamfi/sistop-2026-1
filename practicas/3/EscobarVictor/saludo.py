import sys

# Si el usuario da un argumento, usarlo como nombre
if len(sys.argv) > 1:
    print(f"Hola, {sys.argv[1]}!")
else:
    # Si no da argumento, mostrar "Hola mundo"
    print("Hola mundo")
