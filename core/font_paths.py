import os
from pathlib import Path


def overlay_font_candidates(language: str | None = None, env_path: str | None = None):
    """Return ordered Unicode-capable font candidates for the requested language."""
    root = Path(__file__).resolve().parent.parent
    lang = (language or "en").strip().lower()
    candidates = []
    if env_path:
        candidates.append(env_path)

    if lang.startswith("bn"):
        candidates += [
            str(root / "assets/fonts/NotoSansBengali-Regular.ttf"),
            "C:/Windows/Fonts/Nirmala.ttf",
            "C:/Windows/Fonts/kalpurush.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf",
        ]
    elif lang.startswith("hi"):
        candidates += [
            str(root / "assets/fonts/NotoSansDevanagari-Regular.ttf"),
            "C:/Windows/Fonts/Mangal.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        ]
    elif lang.startswith("ar"):
        candidates += [
            str(root / "assets/fonts/NotoNaskhArabic-Regular.ttf"),
            "C:/Windows/Fonts/segoeui.ttf",
            "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
        ]
    elif lang.startswith("ru"):
        candidates += [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    else:
        candidates += [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]

    seen = set()
    ordered = []
    for candidate in candidates:
        normalized = os.path.normpath(str(candidate))
        if normalized not in seen:
            seen.add(normalized)
            ordered.append(normalized)
    return ordered
