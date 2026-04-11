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
    time.sleep(3)
    
    print("📜 Cargando todos los productos...")
    
    # Hacer clic en "Ver más" hasta que no haya más
    clicks = 0
    max_clicks = 20  # Límite de seguridad
    
    while clicks < max_clicks:
        try:
            # Buscar el botón "Ver más"
            ver_mas = page.locator('button:has-text("Ver más")').first
            if ver_mas.is_visible():
                ver_mas.click()
                clicks += 1
                print(f"  👆 Clic {clicks} en 'Ver más'")
                time.sleep(2)  # Esperar a que carguen los productos
            else:
                print("  ✅ No hay más botón 'Ver más'")
                break
        except:
            print("  ✅ No se encontró el botón 'Ver más'")
            break
    
    # Scroll final para asegurar que todo cargó
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(2)
    
    print("🔍 Extrayendo productos...")
    
    productos = page.evaluate("""
        () => {
            const prods = [];
            
            // Seleccionar todos los product-card
            const cards = document.querySelectorAll('product-card');
            
            cards.forEach((card, i) => {
                // Buscar el título (nombre del producto)
                const titleElem = card.querySelector('.title');
                const nombre = titleElem ? titleElem.innerText.trim() : '';
                
                // Buscar el precio (está en .description)
                const descElem = card.querySelector('.description');
                let precio = 0;
                if (descElem) {
                    const precioTexto = descElem.innerText;
                    // Extraer número del formato "Bs. 810.75" o "Bs 810,75"
                    const match = precioTexto.match(/([\\d.,]+)/);
                    if (match) {
                        precio = parseFloat(match[1].replace(',', '.'));
                    }
                }
                
                // Buscar imagen
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

print(f"\n✅ {len(productos)} productos guardados")

# Mostrar los primeros 5 como muestra
print("\n📋 Muestra:")
for p in productos[:5]:
    print(f"  - {p['nombre']}: {p['precio']} Bs")
