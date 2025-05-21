from app.services.scraping_service import scrape_and_save, URLS

def run_batch_scraping():
    for url in URLS:
        print(f"Iniciando scraping para: {url}")
        scrape_and_save(url)

if __name__ == "__main__":
    run_batch_scraping()
