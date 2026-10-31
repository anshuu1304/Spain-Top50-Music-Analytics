"""Synthetic fixtures for edge-case testing ONLY. Never mixed into the real dataset."""
import pandas as pd


def make_clean(days):
    """days: list of (date_str, complete: bool, slots: {pos: (song_key, popularity)}).

    song_key format: "title || artist" (already normalised, lower case).
    Returns a DataFrame with the columns the lifecycle/churn code expects.
    """
    rows = []
    for ds, complete, slots in days:
        d = pd.Timestamp(ds)
        for pos, (key, pop) in slots.items():
            title, artist = key.split(" || ")
            rows.append({
                "date": d, "position": pos, "song": title.upper(), "artist": artist,
                "song_key": key, "popularity": pop, "popularity_valid": float(pop) if pop else None,
                "snapshot_complete": complete,
            })
    return pd.DataFrame(rows)


def full_day(named):
    """Complete 50-slot snapshot. Unnamed slots get a stable filler keyed by position."""
    slots = {}
    for p in range(1, 51):
        slots[p] = named.get(p, (f"fill{p} || filler", 50))
    return slots


def slot_day(keys_by_slot):
    """Complete 50-slot snapshot keyed by slot index 1..50 -> song_key (popularity fixed at 60)."""
    return {p: (k, 60) for p, k in keys_by_slot.items()}
