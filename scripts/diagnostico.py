#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import time

URL = "https://precios.cecosesola.coop/"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(URL, wait_until="networkidle", timeout=30000)
    
    # Esperar a que cargue algo
    page.wait_for_selector('table tbody tr', timeout=10000)
    time.sleep(2)
    
    # Scroll para cargar más productos
    print("📜 Haciendo scroll para cargar más...")
    last_height = page.evaluate("document.body.scrollHeight")
    scroll_count = 0
    
    while scroll_count < 10:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(2)
        new_height = page.evaluate("document.body.scrollHeight")
        if new_height == last_height:
            # Intentar hacer clic en "Ver más" si existe
            try:
                page.click('text="Ver más"', timeout=2000)
                time.sleep(2)
            except:
                pass
            break
        last_height = new_height
        scroll_count += 1
    
    # Ver cuántos productos hay ahora
    total = page.evaluate("document.querySelectorAll('table tbody tr').length")
    print(f"✅ Productos cargados: {total}")
    
    # Ver las primeras 3 filas en detalle
    filas = page.evaluate("""
        () => {
            const filas = document.querySelectorAll('table tbody tr');
            const resultado = [];
            for (let i = 0; i < Math.min(5, filas.length); i++) {
                const fila = filas[i];
                const celdas = fila.querySelectorAll('td');
                resultado.push({
                    texto_celdas: Array.from(celdas).map(td => td.innerText.trim()),
                    html_celda2: celdas[1] ? celdas[1].innerHTML : ''
                });
            }
            return resultado;
        }
    """)
    
    for i, f in enumerate(filas):
        print(f"\n=== FILA {i+1} ===")
        print(f"Celdas: {f['texto_celdas']}")
        print(f"HTML celda 2 (precio): {f['html_celda2'][:200]}")
    
    browser.close()
