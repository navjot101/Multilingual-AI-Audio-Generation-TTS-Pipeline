import re

SEGMENT_PATTERN = re.compile(
    r'\[SPEAKER:(\w+)\]\[EMOTION:(\w+)\]\s*(.+?)(?=\[SPEAKER:|\Z)',
    re.DOTALL,
)


def parse_script(text: str) -> list[dict]:
    segments = []
    for match in SEGMENT_PATTERN.finditer(text):
        segments.append({
            "speaker": match.group(1),
            "emotion": match.group(2),
            "text": match.group(3).strip(),
        })
    return segments
