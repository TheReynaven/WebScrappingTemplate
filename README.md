# Books Scraper

Scraper profesional del catálogo de [books.toscrape.com](https://books.toscrape.com)
—un sitio público diseñado para practicar web scraping—. Recorre las 50 páginas del
catálogo, valida cada uno de los ~1000 libros con pydantic y los persiste en DuckDB,
con exports a CSV y Parquet. La salida en terminal usa [rich](https://github.com/Textualize/rich)
(progress bar y tablas) y toda la interfaz es un CLI de [typer](https://typer.tiangolo.com/).

## Características

- **Paginación automática** siguiendo el link `next` hasta agotar el catálogo.
- **Rate limiting** con delay configurable + jitter aleatorio de ±30% para no
  generar un patrón robótico.
- **Retries selectivos** con backoff exponencial (tenacity): reintenta solo ante
  5xx y timeouts; un 404 no se reintenta.
- **Validación por registro** con pydantic: un dato sucio genera un warning y se
  descarta, el pipeline nunca se cae.
- **User-Agent identificable** y verificación de `robots.txt` al iniciar.
- **Persistencia en DuckDB** con exports nativos a CSV y Parquet.
- **Salida rica** en terminal: progress bar en vivo y tablas de resumen, ratings y top 10.

## Requisitos

- Python 3.12+
- Las dependencias de [`requirements.txt`](requirements.txt) (httpx, BeautifulSoup4 + lxml,
  pydantic, tenacity, DuckDB, rich, typer, pytest).

## Instalación

```bash
python -m venv .venv
```

Activa el entorno virtual según tu shell:

```bash
.venv\Scripts\Activate.ps1     # Windows (PowerShell)
source .venv/Scripts/activate  # Windows (Git Bash)
source .venv/bin/activate      # Linux / macOS
```

E instala el proyecto y sus dependencias:

```bash
pip install -r requirements.txt
pip install -e .
```

## Uso

```bash
# Crawl completo (50 páginas, ~1000 libros)
python -m scraper crawl --pages 50 --delay 0.4 --db books.duckdb

# Top 10 libros por rating y precio
python -m scraper stats --db books.duckdb

# Export a CSV o Parquet
python -m scraper export --format csv
python -m scraper export --format parquet --output catalogo.parquet
```

Cada comando documenta sus opciones con `--help` (p. ej. `python -m scraper crawl --help`).

### Ejemplo de salida

Al terminar el crawl se imprime un resumen como este:

```
     Resumen del crawl              Distribución de ratings
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━┓        ┏━━━━━━━━┳━━━━━━━━┓
┃ Métrica         ┃  Valor ┃        ┃ Rating ┃ Libros ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━┩        ┡━━━━━━━━╇━━━━━━━━┩
│ Total de libros │   1000 │        │ ★      │    226 │
│ Precio promedio │ £35.07 │        │ ★★     │    196 │
│ Precio mínimo   │ £10.00 │        │ ★★★    │    203 │
│ Precio máximo   │ £59.99 │        │ ★★★★   │    179 │
└─────────────────┴────────┘        │ ★★★★★  │    196 │
                                    └────────┴────────┘
```

## Estructura del proyecto

```
books_scraper/
├── requirements.txt
├── pyproject.toml
├── Dockerfile
├── src/scraper/
│   ├── __main__.py      # habilita `python -m scraper`
│   ├── cli.py           # CLI de typer: crawl, stats, export
│   ├── fetch.py         # cliente httpx, retries, rate limit, robots.txt
│   ├── parse.py         # selectores CSS y extracción
│   ├── models.py        # modelo Book de pydantic
│   ├── storage.py       # DuckDB + exports
│   └── analyze.py       # estadísticas
├── tests/
│   ├── fixtures/page1.html   # HTML real para tests sin red
│   └── test_parse.py
└── extras/
    └── api_discovery.py      # descubrimiento de API (ver abajo)
```

## Tests

```bash
pytest
```

Los tests corren contra un HTML real guardado en `tests/fixtures/`, así que no
hacen peticiones de red y son deterministas.

## Docker

```bash
docker build -t books-scraper .
docker run --rm -v "$PWD/data:/app/data" books-scraper crawl --db data/books.duckdb
```

## Extra: descubrimiento de API

`extras/api_discovery.py` scrapea el scroll infinito de
[quotes.toscrape.com/scroll](https://quotes.toscrape.com/scroll) **sin navegador
headless**: en DevTools se ve que el sitio pagina por AJAX contra
`/api/quotes?page=N`, así que se consume ese JSON directamente.

```bash
python extras/api_discovery.py
```

## Decisiones de diseño

- **httpx en lugar de requests**: timeouts explícitos por defecto, HTTP/2 y una
  API idéntica en modo sync y async; si mañana hace falta concurrencia, la
  migración es trivial.
- **DuckDB en lugar de SQLite/CSV**: base analítica embebida (cero
  infraestructura) con SQL completo para las estadísticas y `COPY TO` nativo a
  CSV y Parquet, sin pasar por pandas.
- **Sin Selenium**: el contenido es HTML estático renderizado en servidor; un
  navegador headless multiplicaría el costo por nada. Cuando un sitio carga
  datos por JavaScript, primero se busca el endpoint JSON subyacente en
  DevTools (ver `extras/api_discovery.py`) y solo si no existe se considera
  automatizar un navegador.
- **Validación por registro, no por lote**: un dato sucio genera un warning y
  se descarta; el pipeline nunca se cae por un registro defectuoso.
- **Retries selectivos**: tenacity reintenta con backoff exponencial solo ante
  5xx y timeouts. Un 404 es un resultado, no una falla transitoria.

## Nota ética

Este proyecto scrapea únicamente sitios creados explícitamente para práctica
de scraping. Aun así aplica las buenas prácticas exigibles en producción:
verifica `robots.txt` al iniciar, se identifica con un User-Agent honesto y
espacia los requests con delay + jitter para no cargar el servidor.
