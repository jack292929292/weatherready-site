import pandas as pd
import numpy as np
import requests
from datetime import datetime
from openpyxl import load_workbook
from io import StringIO

# Step 1: Build URL
now = datetime.now()
year_month = now.strftime("%Y%m")
url = f"https://www.bom.gov.au/climate/dwo/{year_month}/text/IDCJDW6111.{year_month}.csv"
headers = {
    "User-Agent": "Mozilla/5.0"
}

# Step 2: Fetch CSV and parse it
response = requests.get(url, headers=headers)
if response.status_code != 200:
    print(f"❌ Failed to fetch BOM data. Status code: {response.status_code}")
    exit()

# Read the CSV, skipping first 6 BOM header rows
data = pd.read_csv(StringIO(response.text), skiprows=6)

# Step 3: Clean date and max temp fields
data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
data["Maximum temperature (°C)"] = pd.to_numeric(data["Maximum temperature (°C)"], errors="coerce")
data = data.dropna(subset=["Date", "Maximum temperature (°C)"])

# Get the most recent valid row
latest = data.iloc[-1]
obs_date = latest["Date"].date()
max_temp = latest["Maximum temperature (°C)"]

# Step 4: Update Excel
file_path = "WeatherReady2025_POWERQUERY_READY.xlsx"
book = load_workbook(file_path)
ws = book["WeatherImport"]
ws["A2"] = obs_date.strftime("%Y-%m-%d")
ws["B2"] = max_temp

# Step 5: Recalculate MaxPredict2
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
    if pd.notna(yd) and yd in weighted_avg and yd in ndmd_avg:
        try:
            mean = (
                (weighted_avg[yd] / (weighted_std[yd]**2) + (row["MaxPredict1"] + ndmd_avg[yd]) / (ndmd_std[yd]**2)) /
                ((1 / (weighted_std[yd]**2)) + (1 / (ndmd_std[yd]**2)))
            )
            std_dev = np.sqrt(1 / ((1 / (weighted_std[yd]**2)) + (1 / (ndmd_std[yd]**2))))
            maxpredict2.append(np.random.normal(loc=mean, scale=std_dev))
        except:
            maxpredict2.append(None)
    else:
        maxpredict2.append(None)

sheet2_df["MaxPredict2"] = maxpredict2

with pd.ExcelWriter(file_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
    writer.book = book
    sheet2_df.to_excel(writer, sheet_name="Sheet2", index=False)

book.save(file_path)

print(f"✅ Refreshed for {obs_date} — Max Temp: {max_temp}°C")
