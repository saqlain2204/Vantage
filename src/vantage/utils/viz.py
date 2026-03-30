from __future__ import annotations

import os
import textwrap
from datetime import datetime
from typing import List

from PIL import Image, ImageDraw, ImageFont

from ..core.models import TraceStep

IMG_WIDTH = 660
MARGIN = 40
BOX_WIDTH = IMG_WIDTH - 2 * MARGIN
CONTENT_WRAP_WIDTH = 66
MAX_CONTENT_CHARS = 400
LINE_H = 17
HEADER_H = 22
BOX_PAD = 12
MIN_BOX_H = 60
ARROW_H = 32
TITLE_H = 48

_BG = (13, 17, 23)
_TITLE_BG = (22, 27, 34)
_BOX_BG = (22, 27, 34)
_TEXT_MAIN = (201, 209, 217)
_TEXT_DIM = (60, 72, 88)
_ARROW = (48, 58, 72)

_STEP_STYLE: dict[str, dict] = {
    "user":    {"outline": (31, 111, 235),  "label_c": (88, 166, 255),  "badge": "USER INPUT"},
    "thought": {"outline": (100, 110, 120), "label_c": (180, 190, 200), "badge": "LLM THINKING"},
    "call":    {"outline": (35, 134, 54),   "label_c": (63, 185, 80),   "badge": "TOOL CALL"},
    "result":  {"outline": (137, 87, 229),  "label_c": (188, 140, 255), "badge": "TOOL RESULT"},
    "final":   {"outline": (219, 109, 40),  "label_c": (255, 166, 77),  "badge": "FINAL RESPONSE"},
}
_DEFAULT_STYLE: dict = {"outline": (80, 90, 100), "label_c": (160, 170, 180), "badge": "STEP"}


def _load_fonts() -> tuple[ImageFont.ImageFont, ImageFont.ImageFont]:
    """Return ``(content_font, label_font)``. Falls back to Pillow default."""
    for name in ("DejaVuSans.ttf", "arial.ttf", "Arial.ttf", "FreeSans.ttf"):
        try:
            return (
                ImageFont.truetype(name, 13),
                ImageFont.truetype(name, 13),
            )
        except (IOError, OSError):
            continue
    default = ImageFont.load_default(size=13)
    return default, default


def _format_content(step: TraceStep) -> str:
    """Return the human-readable body text for a trace step."""
    if step.step_type == "call":
        if step.metadata:
            args_str = ", ".join(f"{k}={v!r}" for k, v in step.metadata.items())
            raw = f"{step.content}({args_str})"
        else:
            raw = f"{step.content}()"
    elif step.step_type == "result":
        tool_name = step.metadata.get("tool", "")
        is_error = step.metadata.get("is_error", False)
        prefix = f"[{tool_name}]{'  ERROR' if is_error else ''}: " if tool_name else ""
        raw = prefix + step.content
    else:
        raw = step.content

    if len(raw) > MAX_CONTENT_CHARS:
        raw = raw[:MAX_CONTENT_CHARS].rstrip() + " \u2026"
    return raw


def _wrap(text: str) -> list[str]:
    """Wrap *text* into display lines, honouring embedded newlines."""
    lines: list[str] = []
    for para in text.splitlines():
        para = para.strip()
        if para:
            lines.extend(textwrap.wrap(para, width=CONTENT_WRAP_WIDTH) or [para])
        else:
            lines.append("")
    return lines or [""]


def _box_height(content_lines: int) -> int:
    return max(
        BOX_PAD + HEADER_H + BOX_PAD + content_lines * LINE_H + BOX_PAD,
        MIN_BOX_H,
    )


def save_trace_png(trace: List[TraceStep], path: str) -> str:
    """Render an agent execution trace to a PNG file at *path*.

    Each step is drawn as a labelled box showing the **actual content** of
    that step (LLM text, tool arguments, tool output, etc.), truncated and
    word-wrapped to fit the image width.  Boxes are connected by arrows in
    execution order.  Returns the resolved output path.
    """
    if not trace:
        raise ValueError("trace is empty — nothing to render")

    content_font, label_font = _load_fonts()

    steps: list[tuple[TraceStep, list[str], int]] = []
    for step in trace:
        raw = _format_content(step)
        lines = _wrap(raw)
        bh = _box_height(len(lines))
        steps.append((step, lines, bh))

    total_boxes_h = sum(bh for _, _, bh in steps)
    total_arrows_h = ARROW_H * (len(steps) - 1)
    img_h = TITLE_H + MARGIN + total_boxes_h + total_arrows_h + MARGIN

    img = Image.new("RGB", (IMG_WIDTH, img_h), _BG)
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, IMG_WIDTH, TITLE_H], fill=_TITLE_BG)
    draw.text(
        (MARGIN, (TITLE_H - HEADER_H) // 2),
        "Vantage Agent Trace",
        fill=(230, 235, 242),
        font=label_font,
    )
    ts = datetime.now().strftime("%Y-%m-%d  %H:%M")
    ts_w = int(draw.textlength(ts, font=content_font))
    draw.text(
        (IMG_WIDTH - MARGIN - ts_w, (TITLE_H - LINE_H) // 2),
        ts,
        fill=(80, 92, 108),
        font=content_font,
    )

    y = TITLE_H + MARGIN
    for idx, (step, lines, bh) in enumerate(steps):
        style = _STEP_STYLE.get(step.step_type, _DEFAULT_STYLE)
        x1, y1 = MARGIN, y
        x2, y2 = MARGIN + BOX_WIDTH, y + bh

        # Box background
        draw.rounded_rectangle(
            [x1, y1, x2, y2],
            radius=8,
            fill=_BOX_BG,
            outline=style["outline"],
            width=2,
        )

        # Step-number badge + type label on the header row
        badge = f"#{idx + 1}"
        draw.text((x1 + BOX_PAD, y1 + BOX_PAD), badge, fill=_TEXT_DIM, font=label_font)
        badge_w = int(draw.textlength(badge, font=label_font))
        draw.text(
            (x1 + BOX_PAD + badge_w + 8, y1 + BOX_PAD),
            style["badge"],
            fill=style["label_c"],
            font=label_font,
        )

        # Content lines
        cy = y1 + BOX_PAD + HEADER_H + BOX_PAD // 2
        for line in lines:
            draw.text((x1 + BOX_PAD, cy), line, fill=_TEXT_MAIN, font=content_font)
            cy += LINE_H

        # Arrow to next box
        if idx < len(steps) - 1:
            cx = MARGIN + BOX_WIDTH // 2
            ay1, ay2 = y2, y2 + ARROW_H
            draw.line([cx, ay1, cx, ay2], fill=_ARROW, width=2)
            draw.polygon([cx - 5, ay2 - 7, cx + 5, ay2 - 7, cx, ay2], fill=_ARROW)

        y += bh + ARROW_H

    out_dir = os.path.dirname(os.path.abspath(path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    img.save(path)
    return path

