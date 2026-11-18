"""Builds <NAME>.gif: the key steps only, silent, no captions. Run in the video's folder.

    python gif.py

HIGHLIGHTS: (clip, start s, end s, speed, (x, y)) where (x, y) is the top-left of a 1280x720
window of the 1920x1080 recording: zoom on the part that matters (a pane, a web page, a menu).
960x540 at 8 fps, one palette. Keep it under 10 MB (GitHub's image limit) and ~60 s.
"""
import os, shutil, subprocess, sys

# ---- edit per video -------------------------------------------------------------------------
NAME = "demo"
PANE, WEB, MENU = (640, 0), (320, 60), (0, 360)
HIGHLIGHTS = [
    ("01-setup", 13, 16, 1, MENU),
    ("02-main", 182, 189, 1.5, PANE),
]
# ---------------------------------------------------------------------------------------------

FF = os.environ.get("FFMPEG") or shutil.which("ffmpeg") or sys.exit("ffmpeg not found (PATH or FFMPEG)")
HERE = os.getcwd()
S, OUT = os.path.join(HERE, "shots"), os.path.join(HERE, "build", "gif")
os.makedirs(OUT, exist_ok=True)
ENC = ["-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p", "-r", "8"]


def run(a):
    if subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", *a]).returncode:
        sys.exit(f"ffmpeg failed: {a}")


parts, total = [], 0.0
for k, (clip, a, b, speed, (x, y)) in enumerate(HIGHLIGHTS):
    p = os.path.join(OUT, f"h{k:02d}.mp4")
    run(["-ss", str(a), "-to", str(b), "-i", os.path.join(S, clip + ".ts"), "-an", "-vf",
         f"setpts=(PTS-STARTPTS)/{speed},fps=8,crop=1280:720:{x}:{y},scale=960:540:flags=lanczos", *ENC, p])
    run(["-sseof", "-0.6", "-i", p, "-frames:v", "1", "-update", "1", os.path.join(OUT, f"last{k:02d}.png")])
    parts.append(p); total += (b - a) / speed
with open(os.path.join(OUT, "list.txt"), "w") as f:
    f.writelines(f"file '{p}'\n" for p in parts)
run(["-f", "concat", "-safe", "0", "-i", os.path.join(OUT, "list.txt"), "-c", "copy", os.path.join(OUT, "highlights.mp4")])
gif = os.path.join(HERE, f"{NAME}.gif")
run(["-i", os.path.join(OUT, "highlights.mp4"), "-vf",
     "split[a][b];[a]palettegen=max_colors=128:stats_mode=diff[p];[b][p]paletteuse=dither=none:diff_mode=rectangle", gif])
mb = os.path.getsize(gif) / 1e6
print(f"{gif}: {total:.0f}s, {mb:.1f} MB" + ("  ← over GitHub's 10 MB: fewer/shorter highlights or faster" if mb > 10 else ""))
print(f"check each crop: {OUT}{os.sep}last*.png")
