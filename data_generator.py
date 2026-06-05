import pandas as pd
import numpy as np
import os

COUNTRIES = {
    "United States": 0.32, "India": 0.18, "United Kingdom": 0.09,
    "Germany": 0.07, "Canada": 0.06, "Australia": 0.05,
    "France": 0.04, "Brazil": 0.04, "Japan": 0.03, "Others": 0.12
}

SOURCES = {
    "google / organic": 0.35, "direct / none": 0.20,
    "facebook / social": 0.12, "email / newsletter": 0.10,
    "google / cpc": 0.09, "twitter / social": 0.06,
    "referral / referral": 0.05, "youtube / social": 0.03
}

HOURS = [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23]
HOUR_WEIGHTS = [0.5,0.3,0.2,0.2,0.3,0.8,1.5,2.5,3.5,4.0,4.5,4.2,
                3.8,4.3,4.5,4.0,3.8,3.5,3.2,2.8,2.5,2.0,1.5,1.0]


def generate_traffic_data():
    np.random.seed(42)
    dates = pd.date_range(start="2022-01-01", end="2024-12-31", freq="D")
    n = len(dates)

    # Sessions with trend + weekly + monthly seasonality
    trend = np.linspace(800, 6000, n)
    weekly = 600 * np.sin(2 * np.pi * np.arange(n) / 7)
    monthly = 400 * np.sin(2 * np.pi * np.arange(n) / 30)
    noise = np.random.normal(0, 250, n)
    sessions = (trend + weekly + monthly + noise).clip(100).astype(int)

    users = (sessions * np.random.uniform(0.72, 0.88, n)).astype(int)
    new_users = (users * np.random.uniform(0.45, 0.65, n)).astype(int)
    bounce_rate = np.clip(np.random.normal(42, 8, n), 20, 75).round(1)
    pages_per_session = np.clip(np.random.normal(3.2, 0.6, n), 1.5, 6.0).round(2)
    avg_session_duration = np.clip(np.random.normal(185, 40, n), 60, 420).astype(int)

    # Conversions — realistic funnel (2-5% conversion rate)
    conversion_rate = np.clip(
        0.03 + 0.015 * np.sin(2 * np.pi * np.arange(n) / 90) + np.random.normal(0, 0.008, n),
        0.01, 0.08
    )
    conversions = (sessions * conversion_rate).astype(int)

    # Source split
    source_names = list(SOURCES.keys())
    source_weights = list(SOURCES.values())
    source_split = np.random.dirichlet(np.array(source_weights) * 10, size=n)

    # Country split
    country_names = list(COUNTRIES.keys())
    country_weights = list(COUNTRIES.values())

    rows = []
    for i, date in enumerate(dates):
        # Top country for the day
        country = np.random.choice(country_names, p=country_weights)
        source = source_names[np.argmax(source_split[i])]
        rows.append({
            "Date": date.strftime("%Y%m%d"),
            "Sessions": sessions[i],
            "Users": users[i],
            "New Users": new_users[i],
            "Bounce Rate": bounce_rate[i],
            "Pages / Session": pages_per_session[i],
            "Avg. Session Duration": avg_session_duration[i],
            "Conversions": conversions[i],
            "Conversion Rate": round(conversion_rate[i] * 100, 2),
            "Source / Medium": source,
            "Country": country,
        })

    df = pd.DataFrame(rows)
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/traffic.csv", index=False)
    return df


def generate_hourly_data(df):
    """Generate hourly breakdown for heatmap."""
    np.random.seed(99)
    hw = np.array(HOUR_WEIGHTS)
    hw = hw / hw.sum()

    records = []
    # Sample last 90 days for speed
    df_sample = df.tail(90).copy()
    df_sample["Date"] = pd.to_datetime(df_sample["Date"], format="%Y%m%d")

    for _, row in df_sample.iterrows():
        daily_sessions = row["Sessions"]
        hour_sessions = np.random.multinomial(daily_sessions, hw)
        for h, s in enumerate(hour_sessions):
            records.append({
                "date": row["Date"],
                "hour": h,
                "day_of_week": row["Date"].day_name()[:3],
                "sessions": s
            })

    return pd.DataFrame(records)


def generate_country_data(df):
    """Aggregate sessions by country."""
    np.random.seed(77)
    country_names = list(COUNTRIES.keys())
    country_weights = np.array(list(COUNTRIES.values()))
    country_weights = country_weights / country_weights.sum()

    total = df["Sessions"].sum()
    country_sessions = (country_weights * total).astype(int)
    country_conversions = (country_sessions * np.random.uniform(0.02, 0.06, len(country_names))).astype(int)

    return pd.DataFrame({
        "Country": country_names,
        "Sessions": country_sessions,
        "Conversions": country_conversions,
        "Conversion Rate": (country_conversions / country_sessions * 100).round(2)
    })


def parse_ga4_upload(uploaded_file):
    """Parse uploaded GA4 CSV."""
    df = pd.read_csv(uploaded_file)
    df.columns = df.columns.str.strip()

    # Normalize date column
    date_col = next((c for c in df.columns if "date" in c.lower()), None)
    if date_col:
        df.rename(columns={date_col: "Date"}, inplace=True)

    # Ensure required columns exist
    required = ["Sessions", "Users", "Conversions"]
    for col in required:
        if col not in df.columns:
            df[col] = 0

    if "Conversion Rate" not in df.columns and "Sessions" in df.columns:
        df["Conversion Rate"] = (df["Conversions"] / df["Sessions"].replace(0, 1) * 100).round(2)

    return df