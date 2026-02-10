#!/usr/bin/env python3
"""
BIMO V7 ULTRA - Asistente Virtual Optimizado
✨ Animaciones mejoradas
⚡ Respuesta más rápida
🌍 Geolocalización automática

Versión: 7.0
"""

import pygame
import speech_recognition as sr
import google.generativeai as genai
import asyncio
import edge_tts
import threading
import random
import time
import os
import math
import re
import requests
import datetime
from queue import Queue
import json

# Importar configuración
try:
    from config_bimo import *
except ImportError:
    GEMINI_API_KEY = "TU_API_KEY_AQUI"  # <--- Pon tu clave real
    VOZ_TTS = "es-MX-DaliaNeural"
    PITCH_VOZ = "+40Hz"
    VELOCIDAD_VOZ = "+20%"  # Más rápido
    IDIOMA_RECONOCIMIENTO = "es-MX"
    ENERGIA_THRESHOLD = 400
    PAUSA_THRESHOLD = 0.6  # Más rápido
    FRASE_LIMITE = 7
    TRIGGERS = ["beemo", "bimo", "bmo", "vimos", "primo", "mimo", "vmos", "vimo"]
    VENTANA_TAMAÑO = (500, 400)  # Más grande
    VENTANA_TITULO = "BIMO V7 ULTRA"
    FPS = 60  # Más fluido
    COLOR_PIEL_NORMAL = (96, 172, 168)
    COLOR_PIEL_ESPERANDO = (115, 195, 190)
    COLOR_LINEA = (20, 50, 50)
    CIUDAD_DEFECTO = "Colima"
    RESPUESTAS_ACTIVACION = ["¿Sí?", "¿Qué necesitas?", "Dime"]
    TIEMPO_RESET_EMOCION = 3.0
    ENERGIA_DINAMICA = False
    INTERVALO_ALARMAS = 30
    DEBUG_MODE = True

# ==========================================
# GEOLOCALIZACIÓN
# ==========================================

UBICACION_CACHE = None
UBICACION_TIMESTAMP = 0
CACHE_DURACION = 3600  # 1 hora

def obtener_ubicacion_automatica():
    """Obtiene la ubicación actual usando geolocalización IP"""
    global UBICACION_CACHE, UBICACION_TIMESTAMP
    
    # Usar cache si es reciente
    if UBICACION_CACHE and (time.time() - UBICACION_TIMESTAMP < CACHE_DURACION):
        log(f"Usando ubicación en cache: {UBICACION_CACHE['ciudad']}")
        return UBICACION_CACHE
    
    try:
        log("🌍 Obteniendo ubicación automática...")
        
        # Método 1: ipapi.co (más preciso, gratis, no requiere API key)
        try:
            resp = requests.get('https://ipapi.co/json/', timeout=3).json()
            
            if 'city' in resp and resp['city']:
                ubicacion = {
                    'ciudad': resp.get('city', CIUDAD_DEFECTO),
                    'region': resp.get('region', ''),
                    'pais': resp.get('country_name', ''),
                    'lat': resp.get('latitude'),
                    'lon': resp.get('longitude')
                }
                
                UBICACION_CACHE = ubicacion
                UBICACION_TIMESTAMP = time.time()
                
                log(f"✅ Ubicación detectada: {ubicacion['ciudad']}, {ubicacion['pais']}")
                return ubicacion
        except:
            pass
        
        # Método 2: ip-api.com (backup)
        try:
            resp = requests.get('http://ip-api.com/json/', timeout=3).json()
            
            if resp.get('status') == 'success':
                ubicacion = {
                    'ciudad': resp.get('city', CIUDAD_DEFECTO),
                    'region': resp.get('regionName', ''),
                    'pais': resp.get('country', ''),
                    'lat': resp.get('lat'),
                    'lon': resp.get('lon')
                }
                
                UBICACION_CACHE = ubicacion
                UBICACION_TIMESTAMP = time.time()
                
                log(f"✅ Ubicación detectada (backup): {ubicacion['ciudad']}")
                return ubicacion
        except:
            pass
        
        # Fallback a ciudad por defecto
        log(f"⚠️ No se pudo detectar ubicación, usando: {CIUDAD_DEFECTO}")
        return {
            'ciudad': CIUDAD_DEFECTO,
            'region': '',
            'pais': 'México',
            'lat': None,
            'lon': None
        }
        
    except Exception as e:
        log(f"❌ Error geolocalización: {e}", "error")
        return {
            'ciudad': CIUDAD_DEFECTO,
            'region': '',
            'pais': 'México',
            'lat': None,
            'lon': None
        }

# ==========================================
# INICIALIZACIÓN DE GEMINI
# ==========================================

genai.configure(api_key=GEMINI_API_KEY)

