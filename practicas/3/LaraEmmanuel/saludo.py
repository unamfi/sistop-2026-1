import sys

def main():
 if len(sys.argv) > 1:
    nombre = sys.argv[1]
    print(f"¡Hola {nombre}!")
 else:
    print("¡Hola mundo!")

if __name__ == "__main__":
    main()
