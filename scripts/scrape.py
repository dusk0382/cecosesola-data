#!/usr/bin/env python3
import json
import time
import requests
import os
import hashlib
from datetime import datetime
from playwright.sync_api import sync_playwright
from PIL import Image
from io import BytesIO

URL = "https://precios.cecosesola.coop/"
OUTPUT_JSON = "precios.json"
IMAGES_DIR = "images"

def descargar_y_optimizar_imagen(url, producto_id):
    """Descarga y optimiza una imagen. Retorna URL pública o None."""
    if not url or not url.startswith("http"):
        return None
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None
        
        img = Image.open(BytesIO(response.content))
        
        # Convertir a RGB si es necesario
        if img.mode in ('RGBA', 'LA', 'P'):
            bg = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            bg.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = bg
        
        # Redimensionar a máximo 120x120
        img.thumbnail((120, 120), Image.Resampling.LANCZOS)
        
        # Generar nombre único
        url_hash = hashlib.md5(url.encode()).hexdigest()[:10]
        filename = f"{producto_id}_{url_hash}.jpg"
        filepath = os.path.join(IMAGES_DIR, filename)
        img.save(filepath, "JPEG", quality=70, optimize=True)
        
        return f"https://raw.githubusercontent.com/dusk0382/cecosesola-data/main/images/{filename}"
    except Exception:
        return None

def main():
    print("🔍 Iniciando scraping...")
    os.makedirs(IMAGES_DIR, exist_ok=True)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, wait_until="networkidle", timeout=30000)
        time.sleep(5)
        
        print("📜 Cargando productos...")
        
        productos_antes = 0
        sin_cambios = 0
        
        while sin_cambios < 3:
            try:
                ver_mas = page.locator('button:has-text("Ver más")').first
                if ver_mas.is_visible():
                    ver_mas.click()
                    time.sleep(2)
            except:
                pass
            
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(1)
            
            productos_actuales = page.evaluate("document.querySelectorAll('product-card').length")
            
            if productos_actuales == productos_antes:
                sin_cambios += 1
            else:
                sin_cambios = 0
                print(f"  📦 {productos_actuales} productos")
            
            productos_antes = productos_actuales
        
        print(f"\n🔍 Extrayendo {productos_antes} productos...")
        
        productos = page.evaluate("""
            () => {
                const prods = [];
                const cards = document.querySelectorAll('product-card');
                
                cards.forEach((card, i) => {
                    const titleElem = card.querySelector('.title');
                    const descElem = card.querySelector('.description');
                    const imgElem = card.querySelector('img.image');
                    
                    const nombre = titleElem ? titleElem.innerText.trim() : '';
                    let precio = 0;
                    
                    if (descElem) {
                        const texto = descElem.innerText;
                        const match = texto.match(/(\\d+(?:[.,]\\d+)?)/);
                        if (match) precio = parseFloat(match[1].replace(',', '.'));
                    }
                    
                    const imagen = imgElem ? imgElem.src : '';
                    
                    if (nombre && precio > 0) {
                        prods.push({
                            id: String(i + 1),
                            nombre: nombre,
                            precio: precio,
                            imagen: imagen
                        });
                    }
                });
                
                return prods;
            }
        """)
        
        browser.close()
    
    print(f"  🖼️ Procesando imágenes...")
    
    imagenes_validas = 0
    for p in productos:
        if p.get('imagen'):
            url_opt = descargar_y_optimizar_imagen(p['imagen'], p['id'])
            if url_opt:
                p['imagen'] = url_opt
                imagenes_validas += 1
            else:
                p['imagen'] = ""
        else:
            p['imagen'] = ""
    
    output = {
        "fecha_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_productos": len(productos),
        "productos": productos
    }
    
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ {len(productos)} productos guardados")
    print(f"🖼️ {imagenes_validas} imágenes válidas descargadas")
    
    if productos:
        print("\n📋 Muestra:")
        for p in productos[:5]:
            print(f"  - {p['nombre']}: {p['precio']} Bs")

if __name__ == "__main__":
    main()
