"""Three-way check: requirements.txt, the live interpreter, and NUMBERS.txt.

WHY THIS EXISTS

  requirements.txt says the environment NUMBERS.txt is defined against, and
  verify_paper.py prints the LIVE versions into section 10 on every run "so a
  mismatch is visible in the diff rather than silent".  Visible in a diff is
  not the same as caught: numpy and pandas drifted from 2.4.6/3.0.3 to
  2.5.2/3.0.5 and nothing failed, because nothing compared the two.

  So this compares all three:

    1. requirements.txt against the interpreter actually running   -- is the
       pin honest, i.e. would `pip install -r requirements.txt` reproduce this
    2. requirements.txt against the banner in NUMBERS.txt section 10 -- was
       the committed NUMBERS.txt produced by the pinned stack
    3. the python version, which the pin cannot express and the file states in
       prose

  A drift is not automatically wrong -- the 2026-08-21 one moved zero computed
  figures, and requirements.txt records how that was measured.  It is a thing
  that must be NOTICED and then either corrected or documented, which is what
  a checker is for.

    python3 verify_env.py
"""
import re
import sys

PY_REQUIRED = (3, 14)
FAIL = []


def installed():
    import importlib
    out = {}
    for mod, dist in (("numpy", "numpy"), ("pandas", "pandas"),
                      ("sklearn", "scikit-learn"), ("scipy", "scipy")):
        try:
            out[dist] = importlib.import_module(mod).__version__
        except Exception as e:                       # noqa: BLE001
            FAIL.append(f"{dist}: not importable ({e})")
    return out


def pinned():
    out = {}
    for line in open("requirements.txt"):
        line = line.split("#")[0].strip()
        m = re.match(r"^([A-Za-z0-9_.\-]+)==([0-9][0-9A-Za-z.\-]*)$", line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def banner():
    """The versions verify_paper.py stamped into NUMBERS.txt section 10."""
    try:
        txt = open("NUMBERS.txt").read()
    except FileNotFoundError:
        FAIL.append("NUMBERS.txt missing — cannot check what produced it")
        return {}
    m = re.search(r"^python ([\d.]+)\s+numpy ([\d.]+)\s+pandas ([\d.]+)\s+"
                  r"scikit-learn ([\d.]+)\s+scipy ([\d.]+)", txt, re.M)
    if not m:
        FAIL.append("NUMBERS.txt has no version banner in section 10 — "
                    "verify_paper.py should be printing one")
        return {}
    return dict(python=m.group(1), numpy=m.group(2), pandas=m.group(3),
                **{"scikit-learn": m.group(4), "scipy": m.group(5)})


def main():
    inst, pin, ban = installed(), pinned(), banner()

    print("=" * 74)
    print("ENVIRONMENT — requirements.txt vs the interpreter vs NUMBERS.txt")
    print("=" * 74)
    print(f'  {"package":<16}{"pinned":>12}{"installed":>12}{"NUMBERS.txt":>14}')
    for k in sorted(set(pin) | set(inst)):
        p, i, b = pin.get(k, "—"), inst.get(k, "—"), ban.get(k, "—")
        mark = "  ok" if (p == i == b or "—" in (p, i, b)) else "  MISMATCH"
        print(f"  {k:<16}{p:>12}{i:>12}{b:>14}{mark}")
        if p != "—" and i != "—" and p != i:
            FAIL.append(f"{k}: requirements.txt pins {p}, the running "
                        f"interpreter has {i} — the pin does not reproduce "
                        f"this environment")
        if p != "—" and b != "—" and p != b:
            FAIL.append(f"{k}: requirements.txt pins {p}, but NUMBERS.txt was "
                        f"produced under {b} — regenerate it or correct the pin")

    v = sys.version_info[:2]
    pyb = ban.get("python", "")
    print(f'\n  {"python":<16}{".".join(map(str, PY_REQUIRED)) + ".x":>12}'
          f'{".".join(map(str, v)):>12}{pyb:>14}')
    if v != PY_REQUIRED:
        FAIL.append(f"python {v[0]}.{v[1]} is running; requirements.txt states "
                    f"CPython {PY_REQUIRED[0]}.{PY_REQUIRED[1]} in prose — the "
                    f"interpreter is part of the pin and cannot be expressed "
                    f"in the file")
    if pyb and not pyb.startswith(".".join(map(str, PY_REQUIRED))):
        FAIL.append(f"NUMBERS.txt was produced under python {pyb}")

    print()
    for f in FAIL:
        print(f"  FAIL  {f}")
    if not FAIL:
        print("  The pin, the interpreter and the committed NUMBERS.txt agree.")
        print("  `pip install -r requirements.txt` reproduces the stack these")
        print("  numbers were computed on.")
    print(f"\n  {len(FAIL)} failure(s).")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
