# demo-video: a Claude Code skill for demo videos

Teaches Claude Code to turn a real workflow on your screen (a terminal, a browser, an app) into:

- a **YouTube cut**: MP4 with a text-to-speech voiceover (Microsoft neural voices via edge-tts) and a separate `.en.srt` captions file;
- a **highlights GIF**: just the key steps, silent, cropped to where the action is, under GitHub's 10 MB limit;
- optionally an MP4 with burned-in captions.

You drive the workflow; Claude places the windows, records, finds the moments with timestamped contact sheets, writes the narration, speeds up the waits and builds the outputs.

## Install

```sh
git clone https://github.com/shannonbay/claude-demo-video-skill ~/.claude/skills/demo-video
```

Then ask Claude Code to "record a demo of …" or "make a GIF of …".

## Needs

- ffmpeg on `PATH` (or `FFMPEG` / `FFPROBE` env vars). Windows: `winget install Gyan.FFmpeg`
- Python 3, and `pip install edge-tts` for the voice
- The recorder (`scripts/rec.ps1`) is Windows-only (Desktop Duplication via ffmpeg's `ddagrab`); the rest runs anywhere ffmpeg does

## What's inside

| File | What |
|---|---|
| `SKILL.md` | The workflow Claude follows: plan → frame the windows → record → find moments → narrate → build → GIF |
| `scripts/rec.ps1` | `monitors`, `place` (windows exactly on the capture box, DPI- and invisible-border-aware), `grab`, `start`/`stop`/`mark` (native-resolution MPEG-TS) |
| `scripts/sheets.py` | Timestamped contact sheets of a clip, optionally cropped |
| `scripts/voice.py` | Voices `lines.txt`, one mp3 per scene, with a pronunciation map |
| `scripts/build.py` | Scenes of `(clip, start, end, speed)` → voiced MP4 + `.srt` + thumbnail (`--burn` for burned-in captions) |
| `scripts/gif.py` | Highlights `(clip, start, end, speed, crop)` → GIF |

## Lessons baked in

- `gdigrab` captures a scaled-down desktop on a monitor with display scaling; `ddagrab` gives native pixels, but a monitor on a second GPU needs `-init_hw_device d3d11va=dx:1`.
- Record MPEG-TS: stopping the recorder kills it, which leaves an MP4/MKV without its header.
- Windows 10/11 windows have invisible borders: size them by their DWM visible bounds.
- A GIF of the whole video is too long and too big: pick the key steps instead.

## License

MIT
