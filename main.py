import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from openpyxl import load_workbook

# Step 1: Get yesterday's date
yesterday = (datetime.now() - timedelta(days=1)).date()

# Step 2: Fetch BOM data for Perth Metro (station 009225)
url = "https://www.bom.gov.au/climate/dwo/IDCJDW6111.latest.txt"
response = requests.get(url)
lines = response.text.splitlines()

max_temp = None
for line in lines:
    parts = line.split()
    if len(parts) >= 3:
        try:
            date = datetime.strptime(parts[0], "%d/%m/%Y").date()
            if date == yesterday:
                max_temp = float(parts[2])
                break
        except:
            continue

if max_temp is None:
    print(f"❌ Could not find max temperature for {yesterday}")
    exit()

# Step 3: Load and update the Excel file
file_path = "WeatherReady2025_POWERQUERY_READY.xlsx"
book = load_workbook(file_path)

# Write to WeatherImport!A2 and B2
ws = book["WeatherImport"]
ws["A2"] = yesterday.strftime("%Y-%m-%d")
ws["B2"] = max_temp

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

# Save updates
with pd.ExcelWriter(file_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
    writer.book = book
    sheet2_df.to_excel(writer, sheet_name="Sheet2", index=False)

book.save(file_path)

print(f"✅ Refreshed for {yesterday} — Max Temp: {max_temp}°C")
