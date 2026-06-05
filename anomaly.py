import pandas as pd
from sklearn.ensemble import IsolationForest

def detect_anomalies(df):
    model = IsolationForest(contamination=0.05, random_state=42)
    df = df.copy()
    df["anomaly"] = model.fit_predict(df[["sessions"]])
    df["is_anomaly"] = df["anomaly"] == -1
    return df