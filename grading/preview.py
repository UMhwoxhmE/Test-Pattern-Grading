import pymupdf as fitz, sys
def show(src, names, fn, page, clip=None, dpi=30):
    d=fitz.open(src)
    for c in d.layer_ui_configs():
        d.set_layer_ui_config(c['number'], 0 if c['text'] in names else 2)
    d[page].get_pixmap(dpi=dpi, clip=fitz.Rect(*clip) if clip else None).save(fn)
