"""Compose words from the Omarchy logo's pixel glyphs (15px grid).

glyphs_raw.json holds the letter outlines from Omarchy's /usr/share/omarchy/logo.svg
(MIT licensed, like the rest of Omarchy)."""
import json, subprocess
import numpy as np

U = 15
_raw = json.load(open(__file__.rsplit('/', 1)[0] + '/glyphs_raw.json'))
_names = {1: 'O', 2: 'M', 3: 'A', 0: 'R', 4: 'C', 5: 'H', 6: 'Y'}
G = {}
for x in _raw:
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="1215" height="300"><path fill-rule="{x["fr"]}" d="{x["d"]}"/></svg>'
    png = subprocess.run(['rsvg-convert', '-'], input=svg.encode(), capture_output=True).stdout
    raw = subprocess.run(['magick', 'png:-', '-alpha', 'extract', 'gray:-'], input=png, capture_output=True).stdout
    a = (np.frombuffer(raw, np.uint8).reshape(300, 1215) > 127)[7::U, 7::U]
    cols = np.where(a.any(0))[0]
    G[_names[x['i']]] = dict(d=x['d'], fr=x['fr'], grid=a[:, cols.min():cols.max() + 1], x0=int(cols.min()) * U)


def _edges(grid, right):
    out = []
    for row in grid:
        idx = np.where(row)[0]
        out.append((idx.max() if right else idx.min()) if len(idx) else None)
    return out


def _mode(edges):
    vals = [e for e in edges if e is not None]
    return max(set(vals), key=vals.count)


def layout(word):
    """Return [(letter, x_px)] and total width, kerned like the original logo."""
    word = word.upper()
    pos, prev = [], None
    for ch in word:
        if prev is None:
            pos.append((ch, 0)); prev = (ch, 0); continue
        pc, px = prev
        pr = _edges(G[pc]['grid'], True)
        nl = _edges(G[ch]['grid'], False)
        for off in range(0, 40):
            gaps = [off + l - r - 1 for r, l in zip(pr, nl) if r is not None and l is not None]
            stem = off + _mode(nl) - _mode(pr) - 1
            if min(gaps) >= 1 and stem >= 2:
                break
        x = (px // U + off) * U
        pos.append((ch, x)); prev = (ch, x)
    last, lx = pos[-1]
    return pos, lx + G[last]['grid'].shape[1] * U


def glyph_path(ch, x, y=0, **attrs):
    g = G[ch]
    a = ' '.join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
    return f'<path transform="translate({x - g["x0"]},{y})" fill-rule="{g["fr"]}" d="{g["d"]}" {a}/>'


if __name__ == '__main__':
    print(layout('omarchy'))
    print(layout('chromarchy'))
