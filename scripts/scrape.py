#!/usr/bin/env python3
import json
import time
from playwright.sync_api import sync_playwright

URL = "https://precios.cecosesola.coop/"
OUTPUT_JSON = "precios.json"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(URL, wait_until="networkidle", timeout=30000)
    time.sleep(5)
    
    page.wait_for_selector('product-card', timeout=10000)
    
    for _ in range(3):
        try:
            ver_mas = page.locator('button:has-text("Ver más")').first
            if ver_mas.is_visible():
                ver_mas.click()
                time.sleep(2)
        except:
            pass
    
    diagnostico = page.evaluate("""
        () => {
            const card = document.querySelector('product-card');
            if (!card) return { error: 'No se encontró product-card' };
            
            return {
                innerHTML: card.innerHTML.substring(0, 1000),
                innerText: card.innerText,
                shadowRoot: card.shadowRoot ? 'Presente' : 'Ausente',
                shadowHTML: card.shadowRoot ? card.shadowRoot.innerHTML.substring(0, 1000) : 'N/A',
                titleDirect: card.querySelector('.title') ? card.querySelector('.title').innerText : 'No encontrado',
                titleShadow: card.shadowRoot ? (card.shadowRoot.querySelector('.title') ? card.shadowRoot.querySelector('.title').innerText : 'No en shadow') : 'Sin shadow',
                descDirect: card.querySelector('.description') ? card.querySelector('.description').innerText : 'No encontrado',
                descShadow: card.shadowRoot ? (card.shadowRoot.querySelector('.description') ? card.shadowRoot.querySelector('.description').innerText : 'No en shadow') : 'Sin shadow',
                tagName: card.tagName,
                attributes: Array.from(card.attributes).map(a => a.name + '=' + a.value)
            };
        }
    """)
    
    print("\n=== DIAGNÓSTICO DEL PRIMER PRODUCT-CARD ===\n")
    print(f"Tag: {diagnostico.get('tagName')}")
    print(f"Atributos: {diagnostico.get('attributes')}")
    print(f"Shadow DOM: {diagnostico.get('shadowRoot')}")
    print(f"\n--- innerText ---\n{diagnostico.get('innerText')}")
    print(f"\n--- innerHTML (primeros 1000 chars) ---\n{diagnostico.get('innerHTML')}")
    print(f"\n--- shadowHTML (primeros 1000 chars) ---\n{diagnostico.get('shadowHTML')}")
    print(f"\n--- Búsqueda .title ---")
    print(f"  Directo: {diagnostico.get('titleDirect')}")
    print(f"  Shadow: {diagnostico.get('titleShadow')}")
    print(f"\n--- Búsqueda .description ---")
    print(f"  Directo: {diagnostico.get('descDirect')}")
    print(f"  Shadow: {diagnostico.get('descShadow')}")
    
    browser.close()

output = {"productos": []}
with open(OUTPUT_JSON, 'w') as f:
    json.dump(output, f)
