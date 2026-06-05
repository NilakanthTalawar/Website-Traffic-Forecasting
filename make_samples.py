import pandas as pd
import numpy as np
import os

os.makedirs("sample_data", exist_ok=True)

SOURCES = ["google / organic","direct / none","facebook / social",
           "email / newsletter","google / cpc","twitter / social",
           "referral / referral","youtube / social"]
COUNTRIES = ["United States","India","United Kingdom","Germany",
             "Canada","Australia","France","Brazil","Japan","Others"]
COUNTRY_W = [0.32,0.18,0.09,0.07,0.06,0.05,0.04,0.04,0.03,0.12]

def make_csv(name, start, end, base_sessions, seed):
    np.random.seed(seed)
    dates = pd.date_range(start=start, end=end, freq="D")
    n = len(dates)
    trend = np.linspace(base_sessions * 0.6, base_sessions * 1.4, n)
    weekly = base_sessions * 0.15 * np.sin(2 * np.pi * np.arange(n) / 7)
    monthly = base_sessions * 0.08 * np.sin(2 * np.pi * np.arange(n) / 30)
    noise = np.random.normal(0, base_sessions * 0.06, n)
    sessions = (trend + weekly + monthly + noise).clip(50).astype(int)
    users = (sessions * np.random.uniform(0.72, 0.88, n)).astype(int)
    new_users = (users * np.random.uniform(0.45, 0.65, n)).astype(int)
    bounce_rate = np.clip(np.random.normal(42, 8, n), 20, 75).round(1)
    pages = np.clip(np.random.normal(3.2, 0.6, n), 1.5, 6.0).round(2)
    duration = np.clip(np.random.normal(185, 40, n), 60, 420).astype(int)
    cvr = np.clip(0.03 + 0.015 * np.sin(2 * np.pi * np.arange(n) / 90)
                  + np.random.normal(0, 0.008, n), 0.01, 0.08)
    conversions = (sessions * cvr).astype(int)
    sources = np.random.choice(SOURCES, size=n)
    countries = np.random.choice(COUNTRIES, size=n, p=COUNTRY_W)

    df = pd.DataFrame({
        "Date": dates.strftime("%Y%m%d"),
        "Sessions": sessions,
        "Users": users,
        "New Users": new_users,
        "Bounce Rate": bounce_rate,
        "Pages / Session": pages,
        "Avg. Session Duration": duration,
        "Conversions": conversions,
        "Conversion Rate": (cvr * 100).round(2),
        "Source / Medium": sources,
        "Country": countries,
    })
    df.to_csv(f"sample_data/{name}.csv", index=False)
    print(f"Created: sample_data/{name}.csv ({n} rows)")

make_csv("ecommerce_site_2023",    "2023-01-01", "2023-12-31", 3000, 42)
make_csv("saas_product_2022_2023", "2022-01-01", "2023-12-31", 1500, 77)
make_csv("blog_site_2024",         "2024-01-01", "2024-12-31", 800,  13)
make_csv("startup_2022_2024",      "2022-06-01", "2024-12-31", 500,  99)
make_csv("the_startup_2022_2023",      "2022-06-01", "2024-12-31", 400,  99)

print("Done. Upload any CSV from sample_data/ folder.")