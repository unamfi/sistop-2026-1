from datetime import datetime
with open("salida.log","w",encoding="utf-8") as f:
    f.write(f"Ejecución correcta: {datetime.now()}\n")
