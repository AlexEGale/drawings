# NX Drawing Generator

Generates an ASME-compliant engineering drawing from an NX part file —
views, dimensions, GD&T, title block — as a native NX drawing (`.prt`)
plus a PDF. Runs headless (no NX window).

## Requirements

- Siemens NX / Designcenter installed locally with a Drafting license
  (path is set in `generate_drawing.cmd`)

## Usage

```
generate_drawing.cmd path\to\your_model.prt
```

Outputs, written next to the model:

| File | What it is |
|---|---|
| `<model>_dwg.prt` | native NX master-model drawing |
| `<model>_dwg.pdf` | the drawing as PDF |
| `<model>_dwg_report.txt` | coverage report: every planned dimension/GD&T item, placed or skipped (with reason) |

## Files

- `nx_drawing_generator.py` — the generator (docstring maps every rule to
  its ASME standard: Y14.1, Y14.2, Y14.3, Y14.5)
- `generate_drawing.cmd` — wrapper that launches it inside NX

## Notes

- Works for axis-aligned prismatic parts with holes; features it can't
  dimension yet are listed honestly in the report.
- Default tolerance values (position 0.25, flatness 0.1, general ±0.5)
  are placeholders — edit the `GDT` dict in the script to match design intent.
