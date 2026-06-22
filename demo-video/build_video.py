"""Assemble the demo walkthrough video from screenshots, title cards, and voiceover.

Uses ffmpeg for everything — no heavy Python video libs needed.
Produces: demo-video/output/arad_quality_demo.mp4
"""

import json
import subprocess
import wave
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).parent
SCREENSHOTS = ROOT / "screenshots"
AUDIO = ROOT / "audio"
TITLE_CARDS = ROOT / "title_cards"
OUTPUT = ROOT / "output"

TITLE_CARDS.mkdir(exist_ok=True)
OUTPUT.mkdir(exist_ok=True)

W, H = 1920, 1080
BG_COLOR = (10, 10, 15)
TEXT_COLOR = (255, 255, 255)
SUB_COLOR = (148, 163, 184)

FFMPEG = r"C:\Users\Asus\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.1-full_build\bin\ffmpeg.exe"


def get_wav_duration(path: Path) -> float:
    with wave.open(str(path), "r") as w:
        return w.getnframes() / w.getframerate()


def create_title_card(scene: dict, out_path: Path):
    """Create a title card image using Pillow."""
    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    title = scene["title"]
    subtitle = scene.get("subtitle", "")

    try:
        font_title = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 72)
        font_sub = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 32)
    except OSError:
        font_title = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 72)
        font_sub = ImageFont.truetype(r"C:\Windows\Fonts\arial.ttf", 32)

    bbox = draw.textbbox((0, 0), title, font=font_title)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((W - tw) / 2, H / 2 - 60), title, fill=TEXT_COLOR, font=font_title)

    if subtitle:
        bbox2 = draw.textbbox((0, 0), subtitle, font=font_sub)
        sw = bbox2[2] - bbox2[0]
        draw.text(((W - sw) / 2, H / 2 + 40), subtitle, fill=SUB_COLOR, font=font_sub)

    img.save(str(out_path))


def run_ffmpeg(cmd: list[str]) -> tuple[int, str]:
    """Run ffmpeg and return (returncode, stderr)."""
    result = subprocess.run(cmd, capture_output=True)
    stderr = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
    return result.returncode, stderr


def build_scene_clip(scene: dict, idx: int) -> Path | None:
    """Create a video clip for one scene (image + audio)."""
    scene_id = scene["id"]
    audio_path = AUDIO / f"{scene_id}.wav"
    clip_path = OUTPUT / f"clip_{idx:02d}_{scene_id}.mp4"

    if not audio_path.exists():
        print(f"  SKIP {scene_id}: no audio")
        return None

    audio_dur = get_wav_duration(audio_path)
    duration = max(audio_dur + 1.5, scene.get("duration", 5))

    if scene["type"] == "title_card":
        img_path = TITLE_CARDS / f"{scene_id}.png"
        create_title_card(scene, img_path)
        if not img_path.exists():
            print(f"  SKIP {scene_id}: title card failed")
            return None
    else:
        img_path = SCREENSHOTS / f"{scene_id}.png"
        if not img_path.exists():
            print(f"  SKIP {scene_id}: no screenshot")
            return None

    fade_out_start = max(duration - 0.8, 0.8)
    vf = (
        f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
        f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x0a0a0f,"
        f"format=yuv420p,"
        f"fade=t=in:st=0:d=0.8,"
        f"fade=t=out:st={fade_out_start:.2f}:d=0.8"
    )

    cmd = [
        FFMPEG, "-y",
        "-loop", "1", "-i", str(img_path),
        "-i", str(audio_path),
        "-c:v", "libx264", "-tune", "stillimage", "-preset", "medium", "-crf", "22",
        "-c:a", "aac", "-b:a", "192k",
        "-vf", vf,
        "-t", f"{duration:.2f}",
        "-pix_fmt", "yuv420p",
        "-shortest",
        str(clip_path),
    ]
    rc, stderr = run_ffmpeg(cmd)
    if rc != 0:
        print(f"  ERROR {scene_id}: {stderr[-300:]}")
        return None

    return clip_path


def concat_clips(clip_paths: list[Path], out_path: Path):
    """Concatenate all scene clips into the final video."""
    list_file = OUTPUT / "concat_list.txt"
    with open(list_file, "w") as f:
        for p in clip_paths:
            f.write(f"file '{p.name}'\n")

    cmd = [
        FFMPEG, "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file),
        "-c:v", "libx264", "-crf", "20", "-preset", "medium",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(out_path),
    ]
    rc, stderr = run_ffmpeg(cmd)
    if rc != 0:
        print(f"CONCAT ERROR: {stderr[-500:]}")
        return False
    return True


def main():
    scenes = json.loads((ROOT / "scenes.json").read_text())

    print(f"Building {len(scenes)} scene clips...\n")
    clip_paths = []
    for idx, scene in enumerate(scenes):
        print(f"  [{idx+1}/{len(scenes)}] {scene['id']}...")
        clip = build_scene_clip(scene, idx)
        if clip:
            clip_paths.append(clip)
            size_kb = clip.stat().st_size / 1024
            print(f"    -> {clip.name} ({size_kb:.0f} KB)")
        else:
            print(f"    -> SKIPPED")

    if not clip_paths:
        print("\nNo clips generated.")
        return

    final_path = OUTPUT / "arad_quality_demo.mp4"
    print(f"\nConcatenating {len(clip_paths)} clips into final video...")
    if concat_clips(clip_paths, final_path):
        size_mb = final_path.stat().st_size / (1024 * 1024)
        print(f"\nDONE: {final_path}")
        print(f"Size: {size_mb:.1f} MB")
    else:
        print("\nFailed to concatenate clips.")


if __name__ == "__main__":
    main()
