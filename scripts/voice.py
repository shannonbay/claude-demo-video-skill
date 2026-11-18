"""Voices lines.txt into voice/line<N>.mp3 with Microsoft's neural voices (edge-tts).

    python voice.py                         # every line, the default voice
    python voice.py --voice en-AU-WilliamNeural
    python voice.py --only 3                # just line 3

lines.txt holds the caption text, one line per scene. SAY rewrites it for the voice only
(how a symbol or name should be spoken); the captions keep the original.
Another TTS or a real recording: save one file per line as voice/line<N>.mp3, then run build.py.
"""
import argparse, os, subprocess, sys

HERE = os.getcwd()
SAY = {"#92": "ninety-two", "CI": "C I"}  # edit per video

p = argparse.ArgumentParser()
p.add_argument("--voice", default="en-US-AndrewNeural")
p.add_argument("--rate", default="+4%")
p.add_argument("--only", type=int, help="voice only this line (1-based)")
a = p.parse_args()

os.makedirs(os.path.join(HERE, "voice"), exist_ok=True)
lines = [l.strip() for l in open(os.path.join(HERE, "lines.txt"), encoding="utf-8") if l.strip()]
for i, line in enumerate(lines, 1):
    if a.only and i != a.only:
        continue
    for k, v in SAY.items():
        line = line.replace(k, v)
    out = os.path.join(HERE, "voice", f"line{i}.mp3")
    subprocess.run([sys.executable, "-m", "edge_tts", "--voice", a.voice, f"--rate={a.rate}", "--text", line,
                    "--write-media", out], check=True)
    print("voiced", out)
