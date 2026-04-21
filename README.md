# Screener.in Buyback Announcement Scraper

Extracts **% Responses** and **Promoter Participation** from buyback post-offer announcements on screener.in.

---

## Project Structure

```
screener_scraper/
├── app.py              # Streamlit UI
├── run_cli.py          # CLI runner (no UI)
├── requirements.txt
├── scraper/
│   ├── browser.py      # Playwright search + navigation
│   ├── extractor.py    # Document download + text parsing
│   └── pipeline.py     # Async orchestration + retries
└── utils/
    └── helpers.py      # Fuzzy match, text utils
```

---

## Local Setup

### 1. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Run the Streamlit app

```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

### 4. (Optional) CLI usage

```bash
python run_cli.py companies.xlsx results.xlsx
```

---

## Input Format

Excel file with a column named **`Company Name`**:

| Company Name       |
|--------------------|
| Infosys            |
| Tata Consultancy   |
| Wipro              |

---

## Output Format

| Column                | Description                          |
|-----------------------|--------------------------------------|
| Company Name          | Original input                       |
| % Responses           | Extracted value or "Not found"       |
| Promoter Participated | Yes / No / Unknown                   |
| Document URL          | Source document link                 |
| Status                | Success / Failed                     |
| Error Message         | Details if failed                    |

---

## Configuration

| Setting          | Location              | Default |
|------------------|-----------------------|---------|
| Max concurrency  | `pipeline.py`         | 3       |
| Max retries      | `pipeline.py`         | 2       |
| Base URL         | `browser.py`          | https://www.screener.in |

---

## Deployment Options

### Option A — Streamlit Community Cloud (Free)

1. Push to GitHub
2. Go to https://share.streamlit.io
3. Connect repo → set `app.py` as entry point
4. Add to `packages.txt`:
   ```
   chromium
   chromium-driver
   ```
5. Add to startup: `playwright install chromium`

### Option B — Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt && playwright install --with-deps chromium
CMD ["streamlit", "run", "app.py", "--server.port=8080"]
```

```bash
docker build -t scraper .
docker run -p 8080:8080 scraper
```

### Option C — AWS/GCP/Azure VM

```bash
# On Ubuntu 22.04
sudo apt-get install -y python3-pip
pip install -r requirements.txt
playwright install --with-deps chromium
streamlit run app.py --server.port 80 --server.address 0.0.0.0
```

---

## Notes

- Screener.in requires login for some data. If results consistently fail, try logging in manually first or adding session cookies.
- For >100 companies, consider increasing `MAX_CONCURRENCY` to 5 cautiously (risk of rate limiting).
- The scraper handles both PDF announcements (via pdfplumber) and HTML pages.
