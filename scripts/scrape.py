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
    
    # Guardar screenshot para ver qué cargó
    page.screenshot(path="debug_screenshot.png")
    
    # Guardar HTML completo
    html = page.content()
    with open("debug_page.html", "w", encoding="utf-8") as f:
        f.write(html)
    
    # Buscar cualquier texto que contenga "Bs" o "Precio"
    texto_con_bs = page.evaluate("""
        () => {
            const elementos = document.querySelectorAll('*');
            const encontrados = [];
            elementos.forEach(el => {
                const texto = el.innerText;
                if (texto && (texto.includes('Bs') || texto.includes('Precio') || texto.includes('precio'))) {
                    if (texto.length < 100) {
                        encontrados.push({
                            tag: el.tagName,
                            texto: texto,
                            clase: el.className
                        });
                    }
                }
            });
            return encontrados.slice(0, 20);
        }
    """)
    
    print("=== ELEMENTOS CON 'Bs' O 'Precio' ===")
    for e in texto_con_bs:
        print(f"{e['tag']}.{e['clase']}: {e['texto'][:80]}")
    
    # Buscar tablas
    tablas = page.evaluate("""
        () => {
            const tablas = document.querySelectorAll('table');
            return Array.from(tablas).map(t => ({
                filas: t.querySelectorAll('tr').length,
                texto_muestra: t.innerText.substring(0, 200)
            }));
        }
    """)
    
    print(f"\n=== TABLAS ENCONTRADAS: {len(tablas)} ===")
    for i, t in enumerate(tablas):
        print(f"Tabla {i}: {t['filas']} filas")
        print(f"  Muestra: {t['texto_muestra']}")
    
    browser.close()

# Guardar resultado del diagnóstico
output = {
    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "elementos_bs": texto_con_bs,
    "tablas": tablas
}

with open("diagnostico.json", "w") as f:
    json.dump(output, f, indent=2)

print("\n✅ Diagnóstico guardado")
