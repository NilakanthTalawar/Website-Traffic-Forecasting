import pandas as pd
import numpy as np

def run_forecast(df, periods=90):
    ts = df[["Date", "Sessions"]].copy()
    ts.columns = ["ds", "y"]
    ts["ds"] = pd.to_datetime(ts["ds"])
    ts = ts.dropna().sort_values("ds").reset_index(drop=True)

    y = ts["y"].values.astype(float)
    n = len(y)
    x = np.arange(n)

    # Trend via linear regression
    coeffs = np.polyfit(x, y, 2)
    trend = np.polyval(coeffs, x)

    # Weekly seasonality
    residual = y - trend
    weekly = np.array([residual[i::7].mean() for i in range(7)])
    seasonal = np.array([weekly[i % 7] for i in range(n)])

    fitted = trend + seasonal
    std = np.std(y - fitted)

    # Future
    x_future = np.arange(n, n + periods)
    trend_future = np.polyval(coeffs, x_future)
    seasonal_future = np.array([weekly[i % 7] for i in range(periods)])
    yhat_future = trend_future + seasonal_future

    future_dates = [ts["ds"].iloc[-1] + pd.Timedelta(days=i+1) for i in range(periods)]

    all_ds = list(ts["ds"]) + future_dates
    all_yhat = list(fitted) + list(yhat_future)
    upper = [v + 1.5 * std for v in all_yhat]
    lower = [v - 1.5 * std for v in all_yhat]

    forecast = pd.DataFrame({
        "ds": all_ds,
        "yhat": all_yhat,
        "yhat_upper": upper,
        "yhat_lower": lower,
        "trend": list(trend) + list(trend_future),
        "weekly": [weekly[i % 7] for i in range(n + periods)]
    })
    return forecast, coeffs