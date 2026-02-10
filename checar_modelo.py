# Este script permite la deteccion de modelos Gemini permitidos

import google.generativeai as genai

API_KEY = "TU_API_KEY" # <--- Pon tu clave real
genai.configure(api_key=API_KEY)

print("--- MODELOS DISPONIBLES PARA TI ---")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Error al conectar: {e}")
