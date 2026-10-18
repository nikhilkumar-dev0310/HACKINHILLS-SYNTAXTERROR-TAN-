"""Vertical (9:16) cut of the round 2 demo for the Social Pitch & Outreach round.

The 1:28 landscape demo plays in the middle of a 1080x1920 frame. Above it: the Parity mark and what it is.
Below it: the same captions as ../Parity_demo.srt, set large enough to read on a phone, then the repo and live
links, which stay on screen the whole time. Everything that must be read sits inside Instagram's safe area
(clear of the top 220 px, the bottom 320 px and the right-hand buttons).

    python3 vertical.py          # writes ../Parity_demo_vertical.mp4 (about a minute)
"""
import pathlib, re, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).resolve().parent
SRC, SRT = HERE.parent / "Parity_demo.mp4", HERE.parent / "Parity_demo.srt"
OUT = HERE.parent / "Parity_demo_vertical.mp4"
REPO = ("github.com/nikhilkumar-dev0310/", "HACKINHILLS-SYNTAXTERROR-TAN-")
LIVE = "parity-gold-site.vercel.app"
W, H = 1080, 1920
VX, VY, VW, VH = 0, 548, 1080, 608            # the landscape demo, full width
CAP_Y0, CAP_Y1 = 1196, 1420                     # caption band
BG, INK, INK2, INK3, GOLD = (5, 5, 6), (245, 245, 247), (161, 161, 166), (110, 110, 115), (242, 181, 68)


def font(name, size, wght, opsz=None):
    f = ImageFont.truetype(str(HERE / "fonts" / f"{name}.woff"), size)
    f.set_variation_by_axes([opsz or min(32, size), wght] if name == "in" else [wght])
    return f


def spaced(d, xy, text, f, fill, track, anchor="mm"):
    """Draws letter-spaced text centred on xy (PIL has no tracking)."""
    widths = [d.textlength(c, font=f) for c in text]
    total = sum(widths) + track * (len(text) - 1)
    x = xy[0] - total / 2 if anchor == "mm" else xy[0]
    for c, w in zip(text, widths):
        d.text((x, xy[1]), c, font=f, fill=fill, anchor="lm"); x += w + track


def wrap(d, text, f, width):
    lines, cur = [], ""
    for word in text.split():
        t = (cur + " " + word).strip()
        if d.textlength(t, font=f) <= width or not cur: cur = t
        else: lines.append(cur); cur = word
    return lines + [cur]


def background(path):
    im = Image.new("RGB", (W, H), BG)
    glow = Image.new("L", (W, H), 0); g = ImageDraw.Draw(glow)
    for r in range(520, 0, -8):                                 # soft gold light behind the header
        g.ellipse((W / 2 - r * 1.5, 330 - r * 0.7, W / 2 + r * 1.5, 330 + r * 0.7), fill=int(26 * (1 - r / 520)))
    im.paste(Image.new("RGB", (W, H), GOLD), (0, 0), glow)
    d = ImageDraw.Draw(im)
    # the Parity mark: two gold bars (the site's own logo geometry), then the wordmark
    s, mx, my = 3.1, W / 2 - 205, 268
    for dy in (0, 13.4):
        d.polygon([(mx + (x - 9) * s, my + (y - 11 + dy) * s) for x, y in ((14, 13), (34, 13), (37.2, 21.6), (10.8, 21.6))], fill=GOLD)
    d.text((mx + 96, my + 40), "Parity", font=font("sg", 96, 650), fill=INK, anchor="lm")
    spaced(d, (W / 2, 400), "WORKING PROTOTYPE · HACK IN HILLS ’26", font("jb", 25, 500), GOLD, 3.2)
    f = font("in", 38, 420)
    for i, line in enumerate(["MCX’s four gold futures, compared", "per gram of pure gold, every trading day."]):
        d.text((W / 2, 458 + i * 48), line, font=f, fill=INK2, anchor="mm")
    # the links, on screen the whole time
    spaced(d, (W / 2, 1468), "CODE ON GITHUB", font("jb", 23, 500), INK3, 3)
    fm = font("jb", 34, 500)
    d.text((W / 2, 1512), REPO[0], font=fm, fill=INK, anchor="mm")
    d.text((W / 2, 1556), REPO[1], font=fm, fill=INK, anchor="mm")
    spaced(d, (W / 2, 1620), "LIVE, UPDATED EVERY TRADING DAY", font("jb", 23, 500), INK3, 3)
    d.text((W / 2, 1666), LIVE, font=font("sg", 46, 600), fill=GOLD, anchor="mm")
    d.text((W / 2, 1738), "SYNTAX TERROR (TAN) · Nikhil Kumar · Sai Ganesh · Ishaan Chhabra", font=font("in", 25, 450), fill=INK3, anchor="mm")
    im.save(path)


