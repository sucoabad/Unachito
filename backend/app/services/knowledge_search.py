import os
from sentence_transformers import SentenceTransformer, util

# Ruta donde están los archivos de scraping
SCRAPED_DATA_DIR = os.path.join(os.path.dirname(__file__), 'scraped_data')

# Cargar el modelo BERT multilingüe una sola vez
model = SentenceTransformer('distiluse-base-multilingual-cased-v1')

def load_scraped_data():
    """
    Carga todos los textos scrapeados y los devuelve en un diccionario.
    Clave: nombre del archivo, Valor: texto.
    """
    data = {}
    for filename in os.listdir(SCRAPED_DATA_DIR):
        if filename.endswith('.txt'):
            filepath = os.path.join(SCRAPED_DATA_DIR, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                data[filename] = f.read()
    return data

def split_text_into_chunks(text, max_chunk_size=500):
    """
    Divide un texto largo en fragmentos más pequeños (máx. 500 caracteres por defecto).
    """
    sentences = text.split('\n')
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) < max_chunk_size:
            current_chunk += sentence + " "
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence + " "
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

def search_in_scraped_data(pregunta_usuario, umbral_similitud=0.65, return_source=False):
    """
    Busca la pregunta en los archivos scrapeados y devuelve el fragmento más similar.
    Si return_source=True, devuelve una tupla (respuesta, fuente).
    """
    scraped_data = load_scraped_data()
    pregunta_embedding = model.encode(pregunta_usuario, convert_to_tensor=True)

    mejor_similitud = 0
    mejor_fragmento = None
    mejor_fuente = None

    for archivo, texto in scraped_data.items():
        chunks = split_text_into_chunks(texto)
        for chunk in chunks:
            chunk_embedding = model.encode(chunk, convert_to_tensor=True)
            similitud = util.pytorch_cos_sim(pregunta_embedding, chunk_embedding).item()

            if similitud > mejor_similitud:
                mejor_similitud = similitud
                mejor_fragmento = chunk
                mejor_fuente = archivo

    print(f"[🔎] Mejor similitud: {mejor_similitud:.2f} (fuente: {mejor_fuente})")

    if mejor_similitud >= umbral_similitud:
        if return_source:
            import os
            nombre_limpio = os.path.splitext(mejor_fuente)[0] if mejor_fuente else None
            return mejor_fragmento.strip(), nombre_limpio

        else:
            return mejor_fragmento.strip()
    else:
        if return_source:
            return None, None
        else:
            return None

