"""
Big Data + AI 
in this file :
1) Pull sensor readings from firestore and plant thresholds (min_soil)
2) Analyze:
   - % of readings below threshold
   - before vs after first critical event (reaction proxy)
3) Use Hugging Face model (AI in the cloud ecosystem) to classify threshold state from text
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from collections import Counter
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
import matplotlib.pyplot as plt

#imports from the Project 
import data_manager
from config import get_db

# Hugging Face 
from transformers import pipeline



# -----------------------------
#prepare data 
# -----------------------------


#normalize firestore timestamps into datetime objects
def to_datetime(ts: Any) -> Optional[datetime]:
    if ts is None:
        return None
    
    #check if ts is already an instance of the class datetime:
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)

    #check if ts is a string
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            return None
    return None


#this function reads all plants from the firestore -across all users- and builds a dictionary.
#the dict maps: plant_id -> minimum soil threshold
#function goal : to "shape and normalize" the data.
def fetch_thresholds_min_soil() -> Dict[str, float]:
    db = get_db()
    out: Dict[str, float] = {} 

    # collection_group pulls all "plants" subcollections across users
    for doc in db.collection_group("plants").stream():
        d = doc.to_dict() or {}
        plant_id = str(d.get("plant_id") or doc.id).strip()
        min_soil = d.get("min_soil", None)

        #to validate the data before adding : plant_id and min_soil exist
        if plant_id and min_soil is not None:
            try:
                out[plant_id] = float(min_soil)
            except Exception:
                pass

    return out


#go over !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
#this function fetches IoT sensor rows from the firestore and 
def fetch_sensor_rows(limit: int = 800) -> List[Dict[str, Any]]:
    return data_manager.get_all_readings(limit=limit)


#function to join sensor readings with plant soil thresholds into one data frame:
#plant_id, timestamp, soil, min_soil, is_below
def make_dataframe(sensor_rows: List[Dict[str, Any]], thresholds: Dict[str, float]) -> pd.DataFrame:

    rows = []

    for r in sensor_rows:
        plant_id = str(r.get("plant_id", "")).strip()
        soil = r.get("soil", None)
        ts = to_datetime(r.get("timestamp"))

        if not plant_id or ts is None or soil is None:
            continue
        if plant_id not in thresholds:
            continue

        try:
            soil_val = float(soil)
        except Exception:
            continue

        min_soil = float(thresholds[plant_id])
        rows.append({
            "plant_id": plant_id,
            "timestamp": ts,
            "soil": soil_val,
            "min_soil": min_soil,
            "is_below": soil_val < min_soil
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["plant_id", "timestamp"]).reset_index(drop=True)
    return df


# -----------------------------
#Build Pipeline (Big Data + AI)
# -----------------------------

#function to calculate the % of sensor readings where soil moisture is below the minimum threshold
def analysis_percent_below(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    return 100.0 * float(df["is_below"].mean())



#graph 1:
#function to create and save a bar chart that shows the % of soil readings below vs. above the AI soil threshold
def plot_percent_below(df: pd.DataFrame, out_png: str = "percent_below.png") -> None:
  
    pct_below = analysis_percent_below(df)
    pct_above = 100.0 - pct_below

    plt.figure()
    plt.bar(["Below min_soil", "Above/Equal min_soil"], [pct_below, pct_above])
    plt.ylabel("Percent (%)")
    plt.title("Soil Readings vs AI Threshold (min_soil)")
    plt.ylim(0, 100)
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    plt.close()

    print(f"[OK] Saved: {out_png} | Below={pct_below:.1f}% Above/Equal={pct_above:.1f}%")



#prepare for graph 2:
#function to estiamte whether users react after a plant becomes critical
#how: by checking if soil moisture imporves within  few hours after the first critical event.
def compute_reaction_proxy(df: pd.DataFrame,window_hours: int = 6,min_improve: float = 3.0) -> Tuple[float, float, int]:

    if df.empty:
        return 0.0, 0.0, 0

    w = timedelta(hours=window_hours)
    before_vals = []
    after_vals = []
    reacted = 0

    for plant_id, g in df.groupby("plant_id", sort=False):
        #find first critical reading (soil < min_soil)
        g = g.sort_values("timestamp")
        crit = g[g["is_below"] == True]
        if crit.empty:
            continue
        
        t0 = crit.iloc[0]["timestamp"]

        before = g[(g["timestamp"] >= t0 - w) & (g["timestamp"] < t0)]
        after = g[(g["timestamp"] > t0) & (g["timestamp"] <= t0 + w)]

        if before.empty or after.empty:
            continue

        #average soil BEFORE and average soil AFTER 
        avg_before = float(before["soil"].mean())
        avg_after = float(after["soil"].mean())

        before_vals.append(avg_before)
        after_vals.append(avg_after)

        #if AFTER - BEFORE >= min_improve => "reacted"
        if (avg_after - avg_before) >= min_improve:
            reacted += 1

    if not before_vals:
        return 0.0, 0.0, 0

    #Returns: avg_before_all, avg_after_all, reacted_count
    return float(sum(before_vals) / len(before_vals)), float(sum(after_vals) / len(after_vals)), reacted


#graph 2: average soil BEFORE vs AFTER critical event
def plot_before_after(avg_before: float, avg_after: float, out_png: str = "before_after.png") -> None:

    plt.figure()
    plt.bar(["Avg BEFORE critical", "Avg AFTER critical"], [avg_before, avg_after])
    plt.ylabel("Soil Moisture")
    plt.title("Reaction Proxy: Soil Change Around First Critical Event")
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    plt.close()

    print(f"[OK] Saved: {out_png} | BEFORE={avg_before:.2f} AFTER={avg_after:.2f}")


#Hugging Face
#using hugging face zero-shot classifier to predict whether each soil reading is below or above the threshold
#then compare the prediction to the real numeric result
#return the accuracy score
def huggingface_zero_shot_check(df: pd.DataFrame, sample_n: int = 80) -> float:

    if df.empty:
        return 0.0

    df_s = df.sample(n=min(sample_n, len(df)), random_state=42).copy()

    clf = pipeline("zero-shot-classification", model="typeform/distilbert-base-uncased-mnli")
    labels = ["below threshold", "above or equal threshold"]

    correct = 0
    total = 0

    for _, row in df_s.iterrows():
        text = f"Soil moisture is {row['soil']:.1f} percent. Minimum threshold is {row['min_soil']:.1f} percent."
        pred = clf(text, candidate_labels=labels)
        predicted = pred["labels"][0]

        truth = "below threshold" if bool(row["is_below"]) else "above or equal threshold"
        correct += int(predicted == truth)
        total += 1

    acc = correct / total if total else 0.0
    print(f"[HF] Zero-shot accuracy on sample={total}: {acc:.2%}")
    return acc



#testing
def main():
    print("=== Step 3: Preparing data from Firestore ===")
    thresholds = fetch_thresholds_min_soil()
    sensors = fetch_sensor_rows(limit=800)

    print(f"Thresholds loaded: {len(thresholds)} plants")
    print(f"Sensor rows loaded: {len(sensors)}")

    df = make_dataframe(sensors, thresholds)
    print(f"Joined usable rows: {len(df)}")

    if df.empty:
        print("\n[ERROR] No usable rows. Check:")
        print("- You have sensors docs with plant_id + soil + timestamp")
        print("- You have plants docs with min_soil")
        print("- Firebase credentials are configured locally")
        return

    print("\nBig Data analytics outputs")
    plot_percent_below(df, out_png="percent_below.png")

    avg_before, avg_after, reacted = compute_reaction_proxy(df, window_hours=6, min_improve=3.0)
    plot_before_after(avg_before, avg_after, out_png="before_after.png")

    # Reaction rate: reacted plants / plants with valid before+after windows
    # We compute it by counting how many plants had before/after at all:
    valid_plants = 0
    for plant_id, g in df.groupby("plant_id", sort=False):
        g = g.sort_values("timestamp")
        crit = g[g["is_below"] == True]
        if crit.empty:
            continue
        t0 = crit.iloc[0]["timestamp"]
        w = timedelta(hours=6)
        before = g[(g["timestamp"] >= t0 - w) & (g["timestamp"] < t0)]
        after = g[(g["timestamp"] > t0) & (g["timestamp"] <= t0 + w)]
        if not before.empty and not after.empty:
            valid_plants += 1

    reaction_rate = (100.0 * reacted / valid_plants) if valid_plants else 0.0
    print(f"[Analytics] Reaction rate (>=3 soil points within 6h): {reaction_rate:.1f}% (n={valid_plants})")

    print("Test AI model usage (Hugging Face)")
    hf_acc = huggingface_zero_shot_check(df, sample_n=80)

    pct_below = analysis_percent_below(df)

    print("\n--- KPIs (copy-paste to Word) ---")
    print(f"1) Risk Rate: {pct_below:.1f}% of soil readings are below the AI min_soil threshold.")
    print(f"2) Reaction Proxy: {reaction_rate:.1f}% of plants show soil improvement (>=3 points) within 6 hours after first critical event.")
    print(f"3) HF Model Check: Zero-shot classifier achieved {hf_acc:.2%} accuracy on below-vs-above classification (sample).")


if __name__ == "__main__":
    main()
