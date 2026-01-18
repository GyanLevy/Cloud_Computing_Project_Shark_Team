from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import matplotlib.pyplot as plt

#project imports
import data_manager
from config import get_db


# -------------------------
# Utilities
# -------------------------

#Convert Firestore timestamp / iso string into timezone-aware datetime.
def to_dt(x: Any) -> Optional[datetime]:
    if x is None:
        return None
    if isinstance(x, datetime):
        return x if x.tzinfo else x.replace(tzinfo=timezone.utc)
    if isinstance(x, str):
        try:
            return datetime.fromisoformat(x.replace("Z", "+00:00"))
        except Exception:
            return None
    return None

#Reads from Firestore collection_group('plants').
def load_thresholds_min_soil() -> Dict[str, float]:

    db = get_db()
    out: Dict[str, float] = {}

    for doc in db.collection_group("plants").stream():
        d = doc.to_dict() or {}
        plant_id = str(d.get("plant_id") or doc.id).strip()
        min_soil = d.get("min_soil", None)
        if not plant_id or min_soil is None:
            continue
        try:
            out[plant_id] = float(min_soil)
        except Exception:
            continue

    return out


def load_sensor_rows(limit: int = 800) -> List[Dict[str, Any]]:
    return data_manager.get_all_readings(limit=limit)


def build_df(sensor_rows: List[Dict[str, Any]], thresholds: Dict[str, float]) -> pd.DataFrame:
    """
    Build DataFrame with:
      plant_id, timestamp, soil, min_soil, is_below
    """
    rows = []
    for r in sensor_rows:
        plant_id = str(r.get("plant_id", "")).strip()
        soil = r.get("soil", None)
        ts = to_dt(r.get("timestamp", None))

        if not plant_id or soil is None or ts is None:
            continue
        if plant_id not in thresholds:
            continue

        try:
            soil_val = float(soil)
            min_soil = float(thresholds[plant_id])
        except Exception:
            continue

        rows.append({
            "plant_id": plant_id,
            "timestamp": ts,
            "soil": soil_val,
            "min_soil": min_soil,
            "is_below": soil_val < min_soil,
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values(["plant_id", "timestamp"]).reset_index(drop=True)
    return df


# -------------------------
# Analytics + Graphs
# -------------------------

def percent_below(df: pd.DataFrame) -> float:
    if df.empty:
        return 0.0
    return 100.0 * float(df["is_below"].mean())


def save_graph_percent_below(df: pd.DataFrame, out_png: str = "percent_below.png") -> None:
    below = percent_below(df)
    above = 100.0 - below

    plt.figure()
    plt.bar(["Below min_soil", "Above/Equal min_soil"], [below, above])
    plt.ylabel("Percent (%)")
    plt.ylim(0, 100)
    plt.title("Soil Readings vs AI Threshold (min_soil)")
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    plt.close()


def reaction_before_after(
    df: pd.DataFrame,
    window_hours: int = 6,
    min_improve: float = 3.0,
) -> Tuple[float, float, float, int]:
    """
    Finds first critical event per plant (soil < min_soil).
    Compares avg soil BEFORE vs AFTER in a time window.
    Returns:
      avg_before_all, avg_after_all, reaction_rate_percent, valid_plants_count
    """
    if df.empty:
        return 0.0, 0.0, 0.0, 0

    w = timedelta(hours=window_hours)
    before_vals: List[float] = []
    after_vals: List[float] = []
    reacted = 0

    for plant_id, g in df.groupby("plant_id", sort=False):
        g = g.sort_values("timestamp")
        crit = g[g["is_below"] == True]
        if crit.empty:
            continue

        t0 = crit.iloc[0]["timestamp"]
        before = g[(g["timestamp"] >= t0 - w) & (g["timestamp"] < t0)]
        after = g[(g["timestamp"] > t0) & (g["timestamp"] <= t0 + w)]

        if before.empty or after.empty:
            continue

        avg_b = float(before["soil"].mean())
        avg_a = float(after["soil"].mean())
        before_vals.append(avg_b)
        after_vals.append(avg_a)

        if (avg_a - avg_b) >= min_improve:
            reacted += 1

    valid = len(before_vals)
    if valid == 0:
        return 0.0, 0.0, 0.0, 0

    avg_before = float(sum(before_vals) / valid)
    avg_after = float(sum(after_vals) / valid)
    reaction_rate = 100.0 * reacted / valid
    return avg_before, avg_after, reaction_rate, valid


def save_graph_before_after(avg_before: float, avg_after: float, out_png: str = "before_after.png") -> None:
    plt.figure()
    plt.bar(["Avg BEFORE critical", "Avg AFTER critical"], [avg_before, avg_after])
    plt.ylabel("Soil Moisture")
    plt.title("Reaction Proxy: Soil Change Around First Critical Event")
    plt.tight_layout()
    plt.savefig(out_png, dpi=200)
    plt.close()


def main():
    thresholds = load_thresholds_min_soil()
    sensors = load_sensor_rows(limit=800)
    df = build_df(sensors, thresholds)

    print(f"thresholds loaded: {len(thresholds)}")
    print(f"sensor rows loaded: {len(sensors)}")
    print(f"joined usable rows: {len(df)}")

    if df.empty:
        print("No usable data. Check Firestore schema / field names / credentials.")
        return

    # Graph 1 
    below_pct = percent_below(df)
    save_graph_percent_below(df, out_png="percent_below.png")

    # Graph 2 
    avg_b, avg_a, react_rate, valid = reaction_before_after(df, window_hours=6, min_improve=3.0)
    save_graph_before_after(avg_b, avg_a, out_png="before_after.png")

if __name__ == "__main__":
    main()
