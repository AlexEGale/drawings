r"""
NX parameter bridge — read and write model expressions from outside NX.

Every NX feature parameter is an expression (p0, p1, ...), and expressions
may be formulas of other expressions (p3 = p1 + p0). This journal exposes
that parameterization as JSON so external code can inspect and drive it.

Runs inside NX via run_journal.exe (see params.cmd). Modes via env vars:

  NXPARAM_MODEL   path to the .prt
  NXPARAM_ACTION  "list" (default) or "set"
  NXPARAM_SET     for set: "name=value;name=formula;..."
                  e.g. "p5=180;p8=p5/2"
  NXPARAM_JSON    for set: path to a JSON file in the same format as the
                  dump — every entry whose "formula" differs from the model
                  is applied (bulk round-trip: dump, edit, apply)

Both modes write <model>_params.json:
  [{"name": "p5", "formula": "160", "value": 160.0, "units": "mm",
    "comment": "", "depends_on": []}, ...]

"set" edits the right-hand sides, rebuilds the model (feature update), and
saves — dependent expressions and geometry follow automatically.
"""

import json
import os
import re
import traceback

import NXOpen

MODEL = os.environ.get("NXPARAM_MODEL", "")
if not MODEL:
    raise RuntimeError("Set NXPARAM_MODEL to the part file path "
                       "(or run via params.cmd)")
ACTION = os.environ.get("NXPARAM_ACTION", "list")
SETS = os.environ.get("NXPARAM_SET", "")
OUT = os.path.splitext(MODEL)[0] + "_params.json"

s = NXOpen.Session.GetSession()
lw = s.ListingWindow
lw.Open()
say = lw.WriteLine


def unit_of(e):
    try:
        u = e.Units
        if u is None:
            return ""
        for attr in ("Abbreviation", "Symbol", "Name"):
            v = getattr(u, attr, None)
            if v:
                return v
    except Exception:
        pass
    return ""


def snapshot(wp):
    """All expressions as plain dicts, dependency-annotated."""
    exprs = list(wp.Expressions)
    names = set()
    for e in exprs:
        try:
            names.add(e.Name)
        except Exception:
            pass
    out = []
    for e in exprs:
        try:
            name = e.Name
        except Exception:
            continue
        d = {"name": name}
        try:
            d["formula"] = e.RightHandSide
        except Exception:
            d["formula"] = ""
        try:
            d["value"] = e.Value
        except Exception:
            try:
                d["value"] = e.StringValue
            except Exception:
                d["value"] = None
        try:
            d["type"] = str(e.Type)
        except Exception:
            d["type"] = ""
        try:
            d["comment"] = e.Description
        except Exception:
            d["comment"] = ""
        d["units"] = unit_of(e)
        refs = set(re.findall(r"[A-Za-z_]\w*", d["formula"] or ""))
        d["depends_on"] = sorted((refs & names) - {name})
        out.append(d)

    def key(d):
        m = re.match(r"^p(\d+)$", d["name"])
        return (0, int(m.group(1))) if m else (1, d["name"])
    out.sort(key=key)
    return out


def apply_sets(wp, sets):
    changed = []
    by_name = {}
    for e in wp.Expressions:
        try:
            by_name[e.Name] = e
        except Exception:
            pass
    for item in [t for t in sets.split(";") if t.strip()]:
        if "->" in item:
            # rename: old->new  (formulas referencing it update automatically)
            old, _, new = item.partition("->")
            old, new = old.strip(), new.strip()
            e = by_name.get(old)
            if e is None:
                say("FAIL %s: no such expression" % old)
            else:
                try:
                    wp.Expressions.Rename(e, new)
                    by_name[new] = e
                    changed.append(new)
                    say("RENAME %s -> %s" % (old, new))
                except Exception:
                    say("FAIL rename %s -> %s:\n  %s"
                        % (old, new, traceback.format_exc().splitlines()[-1]))
            continue
        name, _, rhs = item.partition("=")
        name, rhs = name.strip(), rhs.strip()
        if not name or not rhs:
            say("SKIP malformed: %r" % item)
            continue
        e = by_name.get(name)
        if e is None:
            say("FAIL %s: no such expression" % name)
            continue
        try:
            done = False
            try:
                wp.Expressions.EditWithUnits(e, e.Units, rhs)
                done = True
            except Exception:
                pass
            if not done:
                e.RightHandSide = rhs
            changed.append(name)
            say("SET  %s = %s" % (name, rhs))
        except Exception:
            say("FAIL %s = %s:\n  %s"
                % (name, rhs, traceback.format_exc().splitlines()[-1]))
    if changed:
        mark = s.SetUndoMark(NXOpen.Session.MarkVisibility.Invisible, "param edit")
        s.UpdateManager.DoUpdate(mark)
        wp.Save(NXOpen.BasePart.SaveComponents.TrueValue,
                NXOpen.BasePart.CloseAfterSave.FalseValue)
        say("Model rebuilt and saved (%d change(s))" % len(changed))
    return changed


def json_to_sets(wp, path):
    """Entries whose formula differs from the model -> 'name=rhs;...'."""
    with open(path) as f:
        wanted = json.load(f)
    current = {d["name"]: d.get("formula") for d in snapshot(wp)}
    items = []
    for d in wanted:
        name = d.get("name")
        rhs = d.get("formula")
        if not name or rhs in (None, ""):
            continue
        if name in current and str(current[name]).strip() == str(rhs).strip():
            continue        # unchanged
        items.append("%s=%s" % (name, rhs))
    say("JSON: %d change(s) of %d entries" % (len(items), len(wanted)))
    return ";".join(items)


def main():
    part, _ = s.Parts.OpenDisplay(MODEL)
    wp = s.Parts.Work
    say("Model: " + wp.FullPath)

    if ACTION == "set":
        sets = SETS
        jpath = os.environ.get("NXPARAM_JSON", "")
        if jpath:
            sets = ";".join(t for t in (sets, json_to_sets(wp, jpath)) if t)
        apply_sets(wp, sets)

    snap = snapshot(wp)
    with open(OUT, "w") as f:
        json.dump(snap, f, indent=2)
    say("")
    say("%-10s %-24s %-12s %-6s %s" % ("NAME", "FORMULA", "VALUE", "UNITS", "DEPENDS ON"))
    for d in snap:
        say("%-10s %-24s %-12s %-6s %s"
            % (d["name"], str(d["formula"])[:24], d["value"], d["units"],
               ",".join(d["depends_on"])))
    say("")
    say("Wrote " + OUT)
    say("DONE-PARAMS")


if __name__ == "__main__":
    main()
