"""Timestamped contact sheets of a recording, to find moments without scrubbing.

    python sheets.py shots/03-pipeline.ts --every 10                 # whole clip, 4x4 tiles per sheet
    python sheets.py shots/03-pipeline.ts --from 170 --to 236 --every 2 --crop 900:560:1020:0

Each tile is labelled with its time in the clip (seconds). Sheets go to sheets/.
--crop w:h:x:y zooms on one region (e.g. a side pane) so its text is readable.
"""
import argparse, os, shutil, subprocess, sys

FF = os.environ.get("FFMPEG") or shutil.which("ffmpeg") or sys.exit("ffmpeg not found (PATH or FFMPEG)")
FONT = "C\\:/Windows/Fonts/consola.ttf" if os.name == "nt" else "DejaVuSansMono"

p = argparse.ArgumentParser()
p.add_argument("clip")
p.add_argument("--every", type=float, default=10)
p.add_argument("--from", dest="start", type=float, default=0)
p.add_argument("--to", dest="end", type=float)
p.add_argument("--crop")
p.add_argument("--tile", default="4x4")
p.add_argument("--width", type=int, default=480)
a = p.parse_args()

os.makedirs("sheets", exist_ok=True)
name = os.path.splitext(os.path.basename(a.clip))[0] + (f"-{a.start:g}" if a.start else "")
vf = [f"fps=1/{a.every}"]
if a.crop:
    vf.append(f"crop={a.crop}")
vf += [f"scale={a.width}:-2",
       f"drawtext=fontfile='{FONT}':text='%{{eif\\:t+{a.start}\\:d}}':x=4:y=4:fontsize=24:fontcolor=yellow:box=1:boxcolor=black",
       f"tile={a.tile}"]
args = [FF, "-hide_banner", "-loglevel", "error", "-y", "-ss", str(a.start)]
if a.end:
    args += ["-to", str(a.end)]
subprocess.run(args + ["-i", a.clip, "-vf", ",".join(vf), os.path.join("sheets", f"{name}-%02d.png")], check=True)
print("\n".join(sorted(os.path.join("sheets", f) for f in os.listdir("sheets") if f.startswith(name))))
