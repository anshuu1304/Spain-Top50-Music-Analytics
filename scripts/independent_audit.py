"""Independent audit of the headline numbers.

Deliberately does NOT import anything from src/ or dashboard/. It reads the raw CSV with
the csv module and recomputes the key figures from first principles, then compares them
with outputs/reports/results.json. Exit code 1 if any check fails.
"""
import csv, json, statistics, sys, unicodedata, datetime as dt
from collections import Counter, defaultdict
from pathlib import Path
from scipy.stats import mannwhitneyu

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/Atlantic_Spain.csv"
RESULTS = ROOT / "outputs/reports/results.json"


def norm(s):
    s = unicodedata.normalize("NFC", s or "")
    return " ".join(s.split()).casefold()


with RAW.open(encoding="utf-8-sig", newline="") as fh:
    reader = csv.reader(fh)
    header = [h.replace("\\_", "_").strip() for h in next(reader)]
    rows = [dict(zip(header, r)) for r in reader]

print(f"rows read: {len(rows)}")
by_date = defaultdict(list)
for r in rows:
    d = dt.datetime.strptime(r["date"].strip(), "%d-%m-%Y").date()
    by_date[d].append(r)

dates = sorted(by_date)
complete = []
for d in dates:
    pos = [int(x["position"]) for x in by_date[d]]
    if len(pos) == 50 and sorted(pos) == list(range(1, 51)):
        complete.append(d)
partial = [d for d in dates if d not in complete]
print(f"dates: {len(dates)}, complete: {len(complete)}, partial: {[str(p) for p in partial]}")

def key(r):
    return (norm(r["song"]), norm(r["artist"]))

keys_on = {d: {key(r) for r in by_date[d]} for d in complete}
first_date = complete[0]
window_end = complete[-1]

# transitions between adjacent calendar days, both complete
entries_by_day, exits_by_day = {}, {}
for prev, cur in zip(complete, complete[1:]):
    if (cur - prev).days != 1:
        continue
    entries_by_day[cur] = keys_on[cur] - keys_on[prev]
    exits_by_day[cur] = keys_on[prev] - keys_on[cur]
transitions = len(entries_by_day)
total_entries = sum(len(v) for v in entries_by_day.values())
total_exits = sum(len(v) for v in exits_by_day.values())

# re-entries: an entry whose song was present on some earlier complete day
seen_before = defaultdict(set)
running = set()
reentries = 0
for d in complete:
    if d in entries_by_day:
        for k in entries_by_day[d]:
            if k in keys_on[d] and any(k in keys_on[e] for e in complete if e < d):
                reentries += 1
seen_any = set(keys_on[complete[0]])

# song-level facts
appear_complete = Counter()
for d in complete:
    for k in keys_on[d]:
        appear_complete[k] += 1
first_seen, last_seen = {}, {}
for d in complete:
    for k in keys_on[d]:
        first_seen.setdefault(k, d)
        last_seen[k] = d
left_censored = {k for k, d in first_seen.items() if d == first_date}
observed = {k for k in first_seen if k not in left_censored}
active_at_end = {k for k in first_seen if last_seen[k] == window_end}

# song attributes: modal value per song across all rows
attr_vals = defaultdict(lambda: {"exp": Counter(), "alb": Counter()})
for r in rows:
    k = key(r)
    attr_vals[k]["exp"][r["is_explicit"].strip().upper() == "TRUE"] += 1
    attr_vals[k]["alb"][r["album_type"].strip().lower()] += 1
is_explicit = {k: v["exp"].most_common(1)[0][0] for k, v in attr_vals.items()}
album_type = {k: v["alb"].most_common(1)[0][0] for k, v in attr_vals.items()}

# 14 Oct 2024 wave
wave_day = dt.date(2024, 10, 14)
wave_first = {k for k in entries_by_day.get(wave_day, set()) if first_seen[k] == wave_day}
bb_wave = {k for k in wave_first if "bad bunny" in k[1]}

zero_pop = sum(1 for r in rows if r["popularity"].strip() == "0")

def mw(a_keys, b_keys, values):
    a = [values[k] for k in a_keys]
    b = [values[k] for k in b_keys]
    if not a or not b:
        return None
    return mannwhitneyu(a, b, alternative="two-sided").pvalue, statistics.median(a), statistics.median(b)

