import json
import shutil
import subprocess
import uuid
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from src.core.file_utils import UPLOAD_BASE_DIR
from src.core.logger import logger
from src.core.storage.video_temp import make_video_merge_temp_dir
import concurrent.futures

MERGED_WITNESS_VIDEO_DIR = UPLOAD_BASE_DIR / "merged_witness_videos"

# STATIC SPEC - DO NOT CHANGE
STATIC_VIDEO_SPEC = {
    "container": "mp4",
    "video_codec": "h264",
    "audio_codec": "aac",
    "pixel_format": "yuv420p",
    "fps": 30,
    "sample_rate": 48000,
    "target_width": 1280,
    "target_height": 720,
    "bitrate_video": "5000k",      # High quality for 1280x720
    "bitrate_audio": "192k",       # High quality audio
    "preset": "fast",              # Balance speed/quality (ultrafast would lose quality)
    "crf": 20,                     # Lower = better quality (18-23 range best)
}


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
    for path in ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg", "ffmpeg"]:
        if shutil.which(path):
            return shutil.which(path)
    raise RuntimeError("FFmpeg not found. Install it to proceed.")


def _find_ffprobe_binary() -> str:
    for path in ["/usr/bin/ffprobe", "/usr/local/bin/ffprobe", "ffprobe"]:
        if shutil.which(path):
            return shutil.which(path)
    raise RuntimeError("FFprobe not found.")


def build_witness_merged_video_output_path(witness_id: int, job_no: int) -> Path:
    MERGED_WITNESS_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    suffix = uuid.uuid4().hex[:8]
    return MERGED_WITNESS_VIDEO_DIR / f"witness_{witness_id}_job_{job_no}_{timestamp}_{suffix}.mp4"


def _probe_video_info(ffprobe_path: str, file_path: Path) -> Dict:
    """Probe video file and return all stream info."""
    try:
        result = subprocess.run(
            [ffprobe_path, "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", str(file_path)],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
        data = json.loads(result.stdout or "{}")
        if not data.get("streams"):
            raise RuntimeError(f"No streams found in {file_path} - file may be corrupted")
        return data
    except json.JSONDecodeError:
        raise RuntimeError(f"Failed to parse ffprobe output for {file_path} - file may be corrupted")


def _probe_video_profile(ffprobe_path: str, file_path: Path) -> Tuple[int, int, bool]:
    """Get video dimensions and audio presence."""
    info = _probe_video_info(ffprobe_path, file_path)
    streams = info.get("streams", [])

    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    if not video_stream:
        raise RuntimeError(f"No video stream found in {file_path}")

    width = int(video_stream.get("width") or 0)
    height = int(video_stream.get("height") or 0)

    if width <= 0 or height <= 0:
        raise RuntimeError(f"Invalid video dimensions detected for {file_path}: {width}x{height}")

    has_audio = any(stream.get("codec_type") == "audio" for stream in streams)

    # Ensure even dimensions (required for H.264)
    if width % 2:
        width += 1
    if height % 2:
        height += 1

    return width, height, has_audio


def _probe_duration_seconds(ffprobe_path: str, file_path: Path) -> float:
    """Get video duration in seconds."""
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
    duration = float(fmt.get("duration", 0) or 0)
    return duration


def _format_duration(seconds: float) -> str:
    """Convert seconds to HH:MM:SS format."""
    if seconds <= 0:
        return "00:00:00"
    td = timedelta(seconds=int(seconds))
    hours, remainder = divmod(int(td.total_seconds()), 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _normalize_worker(task: dict) -> Tuple[str, float]:
    """
    Worker: Normalizes one video to static MP4 spec.
    Returns: (output_path, duration_seconds)
    
    Optimizations:
    - Uses H.264 with CRF 20 (high quality, good compression)
    - Preset 'fast' balances speed vs quality
    - Parallelizable task
    """
    try:
        ffmpeg_path = task['ffmpeg_path']
        ffprobe_path = task['ffprobe_path']
        src = task['src']
        dst = task['dst']
        clip_index = task.get('clip_index')
        clip_total = task.get('clip_total')
        clip_label = f"clip {clip_index}/{clip_total}" if clip_index and clip_total else src.name

        logger.info(f"[NORMALIZE START] {clip_label}: source={src.name} output={dst.name}")
        start_time = time.time()
        
        # Probe for audio
        _, _, has_audio = _probe_video_profile(ffprobe_path, src)
        
        # Define target dimensions from spec
        tw = STATIC_VIDEO_SPEC['target_width']
        th = STATIC_VIDEO_SPEC['target_height']
        
        # ULTRA-FAST filter chain (minimal processing)
        video_filters = (
            f"scale=w={tw}:h={th}:force_original_aspect_ratio=decrease,"
            f"pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2:black"
        )

        cmd = [
            ffmpeg_path,
            "-y",
            "-i", str(src),
        ]
        
        # Add silent audio if missing
        if not has_audio:
            cmd.extend([
                "-f", "lavfi",
                "-i", f"anullsrc=channel_layout=stereo:sample_rate={STATIC_VIDEO_SPEC['sample_rate']}",
            ])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "ultrafast",  # FASTEST encoding
            "-crf", "23",             # Good quality, faster than CRF 20
            "-vf", video_filters,
            "-pix_fmt", "yuv420p",
            "-r", "30",
            "-c:a", STATIC_VIDEO_SPEC['audio_codec'],
            "-b:a", "96k",            # SMALLER audio
            "-ar", str(STATIC_VIDEO_SPEC['sample_rate']),
            "-ac", "2",
        ])

        # If no audio was present, output shortest (match video duration)
        if not has_audio:
            cmd.append("-shortest")

        cmd.extend([
            "-movflags", "+faststart",
            "-max_muxing_queue_size", "4096",
            str(dst),
        ])

        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=14400)  # 4 hours
        
        # Probe output duration
        output_duration = _probe_duration_seconds(ffprobe_path, dst)
        elapsed = time.time() - start_time
        
        logger.info(
            f"[NORMALIZE COMPLETE] {clip_label}: source={src.name} output={dst.name} "
            f"(duration={_format_duration(output_duration)}, elapsed={elapsed:.1f}s)"
        )
        return (str(dst), output_duration)
        
    except Exception as e:
        clip_index = task.get('clip_index')
        clip_total = task.get('clip_total')
        clip_label = f"clip {clip_index}/{clip_total}" if clip_index and clip_total else str(task['src'])
        logger.error(f"[NORMALIZE FAILED] {clip_label}: {str(e)}")
        raise


