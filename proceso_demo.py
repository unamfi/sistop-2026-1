import os

# Archivo que se genera automáticamente (derivado)
archivo_autogenerado = "resultado_proceso.txt"

def main():
    print("Proceso padre PID:", os.getpid())

    pid = os.fork()  # Creamos un proceso hijo

    if pid == 0:
        # Proceso hijo
        with open(archivo_autogenerado, "w") as f:
            f.write(f"Soy el hijo con PID {os.getpid()}, generado por fork.\n")
        print("Proceso hijo terminó y generó archivo.")
    else:
        # Proceso padre
        print("Proceso padre espera a que el hijo termine...")
        os.wait()
        print("Proceso padre continúa después de la ejecución del hijo.")

if __name__ == "__main__":
    main()

