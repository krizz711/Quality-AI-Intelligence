"""Generate Bella voiceover audio for each scene using Kokoro TTS."""

import json
import sys
from pathlib import Path

sys.path.insert(0, r"C:\dev\mcp-servers\kokoro-mcp-server")

from aparsoft_tts.core.engine import TTSEngine
from aparsoft_tts.config import TTSConfig

OUT = Path(__file__).parent / "audio"
OUT.mkdir(exist_ok=True)


def main():
    scenes = json.loads((Path(__file__).parent / "scenes.json").read_text())

    print("Loading Bella voice (af_bella)...")
    cfg = TTSConfig(voice="af_bella", speed=0.95)
    engine = TTSEngine(config=cfg)
    print("Engine ready.\n")

    for scene in scenes:
        text = scene["narration"]
        out_path = OUT / f"{scene['id']}.wav"
        print(f"  [{scene['id']}] Generating {len(text)} chars...")
        engine.generate(text=text, output_path=str(out_path), voice="af_bella")
        print(f"    -> {out_path.name}")

    print(f"\nDone — {len(scenes)} audio clips in {OUT}")


if __name__ == "__main__":
    main()
