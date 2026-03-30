import json
import os
import shutil
import subprocess
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from src.core.config import config
from src.core.file_utils import UPLOAD_BASE_DIR
from src.core.logger import logger

MERGED_WITNESS_VIDEO_DIR = UPLOAD_BASE_DIR / "merged_witness_videos"


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def resolve_local_video_path(video_path: str) -> Path:
    path = Path(video_path)
    if path.is_absolute():
        return path.resolve()
    return (_project_root() / path).resolve()


def delete_file_if_exists(file_path: str | Path | None) -> bool:
    if not file_path:
        return False
    path = Path(file_path)
    try:
        if path.exists():
            path.unlink()
            logger.info("Deleted file at %s", path)
            return True
    except Exception as exc:
        logger.warning("Failed to delete file at %s: %s", path, exc)
    return False


def _estimate_merge_required_bytes(video_paths: List[Path]) -> int:
    source_total = sum(path.stat().st_size for path in video_paths if path.exists())
    return max(int(source_total * 1.35), 2 * 1024 * 1024 * 1024)


def _ensure_sufficient_disk_space(video_paths: List[Path], working_dir: Path, *, log_label: str) -> None:
    required_bytes = _estimate_merge_required_bytes(video_paths)
    usage = shutil.disk_usage(working_dir)
    free_bytes = usage.free

    logger.info(
        "Disk space check for %s: required=%s bytes free=%s bytes working_dir=%s",
        log_label,
        required_bytes,
        free_bytes,
        working_dir,
    )

    if free_bytes < required_bytes:
        required_gb = required_bytes / (1024 ** 3)
        free_gb = free_bytes / (1024 ** 3)
        raise RuntimeError(
            f"Not enough disk space to generate complete video for {log_label}. "
            f"Required about {required_gb:.2f} GB but only {free_gb:.2f} GB is available."
        )


def _find_ffmpeg_binary() -> str:
    for path in [
        "/usr/bin/ffmpeg",
        "/usr/local/bin/ffmpeg",
        "/bin/ffmpeg",
        "/opt/bin/ffmpeg",
    ]:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path

    discovered = shutil.which("ffmpeg")
    if discovered:
        return discovered

    raise RuntimeError("FFmpeg not found. Install it before generating merged videos.")


def _find_ffprobe_binary() -> str:
    configured = getattr(config, "RESOLVED_FFPROBE_PATH", None)
    if configured:
        return configured

    for path in [
        "/usr/bin/ffprobe",
        "/usr/local/bin/ffprobe",
        "/bin/ffprobe",
        "/opt/bin/ffprobe",
    ]:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path

    discovered = shutil.which("ffprobe")
    if discovered:
        return discovered

    raise RuntimeError("FFprobe not found. Install it before generating merged videos.")


def build_witness_merged_video_output_path(witness_id: int, job_no: int) -> Path:
    MERGED_WITNESS_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    suffix = uuid.uuid4().hex[:8]
    return MERGED_WITNESS_VIDEO_DIR / f"witness_{witness_id}_job_{job_no}_{timestamp}_{suffix}.mp4"


