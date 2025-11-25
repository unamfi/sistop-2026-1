"""
Servicios de threading para FiUnamFS Manager

Este módulo implementa la arquitectura de 2 hilos:
- IOThread: Hilo de E/S que maneja operaciones del filesystem
- UIThread: Hilo de interfaz que maneja entrada del usuario
- Comunicación mediante queue.Queue (thread-safe)
"""
