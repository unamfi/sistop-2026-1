import datetime
import platform

# Generar reporte del sistema
with open('reporte_sistema.txt', 'w') as f:
    f.write("=== REPORTE DEL SISTEMA ===\n")
    f.write(f"Fecha: {datetime.datetime.now()}\n")
    f.write(f"Sistema: {platform.system()} {platform.release()}\n")
    f.write(f"Procesador: {platform.processor()}\n")
    f.write("Este archivo es generado automáticamente\n")

print("Reporte generado: reporte_sistema.txt")