mine = {
    "window.first_date": str(first_date),
    "window.window_end": str(window_end),
    "window.complete_dates": len(complete),
    "rotation.valid_transitions": transitions,
    "rotation.total_entries": total_entries,
    "rotation.total_exits": total_exits,
    "rotation.total_reentries": reentries,
    "rotation.mean_daily_turnover": total_entries / transitions,
    "rotation.mean_daily_entry_rate_pct": total_entries / transitions / 50 * 100,
    "zero_popularity_rows": zero_pop,
    "cohort_14oct_entries": len(entries_by_day.get(wave_day, set())),
    "cohort_14oct_first_appearances": len(wave_first),
    "cohort_14oct_bad_bunny": len(bb_wave),
    "songs_total": len(first_seen),
    "songs_left_censored": len(left_censored),
    "songs_active_at_window_end": len(active_at_end),
}

# Cumulative appearances = number of data rows (days) on which the song appears,
# including the partial 15 Oct 2024 day. Full-snapshot rules apply to rotation only.
apps = Counter(key(r) for r in rows)
alb_keys = {k for k in observed if album_type[k] == "album"}
sgl_keys = {k for k in observed if album_type[k] == "single"}
r_alb = mw(alb_keys, sgl_keys, apps)
mine["album_vs_single_appearances_MW_p"] = r_alb[0]
mine["album_vs_single_appearances_medians"] = [r_alb[1], r_alb[2]]
exp_keys = {k for k in observed if is_explicit[k]}
cln_keys = {k for k in observed if not is_explicit[k]}
r_exp = mw(exp_keys, cln_keys, apps)
mine["explicit_vs_clean_appearances_MW_p"] = r_exp[0]
mine["explicit_vs_clean_n"] = [len(exp_keys), len(cln_keys)]
mine["observed_entry_songs"] = len(observed)

# compare against the pipeline
pipe = json.loads(RESULTS.read_text())
checks = []
def cmp(name, a, b, tol=1e-6):
    ok = (a == b) if isinstance(a, str) or a is None or isinstance(b, (list, str)) else abs(float(a) - float(b)) <= tol * max(1, abs(float(b)))
    checks.append((name, a, b, ok))

cmp("window.first_date", mine["window.first_date"], pipe["window"]["first_date"])
cmp("window.window_end", mine["window.window_end"], pipe["window"]["window_end"])
cmp("window.complete_dates", mine["window.complete_dates"], pipe["window"]["complete_dates"])
cmp("rotation.valid_transitions", transitions, pipe["rotation"]["valid_transitions"])
cmp("rotation.total_entries", total_entries, pipe["rotation"]["total_entries"])
cmp("rotation.total_reentries", reentries, pipe["rotation"]["total_reentries"])
cmp("rotation.mean_daily_turnover", mine["rotation.mean_daily_turnover"], pipe["rotation"]["mean_daily_turnover"], 1e-9)
cmp("rotation.mean_daily_entry_rate_pct", mine["rotation.mean_daily_entry_rate_pct"], pipe["rotation"]["mean_daily_entry_rate_pct"], 1e-9)
cmp("rotation.total_exits == entries", total_exits, total_entries)
cmp("zero popularity rows (pipeline reports 61 in docs)", zero_pop, 61)
cmp("cohort 14 Oct entries", len(entries_by_day.get(wave_day, set())), 21)
cmp("cohort 14 Oct first appearances", len(wave_first), 20)
cmp("cohort 14 Oct Bad Bunny first appearances", len(bb_wave), 19)
pc = {c["comparison"]: c for c in pipe["comparisons"] if "comparison" in c}
ex = pc["is_explicit: True vs False"]["appearances_MW"]
al = pc["album_type: album vs single"]["appearances_MW"]
cmp("explicit n_a", len(exp_keys), ex["n_a"])
cmp("explicit n_b", len(cln_keys), ex["n_b"])
cmp("explicit median_a", statistics.median([apps[k] for k in exp_keys]), ex["median_a"])
cmp("explicit median_b", statistics.median([apps[k] for k in cln_keys]), ex["median_b"])
cmp("explicit MW p", r_exp[0], ex["p_value"], 1e-6)
cmp("album n_a", len(alb_keys), al["n_a"])
cmp("album n_b", len(sgl_keys), al["n_b"])
cmp("album median_a", r_alb[1], al["median_a"])
cmp("album median_b", r_alb[2], al["median_b"])
cmp("album MW p", r_alb[0], al["p_value"], 1e-6)

print("\nINDEPENDENT VALUES")
for k, v in mine.items():
    print(f"  {k}: {v}")

print("\nCHECKS AGAINST results.json")
fail = 0
for name, a, b, ok in checks:
    print(f"  [{'OK' if ok else 'FAIL'}] {name}: audit={a} pipeline={b}")
    fail += (not ok)
print(f"\n{len(checks) - fail}/{len(checks)} checks agree")
sys.exit(1 if fail else 0)