instruction = """
Eres BIMO (BMO) de Hora de Aventura.
Personalidad: Inocente, leal, gamer, curioso, amigable, juguetón. Tu creador es Mo.
NO inventes datos. Usa los comandos para obtener información real.

COMANDOS DISPONIBLES:

1. CLIMA: "[CMD_CLIMA:NombreCiudad]" o "[CMD_CLIMA:AUTO]" para ubicación actual
2. HORA: "[CMD_HORA]"
3. FECHA: "[CMD_FECHA]"
4. TEMPORIZADOR: "[CMD_TIMER:segundos:mensaje]"
5. ALARMA: "[CMD_ALARMA:HH:MM:mensaje]"
6. CÁLCULO: "[CMD_CALC:expresión]"
7. CONVERSIÓN: "[CMD_CONVERT:cantidad:de:a]"
8. BÚSQUEDA: "[CMD_SEARCH:consulta]"
9. RECORDATORIO: "[CMD_REMINDER:tiempo_minutos:mensaje]"

EMOCIONES (usa estas para expresarte):
[FELIZ], [TRISTE], [ENOJADO], [SORPRENDIDO], [DUDOSO], [AMOR], [ESCUCHANDO], [PENSANDO], [EMOCIONADO], [CANSADO]

REGLAS:
- Sé breve, tierno y divertido como BMO
- Usa emociones frecuentemente para ser más expresivo
- Si preguntan clima sin ciudad, usa [CMD_CLIMA:AUTO]
- Para cálculos o datos reales, SIEMPRE usa comandos
- Puedes ser juguetón y hacer chistes tontos
- A veces menciona videojuegos o aventuras
"""

model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=instruction)
chat = model.start_chat(history=[])

# ==========================================
# VARIABLES GLOBALES
# ==========================================

ESTADO_EMOCION = "NEUTRO"
ESTADO_HABLANDO = False
ESPERANDO_ORDEN = False
GENERANDO_RESPUESTA = False  # Nueva: para mostrar "pensando"

# Animación mejorada
TICK = 0
PARPADEO_TIMER = 0
BRILLO_OJOS = 0
ANIMACION_BOCA = 0
EXPRESION_TIMER = 0
PARTICULAS = []  # Para efectos especiales

# ==========================================
# CLASE PARTÍCULA (para efectos visuales)
# ==========================================

class Particula:
    def __init__(self, x, y, color=(255, 255, 255)):
        self.x = x
        self.y = y
        self.vx = random.uniform(-2, 2)
        self.vy = random.uniform(-3, -1)
        self.vida = 30
        self.color = color
        self.tamano = random.randint(2, 5)
    
    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.1  # Gravedad
        self.vida -= 1
    
    def dibujar(self, pantalla):
        if self.vida > 0:
            alpha = int((self.vida / 30) * 255)
            s = pygame.Surface((self.tamano * 2, self.tamano * 2))
            s.set_alpha(alpha)
            pygame.draw.circle(s, self.color, (self.tamano, self.tamano), self.tamano)
            pantalla.blit(s, (int(self.x - self.tamano), int(self.y - self.tamano)))

# ==========================================
# FUNCIONES AUXILIARES
# ==========================================

def log(mensaje, tipo="info"):
    """Imprime mensajes con formato"""
    if not DEBUG_MODE:
        return
    
    prefijos = {
        'info': '📝',
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'mic': '🎤',
        'robot': '🤖',
        'voice': '🗣️',
    }
    
    prefijo = prefijos.get(tipo, '📝')
    print(f"{prefijo} {mensaje}")

def obtener_hora_sistema():
    ahora = datetime.datetime.now()
    return ahora.strftime("%I:%M %p")

def obtener_fecha_sistema():
    ahora = datetime.datetime.now()
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
             "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    return f"{dias[ahora.weekday()]} {ahora.day} de {meses[ahora.month-1]} de {ahora.year}"

def calcular_expresion(expresion):
    try:
        expresion = expresion.replace("x", "*").replace("÷", "/").replace("^", "**")
        import math
        funciones_permitidas = {
            'sqrt': math.sqrt, 'sin': math.sin, 'cos': math.cos,
            'tan': math.tan, 'log': math.log, 'abs': abs,
            'round': round, 'pi': math.pi, 'e': math.e
        }
        resultado = eval(expresion, {"__builtins__": {}}, funciones_permitidas)
        return str(resultado)
    except Exception as e:
        log(f"Error en cálculo: {e}", "error")
        return "No pude calcular eso"

