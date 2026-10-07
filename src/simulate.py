#!/usr/bin/env python3
"""Replay the dino game from ChromarchyScene.qml in Python: check that the dino
never hits a cactus, and with --webp render docs-style animation to
build/3/anim.webp. Keep the rules in sync with the QML."""
import json, os, random, subprocess, sys
import numpy as np

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'build', '3')
A = json.load(open(f'{D}/meta.json'))['anim']


def rgba(name):
    w, h = map(int, subprocess.run(['magick', 'identify', '-format', '%w %h', f'{D}/{name}.png'],
                                   capture_output=True, text=True).stdout.split())
    raw = subprocess.run(['magick', f'{D}/{name}.png', '-depth', '8', 'rgba:-'], capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w, 4).astype(np.float32) / 255


IMG = {n: rgba(n) for n in ['dino-run1', 'dino-run2', 'dino-jump', 'cactus-big', 'cactus-small', 'cloud',
                            'pebbles', 'logo', 'mask-left', 'mask-right'] + [f'digit-{i}' for i in range(10)]}


class State:
    def __init__(self, rng):
        self.rng = rng
        self.h = self.vy = self.air = self.leg = self.leg_t = 0
        self.cactus = [dict(x=620 + i * 430, kind='small' if i == 1 else 'big') for i in range(3)]
        self.cloud = [430 + i * 230 for i in range(2)]
        self.peb_x = 0
        self.score = self.score_t = 0
        self.img = 'dino-run1'

    def tick(self):
        s = A['speed']
        for c in self.cactus:
            c['x'] -= s
            if c['x'] < -100:
                far = max([A['scene_w']] + [o['x'] for o in self.cactus])
                c['x'] = far + 340 + int(self.rng.random() * 320)
                c['kind'] = 'big' if self.rng.random() < 0.5 else 'small'
        if not self.air:
            for c in self.cactus:
                gap = c['x'] - (A['dino_x'] + A['dino_w'])
                if 0 < gap <= 54:
                    self.air, self.vy = 1, 10
        if self.air:
            self.h += self.vy
            self.vy -= 0.5
            if self.h <= 0:
                self.h, self.air = 0, 0
            self.img = 'dino-jump'
        else:
            self.leg_t += 1
            if self.leg_t >= 5:
                self.leg_t, self.leg = 0, 1 - self.leg
            self.img = 'dino-run1' if self.leg == 0 else 'dino-run2'
        for i in range(2):
            self.cloud[i] -= 0.5
            if self.cloud[i] < -80:
                self.cloud[i] = A['scene_w'] + 40 + int(self.rng.random() * 200)
        self.peb_x -= s
        if self.peb_x <= -A['scene_w']:
            self.peb_x += A['scene_w']
        self.score_t += 1
        if self.score_t >= 5:
            self.score_t, self.score = 0, self.score + 1

    def dino_pos(self):
        return A['dino_x'], A['ground_y'] - A['dino_h'] + 4 - self.h

    def cactus_pos(self, c):
        hh = 60 if c['kind'] == 'big' else 44
        return c['x'], A['ground_y'] - hh + 2


def collides(st):
    dx, dy = st.dino_pos()
    dm = IMG[st.img][..., 3] > 0.5
    for c in st.cactus:
        cx, cy = st.cactus_pos(c)
        cm = IMG[f'cactus-{c["kind"]}'][..., 3] > 0.5
        x0, y0 = int(max(dx, cx)), int(max(dy, cy))
        x1 = int(min(dx + dm.shape[1], cx + cm.shape[1])); y1 = int(min(dy + dm.shape[0], cy + cm.shape[0]))
        if x1 <= x0 or y1 <= y0:
            continue
        a = dm[y0 - int(dy):y1 - int(dy), x0 - int(dx):x1 - int(dx)]
        b = cm[y0 - int(cy):y1 - int(cy), x0 - int(cx):x1 - int(cx)]
        if (a & b).any():
            return True
    return False


def blit(canvas, img, x, y):
    x, y = int(round(x)), int(round(y))
    h, w = img.shape[:2]
    H, W = canvas.shape[:2]
    sx0, sy0 = max(0, -x), max(0, -y)
    dx0, dy0 = max(0, x), max(0, y)
    dx1, dy1 = min(W, x + w), min(H, y + h)
    if dx1 <= dx0 or dy1 <= dy0:
        return
    src = img[sy0:sy0 + dy1 - dy0, sx0:sx0 + dx1 - dx0]
    a = src[..., 3:4]
    canvas[dy0:dy1, dx0:dx1, :3] = src[..., :3] * a + canvas[dy0:dy1, dx0:dx1, :3] * (1 - a)


def frame(st, bg):
    logo = IMG['logo']
    pad = 40
    c = np.zeros((logo.shape[0] + pad * 2, logo.shape[1] + pad * 2, 4), np.float32)
    c[..., :3] = bg
    ox, oy = pad, pad
    blit(c, logo, ox, oy)
    for i, x in enumerate(st.cloud):
        blit(c, IMG['cloud'], ox + x, oy + 50 + i * 26)
    blit(c, IMG['pebbles'], ox + st.peb_x, oy + A['ground_y'] + 2)
    for cc in st.cactus:
        x, y = st.cactus_pos(cc)
        blit(c, IMG[f'cactus-{cc["kind"]}'], ox + x, oy + y)
    x, y = st.dino_pos()
    blit(c, IMG[st.img], ox + x, oy + y)
    for k, ch in enumerate(f'{st.score:05d}'):
        blit(c, IMG[f'digit-{ch}'], ox + A['score_x'] + k * A['digit_w'], oy + A['score_y'])
    blit(c, IMG['mask-left'], ox - 900, oy)
    blit(c, IMG['mask-right'], ox + A['scene_w'] - 60, oy)
    return (c[..., :3] * 255).astype(np.uint8)


if __name__ == '__main__':
    hits = 0
    for seed in range(20):
        st = State(random.Random(seed))
        for t in range(50 * 120):  # two minutes at 50 fps
            st.tick()
            if collides(st):
                hits += 1
    print('collision frames over 20 x 2 min:', hits)

    if '--webp' in sys.argv:
        bg = np.array([0x20, 0x21, 0x24], np.float32) / 255
        st = State(random.Random(7))
        frames = []
        for t in range(50 * 8):
            st.tick()
            if t % 2 == 0:  # 25 fps is plenty for the preview
                frames.append(frame(st, bg))
        h, w = frames[0].shape[:2]
        out = f'{D}/anim.webp'
        subprocess.run(['magick', '-size', f'{w}x{h}', '-depth', '8', '-delay', '4', 'rgb:-', '-loop', '0',
                        '-quality', '80', out], input=b''.join(f.tobytes() for f in frames), check=True)
        print('wrote', out, len(frames), 'frames')
