#!/usr/bin/env python3
"""
Script para scrapear los precios de Cecosesola
SIN DATOS DE EJEMPLO - Solo datos reales
"""

import json
import os
import re
from datetime import datetime
from io import BytesIO

import requests
from PIL import Image

# Configuración
URL = "https://precios.cecosesola.coop"
OUTPUT_JSON = "precios.json"
IMAGES_DIR = "images"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}


def descargar_y_optimizar_imagen(url, producto_id):
    """Descarga y optimiza una imagen. Retorna URL pública o None."""
    if not url or not url.startswith("http"):
        return None

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return None

        img = Image.open(BytesIO(response.content))

        if img.mode in ('RGBA', 'LA', 'P'):
            bg = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            bg.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = bg

        img.thumbnail((120, 120), Image.Resampling.LANCZOS)

        filename = f"{producto_id}.jpg"
        filepath = os.path.join(IMAGES_DIR, filename)
        img.save(filepath, "JPEG", quality=70, optimize=True)

        return f"https://raw.githubusercontent.com/dusk0382/cecosesola-data/main/images/{filename}"
    except Exception:
        return None


def extraer_desde_json_embebido(html):
    """Intenta extraer datos de JSON embebido (React/Next.js)."""
    productos = []

    patrones = [
        r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',
        r'<script[^>]*id="__INITIAL_STATE__"[^>]*>(.*?)</script>',
        r'window\.__PRELOADED_STATE__\s*=\s*({.*?});',
        r'<script[^>]*type="application/json"[^>]*>(.*?)</script>',
    ]

    for patron in patrones:
        match = re.search(patron, html, re.DOTALL)
        if not match:
            continue

        try:
            data = json.loads(match.group(1))

            # Navegar estructuras anidadas comunes
            for key in ['props', 'pageProps', 'initialState', 'state', 'products', 'productos', 'items']:
                if isinstance(data, dict) and key in data:
                    data = data[key]

            # Si es lista, procesar
            if isinstance(data, list):
                for i, p in enumerate(data):
                    if isinstance(p, dict):
                        nombre = p.get('name') or p.get('nombre') or p.get('title') or ''
                        precio = p.get('price') or p.get('precio') or 0
                        if nombre and precio:
                            productos.append({
                                "id": str(p.get('id', i + 1)),
                                "nombre": nombre.strip(),
                                "precio": float(precio),
                                "categoria": p.get('category', p.get('categoria', '')),
                                "presentacion": p.get('presentation', p.get('presentacion', '')),
                                "imagen": p.get('image') or p.get('imagen') or p.get('img') or ''
                            })
                if productos:
                    break
        except (json.JSONDecodeError, TypeError, ValueError):
            continue

    return productos


def extraer_desde_html(html):
    """Extrae productos buscando tablas HTML."""
    productos = []

    # Buscar tabla
    tabla_pattern = r'<table[^>]*>(.*?)</table>'
    tabla_match = re.search(tabla_pattern, html, re.DOTALL | re.IGNORECASE)

    if not tabla_match:
        return productos

    tabla_html = tabla_match.group(1)
    fila_pattern = r'<tr[^>]*>(.*?)</tr>'
    filas = re.findall(fila_pattern, tabla_html, re.DOTALL | re.IGNORECASE)

    for i, fila in enumerate(filas):
        celda_pattern = r'<td[^>]*>(.*?)</td>'
        celdas = re.findall(celda_pattern, fila, re.DOTALL | re.IGNORECASE)

        if len(celdas) < 2:
            continue

        # Limpiar nombre
        nombre = re.sub(r'<[^>]+>', '', celdas[0]).strip()
        if not nombre:
            continue

        # Limpiar precio
        precio_texto = re.sub(r'<[^>]+>', '', celdas[1]).strip()
        precio_texto = re.sub(r'[^\d.,]', '', precio_texto).replace(',', '.')
        try:
            precio = float(precio_texto)
        except ValueError:
            continue

        # Presentación
        presentacion = ""
        if len(celdas) >= 3:
            presentacion = re.sub(r'<[^>]+>', '', celdas[2]).strip()

        # Imagen
        imagen_match = re.search(r'<img[^>]*src="([^"]+)"', fila, re.IGNORECASE)
        imagen_url = imagen_match.group(1) if imagen_match else ""

        productos.append({
            "id": str(i + 1),
            "nombre": nombre,
            "precio": precio,
            "categoria": "",
            "presentacion": presentacion,
            "imagen": imagen_url
        })

    return productos


def main():
    print(f"🔍 Scrapeando {URL}...")

    os.makedirs(IMAGES_DIR, exist_ok=True)

    productos = []

    try:
        response = requests.get(URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
        html = response.text

        # Primero intentar JSON embebido (más fiable)
        productos = extraer_desde_json_embebido(html)

        # Si no, intentar HTML
        if not productos:
            productos = extraer_desde_html(html)

        # Procesar imágenes de los productos encontrados
        for p in productos:
            if p.get('imagen'):
                url_optimizada = descargar_y_optimizar_imagen(p['imagen'], p['id'])
                p['imagen'] = url_optimizada if url_optimizada else ""

    except Exception as e:
        print(f"❌ Error durante el scraping: {e}")
        productos = []

    # SIEMPRE guardar, incluso si está vacío
    output = {
        "fecha_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_productos": len(productos),
        "productos": productos
    }

    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    if productos:
        print(f"✅ {len(productos)} productos reales extraídos")
    else:
        print("⚠️ No se encontraron productos. Se guardó archivo vacío.")


if __name__ == "__main__":
    main()