def _probe_video_info(ffprobe_path: str, file_path: Path) -> dict:
    result = subprocess.run(
        [
            ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-show_format",
            str(file_path),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return json.loads(result.stdout or "{}")


def _probe_video_profile(ffprobe_path: str, file_path: Path) -> Tuple[int, int, bool]:
    info = _probe_video_info(ffprobe_path, file_path)
    streams = info.get("streams", [])

    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    if not video_stream:
        raise RuntimeError(f"No video stream found in {file_path}")

    width = int(video_stream.get("width") or 0)
    height = int(video_stream.get("height") or 0)

    if width <= 0 or height <= 0:
        raise RuntimeError(f"Invalid video dimensions detected for {file_path}")

    has_audio = any(stream.get("codec_type") == "audio" for stream in streams)

    if width % 2:
        width += 1
    if height % 2:
        height += 1

    return width, height, has_audio


def _probe_duration_seconds(ffprobe_path: str, file_path: Path) -> float:
    result = subprocess.run(
        [
            ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            str(file_path),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    info = json.loads(result.stdout or "{}")
    fmt = info.get("format", {})
    return float(fmt.get("duration", 0) or 0)


def _probe_concat_profile(ffprobe_path: str, file_path: Path) -> Dict[str, object]:
    info = _probe_video_info(ffprobe_path, file_path)
    streams = info.get("streams", [])

    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)

    if not video_stream:
        raise RuntimeError(f"No video stream found in {file_path}")

    def _fps_value(stream: dict) -> float:
        raw = stream.get("avg_frame_rate") or stream.get("r_frame_rate") or "0/1"
        try:
            num_str, den_str = str(raw).split("/", 1)
            num = float(num_str)
            den = float(den_str)
            return 0.0 if den == 0 else round(num / den, 3)
        except Exception:
            return 0.0

    return {
        "video_codec": video_stream.get("codec_name"),
        "pixel_format": video_stream.get("pix_fmt"),
        "width": int(video_stream.get("width") or 0),
        "height": int(video_stream.get("height") or 0),
        "fps": _fps_value(video_stream),
        "video_time_base": video_stream.get("time_base"),
        "has_audio": audio_stream is not None,
        "audio_codec": audio_stream.get("codec_name") if audio_stream else None,
        "sample_rate": str(audio_stream.get("sample_rate")) if audio_stream else None,
        "channels": int(audio_stream.get("channels") or 0) if audio_stream else 0,
    }


def _videos_already_compatible(ffprobe_path: str, video_paths: List[Path]) -> bool:
    if not video_paths:
        return False

    try:
        profiles = [_probe_concat_profile(ffprobe_path, path) for path in video_paths]
    except Exception as exc:
        logger.info("Compatibility probe failed; falling back to normalization: %s", exc)
        return False

    baseline = profiles[0]
    baseline_path = str(video_paths[0])

    IMPORTANT_KEYS = [
        "video_codec",
        "pixel_format",
        "width",
        "height",
        "fps",
        "has_audio",
        "audio_codec",
        "sample_rate",
        "channels",
    ]

    for index, profile in enumerate(profiles[1:], start=1):
        mismatched_keys = [key for key in IMPORTANT_KEYS if baseline.get(key) != profile.get(key)]
        if mismatched_keys:
            logger.info(
                "Normalization required for %s because it differs from baseline %s. mismatched_fields=%s baseline=%s current=%s",
                video_paths[index],
                baseline_path,
                mismatched_keys,
                baseline,
                profile,
            )
            return False

    logger.info("All source videos already share same concat profile for fast-path merge")
    return True


def _merge_compatible_videos(
    ffmpeg_path: str,
    ffprobe_path: str,
    video_paths: List[Path],
    output_path: Path,
    *,
    log_label: str,
    timeout_seconds: int,
) -> Path:
    working_dir = Path(tempfile.gettempdir()) / f"merge_fast_{uuid.uuid4().hex}"
    working_dir.mkdir(parents=True, exist_ok=True)
    concat_file = working_dir / "concat_list.txt"

    try:
        with open(concat_file, "w", encoding="utf-8") as handle:
            for path in video_paths:
                escaped_path = str(path).replace("'", "'\\''")
                handle.write(f"file '{escaped_path}'\n")

        source_duration_total = sum(_probe_duration_seconds(ffprobe_path, path) for path in video_paths)

        subprocess.run(
            [
                ffmpeg_path,
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-fflags", "+genpts",
                "-i", str(concat_file),
                "-c", "copy",
                "-movflags", "+faststart",
                "-max_muxing_queue_size", "4096",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout_seconds,
        )

        merged_duration_seconds = _probe_duration_seconds(ffprobe_path, output_path)

        logger.info(
            "Fast-path merged %s video(s) for %s into %s (source_duration=%.2fs, merged_duration=%.2fs)",
            len(video_paths),
            log_label,
            output_path,
            source_duration_total,
            merged_duration_seconds,
        )

        return output_path
    finally:
        if working_dir.exists():
            shutil.rmtree(working_dir, ignore_errors=True)


def _normalize_clip_for_concat(
    ffmpeg_path: str,
    ffprobe_path: str,
    source_path: Path,
    normalized_path: Path,
    *,
    target_width: int,
    target_height: int,
    timeout_seconds: int,
) -> Path:
    _, _, has_audio = _probe_video_profile(ffprobe_path, source_path)

    scale_filter = (
        "scale="
        f"w='if(gt(a,{target_width}/{target_height}),min({target_width},iw),-2)':"
        f"h='if(gt(a,{target_width}/{target_height}),-2,min({target_height},ih))'"
    )

    filter_chain = (
        f"{scale_filter},"
        f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:color=black,"
        "setsar=1,setpts=PTS-STARTPTS,fps=30,format=yuv420p"
    )

    command = [
        ffmpeg_path,
        "-y",
        "-i", str(source_path),
    ]

    if not has_audio:
        command.extend([
            "-f", "lavfi",
            "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
        ])

    command.extend([
        "-threads", "0",
        "-vf", filter_chain,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-vsync", "cfr",
        "-c:a", "aac",
        "-b:a", "128k",
        "-ar", "48000",
        "-ac", "2",
        "-af", "aresample=async=1:first_pts=0",
    ])

    if not has_audio:
        command.extend(["-shortest"])

    command.extend([
        "-movflags", "+faststart",
        str(normalized_path),
    ])

    subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=True,
        timeout=timeout_seconds,
    )

    logger.info("Normalized clip for merge: %s -> %s (has_audio=%s)", source_path, normalized_path, has_audio)
    return normalized_path


def merge_video_files_ffmpeg(
    video_paths: Iterable[str],
    output_path: Path,
    *,
    log_label: str,
    normalize_timeout_seconds: int = 7200,
    concat_timeout_seconds: int = 7200,
) -> Path:
    valid_paths: List[Path] = []

    for raw_path in video_paths:
        if not raw_path:
            continue
        resolved = resolve_local_video_path(str(raw_path))
        if resolved.exists():
            valid_paths.append(resolved)
        else:
            logger.warning("Skipping missing merge source for %s: %s", log_label, resolved)

    if not valid_paths:
        raise ValueError(f"No valid source videos found for {log_label}")

    ffmpeg_path = _find_ffmpeg_binary()
    ffprobe_path = _find_ffprobe_binary()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    _ensure_sufficient_disk_space(valid_paths, Path(tempfile.gettempdir()), log_label=log_label)

    if len(valid_paths) == 1:
        shutil.copy2(valid_paths[0], output_path)
        logger.info("Only one source video for %s. Copied directly to %s", log_label, output_path)
        return output_path

    if _videos_already_compatible(ffprobe_path, valid_paths):
        try:
            return _merge_compatible_videos(
                ffmpeg_path,
                ffprobe_path,
                valid_paths,
                output_path,
                log_label=log_label,
                timeout_seconds=concat_timeout_seconds,
            )
        except subprocess.CalledProcessError as exc:
            logger.warning(
                "Fast-path concat failed for %s; falling back to normalization: %s",
                log_label,
                exc.stderr,
            )
        except Exception as exc:
            logger.warning(
                "Fast-path concat failed for %s; falling back to normalization: %s",
                log_label,
                exc,
            )

    target_width, target_height, _ = _probe_video_profile(ffprobe_path, valid_paths[0])

    normalized_dir = Path(tempfile.gettempdir()) / f"merge_normalized_{uuid.uuid4().hex}"
    normalized_dir.mkdir(parents=True, exist_ok=True)
    concat_file = normalized_dir / "concat_list.txt"

    try:
        normalized_paths: List[Path] = []

        for index, source_path in enumerate(valid_paths, start=1):
            normalized_path = normalized_dir / f"clip_{index:03d}.mp4"
            _normalize_clip_for_concat(
                ffmpeg_path,
                ffprobe_path,
                source_path,
                normalized_path,
                target_width=target_width,
                target_height=target_height,
                timeout_seconds=normalize_timeout_seconds,
            )
            normalized_paths.append(normalized_path)

        with open(concat_file, "w", encoding="utf-8") as handle:
            for path in normalized_paths:
                escaped_path = str(path).replace("'", "'\\''")
                handle.write(f"file '{escaped_path}'\n")

        source_duration_total = sum(_probe_duration_seconds(ffprobe_path, path) for path in valid_paths)

        subprocess.run(
            [
                ffmpeg_path,
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-fflags", "+genpts",
                "-i", str(concat_file),
                "-c", "copy",
                "-movflags", "+faststart",
                "-max_muxing_queue_size", "4096",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=concat_timeout_seconds,
        )

        merged_duration_seconds = _probe_duration_seconds(ffprobe_path, output_path)

        logger.info(
            "Merged %s normalized video(s) for %s into %s (source_duration=%.2fs, merged_duration=%.2fs)",
            len(normalized_paths),
            log_label,
            output_path,
            source_duration_total,
            merged_duration_seconds,
        )

        if abs(merged_duration_seconds - source_duration_total) > 2.0:
            logger.warning(
                "Merged duration differs from source total for %s by %.2fs",
                log_label,
                abs(merged_duration_seconds - source_duration_total),
            )

        return output_path

    except subprocess.CalledProcessError as exc:
        logger.error("FFmpeg merge failed for %s: %s", log_label, exc.stderr)
        raise RuntimeError(exc.stderr or f"FFmpeg merge failed for {log_label}") from exc

    finally:
        if normalized_dir.exists():
            shutil.rmtree(normalized_dir, ignore_errors=True)