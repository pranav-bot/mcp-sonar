from __future__ import annotations


def estimate_tokens(text: str, *, encoding: str = "cl100k_base") -> tuple[int, str]:
    """Return (token_count, method). Uses tiktoken when installed, else chars/4 heuristic."""
    if not text:
        return 0, "empty"
    try:
        import tiktoken  # noqa: PLC0415

        enc = tiktoken.get_encoding(encoding)
        return len(enc.encode(text)), f"tiktoken:{encoding}"
    except ImportError:
        return max(1, len(text) // 4), "chars/4"
    except Exception:
        return max(1, len(text) // 4), "chars/4"
