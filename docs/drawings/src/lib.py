"""SVG drawing helpers for the ChoroQ RC design drawings."""
from xml.sax.saxutils import escape

FONT = "'Hiragino Sans','Hiragino Kaku Gothic ProN',sans-serif"
INK = "#1f2933"
MUTED = "#6b7280"
BLUE = "#e8f0fe"
BLUE_S = "#3b6fd8"
ORANGE = "#fff1e0"
ORANGE_S = "#d9822b"
GREEN = "#e6f6ea"
GREEN_S = "#2f9e57"
GRAY = "#f1f3f5"
GRAY_S = "#868e96"
RED = "#fdecec"
RED_S = "#d64545"
PURPLE = "#f1eafd"
PURPLE_S = "#7c4dd6"


class Svg:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.parts = []

    def add(self, s):
        self.parts.append(s)

    def render(self):
        defs = f"""<defs>
<marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{INK}"/></marker>
<marker id="arrb" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{BLUE_S}"/></marker>
<marker id="arro" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{ORANGE_S}"/></marker>
<marker id="arrg" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{GREEN_S}"/></marker>
<marker id="arrr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{RED_S}"/></marker>
<marker id="dim" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,1 L10,5 L0,9 z" fill="{MUTED}"/></marker>
<pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="{GRAY_S}" stroke-width="1"/></pattern>
</defs>"""
        body = "\n".join(self.parts)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
                f'viewBox="0 0 {self.w} {self.h}" font-family="{FONT}">\n'
                f'<rect width="100%" height="100%" fill="#ffffff"/>\n{defs}\n{body}\n</svg>')

    # primitives -------------------------------------------------------
    def text(self, x, y, s, size=13, anchor="start", weight="normal", fill=INK, italic=False):
        style = ' font-style="italic"' if italic else ""
        self.add(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}" '
                 f'font-weight="{weight}" fill="{fill}"{style}>{escape(s)}</text>')

    def lines(self, x, y, rows, size=13, anchor="start", gap=None, fill=INK, weight="normal"):
        gap = gap or size * 1.45
        for i, r in enumerate(rows):
            self.text(x, y + i * gap, r, size, anchor, weight, fill)

    def rect(self, x, y, w, h, fill=GRAY, stroke=INK, sw=1.4, rx=6, dash=None, opacity=1):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" '
                 f'stroke="{stroke}" stroke-width="{sw}"{d} fill-opacity="{opacity}"/>')

    def box(self, x, y, w, h, title, rows=(), fill=GRAY, stroke=INK, size=13, tsize=14, dash=None, rx=8):
        self.rect(x, y, w, h, fill, stroke, 1.5, rx, dash)
        cx = x + w / 2
        n = len(rows)
        total = tsize * 1.5 + n * size * 1.45
        y0 = y + (h - total) / 2 + tsize
        self.text(cx, y0, title, tsize, "middle", "bold")
        for i, r in enumerate(rows):
            self.text(cx, y0 + tsize * 0.55 + (i + 1) * size * 1.45 - size * 0.35, r, size, "middle", fill="#374151")

    def line(self, x1, y1, x2, y2, color=INK, sw=1.5, dash=None, end=None, start=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        me = f' marker-end="url(#{end})"' if end else ""
        ms = f' marker-start="url(#{start})"' if start else ""
        self.add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}"{d}{me}{ms}/>')

    def poly(self, pts, color=INK, sw=1.5, dash=None, end=None, start=None, fill="none"):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        me = f' marker-end="url(#{end})"' if end else ""
        ms = f' marker-start="url(#{start})"' if start else ""
        p = " ".join(f"{a},{b}" for a, b in pts)
        self.add(f'<polyline points="{p}" fill="{fill}" stroke="{color}" stroke-width="{sw}" '
                 f'stroke-linejoin="round"{d}{me}{ms}/>')

    def path(self, d, color=INK, sw=1.5, fill="none", dash=None, end=None):
        da = f' stroke-dasharray="{dash}"' if dash else ""
        me = f' marker-end="url(#{end})"' if end else ""
        self.add(f'<path d="{d}" fill="{fill}" stroke="{color}" stroke-width="{sw}"{da}{me}/>')

    def circle(self, cx, cy, r, fill="none", stroke=INK, sw=1.4, dash=None):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

    def label_bg(self, x, y, s, size=12, fill=INK, bg="#ffffff", anchor="middle", weight="normal"):
        w = sum(size if ord(c) > 255 else size * 0.6 for c in s) + 8
        x0 = x - w / 2 if anchor == "middle" else (x if anchor == "start" else x - w)
        self.add(f'<rect x="{x0}" y="{y - size}" width="{w}" height="{size * 1.4}" rx="3" fill="{bg}" fill-opacity="0.95"/>')
        tx = x if anchor == "middle" else (x0 + 4 if anchor == "start" else x - 4)
        self.text(tx, y, s, size, anchor if anchor != "end" else "end", weight, fill)

    # drafting ---------------------------------------------------------
    def dim_h(self, x1, x2, y, label, y_from=None, size=12):
        if y_from is not None:
            for x in (x1, x2):
                self.line(x, y_from, x, y + (4 if y > y_from else -4), MUTED, 0.8)
        self.line(x1, y, x2, y, MUTED, 0.9, end="dim", start="dim")
        self.label_bg((x1 + x2) / 2, y - 4, label, size, MUTED)

    def dim_v(self, y1, y2, x, label, x_from=None, size=12):
        if x_from is not None:
            for y in (y1, y2):
                self.line(x_from, y, x + (4 if x > x_from else -4), y, MUTED, 0.8)
        self.line(x, y1, x, y2, MUTED, 0.9, end="dim", start="dim")
        cy = (y1 + y2) / 2
        self.add(f'<g transform="translate({x - 5},{cy}) rotate(-90)">'
                 f'<rect x="{-(len(label) * size * 0.62 + 8) / 2}" y="{-size}" width="{len(label) * size * 0.62 + 8}" '
                 f'height="{size * 1.35}" fill="#fff"/>'
                 f'<text x="0" y="0" font-size="{size}" text-anchor="middle" fill="{MUTED}">{escape(label)}</text></g>')

    def spring(self, x, y1, y2, w=8, n=6, color=INK, sw=1.3):
        """vertical zigzag spring from y1(top) to y2(bottom)"""
        h = (y2 - y1)
        pts = [(x, y1)]
        step = h / (n * 2 + 2)
        yy = y1 + step
        pts.append((x, yy))
        for i in range(n * 2):
            yy += step
            pts.append((x + (w if i % 2 == 0 else -w), yy))
        pts.append((x, y2 - step))
        pts.append((x, y2))
        self.poly(pts, color, sw)

    def title_block(self, no, name, scale="NTS（尺度なし）", unit="mm", date="2026-10-25", sub="遠隔操作チョロQ"):
        w, h = 430, 66
        x, y = self.w - w - 14, self.h - h - 14
        self.rect(x, y, w, h, "#fff", INK, 1.2, 0)
        self.line(x + 110, y, x + 110, y + h, INK, 0.8)
        self.line(x, y + 33, x + 110, y + 33, INK, 0.8)
        self.line(x + 110, y + 40, x + w, y + 40, INK, 0.8)
        self.text(x + 8, y + 14, "図番", 10, fill=MUTED)
        self.text(x + 55, y + 27, no, 14, "middle", "bold")
        self.text(x + 8, y + 47, "単位", 10, fill=MUTED)
        self.text(x + 70, y + 59, unit, 12, "middle")
        self.text(x + 118, y + 14, sub, 10, fill=MUTED)
        self.text(x + 118, y + 33, name, 15, weight="bold")
        self.text(x + 118, y + 57, f"尺度 {scale}   作成 {date}", 11, fill=MUTED)

    def heading(self, s, sub=None):
        self.text(24, 38, s, 22, weight="bold")
        if sub:
            self.text(24, 62, sub, 13, fill=MUTED)

    def note_box(self, x, y, w, rows, title="注記", size=12, fill="#fffbea", stroke="#e0b100"):
        h = 30 + len(rows) * size * 1.5
        self.rect(x, y, w, h, fill, stroke, 1.2, 6)
        self.text(x + 12, y + 20, title, 13, weight="bold")
        for i, r in enumerate(rows):
            self.text(x + 12, y + 40 + i * size * 1.5, r, size, fill="#374151")
        return h

    def netflag(self, x, y, name, color=INK, anchor="start"):
        """small net label flag"""
        size = 11
        w = sum(size if ord(c) > 255 else size * 0.62 for c in name) + 12
        if anchor == "start":
            pts = [(x, y), (x + 6, y - 8), (x + w, y - 8), (x + w, y + 8), (x + 6, y + 8)]
            tx = x + 8
        else:
            pts = [(x, y), (x - 6, y - 8), (x - w, y - 8), (x - w, y + 8), (x - 6, y + 8)]
            tx = x - w + 3
        p = " ".join(f"{a},{b}" for a, b in pts)
        self.add(f'<polygon points="{p}" fill="#fff" stroke="{color}" stroke-width="1.1"/>')
        self.text(tx, y + 4, name, size, fill=color, weight="bold")

    def gnd(self, x, y):
        self.line(x, y, x, y + 8)
        self.line(x - 9, y + 8, x + 9, y + 8, sw=1.6)
        self.line(x - 6, y + 12, x + 6, y + 12, sw=1.4)
        self.line(x - 3, y + 16, x + 3, y + 16, sw=1.2)

    def resistor_v(self, x, y1, y2, label=None):
        mid1, mid2 = y1 + (y2 - y1) * 0.25, y1 + (y2 - y1) * 0.75
        self.line(x, y1, x, mid1)
        self.rect(x - 6, mid1, 12, mid2 - mid1, "#fff", INK, 1.3, 1)
        self.line(x, mid2, x, y2)
        if label:
            self.text(x + 11, (y1 + y2) / 2 + 4, label, 11)

    def cap_v(self, x, y1, y2, label=None, polar=False):
        m = (y1 + y2) / 2
        self.line(x, y1, x, m - 3)
        self.line(x - 9, m - 3, x + 9, m - 3, sw=2)
        if polar:
            self.path(f"M{x - 9},{m + 5} Q{x},{m - 1} {x + 9},{m + 5}", INK, 2)
            self.text(x - 16, m - 5, "+", 11)
        else:
            self.line(x - 9, m + 3, x + 9, m + 3, sw=2)
        self.line(x, m + 3, x, y2)
        if label:
            self.text(x + 13, m + 4, label, 11)

    def dot(self, x, y, r=3, color=INK):
        self.add(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>')

    def wheel_side(self, cx, cy, r, fill="#4b5563"):
        self.circle(cx, cy, r, fill, INK, 1.4)
        self.circle(cx, cy, r * 0.55, "#d1d5db", INK, 1)
        self.circle(cx, cy, 2.2, INK, INK, 1)

    def save(self, path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.render())