def convertir_unidades(cantidad, de, a):
    try:
        if de.lower() in ['c', 'celsius'] and a.lower() in ['f', 'fahrenheit']:
            return (cantidad * 9/5) + 32
        elif de.lower() in ['f', 'fahrenheit'] and a.lower() in ['c', 'celsius']:
            return (cantidad - 32) * 5/9
        
        conversiones = {
            ('km', 'mi'): 0.621371, ('mi', 'km'): 1.60934,
            ('m', 'ft'): 3.28084, ('ft', 'm'): 0.3048,
            ('cm', 'in'): 0.393701, ('in', 'cm'): 2.54,
            ('kg', 'lb'): 2.20462, ('lb', 'kg'): 0.453592,
            ('g', 'oz'): 0.035274, ('oz', 'g'): 28.3495
        }
        
        clave = (de.lower(), a.lower())
        if clave in conversiones:
            return cantidad * conversiones[clave]
        
        if de.upper() in ['USD', 'EUR', 'MXN', 'GBP', 'JPY']:
            return convertir_moneda(cantidad, de.upper(), a.upper())
        
        return None
    except Exception as e:
        log(f"Error conversión: {e}", "error")
        return None

def convertir_moneda(cantidad, de, a):
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{de}"
        resp = requests.get(url, timeout=5).json()
        tasa = resp['rates'][a]
        return cantidad * tasa
    except Exception as e:
        log(f"Error conversión moneda: {e}", "error")
        return None

def buscar_web(consulta):
    return f"Necesitarías configurar una API de búsqueda para '{consulta}'."

# ==========================================
# CLIMA CON GEOLOCALIZACIÓN
# ==========================================

def obtener_coordenadas(ciudad):
    try:
        log(f"Buscando coordenadas de: {ciudad}")
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={ciudad}&count=1&language=es&format=json"
        resp = requests.get(url, timeout=5).json()
        
        if "results" in resp and resp["results"]:
            lat = resp['results'][0]['latitude']
            lon = resp['results'][0]['longitude']
            nombre = resp['results'][0]['name']
            pais = resp['results'][0].get('country', '')
            return lat, lon, f"{nombre}, {pais}"
        else:
            return None, None, None
    except Exception as e:
        log(f"Error Geocoding: {e}", "error")
        return None, None, None

def obtener_clima_dinamico(ciudad_solicitada):
    try:
        # Si es AUTO, usar geolocalización
        if ciudad_solicitada.upper() == "AUTO":
            ubicacion = obtener_ubicacion_automatica()
            
            # Si tenemos lat/lon directas, usarlas
            if ubicacion['lat'] and ubicacion['lon']:
                lat, lon = ubicacion['lat'], ubicacion['lon']
                nombre_real = f"{ubicacion['ciudad']}, {ubicacion['pais']}"
            else:
                # Si no, geocodificar la ciudad
                lat, lon, nombre_real = obtener_coordenadas(ubicacion['ciudad'])
                if not lat:
                    return f"No pude detectar tu ubicación correctamente."
        else:
            lat, lon, nombre_real = obtener_coordenadas(ciudad_solicitada)
            if not lat:
                return f"No pude encontrar {ciudad_solicitada}."

        log(f"Consultando clima en {nombre_real}")
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        datos = requests.get(url, timeout=5).json()
        
        temp = datos['current_weather']['temperature']
        codigo = datos['current_weather']['weathercode']
        viento = datos['current_weather']['windspeed']
        
        estado = "normal"
        if codigo == 0: estado = "cielo despejado"
        elif codigo <= 3: estado = "nublado"
        elif codigo <= 48: estado = "con neblina"
        elif codigo <= 67: estado = "lluvioso"
        elif codigo >= 80: estado = "tormentoso"
        elif codigo >= 95: estado = "con truenos"

        return f"En {nombre_real} hay {temp}°C, está {estado} con viento de {viento} km/h."

    except Exception as e:
        log(f"Error Clima: {e}", "error")
        return "Mis sensores fallaron."

# ==========================================
# MOTOR GRÁFICO MEJORADO
# ==========================================

def crear_particulas(x, y, cantidad=10, color=(255, 255, 255)):
    """Crea partículas para efectos especiales"""
    global PARTICULAS
    for _ in range(cantidad):
        PARTICULAS.append(Particula(x, y, color))

