"""Builds the narrated cut from shots/*.ts, lines.txt and voice/line<N>.mp3. Run in the video's folder.

    python build.py            # youtube/<NAME>-youtube.mp4 + .en.srt + thumbnail
    python build.py --burn     # also <NAME>-captioned.mp4 with burned-in captions

SCENES: one per line of lines.txt, each a list of segments (clip, start s, end s, speed).
Waits run fast with a ▶▶ badge (speed >= 3); the person's clicks near real time. A scene shorter
than LEAD + its line + TAIL has its last frame held, so the voice never overruns.
"""
import argparse, os, shutil, subprocess, sys

# ---- edit per video -------------------------------------------------------------------------
NAME = "demo"
SCENES = [
    [("01-setup", 10, 30, 1), ("01-setup", 30, 110, 16)],
    [("02-main", 100, 170, 35), ("02-main", 170, 190, 2)],
]
THUMB = ("02-main", 180, "crop=1280:720:640:0")  # clip, second, filter
LEAD, TAIL = 0.5, 0.7  # silence before each line, and after it before the next scene
# ---------------------------------------------------------------------------------------------

FF = os.environ.get("FFMPEG") or shutil.which("ffmpeg") or sys.exit("ffmpeg not found (PATH or FFMPEG)")
FP = os.environ.get("FFPROBE") or shutil.which("ffprobe") or os.path.join(os.path.dirname(FF), "ffprobe")
HERE = os.getcwd()
S, V, OUT, YT = (os.path.join(HERE, d) for d in ("shots", "voice", "build", "youtube"))
os.makedirs(OUT, exist_ok=True); os.makedirs(YT, exist_ok=True)
FPS = 30
ENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(FPS)]
FONT = "C\\:/Windows/Fonts/seguisb.ttf" if os.name == "nt" else "DejaVuSans-Bold"
ap =argparse.ArgumentParser(); ap.add_argument("--burn", action="store_true"); args = ap.parse_args()


def run(a):
    if subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", *a]).returncode:
        sys.exit(f"ffmpeg failed: {a}")


def dur(path):
    return float(subprocess.check_output([FP, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]))


def concat(parts, out):
    with open(out + ".txt", "w") as f:
        f.writelines(f"file '{p}'\n" for p in parts)
    run(["-f", "concat", "-safe", "0", "-i", out + ".txt", "-c", "copy", out])


def segment(out, clip, a, b, speed):
    vf = [f"setpts=(PTS-STARTPTS)/{speed}", f"fps={FPS}"]
    if speed >= 3:
        vf.append(f"drawtext=fontfile='{FONT}':text='▶▶ {speed:g}×':fontsize=34:fontcolor=0xffd75e"
                  f":box=1:boxcolor=0x000000@0.72:boxborderw=12:x=w-tw-36:y=36")
    run(["-ss", str(a), "-to", str(b), "-i", os.path.join(S, clip + ".ts"), "-an", "-vf", ",".join(vf), *ENC, out])


lines = [l.strip() for l in open(os.path.join(HERE, "lines.txt"), encoding="utf-8") if l.strip()]
if len(lines) != len(SCENES):
    sys.exit(f"{len(lines)} lines for {len(SCENES)} scenes")
audio = [dur(os.path.join(V, f"line{i + 1}.mp3")) for i in range(len(lines))]

scenes, t, cues, mix_in, mix = [], 0.0, [], [], []
for n, segs in enumerate(SCENES):
    parts = []
    for k, seg in enumerate(segs):
        p = os.path.join(OUT, f"s{n + 1}_{k}.mp4"); segment(p, *seg); parts.append(p)
    scene = os.path.join(OUT, f"scene{n + 1}.mp4"); concat(parts, scene)
    d, need = dur(scene), LEAD + audio[n] + TAIL
    if d < need:
        held = os.path.join(OUT, f"scene{n + 1}-held.mp4")
        run(["-i", scene, "-vf", f"tpad=stop_mode=clone:stop_duration={need - d:.2f}", *ENC, held])
        scene, d = held, dur(held)
    scenes.append(scene)
    ms = int((t + LEAD) * 1000)
    mix_in += ["-i", os.path.join(V, f"line{n + 1}.mp3")]
    mix.append(f"[{n}:a]adelay={ms}|{ms}[a{n}]")
    cues.append((t + LEAD, t + LEAD + audio[n], lines[n]))
    print(f"scene {n + 1}: {d:.1f}s, line {audio[n]:.1f}s")
    t += d

concat(scenes, os.path.join(OUT, "video.mp4"))
amix = ";".join(mix) + ";" + "".join(f"[a{i}]" for i in range(len(SCENES))) + f"amix=inputs={len(SCENES)}:normalize=0[a]"
run([*mix_in, "-filter_complex", amix, "-map", "[a]", "-t", f"{t:.2f}", "-c:a", "aac", "-b:a", "160k", os.path.join(OUT, "voice.m4a")])
yt = os.path.join(YT, f"{NAME}-youtube.mp4")
run(["-i", os.path.join(OUT, "video.mp4"), "-i", os.path.join(OUT, "voice.m4a"), "-map", "0:v", "-map", "1:a",
     "-c", "copy", "-movflags", "+faststart", yt])


def ts(x):
    return f"{int(x // 3600):02}:{int(x % 3600 // 60):02}:{x % 60:06.3f}".replace(".", ",")


def chunks(text, start, end, width=70):
    """A line in caption-sized pieces, each timed by its share of the characters."""
    out, cur = [], []
    for w in text.split():
        cur.append(w); s = " ".join(cur)
        if len(s) > width or (w.endswith((".", "?", ":")) and len(s) > 25):
            out.append(s); cur = []
    if cur:
        out.append(" ".join(cur))
    total, at, res = sum(len(c) for c in out), start, []
    for c in out:
        span = (end - start) * len(c) / total; res.append((at, at + span, c)); at += span
    return res


srt = os.path.join(YT, f"{NAME}-youtube.en.srt")
with open(srt, "w", encoding="utf-8") as f:
    k = 0
    for start, end, text in cues:
        for a, b, c in chunks(text, start, end):
            k += 1; f.write(f"{k}\n{ts(a)} --> {ts(b)}\n{c}\n\n")

clip, sec, vf = THUMB
run(["-ss", str(sec), "-i", os.path.join(S, clip + ".ts"), "-frames:v", "1", "-update", "1", "-vf", vf,
     os.path.join(YT, "thumbnail.png")])

if args.burn:
    shutil.copy(srt, os.path.join(OUT, "captions.srt"))
    style = "FontName=Segoe UI,FontSize=22,PrimaryColour=&H00FFFFFF,BorderStyle=4,BackColour=&H99000000,Outline=1,Shadow=0,MarginV=36"
    os.chdir(OUT)  # the subtitles filter takes a plain relative path most reliably
    run(["-i", "video.mp4", "-i", "voice.m4a", "-vf", f"subtitles=captions.srt:force_style='{style}'",
         "-map", "0:v", "-map", "1:a", *ENC, "-c:a", "copy", "-movflags", "+faststart",
         os.path.join(HERE, f"{NAME}-captioned.mp4")])
print(f"built: {yt} ({t:.0f}s) + {srt}")
