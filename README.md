# NX Drawing Generator

Command-line tools for Siemens NX that run headless — no NX window:

- **`generate_drawing.cmd`** — makes an ASME-compliant engineering drawing
  from a part file: views, dimensions, GD&T, title block. Outputs a native
  NX drawing (`.prt`) and a PDF.
- **`params.cmd`** — see and change a model's parameters (NX expressions)
  from outside NX.

## Setup

Needs a local Siemens NX / Designcenter install with a Drafting license.
The scripts find NX automatically; if that fails, set `NX_DIR` to your
install folder (the one containing `NXBIN`).

## Make a drawing

```
generate_drawing.cmd path\to\model.prt
```

Written next to the model:

| File | What it is |
|---|---|
| `<model>_dwg.prt` | native NX master-model drawing |
| `<model>_dwg.pdf` | the drawing as PDF |
| `<model>_dwg_report.txt` | every planned dimension and GD&T item — placed or skipped, with reasons |

## Work with parameters

```
params.cmd model.prt                     lists parameters -> <model>_params.json
params.cmd model.prt "p5=180" "p8=p5/2"  changes values or formulas, rebuilds, saves
params.cmd model.prt "p0->side_length"   renames a parameter (quotes required)
params.cmd model.prt changes.json        bulk-applies formulas from an edited JSON
```

The JSON lists each parameter's name, formula, value, units, and what it
depends on. Bulk workflow: list once, edit the JSON with anything (editor,
script, optimizer), pass it back — only changed formulas are applied, then
the model rebuilds once. Formulas stay live: `p8=p5/2` updates whenever
`p5` changes. Chain `generate_drawing.cmd` after it to get a drawing of
each variant.

## Notes

- Works for axis-aligned prismatic parts with holes; anything it can't
  dimension is listed in the report rather than silently skipped.
- The generator's docstring maps every rule to its ASME standard
  (Y14.1, Y14.2, Y14.3, Y14.5).
- Default tolerances (position 0.25, flatness 0.1, general ±0.5) are
  placeholders — edit the `GDT` dict in `nx_drawing_generator.py`.
