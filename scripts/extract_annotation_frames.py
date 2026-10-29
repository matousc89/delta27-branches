#!/usr/bin/env python3
"""Extract one representative frame from each Samsung Motion Photo."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

def run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def extract_motion_frame(source: Path, output: Path, video_offset: int) -> tuple[int, int]:
    with tempfile.NamedTemporaryFile(suffix=".mp4") as temporary_video:
        with source.open("rb") as input_file:
            input_file.seek(video_offset)
            shutil.copyfileobj(input_file, temporary_video)
            temporary_video.flush()

        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=nb_frames",
                "-of",
                "json",
                temporary_video.name,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        total_frames = int(json.loads(probe.stdout)["streams"][0]["nb_frames"])
        selected_frame = total_frames // 2

        run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-i",
                temporary_video.name,
                "-vf",
                f"select=eq(n\\,{selected_frame})",
                "-frames:v",
                "1",
                str(output),
            ]
        )
    return selected_frame, total_frames


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str | int]] = []

    for source in sorted(args.source_dir.glob("*.jpg")):
        data = source.read_bytes()
        ftyp_position = data.find(b"ftyp")
        output = args.output_dir / f"{source.stem}.png"

        # Static JPEGs cannot be used for mask propagation. Some source
        # directories also contain already annotated static copies, so skip
        # every file that has no embedded MP4 payload.
        if ftyp_position < 4:
            continue

        selected_frame, total_frames = extract_motion_frame(source, output, ftyp_position - 4)

        rows.append(
            {
                "annotation_file": output.name,
                "source_file": source.name,
                "source_type": "motion_photo",
                "selected_frame": selected_frame,
                "total_video_frames": total_frames,
            }
        )

    with (args.output_dir / "manifest.csv").open("w", newline="", encoding="utf-8") as manifest:
        writer = csv.DictWriter(manifest, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Extracted {len(rows)} annotation images into {args.output_dir}")


if __name__ == "__main__":
    main()
