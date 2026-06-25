import os
import logging
from pydub import AudioSegment

log = logging.getLogger(__name__)

SILENCE_MS = 300


def stitch_audio(segment_paths: list[str], task_id: str, shared_path: str) -> str:
    combined = AudioSegment.silent(duration=0)

    for i, path in enumerate(segment_paths):
        segment = AudioSegment.from_mp3(path)
        if i > 0:
            combined += AudioSegment.silent(duration=SILENCE_MS)
        combined += segment

    output_path = os.path.join(shared_path, f"{task_id}.wav")
    os.makedirs(shared_path, exist_ok=True)
    combined.export(output_path, format="wav")
    log.info("Exported stitched audio to %s (%d ms)", output_path, len(combined))

    for path in segment_paths:
        os.remove(path)
        log.debug("Cleaned up temp file %s", path)

    return output_path
