"""Number and table formatting for the generated Indonesian Markdown reports."""

from __future__ import annotations


def number(x: float, decimals: int = 2) -> str:
    """2.50 -> '2,5'; trailing zeros dropped, comma as decimal separator."""

    text = f"{x:.{decimals}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text.replace(".", ",")


def fixed(x: float, decimals: int = 3) -> str:
    """Fixed decimals with a comma: 0.5 -> '0,500'."""

    return f"{x:.{decimals}f}".replace(".", ",")


def thousands(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def table(header: list[str], rows: list[list[object]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join(lines)