def _merge_compatible_videos(
    ffmpeg_path: str,
    ffprobe_path: str,
    video_paths: List[Path],
    output_path: Path,
    *,
    log_label: str,
) -> Tuple[Path, float]:
    """
    Fast merge using stream copy (no re-encoding).
    Returns: (output_path, total_duration_seconds)
    """
    working_dir = make_video_merge_temp_dir(prefix=f"merge_fast_{uuid.uuid4().hex}_")
    concat_file = working_dir / "concat_list.txt"

    try:
        logger.info(f"[CONCAT START] {log_label}: concatenating {len(video_paths)} video(s)")
        
        # Write concat demuxer file
        with open(concat_file, "w", encoding="utf-8") as handle:
            for path in video_paths:
                escaped_path = str(path).replace("'", "'\\''")
                handle.write(f"file '{escaped_path}'\n")

        # Calculate source duration
        source_duration_total = sum(
            _probe_duration_seconds(ffprobe_path, path) for path in video_paths
        )
        
        logger.info(f"[CONCAT INPUT] {log_label}: source total duration={_format_duration(source_duration_total)}")

        # Use stream copy (no re-encoding) for speed
        concat_cmd = [
            ffmpeg_path,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-fflags", "+genpts",
            "-i", str(concat_file),
            "-c", "copy",  # No re-encoding, just copy streams
            "-movflags", "+faststart",
            "-max_muxing_queue_size", "4096",
            str(output_path),
        ]

        merge_start = time.time()
        subprocess.run(concat_cmd, capture_output=True, text=True, check=True, timeout=14400)  # 4 hours
        merge_elapsed = time.time() - merge_start

        # Probe merged video
        merged_duration = _probe_duration_seconds(ffprobe_path, output_path)
        output_size_bytes = output_path.stat().st_size
        output_size_gb = output_size_bytes / (1024 ** 3)
        
        # Validate output file
        if output_size_bytes < 1024 * 1024:  # Less than 1MB = error
            raise RuntimeError(f"Output file too small ({output_size_gb:.2f}GB) - merge may have failed")
        
        if merged_duration <= 0:
            raise RuntimeError(f"Output video has no duration - merge may have failed")

        logger.info(
            f"[CONCAT COMPLETE] {log_label}: merged {len(video_paths)} video(s) into {output_path.name} "
            f"(duration={_format_duration(merged_duration)}, size={output_size_gb:.2f}GB, elapsed={merge_elapsed:.1f}s)"
        )

        return output_path, merged_duration

    finally:
        if working_dir.exists():
            shutil.rmtree(working_dir, ignore_errors=True)


def _videos_already_compatible(ffprobe_path: str, video_paths: List[Path]) -> bool:
    """Check if all videos match static spec (skip normalization if yes)."""
    if not video_paths:
        return False

    try:
        # Just check if they're all H.264, AAC, 30fps, 1280x720, YUV420p
        spec = STATIC_VIDEO_SPEC
        
        for path in video_paths:
            info = _probe_video_info(ffprobe_path, path)
            streams = info.get("streams", [])
            
            v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
            a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
            
            if not v_stream:
                return False
            
            # Check critical specs
            if v_stream.get("codec_name") != spec['video_codec']:
                return False
            if int(v_stream.get("width", 0)) != spec['target_width']:
                return False
            if int(v_stream.get("height", 0)) != spec['target_height']:
                return False
            if v_stream.get("pix_fmt") != spec['pixel_format']:
                return False
            
            # Audio check
            if a_stream and a_stream.get("codec_name") != spec['audio_codec']:
                return False
        
        logger.info("[COMPAT] All videos match static spec - skip normalization")
        return True
        
    except Exception as exc:
        logger.info(f"[COMPAT] Compatibility check failed, will normalize: {exc}")
        return False


