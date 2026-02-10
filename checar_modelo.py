import google.generativeai as genai

API_KEY = "AIzaSyARUfg-jtcxd5myWkSPio8R1x89aUU4C74" # <--- Pon tu clave real
genai.configure(api_key=API_KEY)

print("--- MODELOS DISPONIBLES PARA TI ---")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Error al conectar: {e}")