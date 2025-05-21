import requests
from bs4 import BeautifulSoup
import os

# Directorio donde guardamos los textos scrapeados
SCRAPED_DATA_DIR = os.path.join(os.path.dirname(__file__), 'scraped_data')

# Crear el directorio si no existe
if not os.path.exists(SCRAPED_DATA_DIR):
    os.makedirs(SCRAPED_DATA_DIR)

# Lista de URLs objetivo (puedes ampliarla)
URLS = [
    'https://www.unach.edu.ec',
    'https://moodle.unach.edu.ec',
    'https://alumni.unach.edu.ec',
    'https://biblioteca.unach.edu.ec',
    'https://cebv.unach.edu.ec',
    'https://caicti.unach.edu.ec',
    'https://chakinan.unach.edu.ec',
    'http://dspace.unach.edu.ec',
    'https://dtic.unach.edu.ec',
    'https://editorial.unach.edu.ec',
    'https://eugenioespejo.unach.edu.ec',
    'https://investigacion.unach.edu.ec',
    'https://kairos.unach.edu.ec',
    'https://novasinergia.unach.edu.ec',
    'https://online.unach.edu.ec',
    'https://posgrado.unach.edu.ec',
    'https://posgradovirtual.unach.edu.ec',
    'https://sgc.unach.edu.ec',
    'https://sicoaweb.unach.edu.ec',
    'https://sicoaweb2.unach.edu.ec',
    'https://soludableecuador.unach.edu.ec',
    'https://uvirtual.unach.edu.ec',
    'https://vinculacion.unach.edu.ec',
    'http://wireless.unach.edu.ec'
]


def clean_text(text):
    """Limpia el texto eliminando saltos de línea y espacios extra."""
    return ' '.join(text.split())

from urllib.parse import urljoin, urlparse

def scrape_and_save(url, max_pages=5):
    """
    Scrapea una URL y también visita enlaces internos (hasta max_pages).
    Guarda todo el texto en un archivo local.
    """
    visited = set()
    to_visit = [url]
    all_texts = []

    while to_visit and len(visited) < max_pages:
        current_url = to_visit.pop(0)
        if current_url in visited:
            continue

        print(f"Scrapeando: {current_url}")
        try:
            response = requests.get(current_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extraer texto visible
            texts = []
            for tag in soup.find_all(['p', 'li', 'span']):
                content = tag.get_text(strip=True)
                if content:
                    texts.append(content)

            all_texts.extend(texts)
            visited.add(current_url)

            # Buscar enlaces internos
            for link in soup.find_all('a', href=True):
                href = link['href']
                full_url = urljoin(url, href)
                # Asegurar que pertenece al mismo dominio
                if urlparse(full_url).netloc == urlparse(url).netloc:
                    if full_url not in visited and full_url not in to_visit:
                        to_visit.append(full_url)

        except Exception as e:
            print(f"[⚠️] Error scrapeando {current_url}: {e}")

    # Limpiar y unir texto
    final_text = '\n'.join([clean_text(t) for t in all_texts])

    # Guardar en archivo local
    domain = url.replace('https://', '').replace('http://', '').replace('/', '_')
    filepath = os.path.join(SCRAPED_DATA_DIR, f"{domain}.txt")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(final_text)

    print(f"[✔️] Scraping + crawling completado para: {url} (guardado en {filepath})")
    return filepath


def load_scraped_data():
    """Carga todos los textos scrapeados y los devuelve en un diccionario."""
    data = {}
    for filename in os.listdir(SCRAPED_DATA_DIR):
        if filename.endswith('.txt'):
            with open(os.path.join(SCRAPED_DATA_DIR, filename), 'r', encoding='utf-8') as f:
                data[filename] = f.read()
    return data

def scrape_live(url):
    """Scrapea en vivo y devuelve el texto sin guardarlo."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        texts = []
        for tag in soup.find_all(['p', 'li', 'span']):
            content = tag.get_text(strip=True)
            if content:
                texts.append(content)
        final_text = '\n'.join([clean_text(t) for t in texts])
        print(f"[🔎] Scraping en vivo completado para: {url}")
        return final_text
    except Exception as e:
        print(f"[⚠️] Error en scraping en vivo {url}: {e}")
        return ''




from sentence_transformers import SentenceTransformer, util

# Modelo reutilizable (evita cargar múltiples veces)
_model = SentenceTransformer("all-MiniLM-L6-v2")

def search_in_scraped_data(query: str, threshold: float = 0.6) -> str:
    """
    Busca semánticamente en los textos scrapeados usando embeddings.
    Retorna el fragmento más similar si supera el umbral.
    """
    query_embedding = _model.encode(query, convert_to_tensor=True)

    data = load_scraped_data()
    mejores_similitudes = []

    for archivo, texto in data.items():
        oraciones = [line.strip() for line in texto.split('\n') if len(line.strip()) > 20]
        if not oraciones:
            continue

        oraciones_embeddings = _model.encode(oraciones, convert_to_tensor=True)
        similitudes = util.pytorch_cos_sim(query_embedding, oraciones_embeddings)[0]

        best_idx = similitudes.argmax().item()
        best_score = similitudes[best_idx].item()

        if best_score >= threshold:
            fragmento = oraciones[best_idx]
            mejores_similitudes.append((best_score, archivo, fragmento))

    if mejores_similitudes:
        mejores_similitudes.sort(reverse=True)  # mayor similitud primero
        score, archivo, frag = mejores_similitudes[0]
        return f"{frag} <br><small>🔎 Fuente scraping: {archivo} (similitud: {score:.2f})</small>"

    return ""

