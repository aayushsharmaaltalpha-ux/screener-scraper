"""
CLI runner: python run_cli.py input.xlsx [output.xlsx]
Useful for headless/server execution without Streamlit.
"""
import asyncio
import sys
import logging
import pandas as pd
from datetime import datetime
from scraper.pipeline import run_pipeline
from utils.helpers import setup_logging

setup_logging("INFO")
logger = logging.getLogger(__name__)


async def main(input_path: str, output_path: str):
    df = pd.read_excel(input_path)
    if "Company Name" not in df.columns:
        logger.error("Input file must contain a 'Company Name' column.")
        sys.exit(1)

    companies = df["Company Name"].dropna().str.strip().tolist()
    logger.info(f"Starting scrape for {len(companies)} companies...")

    results = []
    async for i, result in run_pipeline(companies):
        results.append(result)
        status_icon = "✓" if result["Status"] == "Success" else "✗"
        logger.info(f"[{i+1}/{len(companies)}] {status_icon} {result['Company Name']}")

    df_out = pd.DataFrame(results, columns=[
        "Company Name", "% Responses", "Promoter Participated",
        "Document URL", "Status", "Error Message"
    ])

    from openpyxl import load_workbook
    df_out.to_excel(output_path, index=False, engine="openpyxl")

    # Auto-size columns
    wb = load_workbook(output_path)
    ws = wb.active
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 60)
    wb.save(output_path)

    success = (df_out["Status"] == "Success").sum()
    logger.info(f"Done. {success}/{len(results)} succeeded. Output: {output_path}")


if __name__ == "__main__":
    inp = sys.argv[1] if len(sys.argv) > 1 else "input.xlsx"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = sys.argv[2] if len(sys.argv) > 2 else f"output_{ts}.xlsx"
    asyncio.run(main(inp, out))
