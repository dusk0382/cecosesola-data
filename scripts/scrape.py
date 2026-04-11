#!/usr/bin/env python3
import json
import time
from datetime import datetime
from playwright.sync_api import sync_playwright

URL = "https://precios.cecosesola.coop/"
OUTPUT_JSON = "precios.json"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(URL, wait_until="networkidle", timeout=30000)
    time.sleep(5)  # Esperar carga inicial
    
    print("📜 Cargando productos...")
    
    # Contar productos iniciales
    productos_antes = 0
    sin_cambios = 0
    
    while sin_cambios < 3:  # Intentar hasta 3 veces sin cambios
        # Hacer clic en "Ver más" si existe
        try:
            ver_mas = page.locator('button:has-text("Ver más")').first
            if ver_mas.is_visible():
                ver_mas.click()
                print("  👆 Clic en 'Ver más'")
                time.sleep(3)  # Esperar a que carguen
        except:
            pass
        
        # Scroll para trigger lazy loading
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)
        
        # Contar productos actuales
        productos_actuales = page.evaluate("document.querySelectorAll('product-card').length")
        print(f"  📦 Productos detectados: {productos_actuales}")
        
        if productos_actuales == productos_antes:
            sin_cambios += 1
        else:
            sin_cambios = 0
        
        productos_antes = productos_actuales
    
    print(f"\n🔍 Total productos cargados: {productos_antes}")
    print("⏳ Esperando 3 segundos para renderizado completo...")
    time.sleep(3)
    
    # Extraer productos
    productos = page.evaluate("""
        () => {
            const prods = [];
            const cards = document.querySelectorAll('product-card');
            
            cards.forEach((card, i) => {
                const titleElem = card.querySelector('.title');
                const nombre = titleElem ? titleElem.innerText.trim() : '';
                
                const descElem = card.querySelector('.description');
                let precio = 0;
                if (descElem) {
                    const precioTexto = descElem.innerText;
                    const match = precioTexto.match(/([\\d.,]+)/);
                    if (match) {
                        precio = parseFloat(match[1].replace(',', '.'));
                    }
                }
                
                const imgElem = card.querySelector('img.image');
                const imagen = imgElem ? imgElem.src : '';
                
                if (nombre && precio > 0) {
                    prods.push({
                        id: String(i + 1),
                        nombre: nombre,
                        precio: precio,
                        categoria: '',
                        presentacion: '',
                        imagen: imagen
                    });
                }
            });
            
            return prods;
        }
    """)
    
    browser.close()

output = {
    "fecha_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "total_productos": len(productos),
    "productos": productos
}

with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"\n✅ {len(productos)} productos guardados en {OUTPUT_JSON}")

if productos:
    print("\n📋 Primeros 5 productos:")
    for p in productos[:5]:
        print(f"  - {p['nombre']}: {p['precio']} Bs")
else:
    print("\n⚠️ No se encontraron productos")
