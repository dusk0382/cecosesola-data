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
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

URL = "https://precios.cecosesola.coop/"
OUTPUT_JSON = "precios.json"
IMAGES_DIR = "images"
MANIFEST_FILE = "images_manifest.json"

# NUEVO: User-Agent global para consistencia
USER_AGENT = "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36"

def cargar_manifest():
    if os.path.exists(MANIFEST_FILE):
        with open(MANIFEST_FILE, 'r') as f:
            return json.load(f)
    return {}

def guardar_manifest(manifest):
    with open(MANIFEST_FILE, 'w') as f:
        json.dump(manifest, f)

def configurar_sesion_robusta():
    """NUEVO: Configura una sesión HTTP con reintentos automáticos y User-Agent"""
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    
    # Si hay un fallo de red o el servidor devuelve error 500+, reintenta 3 veces
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

def descargar_y_optimizar_imagen(producto, manifest, session):
    url = producto.get('imagen')
    producto_id = producto['id']
    es_nueva = False
    
    if not url or not url.startswith("http"):
        producto['imagen'] = ""
        return producto, es_nueva

    url_hash = hashlib.md5(url.encode()).hexdigest()

    if url_hash in manifest:
        filename = manifest[url_hash]
        if os.path.exists(os.path.join(IMAGES_DIR, filename)):
            producto['imagen'] = f"https://raw.githubusercontent.com/dusk0382/cecosesola-data/main/images/{filename}"
            return producto, es_nueva

    try:
        response = session.get(url, timeout=15) # Aumentado un poco para CI
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))

            if img.mode in ('RGBA', 'LA', 'P'):
                bg = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                bg.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = bg

            img.thumbnail((120, 120), Image.Resampling.LANCZOS)

            filename = f"{producto_id}_{url_hash[:8]}.jpg"
            filepath = os.path.join(IMAGES_DIR, filename)
            img.save(filepath, "JPEG", quality=70, optimize=True)

            producto['imagen'] = f"https://raw.githubusercontent.com/dusk0382/cecosesola-data/main/images/{filename}"
            producto['_url_hash_nuevo'] = url_hash
            producto['_filename_nuevo'] = filename
            es_nueva = True
        else:
            producto['imagen'] = ""
            
    except Exception as e:
        print(f"    ⚠️ Error en ID {producto_id}: {e}")
        producto['imagen'] = ""

    return producto, es_nueva

def main():
    print("🔍 Iniciando scraping...")
    start_time = time.time()

    os.makedirs(IMAGES_DIR, exist_ok=True)
    manifest = cargar_manifest()

    with sync_playwright() as p:
        # NUEVO: Argumentos extra para evitar ser detectados como bot en CI
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        # NUEVO: Sincronizar el User-Agent y emular pantalla móvil (Viewport)
        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={'width': 412, 'height': 915},
            is_mobile=True
        )
        
        page = context.new_page()
        page.goto(URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(5000)

        print("📜 Cargando productos...")

        productos_antes = 0
        sin_cambios = 0

        while sin_cambios < 3:
            try:
                ver_mas = page.locator('button:has-text("Ver más")').first
                if ver_mas.is_visible(timeout=1000):
                    ver_mas.click()
                    page.wait_for_timeout(2000)
            except Exception:
                pass

            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(1000)

            productos_actuales = page.evaluate("document.querySelectorAll('product-card').length")

            if productos_actuales == productos_antes:
                sin_cambios += 1
            else:
                sin_cambios = 0
                print(f"  📦 {productos_actuales} productos detectados")

            productos_antes = productos_actuales

        print(f"\n🔍 Extrayendo datos de {productos_antes} productos...")

        productos_crudos = page.evaluate("""
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
                        const match = descElem.innerText.match(/(\\d+(?:[.,]\\d+)?)/);
                        if (match) precio = parseFloat(match[1].replace(',', '.'));
                    }

                    if (nombre && precio > 0) {
                        prods.push({
                            id: String(i + 1),
                            nombre: nombre,
                            precio: precio,
                            imagen: imgElem ? imgElem.src : ''
                        });
                    }
                });
                return prods;
            }
        """)
        context.close()
        browser.close()

    print(f"\n🖼️ Procesando imágenes concurrentemente...")
    imagenes_validas = 0
    imagenes_nuevas = 0
    productos_finales = []

    # Inicializamos la sesión robusta
    session = configurar_sesion_robusta()
    
    # En GitHub Actions (2 cores), ThreadPool tomará unos 6 workers. Ideal para no saturar.
    max_workers = min(10, os.cpu_count() + 4) 
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futuros = {executor.submit(descargar_y_optimizar_imagen, p, manifest, session): p for p in productos_crudos}
        
        for futuro in as_completed(futuros):
            prod_procesado, es_nueva = futuro.result()
            
            if es_nueva:
                imagenes_nuevas += 1
                manifest[prod_procesado['_url_hash_nuevo']] = prod_procesado['_filename_nuevo']
                print(f"    🆕 Descargada: {prod_procesado['_filename_nuevo']}")
                del prod_procesado['_url_hash_nuevo']
                del prod_procesado['_filename_nuevo']
                
            if prod_procesado['imagen']:
                imagenes_validas += 1
                
            productos_finales.append(prod_procesado)

    productos_finales.sort(key=lambda x: int(x['id']))

    guardar_manifest(manifest)

    output = {
        "fecha_actualizacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_productos": len(productos_finales),
        "productos": productos_finales
    }

    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - start_time
    print(f"\n✅ {len(productos_finales)} productos guardados")
    print(f"🖼️ {imagenes_validas} imágenes enlazadas ({imagenes_nuevas} descargas nuevas)")
    print(f"⏱️ Tiempo total: {elapsed:.1f} segundos")

if __name__ == "__main__":
    main()
