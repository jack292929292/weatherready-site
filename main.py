import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from openpyxl import load_workbook

# Get yesterday's date
yesterday_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

# Fetch yesterday's max temp from Open-Meteo
url = (
    f"https://archive-api.open-meteo.com/v1/archive"
    f"?latitude=-31.95&longitude=115.86"
    f"&start_date={yesterday_date}&end_date={yesterday_date}"
    f"&daily=temperature_2m_max"
    f"&timezone=Australia/Perth"
)

response = requests.get(url)
if response.status_code != 200:
    print(f"❌ Failed to fetch Open-Meteo data. Status code: {response.status_code}")
    exit()

try:
    max_temp = response.json()["daily"]["temperature_2m_max"][0]
except Exception:
    print(f"❌ Could not find max temperature for {yesterday_date}")
    exit()

# Update WeatherImport sheet in Excel
file_path = "WeatherReady2025_POWERQUERY_READY.xlsx"
book = load_workbook(file_path)
ws = book["WeatherImport"]
ws["A2"] = yesterday_date
ws["B2"] = max_temp
book.save(file_path)

# Recalculate MaxPredict2 in Sheet2
sheet2_df = pd.read_excel(file_path, sheet_name="Sheet2")
sheet2_df["YearDay"] = pd.to_datetime(sheet2_df["Date"]).dt.dayofyear

grouped = sheet2_df.groupby("YearDay")
weighted_avg = grouped["MaxWeightedAverage"].mean()
weighted_std = grouped["MaxWeightedAverage"].std()
ndmd_avg = grouped["NDMDAverage"].mean()
ndmd_std = grouped["NDMDAverage"].std()

maxpredict2 = []
for idx, row in sheet2_df.iterrows():
    yd = row["YearDay"]
    try:
        wa = weighted_avg[yd]
        ws = weighted_std[yd]
        na = ndmd_avg[yd]
        ns = ndmd_std[yd]
        mean = (
            (wa / (ws**2) + (row["MaxPredict1"] + na) / (ns**2)) /
            ((1 / (ws**2)) + (1 / (ns**2)))
        )
        std_dev = np.sqrt(1 / ((1 / (ws**2)) + (1 / (ns**2))))
        maxpredict2.append(np.random.normal(loc=mean, scale=std_dev))
    except:
        maxpredict2.append(None)

sheet2_df["MaxPredict2"] = maxpredict2

# Save Sheet2 safely
with pd.ExcelWriter(file_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
    sheet2_df.to_excel(writer, sheet_name="Sheet2", index=False)

print(f"✅ Refreshed for {yesterday_date} — Max Temp: {max_temp}°C")
