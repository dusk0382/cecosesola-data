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
    
    print("📜 Cargando...")
    
    # Cargar algunos productos (no todos para prueba rápida)
    for _ in range(5):
        try:
            ver_mas = page.locator('button:has-text("Ver más")').first
            if ver_mas.is_visible():
                ver_mas.click()
                time.sleep(2)
        except:
            pass
    
    # Extraer con diagnóstico incluido
    resultado = page.evaluate("""
        () => {
            const prods = [];
            const cards = document.querySelectorAll('product-card');
            const debug = [];
            
            for (let i = 0; i < Math.min(cards.length, 10); i++) {
                const card = cards[i];
                const titleElem = card.querySelector('.title');
                const descElem = card.querySelector('.description');
                
                const nombre = titleElem ? titleElem.innerText.trim() : 'NO_TITLE';
                let precio = 0;
                
                if (descElem) {
                    const texto = descElem.innerText;
                    const match = texto.match(/([\\d.,]+)/);
                    if (match) precio = parseFloat(match[1].replace(',', '.'));
                }
                
                debug.push({
                    index: i,
                    nombre: nombre,
                    precio: precio,
                    descText: descElem ? descElem.innerText : 'NO_DESC'
                });
                
                if (nombre && nombre !== 'NO_TITLE' && precio > 0) {
                    prods.push({ id: String(i+1), nombre: nombre, precio: precio, imagen: '' });
                }
            }
            
            return { productos: prods, debug: debug, totalCards: cards.length };
        }
    """)
    
    browser.close()

print(f"\n📊 Total cards: {resultado['totalCards']}")
print(f"📦 Productos extraídos: {len(resultado['productos'])}")

print("\n🔍 DEBUG (primeras 10 cards):")
for d in resultado['debug']:
    print(f"  [{d['index']}] nombre='{d['nombre'][:30]}' | precio={d['precio']} | descText='{d['descText']}'")

output = {
    "fecha_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "total_productos": len(resultado['productos']),
    "productos": resultado['productos']
}

with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