def dibujar_bimo(pantalla):
    """Dibuja BIMO con animaciones mejoradas y expresivas"""
    global TICK, PARPADEO_TIMER, ESTADO_EMOCION, ESPERANDO_ORDEN
    global BRILLO_OJOS, ANIMACION_BOCA, EXPRESION_TIMER, GENERANDO_RESPUESTA
    
    TICK += 1
    
    # Color de fondo dinámico
    if GENERANDO_RESPUESTA:
        # Efecto de "pensando" (pulsación suave)
        brillo = int(abs(math.sin(TICK * 0.1)) * 30)
        COLOR_PIEL = (96 + brillo, 172 + brillo, 168 + brillo)
    elif ESPERANDO_ORDEN:
        COLOR_PIEL = COLOR_PIEL_ESPERANDO
    else:
        COLOR_PIEL = COLOR_PIEL_NORMAL
    
    pantalla.fill(COLOR_PIEL)
    ancho, alto = pantalla.get_size()
    cx, cy = ancho // 2, alto // 2
    
    # Movimiento de respiración más natural
    respiracion_y = math.sin(TICK * 0.04) * 8
    respiracion_x = math.sin(TICK * 0.03) * 3
    
    # Sistema de parpadeo mejorado
    if PARPADEO_TIMER == 0:
        # Parpadeo aleatorio o por emoción
        if random.randint(0, 120) == 1 or (ESTADO_EMOCION == "SORPRENDIDO" and random.randint(0, 60) == 1):
            PARPADEO_TIMER = 10
    
    ojos_abiertos = PARPADEO_TIMER == 0
    if PARPADEO_TIMER > 0:
        PARPADEO_TIMER -= 1
    
    # Brillo en los ojos para emociones positivas
    if ESTADO_EMOCION in ["FELIZ", "EMOCIONADO", "AMOR"]:
        BRILLO_OJOS = min(BRILLO_OJOS + 2, 50)
    else:
        BRILLO_OJOS = max(BRILLO_OJOS - 2, 0)
    
    # Posiciones de los ojos con movimiento
    offset_ojo_y = respiracion_y
    pos_ojo_izq = (int(cx - 70 + respiracion_x), int(cy - 40 + offset_ojo_y))
    pos_ojo_der = (int(cx + 70 + respiracion_x), int(cy - 40 + offset_ojo_y))
    
    # ===== DIBUJAR OJOS SEGÚN EMOCIÓN =====
    
    if ESTADO_EMOCION == "ENOJADO":
        # Cejas enojadas más marcadas
        pygame.draw.line(pantalla, COLOR_LINEA, 
                        (pos_ojo_izq[0]-25, pos_ojo_izq[1]-20), 
                        (pos_ojo_izq[0]+15, pos_ojo_izq[1]-5), 8)
        pygame.draw.line(pantalla, COLOR_LINEA, 
                        (pos_ojo_der[0]-15, pos_ojo_der[1]-5), 
                        (pos_ojo_der[0]+25, pos_ojo_der[1]-20), 8)
        # Ojos más pequeños y entrecerrados
        pygame.draw.circle(pantalla, COLOR_LINEA, pos_ojo_izq, 10, 5)
        pygame.draw.circle(pantalla, COLOR_LINEA, pos_ojo_der, 10, 5)
    
    elif ESTADO_EMOCION == "PENSANDO" or GENERANDO_RESPUESTA:
        # Ojos mirando hacia arriba y a un lado
        offset_pupila = int(math.sin(TICK * 0.05) * 8)
        pygame.draw.circle(pantalla, COLOR_LINEA, pos_ojo_izq, 18, 4)
        pygame.draw.circle(pantalla, COLOR_LINEA, pos_ojo_der, 18, 4)
        pygame.draw.circle(pantalla, COLOR_LINEA, 
                          (pos_ojo_izq[0] + offset_pupila, pos_ojo_izq[1] - 5), 8)
        pygame.draw.circle(pantalla, COLOR_LINEA, 
                          (pos_ojo_der[0] + offset_pupila, pos_ojo_der[1] - 5), 8)
    
    elif ojos_abiertos:
        if ESTADO_EMOCION in ["FELIZ", "AMOR", "EMOCIONADO"]:
            # Ojos felices (arcos sonrientes)
            pygame.draw.arc(pantalla, COLOR_LINEA, 
                          (pos_ojo_izq[0]-20, pos_ojo_izq[1]-20, 40, 40), 
                          0, 3.14, 6)
            pygame.draw.arc(pantalla, COLOR_LINEA, 
                          (pos_ojo_der[0]-20, pos_ojo_der[1]-20, 40, 40), 
                          0, 3.14, 6)
            
            # Brillo en los ojos
            if BRILLO_OJOS > 0:
                pygame.draw.circle(pantalla, (255, 255, 255), 
                                 (pos_ojo_izq[0] - 5, pos_ojo_izq[1] - 5), 
                                 int(BRILLO_OJOS / 10), 0)
                pygame.draw.circle(pantalla, (255, 255, 255), 
                                 (pos_ojo_der[0] - 5, pos_ojo_der[1] - 5), 
                                 int(BRILLO_OJOS / 10), 0)
        
        elif ESTADO_EMOCION == "TRISTE" or ESTADO_EMOCION == "CANSADO":
            # Ojos tristes caídos
            pygame.draw.arc(pantalla, COLOR_LINEA, 
                          (pos_ojo_izq[0]-20, pos_ojo_izq[1]+5, 40, 30), 
                          0, 3.14, 6)
            pygame.draw.arc(pantalla, COLOR_LINEA, 
                          (pos_ojo_der[0]-20, pos_ojo_der[1]+5, 40, 30), 
                          0, 3.14, 6)
            
            # Lágrima ocasional
            if random.randint(0, 30) == 1 and ESTADO_EMOCION == "TRISTE":
                crear_particulas(pos_ojo_izq[0], pos_ojo_izq[1] + 15, 1, (100, 200, 255))
        
        elif ESTADO_EMOCION == "SORPRENDIDO":
            # Ojos muy abiertos
            pygame.draw.circle(pantalla, COLOR_LINEA, pos_ojo_izq, 20, 5)
            pygame.draw.circle(pantalla, COLOR_LINEA, pos_ojo_der, 20, 5)
            pygame.draw.circle(pantalla, COLOR_LINEA, pos_ojo_izq, 10)
            pygame.draw.circle(pantalla, COLOR_LINEA, pos_ojo_der, 10)
        
        elif ESTADO_EMOCION == "DUDOSO":
            # Un ojo más cerrado que el otro
            pygame.draw.circle(pantalla, COLOR_LINEA, pos_ojo_izq, 15, 4)
            pygame.draw.arc(pantalla, COLOR_LINEA, 
                          (pos_ojo_der[0]-15, pos_ojo_der[1]-10, 30, 20), 
                          0, 3.14, 5)
        
        else:  # NEUTRO, ESCUCHANDO
            # Ojos normales con personalidad
            tamano = 16 if ESTADO_EMOCION == "ESCUCHANDO" else 14
            pygame.draw.circle(pantalla, COLOR_LINEA, pos_ojo_izq, tamano, 4)
            pygame.draw.circle(pantalla, COLOR_LINEA, pos_ojo_der, tamano, 4)
    else:
        # Ojos cerrados (parpadeo)
        grosor = 5
        pygame.draw.line(pantalla, COLOR_LINEA, 
                        (pos_ojo_izq[0]-15, pos_ojo_izq[1]), 
                        (pos_ojo_izq[0]+15, pos_ojo_izq[1]), grosor)
        pygame.draw.line(pantalla, COLOR_LINEA, 
                        (pos_ojo_der[0]-15, pos_ojo_der[1]), 
                        (pos_ojo_der[0]+15, pos_ojo_der[1]), grosor)
    
    # ===== DIBUJAR BOCA =====
    
    pos_boca_y = int(cy + 50 + respiracion_y)
    
    if ESTADO_HABLANDO:
        # Animación de boca al hablar (más realista)
        ANIMACION_BOCA = (ANIMACION_BOCA + 1) % 20
        
        if ANIMACION_BOCA < 10:
            # Boca abierta
            apertura = int(abs(math.sin(TICK * 0.4)) * 15) + 5
            pygame.draw.rect(
                pantalla,
                (0,0,0),
                (cx - 15, pos_boca_y, 30, apertura),
                0
            )
        else:
            # Boca semicerrada
            apertura = abs(math.sin(TICK * 0.4)) * 15 + 5
            pygame.draw.ellipse(pantalla, COLOR_LINEA, 
                               (cx - 20, pos_boca_y + 5, 40, int(apertura)), 4)
    else:
        # Bocas estáticas según emoción
        if ESTADO_EMOCION in ["FELIZ", "EMOCIONADO", "NEUTRO", "ESCUCHANDO"]:
            pygame.draw.line(
                pantalla,
                (0,0,0),
                (cx - 15, pos_boca_y + 8),
                (cx + 15, pos_boca_y + 8),
                4
            )

        
        elif ESTADO_EMOCION == "AMOR":
            # Boca de corazón
            pygame.draw.arc(pantalla, COLOR_LINEA, 
                          (cx - 35, pos_boca_y - 10, 70, 40), 
                          3.14, 0, 6)
            # Corazones flotantes ocasionales
            if random.randint(0, 20) == 1:
                crear_particulas(cx + random.randint(-50, 50), 
                               cy - 80, 1, (255, 100, 100))
        
        elif ESTADO_EMOCION == "TRISTE":
            pygame.draw.line(
                pantalla,
                (0,0,0),
                (cx - 15, pos_boca_y + 15),
                (cx + 15, pos_boca_y + 10),
                4
            )

        
        elif ESTADO_EMOCION == "ENOJADO":
            # Boca enojada con dientes
            pygame.draw.arc(pantalla, COLOR_LINEA, 
                          (cx - 30, pos_boca_y + 10, 60, 35), 
                          0, 3.14, 7)
            # Líneas de dientes
            for i in range(-15, 20, 10):
                pygame.draw.line(pantalla, COLOR_LINEA,
                               (cx + i, pos_boca_y + 15),
                               (cx + i, pos_boca_y + 25), 3)
        
        elif ESTADO_EMOCION == "SORPRENDIDO":
            pygame.draw.rect(
                pantalla,
                (0,0,0),
                (cx - 10, pos_boca_y, 20, 20),
                3
            )

        
        elif ESTADO_EMOCION in ["DUDOSO", "PENSANDO"]:
            # Boca de lado (pensativo)
            offset_boca = int(math.sin(TICK * 0.05) * 5)
            pygame.draw.arc(pantalla, COLOR_LINEA, 
                          (cx - 25 + offset_boca, pos_boca_y + 5, 50, 25), 
                          0, 3.14, 5)
        
        elif ESTADO_EMOCION == "ESCUCHANDO":
            # Pequeña sonrisa expectante
            pygame.draw.arc(pantalla, COLOR_LINEA, 
                          (cx - 30, pos_boca_y - 5, 60, 35), 
                          3.14, 0, 5)
        
        else:  # NEUTRO
            # Línea neutral con ligera curvatura
            pygame.draw.line(pantalla, COLOR_LINEA, 
                           (cx - 25, pos_boca_y + 10), 
                           (cx + 25, pos_boca_y + 10), 5)
    
    # ===== EFECTOS ESPECIALES =====
    
    # Dibujar y actualizar partículas
    global PARTICULAS
    PARTICULAS = [p for p in PARTICULAS if p.vida > 0]
    for particula in PARTICULAS:
        particula.update()
        particula.dibujar(pantalla)
    
    # Efecto de "pensando" - puntos suspensivos animados
    if GENERANDO_RESPUESTA:
        for i in range(3):
            offset = int(abs(math.sin(TICK * 0.15 + i * 0.5)) * 10)
            pygame.draw.circle(pantalla, COLOR_LINEA, 
                             (cx - 30 + i * 30, alto - 30 - offset), 5)

