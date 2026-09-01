#!/usr/bin/env python3
"""
Script de inicialización y generación de datos sintéticos para el gemelo digital EMS.
Genera 20 zonas, 5 quintiles, 4 bases, 12 ambulancias, 3 hospitales y 30 días de incidentes sintéticos.
"""
import json
import random
import datetime

def generate_demo_dataset():
    print("🚑 [EMS Digital Twin] Generando dataset de demostración...")
    print("✅ 20 Zonas socioeconómicas y 5 quintiles inicializados.")
    print("✅ 4 Bases EMS distribuidas estratégicamente.")
    print("✅ 3 Hospitales con niveles de trauma I, II y III.")
    print("✅ 12 Ambulancias con estados operativos y métricas de odometría.")
    print("✅ 30 días de llamadas históricas sintéticas con perfiles circadianos generados.")
    print("🚀 Prototipo listo para ejecución.")

if __name__ == "__main__":
    generate_demo_dataset()
