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
    time.sleep(3)
    
    # Extraer atravesando Shadow DOM
    productos = page.evaluate("""
        () => {
            const prods = [];
            const cards = document.querySelectorAll('product-card');
            
            cards.forEach((card, i) => {
                // Intentar acceder al Shadow DOM
                let nombre = '';
                let precio = 0;
                let imagen = '';
                
                // Método 1: Acceder al shadowRoot
                if (card.shadowRoot) {
                    const titleElem = card.shadowRoot.querySelector('.title');
                    nombre = titleElem ? titleElem.innerText.trim() : '';
                    
                    const descElem = card.shadowRoot.querySelector('.description');
                    if (descElem) {
                        const match = descElem.innerText.match(/([\\d.,]+)/);
                        if (match) precio = parseFloat(match[1].replace(',', '.'));
                    }
                    
                    const imgElem = card.shadowRoot.querySelector('img.image');
                    imagen = imgElem ? imgElem.src : '';
                }
                
                // Método 2: Si no hay shadowRoot, buscar en el contenido normal
                if (!nombre) {
                    const titleElem = card.querySelector('.title');
                    nombre = titleElem ? titleElem.innerText.trim() : '';
                    
                    const descElem = card.querySelector('.description');
                    if (descElem) {
                        const match = descElem.innerText.match(/([\\d.,]+)/);
                        if (match) precio = parseFloat(match[1].replace(',', '.'));
                    }
                    
                    const imgElem = card.querySelector('img.image');
                    imagen = imgElem ? imgElem.src : '';
                }
                
                // Método 3: Extraer del texto completo de la card
                if (!nombre && card.innerText) {
                    const lineas = card.innerText.split('\\n').filter(l => l.trim());
                    if (lineas.length >= 2) {
                        nombre = lineas[0].trim();
                        const precioMatch = lineas[1].match(/([\\d.,]+)/);
                        if (precioMatch) precio = parseFloat(precioMatch[1].replace(',', '.'));
                    }
                }
                
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

output = {
    "fecha_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "total_productos": len(productos),
    "productos": productos
}

with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print(f"✅ {len(productos)} productos guardados")

if productos:
    print("\n📋 Muestra:")
    for p in productos[:5]:
        print(f"  - {p['nombre']}: {p['precio']} Bs")
