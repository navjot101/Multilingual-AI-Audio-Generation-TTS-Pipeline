import os
import logging
from gtts import gTTS

log = logging.getLogger(__name__)


def synthesize_segments(segments: list[dict], task_id: str, language: str) -> list[str]:
    paths = []
    for i, segment in enumerate(segments):
        tts = gTTS(text=segment["text"], lang=language, slow=False)
        path = os.path.join("/tmp", f"{task_id}_{i}.mp3")
        tts.save(path)
        log.debug("Synthesized segment %d to %s", i, path)
        paths.append(path)
    return paths
