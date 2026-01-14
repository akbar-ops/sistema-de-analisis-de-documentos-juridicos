#!/usr/bin/env python3
"""
Script rápido para probar la conexión con Ollama
"""

import requests
import json

print("🔍 Probando conexión con Ollama...")

# Test 1: Verificar que Ollama está corriendo
try:
    response = requests.get("http://localhost:11434/api/tags", timeout=5)
    print(f"✅ Ollama está corriendo (status: {response.status_code})")
    
    models = response.json().get('models', [])
    print(f"\n📦 Modelos disponibles ({len(models)}):")
    for model in models:
        print(f"   - {model.get('name', 'unknown')}")
    
except requests.exceptions.ConnectionError:
    print("❌ ERROR: No se puede conectar con Ollama")
    print("💡 Solución: Ejecuta 'ollama serve' en otra terminal")
    exit(1)
except Exception as e:
    print(f"❌ ERROR: {e}")
    exit(1)

# Test 2: Probar generación simple
print("\n🧪 Probando generación de texto...")
try:
    payload = {
        "model": "llama3.2:3b",
        "prompt": "Di 'Hola' en español.",
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": 50
        }
    }
    
    print(f"📤 Enviando: {payload['prompt']}")
    
    response = requests.post(
        "http://localhost:11434/api/generate",
        json=payload,
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Respuesta recibida:")
        print(f"   {result.get('response', 'Sin respuesta')}")
    else:
        print(f"❌ Error: Status {response.status_code}")
        print(f"   {response.text}")
        
except Exception as e:
    print(f"❌ ERROR en generación: {e}")
    exit(1)

print("\n✅ Ollama funciona correctamente!")
print("💡 Ahora puedes probar el chat en el frontend")
