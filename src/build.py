#!/usr/bin/env python3
"""Render the Chromarchy lock screen artwork.

Every design shares the real Omarchy pixel wordmark (from Omarchy's logo.svg),
re-spelled as CHROMARCHY, and dresses it up differently. Writes ../build/<n>/
(logo, password box, padlock, optional footer / top bar, the dino's sprites,
meta.json, and a 1920x1080 preview.png mockup); src/update-assets.sh then copies
what the lock screen uses into ../assets/.

Needs: python3 with numpy, rsvg-convert, ImageMagick, and the fonts listed below.
"""
import json, math, os, shutil, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from wordmark import G, U, layout, glyph_path  # noqa: E402

OUT = os.path.join(HERE, '..', 'build')
W, H = 1920, 1080

GOOGLE = dict(blue='#4285F4', red='#EA4335', yellow='#FBBC05', green='#34A853')
ARCH_BLUE = '#1793D1'
RUBY = '#CC342D'
MONO = "JetBrainsMono Nerd Font"
SANS = "Adwaita Sans"
ARIAL = "Liberation Sans"


# ---------------------------------------------------------------- helpers

def svg(w, h, body, defs=''):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}"><defs>{defs}</defs>{body}</svg>')


def render(doc, path):
    subprocess.run(['rsvg-convert', '-o', path, '-'], input=doc.encode(), check=True)


def size(path):
    out = subprocess.run(['magick', 'identify', '-format', '%w %h', path],
                         capture_output=True, text=True, check=True).stdout
    return tuple(map(int, out.split()))


def text(x, y, s, size, fill, family=MONO, weight=400, anchor='start', spacing=0, style='normal', opacity=1):
    s = s.replace('&', '&amp;').replace('<', '&lt;')
    return (f'<text x="{x}" y="{y}" font-family="{family}" font-size="{size}" font-weight="{weight}" '
            f'font-style="{style}" fill="{fill}" text-anchor="{anchor}" letter-spacing="{spacing}" '
            f'opacity="{opacity}">{s}</text>')


def cells(grid, u, x0=0, y0=0, color='#fff'):
    """Draw a boolean grid (or grid of colors) as crisp u-sized squares."""
    out = []
    for r, row in enumerate(grid):
        for c, v in enumerate(row):
            if v:
                fill = v if isinstance(v, str) else color
                out.append(f'<rect x="{x0 + c * u}" y="{y0 + r * u}" width="{u}" height="{u}" fill="{fill}"/>')
    return ''.join(out)


def ascii_grid(art):
    rows = [r for r in art.strip('\n').split('\n')]
    w = max(map(len, rows))
    return [[ch == '#' for ch in r.ljust(w)] for r in rows]


def wordmark(u, fill='#fff', per_letter=None, skip=()):
    """CHROMARCHY in the Omarchy logo glyphs. Returns (svg_group, width, height)."""
    pos, width = layout('chromarchy')
    s = u / U
    parts = []
    for i, (ch, x) in enumerate(pos):
        if i in skip:
            continue
        f = per_letter[i] if per_letter else fill
        parts.append(glyph_path(ch, x, fill=f))
    return f'<g transform="scale({s})">{"".join(parts)}</g>', width * s, 19 * u, [(c, x * s) for c, x in pos]


def chrome_o_cells(u, x0, y0, center=True):
    """The Omarchy 'O' glyph recolored cell by cell into a Chrome wheel."""
    g = G['O']['grid']
    cx, cy = 4.5, 9.0
    out = []
    for r, row in enumerate(g):
        for c, v in enumerate(row):
            if not v:
                continue
            dx, dy = (c + 0.5 - cx), -(r + 0.5 - cy) * 9 / 16
            a = (math.degrees(math.atan2(dy, dx)) + 360) % 360
            col = GOOGLE['red'] if 30 <= a < 150 else GOOGLE['green'] if 150 <= a < 270 else GOOGLE['yellow']
            out.append(f'<rect x="{x0 + c * u}" y="{y0 + r * u}" width="{u}" height="{u}" fill="{col}"/>')
    if center:
        # blue hub: a notched pill floating in the counter, half a cell off the ring
        h = u / 2
        x, y, w_, hh = x0 + 3.5 * u, y0 + 6.5 * u, 2 * u, 5 * u
        out.append(f'<path fill="{GOOGLE["blue"]}" d="M{x + h},{y} h{w_ - 2 * h} v{h} h{h} v{hh - 2 * h} h{-h} v{h} '
                   f'h{-(w_ - 2 * h)} v{-h} h{-h} v{-(hh - 2 * h)} h{h} z"/>')
    return ''.join(out)