def corners(path, r=28):
    """Rounds the video's corners: background-coloured corners over the video, transparent elsewhere."""
    m = Image.new("L", (VW, VH), 255)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, VW - 1, VH - 1), radius=r, fill=0)
    im = Image.new("RGBA", (VW, VH), BG + (255,)); im.putalpha(m)
    ImageDraw.Draw(im).rounded_rectangle((0, 0, VW - 1, VH - 1), radius=r, outline=(255, 240, 210, 40), width=2)
    im.save(path)


def captions():
    t = SRT.read_text(encoding="utf-8")
    ts = lambda s: sum(float(x) * m for x, m in zip(s.replace(",", ".").split(":"), (3600, 60, 1)))
    for blk in re.split(r"\n\s*\n", t.strip()):
        lines = blk.strip().splitlines()
        a, b = (ts(x.strip()) for x in lines[1].split("-->"))
        text = " ".join(lines[2:]).strip()
        yield a, b, re.sub(r"(\w)'(\w)", "\\1\u2019\\2", text)   # typographic apostrophes, as on the site


def caption_png(path, text):
    im = Image.new("RGBA", (W, CAP_Y1 - CAP_Y0), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    pari = text.startswith("Pari:")
    body = text[5:].strip() if pari else text
    f = font("in", 50 if len(body) < 70 else 44, 600)
    lines = wrap(d, body, f, 900)
    lh = f.size * 1.22
    top = (im.height - lh * len(lines) - (44 if pari else 0)) / 2
    if pari:
        spaced(d, (W / 2, top + 14), "PARI", font("jb", 24, 600), GOLD, 4); top += 44
    for i, line in enumerate(lines):
        d.text((W / 2, top + lh * (i + .5)), line, font=f, fill=GOLD if pari else INK, anchor="mm")
    im.save(path)


def main():
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(SRC)]))
    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        background(tmp / "bg.png"); corners(tmp / "corners.png")
        caps = list(captions())
        for i, (_, _, text) in enumerate(caps):
            caption_png(tmp / f"c{i:02d}.png", text)
        inputs = ["-loop", "1", "-framerate", "30", "-i", str(tmp / "bg.png"), "-i", str(SRC), "-i", str(tmp / "corners.png")]
        for i in range(len(caps)):
            inputs += ["-i", str(tmp / f"c{i:02d}.png")]
        fc = [f"[1:v]scale={VW}:{VH}:flags=lanczos,setsar=1[v]", f"[0:v][v]overlay={VX}:{VY}:shortest=1[a0]",
              f"[a0][2:v]overlay={VX}:{VY}[a1]",
              # a thin gold progress line under the video
              # (a full-length bar slides in from the left; the margin it slides through is painted over again)
              f"[a1]drawbox=x=48:y={VY + VH + 14}:w=984:h=4:color=0xffffff@0.10:t=fill[a2]",
              f"color=c=0xf2b544:s=984x4:r=30[bar]",
              f"[a2][bar]overlay=x='48-984+984*t/{dur:.3f}':y={VY + VH + 14}:shortest=1,"
              f"drawbox=x=0:y={VY + VH + 10}:w=48:h=12:color=0x050506@1:t=fill[b0]"]
        for i, (a, b, _) in enumerate(caps):
            fc.append(f"[b{i}][{i + 3}:v]overlay=0:{CAP_Y0 + 24}:enable='between(t,{a:.3f},{b:.3f})'[b{i + 1}]")
        cmd = ["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", f"[b{len(caps)}]", "-map", "1:a",
               "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-pix_fmt", "yuv420p", "-r", "30",
               "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", f"{dur:.3f}", str(OUT)]
        subprocess.run(cmd, check=True)
    print(OUT, f"{OUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