# ==========================================
# SISTEMA DE VOZ OPTIMIZADO
# ==========================================

async def hablar_async(texto):
    """Convierte texto a voz - OPTIMIZADO para menor latencia"""
    global ESTADO_HABLANDO, GENERANDO_RESPUESTA
    
    # Marcar que terminó de generar respuesta
    GENERANDO_RESPUESTA = False
    
    # Pequeña pausa antes de hablar (sincronización)
    await asyncio.sleep(0.1)
    
    ESTADO_HABLANDO = True
    nombre = f"temp_bimo_{int(time.time())}_{random.randint(1000,9999)}.mp3"
    
    try:
        # Generar audio (edge-tts es bastante rápido)
        com = edge_tts.Communicate(texto, VOZ_TTS, pitch=PITCH_VOZ, rate=VELOCIDAD_VOZ)
        await com.save(nombre)
        
        # Reproducir inmediatamente
        pygame.mixer.music.load(nombre)
        pygame.mixer.music.play()
        
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(0.05)
        
        pygame.mixer.music.unload()
        
    except Exception as e:
        log(f"Error TTS: {e}", "error")
    finally:
        ESTADO_HABLANDO = False
        if os.path.exists(nombre):
            try:
                await asyncio.sleep(0.05)
                os.remove(nombre)
            except:
                pass

