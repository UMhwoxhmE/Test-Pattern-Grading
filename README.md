# Pattern grading between sizes

Adds a new PDF layer ("Graded 20-22-24") to the Cashmerette Marston Raincoat A0 pattern
with a cutting line blended between sizes. The original artwork and size layers are left untouched.

- Bust 20 → waist 22 → hip 24, E/F cup, full bicep.
- Upper pieces: size 20 above the side dart, smooth blend to 22 at the waist seam.
- Lower pieces: 22 at the waist seam, smooth blend to 24 at the hip notch (~7.7" below waist), 24 below.
- Markings on lower pieces (pockets) come from size 24.
- Bust size 20 only: sleeve + sleeve lining (full bicep), cuff, hood pieces, brim, neckline facings,
  zipper flap, zipper facing (cut at the E/F cup line).
- Hip size 24: pocket, pocket flap, hem facings.
- Fold, placement and trim lines and grainlines from the Labels layer are copied onto the graded layer,
  so it can be printed on its own. Pocket gets notches at both ends of its fold line.

Run: `PATTERN_PDF=path/to/pattern.pdf GRADED_PDF=out.pdf python3 build.py` (needs pymupdf, numpy, matplotlib).
Pieces and blend settings are in `pieces.py`. The pattern PDF itself is not committed.

## SVG export for nesting

`PATTERN_PDF=... SVG_OUT=name python3 grading/svg_export.py` writes `name.svg` and `name_with_markings.svg` (mm units):

- Layer "Pieces": one closed path per piece, `inkscape:label` = "<num> <Name> <cut codes>",
  e.g. `1 Upper Front C2M`, `2 Upper Back C1MOF`, `16 Hood Facing C2M C2I`
  (M main, L lining, I interfacing, R ribbing, OF on fold). Numbers drop the cup/bicep letter (1B -> 1).
- Layer "Grainlines": one path per piece, id and label `grain-<num>`. For cut-on-fold pieces it lies on the fold edge.
- `_with_markings` adds a "Markings" layer (groups `marks-<num>`: darts, dots, placement/fold/trim/lengthen lines).
- Pieces keep their positions from the pattern pages, which are laid side by side.
