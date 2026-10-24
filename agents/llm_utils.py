"""Shared NVIDIA model settings and helpers used by every agent.

Models can be overridden from .env without touching code:
    NVIDIA_FAST_MODEL, NVIDIA_RANKING_MODEL, NVIDIA_EMBEDDING_MODEL
"""

import os
import re
import unicodedata
from typing import Any

from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA

from agents.http_clients import create_retry_session

load_dotenv()

# Fast, cheap, good at tool calling: voice intake, scheme selection, JSON extraction.
FAST_MODEL = os.getenv("NVIDIA_FAST_MODEL", "nvidia/nemotron-3-ultra-550b-a55b")
# Reads scheme PDFs / web text into JSON and writes spoken scripts. Override in .env
# with NVIDIA_DOCUMENT_MODEL if you prefer a non-reasoning model for JSON.
DOCUMENT_MODEL = os.getenv("NVIDIA_DOCUMENT_MODEL", FAST_MODEL)
# Ranks every scheme against the profile. Defaults to the fast model, which is
# known to work. For stronger (slower) ranking set in .env:
#   NVIDIA_RANKING_MODEL=nvidia/nemotron-3-super-120b-a12b
RANKING_MODEL = os.getenv("NVIDIA_RANKING_MODEL", FAST_MODEL)
# Multilingual retrieval embeddings (English, Telugu, Hindi questions).
EMBEDDING_MODEL = os.getenv("NVIDIA_EMBEDDING_MODEL", "nvidia/nemotron-3.5-embed-1b")

_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


def build_chat_model(
    model_name: str,
    temperature: float,
    timeout: int,
    max_tokens: int,
) -> ChatNVIDIA:
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        raise ValueError("Please set the NVIDIA_API_KEY environment variable.")

    model = ChatNVIDIA(
        model=model_name,
        temperature=temperature,
        api_key=api_key,
        timeout=timeout,
        max_completion_tokens=max_tokens,
    )
    model._client.get_session_fn = create_retry_session
    return model


def clean_text(content: Any) -> str:
    """Turn a model reply into plain text: join content blocks and remove
    any <think> reasoning so it is never spoken aloud or shown."""
    if isinstance(content, list):
        content = "".join(
            part if isinstance(part, str)
            else str(part.get("text", "")) if isinstance(part, dict)
            else ""
            for part in content
        )
    text = _THINK_BLOCK.sub("", str(content or ""))
    lowered = text.lower()
    if "<think>" in lowered:  # reasoning that never closed
        text = re.split(r"<think>", text, flags=re.IGNORECASE)[0]
    elif "</think>" in lowered:
        text = re.split(r"</think>", text, flags=re.IGNORECASE)[-1]
    return text.strip()


# ---------------------------------------------------------------------------
# Turning model output into clean, readable (and speakable) plain text
# ---------------------------------------------------------------------------
_CUT_AT = re.compile(r"(?im)^[ \t]*(\||[#*_ \t]*ranked list|[#*_ \t]*how the ranking)")
_TABLE_SEPARATOR = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*$")
_BULLET = re.compile(r"^\s*(?:[-*\u2022\u00b7\u25aa\u2013]|\d{1,2}[.)])\s+")
_ARROWS = dict.fromkeys(map(ord, "\u2192\u2794\u279c\u21d2\u2190"), " ")
_DASHES = dict.fromkeys(map(ord, "\u2010\u2011\u2012"), "-")


def strip_markdown(text: str, keep_lines: bool = False) -> str:
    """Remove markdown, tables, emojis and symbols.

    keep_lines=False: flowing paragraphs (for chat bubbles and the voice).
    keep_lines=True: keep one item per line (for internal data like the ranking).
    """
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", str(text or ""))  # [a](url) -> a
    text = re.sub(r"(?i)<br\s*/?>", " ", text)
    text = text.translate(_ARROWS).translate(_DASHES)
    text = "".join(
        ch for ch in text
        if unicodedata.category(ch) not in ("So", "Sk") and ch not in "\ufe0e\ufe0f"
    )

    lines = []
    for line in text.splitlines():
        if _TABLE_SEPARATOR.match(line):
            continue
        if line.strip().startswith("|"):
            line = "; ".join(cell.strip() for cell in line.strip().strip("|").split("|") if cell.strip())
        line = re.sub(r"^\s*#{1,6}\s*", "", line)
        bullet = bool(_BULLET.match(line))
        line = _BULLET.sub("", line)
        heading = bool(re.fullmatch(r"\s*(\*\*|__)[^*_]+(\*\*|__)\s*", line))
        line = re.sub(r"(\*\*|__|~~|`)", "", line).replace("*", "").strip()
        line = re.sub(r"\s*[\u2013\u2014-]+\s*$", "", line)  # dangling dash
        if heading and line and line[-1] not in ".!?:;":
            line += ":"
        if not line:
            lines.append("")
            continue
        if bullet and not keep_lines and line[-1] not in ".!?:;":
            line += "."
        lines.append(("- " + line) if (bullet and keep_lines) else line)

    if keep_lines:
        out = "\n".join(lines)
        return re.sub(r"\n{3,}", "\n\n", out).strip()

    paragraphs, current = [], []
    for line in lines + [""]:
        if line:
            current.append(line)
        elif current:
            paragraphs.append(" ".join(current))
            current = []
    return re.sub(r"[ \t]+", " ", "\n\n".join(paragraphs)).strip()


def speakable(content: Any) -> str:
    """Model reply -> short plain text. Drops reasoning, drops any ranked-list
    table the model repeats at the end, and removes all markdown and symbols."""
    text = clean_text(content)
    match = _CUT_AT.search(text)
    kept = text[: match.start()].strip() if match else text
    return strip_markdown(kept or text)