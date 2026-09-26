# Pattern grading between sizes

Adds a new PDF layer ("Graded 20-22-24") to the Cashmerette Marston Raincoat A0 pattern
with a cutting line blended between sizes. The original artwork and size layers are left untouched.

- Bust 20 → waist 22 → hip 24, E/F cup, full bicep.
- Upper pieces: size 20 above the side dart, smooth blend to 22 at the waist seam.
- Lower pieces: 22 at the waist seam, smooth blend to 24 at the hip notch (~7.7" below waist), 24 below.
- Markings on lower pieces (pockets) come from size 24.

Run: `PATTERN_PDF=path/to/pattern.pdf GRADED_PDF=out.pdf python3 build.py` (needs pymupdf, numpy, matplotlib).
Pieces and blend settings are in `pieces.py`. The pattern PDF itself is not committed.
