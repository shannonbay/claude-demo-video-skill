---
name: demo-video
description: This skill should be used when the user asks to "record a demo", "make a demo video", "screen-record a workflow", "make a GIF of", "make a YouTube video of", "add a voiceover", "add TTS narration", "make captions/subtitles", or wants a walkthrough of a terminal + browser workflow turned into an MP4 with voice and an .srt, and/or a short highlights GIF. Covers window placement, native-resolution capture on Windows, finding moments with contact sheets, scene timing, edge-tts narration, YouTube captions and GIF size limits.
---

# Demo videos: record, cut, narrate, caption, GIF

Turns a real workflow on screen (a terminal, a browser, an app) into:
- a **YouTube cut**: MP4 with a TTS voiceover, no burned captions, plus an `.en.srt`;
- a **highlights GIF**: the key steps only, silent, no captions, small enough for a README;
- optionally a captioned MP4 (burned-in subtitles) for places without caption support.

Scripts in `scripts/` are templates: copy them into a folder for the video (outside any repo: recordings are hundreds of MB) and edit their config blocks. Needs ffmpeg (on PATH, or `FFMPEG`/`FFPROBE` env vars), Python 3, `pip install edge-tts` for the voice.

## 1. Plan with the person

- Agree the story as steps, and which steps are **theirs** (clicks, typing) vs. waiting. Write them the step list with what to press, so they can drive while recording.
- Pick the subject (an issue, a to-do) that shows something visible.
- Clear the stage: remove duplicates of what the demo creates, close personal tabs (open a **fresh browser window** with only the site), hide notifications. Mention anything noisy (update banners).
- Tell them anything they type to Claude while recording is on screen: keep it to "next" / "done".

## 2. Frame both windows on one capture box

Put every window the demo uses at **exactly the same rectangle** (1920×1080 is a good default) and record that box: whichever window is in front is the shot, so switching windows is the edit.

`scripts/rec.ps1 place -X <px> -Y <px>` does it on Windows. Things that bite:
- **DPI scaling**: coordinates from a non-DPI-aware process are scaled (125 % → a "1920" window is 1536 physical). `place` sets per-monitor DPI awareness (`SetThreadDpiAwarenessContext(-4)`) so everything is physical pixels. List monitors with `rec.ps1 monitors`.
- **Invisible borders**: Windows 10/11 windows have ~7 px invisible borders. Size by the DWM visible bounds (`DWMWA_EXTENDED_FRAME_BOUNDS`), not `GetWindowRect`; `place` measures and corrects.
- Grab one frame and **look at it** before recording (Read the PNG).

## 3. Record

`scripts/rec.ps1 start <name>` / `stop` / `mark <text>`. Notes:
- **gdigrab isn't DPI-aware** and captures a scaled-down desktop on a scaled monitor (and `__COMPAT_LAYER=HighDpiAware` doesn't fix it). Use **Desktop Duplication** (`ddagrab`), which is native pixels per monitor. Its `offset_x/y` are relative to that monitor.
- A monitor on a **second GPU** (laptop + external display) isn't on adapter 0: `-init_hw_device d3d11va=dx:<adapter> -filter_hw_device dx` with `ddagrab=output_idx=<n>` in `-filter_complex`. `rec.ps1 start` takes `-Adapter` and `-Output`; try 0/1 if "Failed to enumerate DXGI output".
- Write **MPEG-TS** (`-f mpegts`): the process is killed to stop, and MP4/MKV lose their header that way.
- Split into clips at natural breaks (setup / the person's input / one long take of the waiting). One long take of a slow process is fine; the edit speeds up the waits.
- While the person drives, relay what each background step reports and what to press next, briefly.

## 4. Find the moments

Don't scrub video. Make timestamped contact sheets and Read them:
`python scripts/sheets.py <clip.ts> --every 10` (whole clip), then `--from 170 --to 236 --every 2 --crop 900:560:1020:0` around each click to find the exact seconds a proposal appears, a button is pressed, a page loads.
Write down: (clip, start, end) for each step, and which spans are waits.

## 5. Narration

`lines.txt`: one line per **scene** (a step of the story), written as caption text. Spoken English, short sentences, says why not just what. `voice.py` has a `SAY` map for how symbols are spoken (`#92` → "ninety-two", `/goal-new` → "goal new", `CI` → "C I"); captions keep the original. Default voice `en-US-AndrewNeural` at +4 %; list voices with `python -m edge_tts --list-voices`. Re-voice one line with `--only N`.

## 6. Build

`scripts/build.py`: `SCENES` is a list of scenes, each a list of segments `(clip, start, end, speed)`:
- the person's clicks at 1–2×; browser pages at 2–4×; machine work at 6–40× with a `▶▶ N×` badge (drawn when speed ≥ 3);
- a scene shorter than `LEAD + its line + TAIL` gets its last frame held (`tpad`), so the voice never overruns;
- outputs `youtube/<name>-youtube.mp4` (video + voice, `-c copy`), `youtube/<name>-youtube.en.srt` (each line split into ~70-char cues timed by character share), and a thumbnail.
- `--burn` also writes `<name>-captioned.mp4` with burned-in subtitles.

Aim for 1.5–3.5 min. If narration leaves long silences, speed up the scene rather than padding words.

## 7. GIF

A GIF is **not** the video at speed: it's the key steps only. `scripts/gif.py`: `HIGHLIGHTS` = `(clip, start, end, speed, crop)`, each 3–7 s, cropped (1280×720 window of the frame: the pane, the web page, a menu) and scaled to 960×540 at 8 fps, one palette (`palettegen stats_mode=diff`, `paletteuse dither=none diff_mode=rectangle`). No captions, no badges. Keep it under **10 MB** (GitHub's image limit) and under ~60 s. Check it by tiling each highlight's last frame and reading the image.

## 8. Hand-off

A `README.md` in the video folder: what the video shows, outputs table, what each source/script is, the recorder's frame and any capture quirks, and how to rebuild (re-voice → build → gif). Offer to remember the folder's location in memory.
