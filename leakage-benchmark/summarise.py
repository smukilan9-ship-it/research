"""Assemble the paper's tables from the saved per-spec JSON.

Numbers in the manuscript should come from here, not from reading them off a
log, so that a rerun updates the text mechanically.
"""
import json, glob, os

HERE = os.path.dirname(os.path.abspath(__file__)) + "/"
ORDER = ["KOI", "DIABETES", "DIABETES_PURE", "LC", "COMPAS", "AI4I", "TITANIC"]

R = {}
for f in glob.glob(HERE + "res_*.json"):
    d = json.load(open(f))
    R[d["name"]] = d
rows = [R[n] for n in ORDER if n in R]
missing = [n for n in ORDER if n not in R]

print("TABLE 1 -- what the leak does to the headline number\n")
print(f"{'dataset':<14}{'domain':<18}{'n':>8}{'acc':>18}{'macro F1':>18}{'x':>6}")
for r in rows:
    a = f"{r['acc_clean']:.3f}->{r['acc_leak']:.3f}"
    m = f"{r['mf1_clean']:.3f}->{r['mf1_leak']:.3f}"
    x = abs(r["d_mf1"]) / max(abs(r["d_acc"]), 1e-9)
    print(f"{r['name']:<14}{r['domain']:<18}{r['n']:>8}{a:>18}{m:>18}{x:>5.1f}x")

print("\n\nTABLE 2 -- the boundary the leak is silent about\n")
print(f"{'dataset':<14}{'size-matched':>26}{'composition-matched':>28}{'McNemar':>12}")
for r in rows:
    if "common_p" not in r:
        continue
    s = f"{r['pair_delta_pts']:+.2f}pts p={r['pair_p']:.1e}"
    c = f"{r['common_delta_pts']:+.2f}pts p={r['common_p']:.1e}"
    m = f"{r['mcnemar_sig_partitions']}/10 sig"
    print(f"{r['name']:<14}{s:>26}{c:>28}{m:>12}")
print("\n  size-matched equalises the COUNT of objects scored on the boundary.")
print("  composition-matched scores both arms on the SAME objects.")
print("  McNemar is the object-level test; the t-test p-values above are")
print("  across CV partitions of identical rows and overstate significance.")

print("\n\nTABLE 3 -- detection\n")
print(f"{'dataset':<14}{'univariate':>22}{'subset scan (per-class z)':>30}{'macro':>9}{'maxcls':>9}")
for r in rows:
    u = f"rank {r['uni_best_rank']}/{r['uni_ncols']} {'CAUGHT' if r['uni_caught'] else 'MISSED'}"
    if r.get("scan") == "degenerate":
        s, mac, mx = "k=1, degenerate", "-", "-"
    else:
        s = (f"z={r['scan_z']:+.2f} on {r['scan_class']}"
             f" {'DET' if r['scan_detected'] else 'MISS'}")
        mac, mx = f"{r['scan_z_macro']:+.2f}", f"{r['scan_z_maxclass']:+.2f}"
    print(f"{r['name']:<14}{u:>22}{s:>30}{mac:>9}{mx:>9}")
print("\n  'macro' and 'maxcls' are the two statistics that DO NOT work, kept so")
print("  the failure mode is on record: macro buries a one-sided leak, maxcls")
print("  collapses to the majority-class F1 under imbalance.")

def f1_from_cm(cm, i):
    tp = cm[i][i]
    fn = sum(cm[i]) - tp
    fp = sum(row[i] for row in cm) - tp
    return 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else 0.0


print("\n\nTABLE 4 -- per-class F1, clean -> +leak\n")
print("  The leak lifts the class it marks and leaves the rest roughly alone.")
print("  That asymmetry is the whole phenomenon.\n")
for r in rows:
    src = "10-partition mean" if "perclass_clean" in r else "seed-0 confusion matrix"
    print(f"  {r['name']:<14} ({src})")
    for i, lab in enumerate(r["labels"]):
        if "perclass_clean" in r:
            a, b = r["perclass_clean"][i], r["perclass_leak"][i]
            sup = r["support"][i]
        else:
            a, b = f1_from_cm(r["cm_clean"], i), f1_from_cm(r["cm_leak"], i)
            sup = sum(r["cm_clean"][i])
        bar = "#" * int(round(max(b - a, 0) * 40))
        print(f"     {lab:<16} n={sup:>6}  {a:.3f} -> {b:.3f}  ({b-a:+.3f}) {bar}")
    print()
if missing:
    print(f"!! MISSING SPECS (still running or failed): {missing}")