def arch_cells(n):
    """Rasterize the Arch Linux logo to an n x n boolean grid."""
    raw = subprocess.run(
        ['magick', '-background', 'none', '-density', '300', '/usr/share/pixmaps/archlinux-logo.svg',
         '-trim', '-resize', f'{n}x{n}!', '-alpha', 'extract', '-threshold', '45%', '-depth', '8', 'gray:-'],
        capture_output=True, check=True).stdout
    return (np.frombuffer(raw, np.uint8).reshape(n, n) > 127).tolist()


def box_entry(path, w, h, stroke, fill='none', radius=6, sw=2):
    render(svg(w, h, f'<rect x="{sw / 2}" y="{sw / 2}" width="{w - sw}" height="{h - sw}" rx="{radius}" '
                     f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'), path)


def lock_icon(path, color):
    # 84x96 padlock, same footprint as Omarchy's so the script's scaling holds
    render(svg(84, 96, f'<path d="M18 40 V28 a24 24 0 0 1 48 0 V40" fill="none" stroke="{color}" stroke-width="10"/>'
                       f'<rect x="4" y="40" width="76" height="54" rx="8" fill="{color}"/>'), path)


def blank(path, w=1, h=1):
    subprocess.run(['magick', '-size', f'{w}x{h}', 'xc:none', path], check=True)


def bullet(path, color):
    render(svg(14, 14, f'<circle cx="7" cy="7" r="7" fill="{color}"/>'), path)


def bars(d, track, fill):
    render(svg(300, 10, f'<rect width="300" height="10" rx="5" fill="{track}"/>'), f'{d}/progress_box.png')
    if isinstance(fill, list):
        seg = 300 / len(fill)
        body = ''.join(f'<rect x="{i * seg}" width="{seg + 0.5}" height="10" fill="{c}"/>' for i, c in enumerate(fill))
        render(svg(300, 10, f'<clipPath id="r"><rect width="300" height="10" rx="5"/></clipPath><g clip-path="url(#r)">{body}</g>'),
               f'{d}/progress_bar.png')
    else:
        render(svg(300, 10, f'<rect width="300" height="10" rx="5" fill="{fill}"/>'), f'{d}/progress_bar.png')


# ---------------------------------------------------------------- variants

def v1_fusion(d):
    """Chr + Omarchy: the O of 'omarchy' becomes a Chrome wheel."""
    bg, fg, muted = '#1a1b26', '#dfe3f0', '#565f89'
    u = 7
    wm, ww, wh, pos = wordmark(u, fill=fg, skip=(3,))
    ox = pos[3][1]
    body = wm + chrome_o_cells(u, ox, 0)
    tag = text(ww / 2, wh + 46, 'chrome outside  ·  omakase inside', 17, muted, anchor='middle', spacing=3)
    render(svg(math.ceil(ww), wh + 56, body + tag), f'{d}/logo.png')
    box_entry(f'{d}/entry.png', 300, 46, '#3b4261')
    lock_icon(f'{d}/lock.png', GOOGLE['blue'])
    bullet(f'{d}/bullet.png', fg)
    bars(d, '#24283b', [GOOGLE['red'], GOOGLE['yellow'], GOOGLE['green'], GOOGLE['blue']])
    return dict(bg=bg, bullet_dx=20)


def v2_feeling_archy(d):
    """Google homepage, but it's a LUKS prompt."""
    bg = '#202124'
    seq = ['blue', 'red', 'yellow', 'blue', 'green', 'red', 'blue', 'red', 'yellow', 'green']
    u = 7
    wm, ww, wh, _ = wordmark(u, per_letter=[GOOGLE[c] for c in seq])
    render(svg(math.ceil(ww), wh, wm), f'{d}/logo.png')

    ew, eh = 560, 48
    mag = (f'<circle cx="27" cy="22" r="7" fill="none" stroke="#9aa0a6" stroke-width="2.4"/>'
           f'<line x1="32" y1="27" x2="38" y2="33" stroke="#9aa0a6" stroke-width="2.6" stroke-linecap="round"/>')
    arch = arch_cells(20)
    archlogo = cells(arch, 1, ew - 40, 14, ARCH_BLUE)
    pill = f'<rect x="1" y="1" width="{ew - 2}" height="{eh - 2}" rx="{(eh - 2) / 2}" fill="#303134" stroke="#5f6368"/>'
    render(svg(ew, eh, pill + mag + archlogo), f'{d}/entry.png')
    render(svg(ew - 100, eh, text(0, 30, 'Search the Arch Wiki or type your passphrase', 16, '#9aa0a6', ARIAL)),
           f'{d}/hint.png')
    blank(f'{d}/lock.png', 84, 96)
    bullet(f'{d}/bullet.png', '#e8eaed')

    fw = 560

    def button(cx, label):
        bw = 30 + len(label) * 8.2
        return (f'<rect x="{cx - bw / 2}" y="0" width="{bw}" height="36" rx="4" fill="#303134"/>' +
                text(cx, 23, label, 14, '#e8eaed', ARIAL, anchor='middle'))
    langs = (f'<text x="{fw / 2}" y="86" font-family="{ARIAL}" font-size="13" fill="#bdc1c6" text-anchor="middle" '
             f'xml:space="preserve">Chromarchy offered in:  <tspan fill="#8ab4f8">Bash</tspan>  '
             f'<tspan fill="#8ab4f8">Ruby</tspan>  <tspan fill="#8ab4f8">Lua</tspan></text>')
    render(svg(fw, 96, button(fw / 2 - 86, 'Pacman Search') + button(fw / 2 + 86, "I'm Feeling Arch-y") + langs),
           f'{d}/footer.png')
    bars(d, '#303134', [GOOGLE['blue'], GOOGLE['red'], GOOGLE['yellow'], GOOGLE['green']])
    return dict(bg=bg, bullet_dx=52, footer_gap=34)


DINO = r'''
...........########.
..........##.#######
..........##########
..........##########
..........##########
..........#####.....
..........########..
#........#####......
#.......#######.....
##.....#########....
###...##########.#..
###############.....
.#############......
..###########.......
...#########........
....#######.........
.....###.##.........
.....##...#.........
.....#....#.........
.....##...##........
'''

CLOUD = r'''
.......####.......
.....##....##.....
..###........#....
.#............###.
#................#
##################
'''


DINO_LEGS = {
    'jump': DINO.strip('\n').split('\n')[16:],
    'run1': ['.....###.##.', '.....##..##.', '.....#......', '.....##.....'],
    'run2': ['.....###.##.', '......#...#.', '..........#.', '..........##'],
}

# Scene geometry for the animated dino variant. ChromarchyScene.qml and
# src/simulate.py use the same numbers; keep all three in sync.
DINO_ANIM = dict(scene_w=820, scene_h=220, ground_y=180, dino_x=90, dino_w=80, dino_h=80,
                 speed=6, score_x=685, score_y=8, digit_w=13)


def v3_offline(d):
    """Chrome's offline dino, hurdling Arch-logo cacti. Animated on the lock screen; HI score is Linux's birth year."""
    bg, ink, dim = '#202124', '#acacac', '#5f6368'
    A = DINO_ANIM
    sw, sh, gy, p = A['scene_w'], A['scene_h'], A['ground_y'], 4

    # --- moving parts (each its own PNG, driven by the script)
    body_rows = DINO.strip('\n').split('\n')[:16]
    for name, legs in DINO_LEGS.items():
        grid = ascii_grid('\n'.join(body_rows + legs))
        render(svg(A['dino_w'], A['dino_h'], cells(grid, p, 0, 0, ink)), f'{d}/dino-{name}.png')
    render(svg(60, 60, cells(arch_cells(15), p, 0, 0, ARCH_BLUE)), f'{d}/cactus-big.png')
    render(svg(44, 44, cells(arch_cells(11), p, 0, 0, ARCH_BLUE)), f'{d}/cactus-small.png')
    render(svg(54, 18, cells(ascii_grid(CLOUD), 3, 0, 0, dim)), f'{d}/cloud.png')
    pebbles = [(30, 6), (95, 3), (170, 8), (260, 4), (330, 2), (410, 6), (520, 3), (585, 5), (660, 2), (720, 7), (790, 3)]
    peb = ''.join(f'<rect x="{gx + k * sw}" y="{5 + (i % 3) * 5}" width="{gw}" height="2" fill="{dim}"/>'
                  for k in range(2) for i, (gx, gw) in enumerate(pebbles))
    render(svg(2 * sw, 20, peb), f'{d}/pebbles.png')
    for n in range(10):
        render(svg(A['digit_w'], 22, text(A['digit_w'] / 2, 18, str(n), 18, ink, MONO, 700, anchor='middle')),
               f'{d}/digit-{n}.png')
    # bg-colored masks that fade the scene's edges and hide anything scrolling past them
    for side in ('left', 'right'):
        x1, x2 = ('900', '960') if side == 'left' else ('60', '0')
        grad = (f'<linearGradient id="m" gradientUnits="userSpaceOnUse" x1="{x1}" x2="{x2}" y1="0" y2="0">'
                f'<stop offset="0" stop-color="{bg}"/><stop offset="1" stop-color="{bg}" stop-opacity="0"/></linearGradient>')
        render(svg(960, sh, '<rect width="960" height="100%" fill="url(#m)"/>', grad), f'{d}/mask-{side}.png')

    # --- static logo: ground line, HI score, wordmark, caption
    static = (f'<rect x="0" y="{gy}" width="{sw}" height="2" fill="{ink}"/>' +
              text(A['score_x'] - 12, A['score_y'] + 18, 'HI 01991', 18, ink, MONO, 700, anchor='end', spacing=2))
    u = 5
    wm, ww, wh, _ = wordmark(u, fill='#e8eaed')
    wx = (sw - ww) / 2
    cap = text(sw / 2, sh + 40 + wh + 44, 'ERR_NOT_CHROMEOS  —  booting Arch instead', 16, '#9aa0a6', MONO,
               anchor='middle', spacing=1)
    words = f'<g transform="translate({wx},{sh + 40})">{wm}</g>' + cap
    lh = sh + 40 + wh + 54
    render(svg(sw, lh, static + words), f'{d}/logo.png')

    # --- poster frame for the preview: dino mid-jump over a cactus
    pieces = [('pebbles', -300, gy + 2), ('cloud', 430, 50), ('cloud', 640, 76), ('cactus-big', 300, gy - 60),
              ('cactus-small', 560, gy - 44), ('dino-jump', 290, gy - 76 - 95), ('mask-left', -900, 0),
              ('mask-right', sw - 60, 0)]
    pieces += [(f'digit-{c}', A['score_x'] + i * A['digit_w'], A['score_y']) for i, c in enumerate('00420')]
    args = ['magick', f'{d}/logo.png']
    for name, x, y in pieces:
        args += [f'{d}/{name}.png', '-geometry', f'{x:+d}{y:+d}', '-composite']
    subprocess.run(args + [f'{d}/poster.png'], check=True)

    box_entry(f'{d}/entry.png', 300, 46, dim, radius=2)
    lock_icon(f'{d}/lock.png', ink)
    render(svg(14, 14, f'<rect width="14" height="14" fill="{ink}"/>'), f'{d}/bullet.png')
    bars(d, '#303134', ink)
    return dict(bg=bg, bullet_dx=20, anim=A)


def v4_le_mans(d):
    """DHH's other job: chrome-plated wordmark, Ruby-red extrusion, #37 roundel."""
    bg = '#0c0c10'
    u = 7
    pos, width = layout('chromarchy')
    s = u / U
    chrome = ('<linearGradient id="chrome" gradientUnits="userSpaceOnUse" x1="0" y1="15" x2="0" y2="255">'
              '<stop offset="0" stop-color="#f4fbff"/><stop offset="0.38" stop-color="#8fc3e6"/>'
              '<stop offset="0.5" stop-color="#ffffff"/><stop offset="0.51" stop-color="#2b1d14"/>'
              '<stop offset="0.66" stop-color="#7a4a22"/><stop offset="0.86" stop-color="#e9b874"/>'
              '<stop offset="1" stop-color="#fff2d0"/></linearGradient>')

    def word(fill, stroke=None):
        st = f' stroke="{stroke}" stroke-width="3"' if stroke else ''
        return ''.join(glyph_path(c, x, fill=fill) .replace('/>', f'{st}/>') for c, x in pos)
    depth = ''.join(f'<g transform="translate({i * 2.2},{i * 2.2})">{word("#5c1210" if i > 3 else RUBY)}</g>'
                    for i in range(8, 0, -1))
    face = word('url(#chrome)', '#ffffff')
    ww, wh = width * s, 19 * u
    skew = 'skewX(-12)'
    roundel_r = 52
    left = 150  # room for roundel + speed lines
    stripes = ''.join(f'<rect x="{-40 + i * 18}" y="{38 + i * 20}" width="{120 - i * 26}" height="9" fill="{RUBY}" '
                      f'transform="skewX(-12)"/>' for i in range(3))
    roundel = (f'<circle cx="{left - 70}" cy="{wh / 2 + 4}" r="{roundel_r}" fill="#f5f5f5" stroke="{RUBY}" stroke-width="5"/>' +
               text(left - 72, wh / 2 + 26, '37', 60, '#111', SANS, 900, anchor='middle', style='italic', spacing=-2))
    total_w = 2 * (left + 30) + ww
    logo_body = (stripes + roundel +
                 f'<g transform="translate({left + 30},0) {skew} scale({s})">{depth}{face}</g>')
    # checker band + tagline
    cy = wh + 34
    sq = 10
    n = int(ww // sq) // 2 * 2
    cx0 = (total_w - n * sq) / 2
    checks = ''.join(f'<rect x="{cx0 + i * sq}" y="{cy + (i % 2) * sq}" width="{sq}" height="{sq}" fill="#e8e8e8"/>'
                     for i in range(n))
    tag = text(total_w / 2, cy + 58, '24 HOURS OF LE MANS  ·  0 BYTES OF TELEMETRY', 17, '#9aa0a6', SANS, 700,
               anchor='middle', spacing=4, style='italic')
    render(svg(math.ceil(total_w), math.ceil(cy + 70), logo_body + checks + tag, chrome), f'{d}/logo.png')
    box_entry(f'{d}/entry.png', 300, 46, RUBY, radius=0)
    lock_icon(f'{d}/lock.png', '#f5f5f5')
    bullet(f'{d}/bullet.png', '#f5f5f5')
    bars(d, '#22222a', RUBY)
    return dict(bg=bg, bullet_dx=20)


def favicon(x, y):
    return chrome_o_cells(1.1, x, y - 1, center=True)


def v5_new_tab(d):
    """The whole screen is a Chrome New Tab page at chrome://omarchy."""
    bg = '#202124'
    frame, toolbar, ink, dim = '#1b1c1f', '#35363a', '#e8eaed', '#9aa0a6'
    th, tb = 42, 48
    b = [f'<rect width="{W}" height="{th}" fill="{frame}"/>',
         f'<rect y="{th}" width="{W}" height="{tb}" fill="{toolbar}"/>']
    # tabs
    tx, tw = 12, 250
    b.append(f'<path d="M{tx - 8},{th} q8,0 8,-8 v-20 q0,-8 8,-8 h{tw - 16} q8,0 8,8 v20 q0,8 8,8 z" fill="{toolbar}"/>')
    b.append(favicon(tx + 14, 12))
    b.append(text(tx + 36, 26, 'Chromarchy', 13, ink, SANS, 500))
    b.append(text(tx + tw - 18, 27, '×', 17, dim, SANS, anchor='middle'))
    for i, title in enumerate(['ArchWiki', 'Ruby on Rails Guides']):
        x = tx + tw + i * tw
        b.append(f'<rect x="{x + tw - 1}" y="12" width="1" height="18" fill="#5f6368"/>')
        b.append(cells(arch_cells(14), 1, x + 14, 14, ARCH_BLUE) if i == 0 else
                 f'<path d="M{x + 14},{18} l7,-4 l7,4 l-7,10 z" fill="{RUBY}"/>')
        b.append(text(x + 36, 26, title, 13, dim, SANS, 500))
        b.append(text(x + tw - 18, 27, '×', 17, dim, SANS, anchor='middle'))
    b.append(text(tx + 3 * tw + 22, 29, '+', 22, dim, SANS, anchor='middle'))
    for i, glyph in enumerate(['–', '□', '×']):
        b.append(text(W - 140 + i * 48, 28, glyph, 16, dim, SANS, anchor='middle'))
    # toolbar
    for i, glyph in enumerate(['←', '→', '↻']):
        b.append(text(28 + i * 40, th + 32, glyph, 20, dim if i == 1 else ink, SANS, anchor='middle'))
    ox, ow = 140, W - 260
    b.append(f'<rect x="{ox}" y="{th + 7}" width="{ow}" height="34" rx="17" fill="{frame}"/>')
    b.append(chrome_o_cells(1.1, ox + 16, th + 15))
    b.append(text(ox + 40, th + 30, 'Chromarchy', 15, ink, SANS, 500))
    b.append(f'<rect x="{ox + 138}" y="{th + 15}" width="1" height="18" fill="#5f6368"/>')
    b.append(f'<text x="{ox + 152}" y="{th + 30}" font-family="{SANS}" font-size="15" fill="{dim}">chrome://'
             f'<tspan fill="{ink}">omarchy</tspan></text>')
    b.append(text(ox + ow - 22, th + 30, '☆', 17, dim, SANS, anchor='middle'))
    # Avatar circle only; the lock screen draws the viewer's own initial on top of it
    b.append(f'<circle cx="{W - 76}" cy="{th + 24}" r="14" fill="{GOOGLE["green"]}"/>')
    b.append(text(W - 34, th + 31, '⋮', 20, ink, SANS, anchor='middle'))
    b.append(f'<rect y="{th + tb - 1}" width="{W}" height="1" fill="#000" opacity=".35"/>')
    render(svg(W, th + tb, ''.join(b)), f'{d}/top.png')

    u = 7
    wm, ww, wh, pos = wordmark(u, fill=ink, skip=(3,))
    render(svg(math.ceil(ww), wh, wm + chrome_o_cells(u, pos[3][1], 0)), f'{d}/logo.png')

    ew, eh = 580, 46
    mag = (f'<circle cx="25" cy="21" r="7" fill="none" stroke="{dim}" stroke-width="2.4"/>'
           f'<line x1="30" y1="26" x2="36" y2="32" stroke="{dim}" stroke-width="2.6" stroke-linecap="round"/>')
    render(svg(ew, eh, f'<rect width="{ew}" height="{eh}" rx="{eh / 2}" fill="#303134"/>' + mag), f'{d}/entry.png')
    render(svg(ew - 100, eh, text(0, 29, 'Type your passphrase or a URL', 16, dim, SANS)), f'{d}/hint.png')
    blank(f'{d}/lock.png', 84, 96)
    bullet(f'{d}/bullet.png', ink)

    tiles = [('ArchWiki', 'arch'), ('AUR', 'AUR'), ('Omarchy Manual', 'O'), ('Hyprland', 'H'),
             ('37signals', '37'), ('Add shortcut', '+')]
    tw_, fw = 112, 112 * 6
    f = []
    for i, (label, icon) in enumerate(tiles):
        cx = i * tw_ + tw_ / 2
        f.append(f'<circle cx="{cx}" cy="28" r="26" fill="#303134"/>')
        if icon == 'arch':
            f.append(cells(arch_cells(26), 1, cx - 13, 15, ARCH_BLUE))
        elif icon == 'O':
            f.append(chrome_o_cells(1.6, cx - 7, 13))
        else:
            col = {'AUR': ARCH_BLUE, 'H': '#58e1ff', '37': '#f2c94c', '+': ink}[icon]
            f.append(text(cx, 36 if icon != '+' else 38, icon, 20 if icon != '+' else 26, col, SANS, 800, anchor='middle'))
        f.append(text(cx, 80, label, 13, ink, SANS, anchor='middle'))
    render(svg(fw, 90, ''.join(f)), f'{d}/footer.png')
    bars(d, '#303134', GOOGLE['blue'])
    return dict(bg=bg, bullet_dx=52, footer_gap=44)


VARIANTS = [
    ('1', 'Chrome-plated Omakase', v1_fusion),
    ('2', "I'm Feeling Arch-y", v2_feeling_archy),
    ('3', 'ERR_NOT_CHROMEOS', v3_offline),
    ('4', 'Le Mans Livery', v4_le_mans),
    ('5', 'chrome://omarchy', v5_new_tab),
]


# ---------------------------------------------------------------- preview

def preview(d, meta, bullets=6, typed=True):
    """Composite a 1920x1080 mockup using the same layout math as ChromarchyScene.qml."""
    logo = f'{d}/poster.png' if os.path.exists(f'{d}/poster.png') else f'{d}/logo.png'
    lw, lh = size(logo)
    ew, eh = size(f'{d}/entry.png')
    lx, ly = (W - lw) // 2, (H - lh) // 2
    ex, ey = (W - ew) // 2, ly + lh + 40
    lock_h = int(eh * 0.8); lock_w = int(84 * lock_h / 96)
    args = ['magick', '-size', f'{W}x{H}', f'xc:{meta["bg"]}']
    if os.path.exists(f'{d}/top.png'):
        args += [f'{d}/top.png', '-geometry', '+0+0', '-composite']
    args += [logo, '-geometry', f'+{lx}+{ly}', '-composite',
             f'{d}/entry.png', '-geometry', f'+{ex}+{ey}', '-composite',
             '(', f'{d}/lock.png', '-resize', f'{lock_w}x{lock_h}!', ')', '-geometry',
             f'+{ex - lock_w - 15}+{ey + eh // 2 - lock_h // 2}', '-composite']
    if typed:
        for i in range(bullets):
            args += ['(', f'{d}/bullet.png', '-resize', '7x7', ')', '-geometry',
                     f'+{ex + meta["bullet_dx"] + i * 12}+{ey + eh // 2 - 4}', '-composite']
    elif os.path.exists(f'{d}/hint.png'):
        hw, hh = size(f'{d}/hint.png')
        args += [f'{d}/hint.png', '-geometry', f'+{ex + meta["bullet_dx"]}+{ey + (eh - hh) // 2}', '-composite']
    if os.path.exists(f'{d}/footer.png'):
        fw, fh = size(f'{d}/footer.png')
        args += [f'{d}/footer.png', '-geometry', f'+{(W - fw) // 2}+{ey + eh + meta.get("footer_gap", 40)}', '-composite']
    args.append(f'{d}/preview{"" if typed else "-empty"}.png')
    subprocess.run(args, check=True)


if __name__ == '__main__':
    only = set(sys.argv[1:])
    for vid, name, fn in VARIANTS:
        if only and vid not in only:
            continue
        d = os.path.join(OUT, vid)
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d)
        meta = fn(d)
        meta['name'] = name
        json.dump(meta, open(f'{d}/meta.json', 'w'), indent=2)
        preview(d, meta, typed=True)
        if os.path.exists(f'{d}/hint.png'):
            preview(d, meta, typed=False)
        print('built', vid, name)