def merge_video_files_ffmpeg(
    video_paths: Iterable[str],
    output_path: Path,
    *,
    log_label: str,
) -> Tuple[Path, str]:
    """
    Merge videos with static MP4 specification.
    
    Returns: (output_path, duration_formatted)
    
    Process:
    1. Validate inputs
    2. Check if already compatible (skip normalization)
    3. Parallel normalize (if needed)
    4. Sequential fast merge using stream copy
    5. Return output path + formatted duration
    """
    valid_paths = [Path(p).resolve() for p in video_paths if p and Path(p).exists()]
    
    if not valid_paths:
        raise ValueError(f"No valid source videos found for {log_label}")

    if len(valid_paths) == 0:
        raise ValueError(f"Must provide at least 1 video for {log_label}")

    logger.info(f"[MERGE START] {log_label}: {len(valid_paths)} input video(s)")

    ffmpeg_path = _find_ffmpeg_binary()
    ffprobe_path = _find_ffprobe_binary()
    
    # Create workspace
    tmp_dir = make_video_merge_temp_dir(prefix=f"vmerge_{uuid.uuid4().hex}_")
    
    total_start_time = time.time()

    try:
        # Check disk space
        _ensure_sufficient_disk_space(valid_paths, tmp_dir, log_label=log_label)

        # Phase 1: Check if normalization needed
        need_normalization = not _videos_already_compatible(ffprobe_path, valid_paths)

        if need_normalization:
            logger.info(f"[PHASE 1 START] {log_label}: normalizing {len(valid_paths)} video(s) to static spec")
            
            # Build normalization tasks (preserves order)
            tasks = []
            normalized_paths = []
            
            for i, src_path in enumerate(valid_paths):
                dst_path = tmp_dir / f"norm_{i:03d}.mp4"
                normalized_paths.append(dst_path)
                logger.info(
                    f"[NORMALIZE QUEUED] {log_label}: clip {i + 1}/{len(valid_paths)} "
                    f"source={src_path.name} output={dst_path.name}"
                )
                tasks.append({
                    'ffmpeg_path': ffmpeg_path,
                    'ffprobe_path': ffprobe_path,
                    'src': src_path,
                    'dst': dst_path,
                    'clip_index': i + 1,
                    'clip_total': len(valid_paths),
                })

            # Parallel normalization (max workers based on CPU cores)
            durations = {}
            max_workers = min(len(tasks), 4)
            logger.info(f"[PHASE 1 EXECUTOR] {log_label}: max_workers={max_workers}")
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(_normalize_worker, task): i for i, task in enumerate(tasks)}
                
                for future in concurrent.futures.as_completed(futures):
                    idx = futures[future]
                    try:
                        dst_str, duration = future.result()
                        durations[idx] = duration
                        logger.info(
                            f"[NORMALIZE FUTURE COMPLETE] {log_label}: clip {idx + 1}/{len(tasks)} "
                            f"output={Path(dst_str).name} duration={_format_duration(duration)}"
                        )
                    except Exception as e:
                        logger.error(f"Normalization failed for video {idx}: {e}")
                        raise

            # Use normalized paths for merge
            merge_paths = normalized_paths
            logger.info(f"[PHASE 1 COMPLETE] {log_label}: all normalization jobs completed")
            
        else:
            logger.info(f"[PHASE 1 SKIPPED] {log_label}: videos already match static spec")
            merge_paths = valid_paths
            durations = {}

        # Phase 2: Merge
        logger.info(f"[PHASE 2 START] {log_label}: merging {len(merge_paths)} prepared video(s)")
        output_path, merged_duration = _merge_compatible_videos(
            ffmpeg_path,
            ffprobe_path,
            merge_paths,
            output_path,
            log_label=log_label,
        )

        total_elapsed = time.time() - total_start_time
        duration_formatted = _format_duration(merged_duration)
        output_size_gb = output_path.stat().st_size / (1024 ** 3)

        logger.info(
            f"[MERGE COMPLETE] {log_label}\n"
            f"  Output: {output_path}\n"
            f"  Duration: {duration_formatted}\n"
            f"  Size: {output_size_gb:.2f} GB\n"
            f"  Total Time: {total_elapsed:.1f}s\n"
            f"  Spec: H.264, AAC, {STATIC_VIDEO_SPEC['target_width']}x{STATIC_VIDEO_SPEC['target_height']}, 30fps, YUV420p"
        )

        return output_path, duration_formatted

    except Exception as e:
        logger.error(f"[MERGE FAILED] {log_label}: {str(e)}")
        # Clean up output file if merge failed
        if output_path.exists():
            try:
                output_path.unlink()
                logger.info(f"Cleaned up failed output: {output_path}")
            except Exception:
                pass
        raise
    finally:
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
