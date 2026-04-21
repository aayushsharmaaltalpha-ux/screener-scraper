import streamlit as st
import pandas as pd
import asyncio
import io
import logging
from datetime import datetime
from scraper.pipeline import run_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

st.set_page_config(page_title="Screener Buyback Scraper", page_icon="📊", layout="centered")

st.title("📊 Screener.in Buyback Announcement Scraper")
st.markdown("Upload an Excel file with a **Company Name** column to extract buyback post-offer data.")

uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx", "xls"])

if uploaded_file:
    try:
        df_input = pd.read_excel(uploaded_file)
        if "Company Name" not in df_input.columns:
            st.error("❌ Excel file must have a column named **'Company Name'**")
        else:
            companies = df_input["Company Name"].dropna().str.strip().tolist()
            st.success(f"✅ Found **{len(companies)}** companies")
            st.dataframe(df_input[["Company Name"]].head(10), use_container_width=True)

            if st.button("🚀 Run Scraper", type="primary"):
                progress_bar = st.progress(0, text="Initializing...")
                status_text = st.empty()
                results_placeholder = st.empty()

                results = []

                async def run_with_progress():
                    async for i, result in run_pipeline(companies):
                        results.append(result)
                        pct = int(((i + 1) / len(companies)) * 100)
                        progress_bar.progress(pct, text=f"Processing {i+1}/{len(companies)}: {result['Company Name']}")
                        status_text.markdown(
                            f"**Last:** {result['Company Name']} → "
                            f"{'✅' if result['Status'] == 'Success' else '❌'} {result['Status']}"
                        )
                        results_placeholder.dataframe(
                            pd.DataFrame(results)[["Company Name", "Status", "% Responses", "Promoter Participated"]],
                            use_container_width=True,
                        )

                asyncio.run(run_with_progress())

                progress_bar.progress(100, text="Done!")
                status_text.markdown(f"**Completed {len(results)} companies**")

                df_out = pd.DataFrame(results, columns=[
                    "Company Name", "% Responses", "Promoter Participated",
                    "Document URL", "Status", "Error Message"
                ])

                buf = io.BytesIO()
                with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                    df_out.to_excel(writer, index=False, sheet_name="Results")
                    ws = writer.sheets["Results"]
                    for col in ws.columns:
                        max_len = max(len(str(cell.value or "")) for cell in col)
                        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 60)
                buf.seek(0)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(
                    label="⬇️ Download Results Excel",
                    data=buf,
                    file_name=f"buyback_results_{timestamp}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )

                success_count = (df_out["Status"] == "Success").sum()
                st.info(f"📈 **{success_count}/{len(results)}** companies scraped successfully")

    except Exception as e:
        st.error(f"Error reading file: {e}")
