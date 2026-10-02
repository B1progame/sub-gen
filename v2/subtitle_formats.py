"""Subtitle serialization helpers for standalone files and selectable tracks."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def stamp_srt(seconds: float) -> str:
    millis = max(0, round(float(seconds) * 1000))
    hours, millis = divmod(millis, 3_600_000)
    minutes, millis = divmod(millis, 60_000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def stamp_vtt(seconds: float) -> str:
    return stamp_srt(seconds).replace(",", ".")


def write_srt(captions: list[dict[str, Any]], path: Path) -> None:
    blocks = [
        f"{index}\n{stamp_srt(item['start'])} --> {stamp_srt(item['end'])}\n{str(item.get('text', '')).strip()}"
        for index, item in enumerate(captions, 1)
    ]
    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8-sig")


def write_vtt(captions: list[dict[str, Any]], path: Path) -> None:
    blocks = [
        f"{stamp_vtt(item['start'])} --> {stamp_vtt(item['end'])}\n{str(item.get('text', '')).strip()}"
        for item in captions
    ]
    path.write_text("WEBVTT\n\n" + "\n\n".join(blocks) + "\n", encoding="utf-8")


def ass_stamp(seconds: float) -> str:
    centiseconds = max(0, round(float(seconds) * 100))
    hours, centiseconds = divmod(centiseconds, 360_000)
    minutes, centiseconds = divmod(centiseconds, 6_000)
    secs, centiseconds = divmod(centiseconds, 100)
    return f"{hours}:{minutes:02}:{secs:02}.{centiseconds:02}"


def ass_color(value: str, alpha: int = 0) -> str:
    raw = str(value or "#ffffff").lstrip("#")
    if len(raw) != 6 or any(char not in "0123456789abcdefABCDEF" for char in raw):
        raw = "ffffff"
    return f"&H{max(0, min(255, alpha)):02X}{raw[4:6]}{raw[2:4]}{raw[0:2]}&".upper()


def _escape_ass(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}").replace("\n", "\\N")


def _karaoke_text(caption: dict[str, Any], base_color: str, highlight_color: str, transform: str = "none", emphasis: str = "color") -> str:
    words = caption.get("words") or []
    if not words:
        return _escape_ass(str(caption.get("text", "")))
    output: list[str] = []
    for word in words:
        start = float(word.get("start", caption["start"]))
        end = float(word.get("end", start + 0.1))
        duration = max(1, round((end - start) * 100))
        raw_token = str(word.get("word", word.get("text", "")))
        if transform == "uppercase": raw_token = raw_token.upper()
        elif transform == "lowercase": raw_token = raw_token.lower()
        token = _escape_ass(raw_token.strip())
        accent_tags = {
            "color": f"\\1c{highlight_color}",
            "color-scale": f"\\1c{highlight_color}\\fscx112\\fscy112\\t(0,{max(1, duration // 2)},\\fscx100\\fscy100)",
            "marker": f"\\3c{highlight_color}\\bord2",
            "underline": "\\u1",
            "outline": f"\\3c{highlight_color}\\bord2",
            "capsule": f"\\3c{highlight_color}\\bord3",
            "italic": "\\i1",
            "tracking": "\\fsp2",
            "none": f"\\1c{base_color}",
        }.get(emphasis, f"\\1c{highlight_color}")
        reset_tags = f"\\1c{base_color}\\3c{base_color}\\bord0\\u0\\i0\\fsp0\\fscx100\\fscy100"
        output.append(f"{{\\k{duration}{accent_tags}}}{token}{{{reset_tags}}}")
    return " ".join(output)


def write_ass(captions: list[dict[str, Any]], style: dict[str, Any], path: Path) -> None:
    font = str(style.get("font", "Arial")).replace(",", " ")[:64]
    size = max(12, min(160, int(float(style.get("size", 42)))))
    weight = -1 if int(style.get("weight", 600)) >= 700 else 0
    primary = ass_color(str(style.get("color", "#ffffff")))
    accent = ass_color(str(style.get("highlight", "#ffbf69")))
    outline_color = ass_color(str(style.get("outlineColor", "#10131b")))
    opacity = max(0, min(100, int(float(style.get("opacity", 72)))))
    panel = ass_color(str(style.get("bg", "#111827")), round((100 - opacity) * 255 / 100))
    outline = max(0, min(10, float(style.get("outlineWidth", 2))))
    shadow = max(0, min(24, float(style.get("shadow", 6)))) / 2
    radius = max(0, min(32, float(style.get("radius", 8))))
    border_style = 3 if opacity > 0 else 1
    alignment_value = style.get("alignment", 2)
    alignment = {"left": 1, "center": 2, "right": 3}.get(str(alignment_value).lower(), 2)
    rect = style.get("rect") if isinstance(style.get("rect"), dict) else {}
    x = round(max(0, min(1, float(rect.get("x", 0.14)) + float(rect.get("w", 0.72)) / 2)) * 1920)
    y = round(max(0, min(1, float(rect.get("y", 0.74)) + float(rect.get("h", 0.16)) / 2)) * 1080)
    header = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1920\nPlayResY: 1080\nWrapStyle: 2\n\n"
        "[V4+ Styles]\n"
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\n"
        f"Style: Caption,{font},{size},{primary},{accent},{outline_color},{panel},{weight},0,0,0,100,100,{max(-2, min(8, float(style.get('letterSpacing', 0))))},0,{border_style},{outline},{shadow},{alignment},60,60,54,1\n\n"
        "[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"
    )
    events: list[str] = []
    effect = str(style.get("effect", "static"))
    speed = {"snappy": 90, "balanced": 150, "gentle": 240}.get(str(style.get("speed", "balanced")), 150)
    for caption in captions:
        start, end = float(caption["start"]), float(caption["end"])
        transform = str(style.get("transform", "none"))
        display_text = str(caption.get("text", ""))
        if transform == "uppercase": display_text = display_text.upper()
        elif transform == "lowercase": display_text = display_text.lower()
        text = _escape_ass(display_text)
        position_tag = f"{{\\an{alignment + 3}\\pos({x},{y})}}"
        text = position_tag + text
        words = caption.get("words") or []
        emphasis = str(style.get("emphasis", "color"))
        display = _karaoke_text(caption, primary, accent, transform, emphasis) if words and emphasis != "none" else _escape_ass(display_text)
        text = position_tag + display
        if effect == "pop":
            text = position_tag + "{\\fscx80\\fscy80\\t(0," + str(speed) + ",\\fscx100\\fscy100)}" + display
        elif effect == "fade":
            text = position_tag + "{\\fad(" + str(speed) + ",100)}" + display
        elif effect == "slide":
            text = "{\\an" + str(alignment + 3) + "\\move(" + str(x) + "," + str(y + 34) + "," + str(x) + "," + str(y) + ",0," + str(speed) + ")}" + display
        elif effect == "bounce":
            text = position_tag + "{\\fscx70\\fscy70\\t(0," + str(speed) + ",\\fscx105\\fscy105)\\t(" + str(speed) + "," + str(speed * 2) + ",\\fscx100\\fscy100)}" + display
        elif effect == "zoom":
            text = position_tag + "{\\fscx70\\fscy70\\blur4\\t(0," + str(speed) + ",\\fscx100\\fscy100\\blur0)}" + display
        elif effect == "blur":
            text = position_tag + "{\\blur10\\t(0," + str(speed) + ",\\blur0)}" + display
        elif effect == "wipe":
            text = position_tag + "{\\clip(0,0,1,1080)\\t(0," + str(speed) + ",\\clip(0,0,1920,1080))}" + display
        events.append(f"Dialogue: 0,{ass_stamp(start)},{ass_stamp(end)},Caption,,0,0,0,,{text}")
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8-sig")