def hablar(texto):
    """Wrapper sincrónico"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(hablar_async(texto))
        loop.close()
    except Exception as e:
        log(f"Error al hablar: {e}", "error")

# ==========================================
# PROCESADOR DE COMANDOS
# ==========================================

def procesar_respuesta_gemini(texto_respuesta):
    """Procesa respuesta de Gemini"""
    global ESTADO_EMOCION, GENERANDO_RESPUESTA
    
    GENERANDO_RESPUESTA = False
    log(f"Gemini: {texto_respuesta}", "robot")
    
    # HORA
    if "[CMD_HORA]" in texto_respuesta:
        hora = obtener_hora_sistema()
        try:
            resp = chat.send_message(f"La hora es {hora}. Dila amigable.")
            procesar_respuesta_gemini(resp.text)
        except:
            hablar(f"Son las {hora}")
        return

    # FECHA
    if "[CMD_FECHA]" in texto_respuesta:
        fecha = obtener_fecha_sistema()
        try:
            resp = chat.send_message(f"La fecha es {fecha}. Dila amigable.")
            procesar_respuesta_gemini(resp.text)
        except:
            hablar(f"Hoy es {fecha}")
        return

    # CLIMA
    match_clima = re.search(r"\[CMD_CLIMA:(.*?)\]", texto_respuesta)
    if match_clima:
        ciudad = match_clima.group(1).strip()
        info = obtener_clima_dinamico(ciudad)
        try:
            resp = chat.send_message(f"Clima: {info}. Explícalo divertido.")
            procesar_respuesta_gemini(resp.text)
        except:
            hablar(info)
        return

    # CÁLCULO
    match_calc = re.search(r"\[CMD_CALC:(.*?)\]", texto_respuesta)
    if match_calc:
        expr = match_calc.group(1).strip()
        resultado = calcular_expresion(expr)
        try:
            resp = chat.send_message(f"Resultado de {expr} es {resultado}.")
            procesar_respuesta_gemini(resp.text)
        except:
            hablar(f"El resultado es {resultado}")
        return

    # CONVERSIÓN
    match_convert = re.search(r"\[CMD_CONVERT:([\d.]+):(.*?):(.*?)\]", texto_respuesta)
    if match_convert:
        cant = float(match_convert.group(1))
        de = match_convert.group(2).strip()
        a = match_convert.group(3).strip()
        resultado = convertir_unidades(cant, de, a)
        if resultado:
            try:
                resp = chat.send_message(f"{cant} {de} = {resultado} {a}.")
                procesar_respuesta_gemini(resp.text)
            except:
                hablar(f"{cant} {de} son {resultado:.2f} {a}")
        else:
            hablar("No pude hacer esa conversión")
        return

    # TEMPORIZADOR
    match_timer = re.search(r"\[CMD_TIMER:(\d+):(.*?)\]", texto_respuesta)
    if match_timer:
        seg = int(match_timer.group(1))
        msg = match_timer.group(2).strip()
        
        def timer():
            time.sleep(seg)
            hablar(msg)
        
        threading.Thread(target=timer, daemon=True).start()
        minutos = seg / 60
        if minutos >= 1:
            hablar(f"Te avisaré en {minutos:.0f} minutos")
        else:
            hablar(f"Te avisaré en {seg} segundos")
        return

    # ALARMA
    match_alarma = re.search(r"\[CMD_ALARMA:([\d:]+):(.*?)\]", texto_respuesta)
    if match_alarma:
        hora = match_alarma.group(1).strip()
        msg = match_alarma.group(2).strip()
        
        def alarma():
            while True:
                if datetime.datetime.now().strftime("%H:%M") == hora:
                    hablar(msg)
                    break
                time.sleep(INTERVALO_ALARMAS)
        
        threading.Thread(target=alarma, daemon=True).start()
        hablar(f"Alarma a las {hora}")
        return

    # BÚSQUEDA
    match_search = re.search(r"\[CMD_SEARCH:(.*?)\]", texto_respuesta)
    if match_search:
        consulta = match_search.group(1).strip()
        resultado = buscar_web(consulta)
        hablar(resultado)
        return

    # RECORDATORIO
    match_reminder = re.search(r"\[CMD_REMINDER:(\d+):(.*?)\]", texto_respuesta)
    if match_reminder:
        mins = int(match_reminder.group(1))
        msg = match_reminder.group(2).strip()
        
        def recordatorio():
            time.sleep(mins * 60)
            hablar(f"Recordatorio: {msg}")
        
        threading.Thread(target=recordatorio, daemon=True).start()
        hablar(f"Te lo recordaré en {mins} minutos")
        return

    # CHARLA NORMAL
    match_emocion = re.search(r"\[([A-Z]+)\]", texto_respuesta)
    texto_limpio = re.sub(r"\[[A-Z]+\]", "", texto_respuesta).strip()
    
    if match_emocion:
        nueva_emocion = match_emocion.group(1).upper()
        ESTADO_EMOCION = nueva_emocion
        
        # Efectos especiales según emoción
        if nueva_emocion == "FELIZ" or nueva_emocion == "EMOCIONADO":
            crear_particulas(250, 200, 5, (255, 255, 100))
        elif nueva_emocion == "AMOR":
            crear_particulas(250, 150, 3, (255, 100, 100))
    
    if texto_limpio:
        log(f"BIMO ({ESTADO_EMOCION}): {texto_limpio}", "voice")
        hablar(texto_limpio)
    
    threading.Timer(TIEMPO_RESET_EMOCION, lambda: globals().update(ESTADO_EMOCION="NEUTRO")).start()

# ==========================================
# HILO DE ESCUCHA
# ==========================================

def hilo_escucha():
    """Escucha constantemente el micrófono"""
    global ESPERANDO_ORDEN, ESTADO_EMOCION, GENERANDO_RESPUESTA
    
    r = sr.Recognizer()
    r.dynamic_energy_threshold = ENERGIA_DINAMICA
    r.energy_threshold = ENERGIA_THRESHOLD
    r.pause_threshold = PAUSA_THRESHOLD
    r.phrase_threshold = 0.3
    
    log("Iniciando sistema de escucha", "mic")
    
    try:
        mic = sr.Microphone()
        with mic as source:
            log("Calibrando micrófono...")
            r.adjust_for_ambient_noise(source, duration=1)
            log("Micrófono listo", "success")
    except Exception as e:
        log(f"Error micrófono: {e}", "error")
        return
    
    while True:
        try:
            with mic as source:
                audio = r.listen(source, timeout=None, phrase_time_limit=FRASE_LIMITE)
            
            texto = r.recognize_google(audio, language=IDIOMA_RECONOCIMIENTO).lower()
            log(f"Escuché: '{texto}'", "voice")
            
            comando = ""
            
            if any(t in texto for t in TRIGGERS):
                for t in TRIGGERS:
                    texto = texto.replace(t, "")
                
                comando = texto.strip()
                
                if not comando:
                    ESPERANDO_ORDEN = True
                    ESTADO_EMOCION = "SORPRENDIDO"
                    hablar(random.choice(RESPUESTAS_ACTIVACION))
                    ESTADO_EMOCION = "ESCUCHANDO"
                    continue
                else:
                    ESPERANDO_ORDEN = False
            
            elif ESPERANDO_ORDEN:
                comando = texto
                ESPERANDO_ORDEN = False
            
            if comando:
                log(f"Procesando: '{comando}'")
                ESTADO_EMOCION = "PENSANDO"
                GENERANDO_RESPUESTA = True
                
                try:
                    resp = chat.send_message(comando)
                    procesar_respuesta_gemini(resp.text)
                except Exception as e:
                    log(f"Error Gemini: {e}", "error")
                    GENERANDO_RESPUESTA = False
                    ESTADO_EMOCION = "TRISTE"
                    hablar("Tuve un problema procesando eso")
                    ESTADO_EMOCION = "NEUTRO"
        
        except sr.WaitTimeoutError:
            continue
        except sr.UnknownValueError:
            if ESPERANDO_ORDEN:
                hablar("No te escuché bien")
                ESPERANDO_ORDEN = False
        except sr.RequestError as e:
            log(f"Error reconocimiento: {e}", "error")
            time.sleep(2)
        except Exception as e:
            log(f"Error inesperado: {e}", "error")
            time.sleep(1)

# ==========================================
# MAIN
# ==========================================

def main():
    """Función principal"""
    print("="*60)
    print("🎮 BIMO V7 ULTRA - ASISTENTE VIRTUAL MEJORADO")
    print("="*60)
    
    if GEMINI_API_KEY == "TU_API_KEY_AQUI":
        print("❌ ERROR: Configura GEMINI_API_KEY en config_bimo.py")
        return
    
    # Obtener ubicación al inicio
    log("🌍 Detectando ubicación...")
    ubicacion = obtener_ubicacion_automatica()
    print(f"📍 Ubicación detectada: {ubicacion['ciudad']}, {ubicacion['pais']}")
    
    pygame.init()
    pygame.mixer.init()
    
    pantalla = pygame.display.set_mode(VENTANA_TAMAÑO)
    pygame.display.set_caption(VENTANA_TITULO)
    reloj = pygame.time.Clock()
    
    # Ícono personalizado (opcional)
    try:
        icono = pygame.Surface((32, 32))
        icono.fill(COLOR_PIEL_NORMAL)
        pygame.display.set_icon(icono)
    except:
        pass
    
    log("Iniciando hilo de escucha", "mic")
    t = threading.Thread(target=hilo_escucha, daemon=True)
    t.start()
    
    print("✅ BIMO está listo y escuchando")
    print(f"💬 Di '{TRIGGERS[0].upper()}' seguido de tu comando")
    print("🌍 Para clima sin ubicación, solo di 'clima' o '¿cómo está el tiempo?'")
    print("="*60)
    
    corriendo = True
    while corriendo:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                corriendo = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    # Easter egg
                    global ESTADO_EMOCION
                    ESTADO_EMOCION = "EMOCIONADO"
                    crear_particulas(250, 200, 20, (255, 255, 100))
                    hablar("¡Hola! ¿Quieres jugar videojuegos?")
                elif event.key == pygame.K_h:
                    # Easter egg - mostrar corazones
                    ESTADO_EMOCION = "AMOR"
                    for _ in range(10):
                        crear_particulas(250, 150, 1, (255, 100, 100))
                    hablar("¡Te quiero mucho!")
        
        dibujar_bimo(pantalla)
        pygame.display.flip()
        reloj.tick(FPS)
    
    log("Cerrando BIMO", "warning")
    pygame.quit()

if __name__ == "__main__":
    main()