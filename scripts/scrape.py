#!/usr/bin/env python3
"""
Script para scrapear precios de Cecosesola usando Playwright
"""

import json
import os
import re
from datetime import datetime
from io import BytesIO
from playwright.sync_api import sync_playwright
import requests
from PIL import Image

URL = "https://precios.cecosesola.coop/"
OUTPUT_JSON = "precios.json"
IMAGES_DIR = "images"

def descargar_y_optimizar_imagen(url, producto_id):
    """Descarga y optimiza una imagen."""
    if not url or not url.startswith("http"):
        return None
    try:
        response = requests.get(url, timeout=10)
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

def extraer_productos():
    """Usa Playwright para esperar a que la página cargue y extraer los productos."""
    productos = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("  🌐 Cargando página con Playwright...")
        page.goto(URL, wait_until="networkidle", timeout=30000)
        
        # Esperar a que aparezca algún elemento de producto
        # Intentar varios selectores comunes
        selectores = [
            'table tbody tr',
            '.producto',
            '.product',
            '[class*="product"]',
            'tr[class*="product"]',
            'div[class*="item"]'
        ]
        
        for selector in selectores:
            try:
                page.wait_for_selector(selector, timeout=5000)
                print(f"  ✅ Encontrado: {selector}")
                break
            except:
                continue
        
        # Extraer datos usando JavaScript en el contexto de la página
        productos = page.evaluate("""
            () => {
                const productos = [];
                
                // Buscar filas de tabla
                const filas = document.querySelectorAll('table tbody tr, tr[class*="product"], div[class*="product"]');
                
                filas.forEach((fila, index) => {
                    // Buscar nombre (primer texto significativo)
                    const nombreElem = fila.querySelector('td:first-child, .nombre, .name, [class*="name"], [class*="title"]');
                    const nombre = nombreElem ? nombreElem.innerText.trim() : '';
                    
                    // Buscar precio (texto con Bs o número)
                    const precioElem = fila.querySelector('td:nth-child(2), .precio, .price, [class*="price"]');
                    const precioTexto = precioElem ? precioElem.innerText : '';
                    const precioMatch = precioTexto.match(/[\\d.,]+/);
                    const precio = precioMatch ? parseFloat(precioMatch[0].replace(',', '.')) : 0;
                    
                    // Buscar imagen
                    const imgElem = fila.querySelector('img');
                    const imagen = imgElem ? imgElem.src : '';
                    
                    // Buscar presentación
                    const presElem = fila.querySelector('td:nth-child(3), .presentacion, [class*="pres"]');
                    const presentacion = presElem ? presElem.innerText.trim() : '';
                    
                    if (nombre && precio > 0) {
                        productos.push({
                            id: String(index + 1),
                            nombre: nombre,
                            precio: precio,
                            categoria: '',
                            presentacion: presentacion,
                            imagen: imagen
                        });
                    }
                });
                
                // Si no encontró con selectores, buscar por estructura genérica
                if (productos.length === 0) {
                    // Buscar cualquier elemento que parezca un producto
                    const elementos = document.querySelectorAll('div, li, tr');
                    elementos.forEach((el, idx) => {
                        const texto = el.innerText || '';
                        // Buscar patrón: texto + número con Bs
                        const match = texto.match(/(.+?)\\s*Bs\\s*([\\d.,]+)/i);
                        if (match) {
                            const nombre = match[1].trim();
                            const precio = parseFloat(match[2].replace(',', '.'));
                            const img = el.querySelector('img');
                            productos.push({
                                id: String(idx + 1),
                                nombre: nombre,
                                precio: precio,
                                categoria: '',
                                presentacion: '',
                                imagen: img ? img.src : ''
                            });
                        }
                    });
                }
                
                return productos;
            }
        """)
        
        browser.close()
    
    return productos

def main():
    print(f"🔍 Scrapeando {URL}...")
    os.makedirs(IMAGES_DIR, exist_ok=True)
    
    productos = []
    
    try:
        productos = extraer_productos()
        print(f"  📦 Productos encontrados: {len(productos)}")
        
        # Procesar imágenes
        for p in productos:
            if p.get('imagen'):
                url_opt = descargar_y_optimizar_imagen(p['imagen'], p['id'])
                p['imagen'] = url_opt if url_opt else ""
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        productos = []
    
    output = {
        "fecha_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_productos": len(productos),
        "productos": productos
    }
    
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    if productos:
        print(f"✅ {len(productos)} productos guardados")
        # Mostrar primeros 3 para debug
        for p in productos[:3]:
            print(f"   - {p['nombre']}: {p['precio']} Bs")
    else:
        print("⚠️ No se encontraron productos")

if __name__ == "__main__":
    main()
