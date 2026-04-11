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
    
    # Scroll para cargar
    for _ in range(5):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)
    
    productos = page.evaluate("""
        () => {
            const prods = [];
            const filas = document.querySelectorAll('table tbody tr');
            
            filas.forEach((fila, i) => {
                const celdas = fila.querySelectorAll('td');
                if (celdas.length >= 2) {
                    const nombre = celdas[0].innerText.trim();
                    const precioCelda = celdas[1].innerText;
                    
                    // Intentar múltiples patrones para extraer el precio
                    let precio = 0;
                    
                    // Patrón 1: número con Bs
                    let match = precioCelda.match(/Bs[\\s.]*([\\d.,]+)/i);
                    if (match) precio = parseFloat(match[1].replace(',', '.'));
                    
                    // Patrón 2: solo número con decimal
                    if (!precio) {
                        match = precioCelda.match(/(\\d+[.,]\\d+)/);
                        if (match) precio = parseFloat(match[1].replace(',', '.'));
                    }
                    
                    // Patrón 3: cualquier número
                    if (!precio) {
                        match = precioCelda.match(/(\\d+)/);
                        if (match) precio = parseFloat(match[1]);
                    }
                    
                    if (nombre && precio > 0) {
                        prods.push({
                            id: String(i),
                            nombre: nombre,
                            precio: precio,
                            categoria: '',
                            presentacion: '',
                            imagen: ''
                        });
                    }
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
for p in productos[:3]:
    print(f"   - {p['nombre']}: {p['precio']} Bs")
