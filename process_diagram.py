"""
Stub module for generating process diagrams.

Replace the body of `generate_diagram` with a real implementation that
accepts a process description and returns an SVG (or other image format)
string representation of the diagram.
"""

from __future__ import annotations


def generate_diagram(process_description: str) -> str:
    """Generate a process diagram from a textual process description.

    Args:
        process_description: A plain-text description of the process steps
            and actors.  The format is intentionally open – the real
            implementation can define whatever DSL or structured format it
            needs.

    Returns:
        An SVG string that can be embedded directly in an HTML page, or an
        empty string when no description is supplied.

    Note:
        This is a stub.  The returned SVG is a placeholder diagram that shows
        the supplied text inside a simple box.  Replace this function body
        with the real diagram-generation logic.
    """
    if not process_description or not process_description.strip():
        return ""

    # ------------------------------------------------------------------
    # STUB IMPLEMENTATION
    # Replace everything below with real diagram-generation code.
    # ------------------------------------------------------------------
    escaped = (
        process_description.strip()
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )

    # Build a simple SVG placeholder that wraps the text in a labelled box.
    lines = escaped.splitlines() or [escaped]
    line_height = 20
    padding = 16
    width = max(len(line) for line in lines) * 8 + padding * 2
    height = len(lines) * line_height + padding * 2 + 30  # 30 for the title bar

    text_elements = "\n".join(
        f'  <text x="{padding}" y="{30 + padding + i * line_height}" '
        f'font-family="monospace" font-size="13" fill="#333">{line}</text>'
        for i, line in enumerate(lines)
    )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
  <rect width="{width}" height="{height}" rx="6" ry="6"
        fill="#f8f9fa" stroke="#6c757d" stroke-width="1.5"/>
  <rect width="{width}" height="30" rx="6" ry="6"
        fill="#6c757d"/>
  <rect x="0" y="20" width="{width}" height="10" fill="#6c757d"/>
  <text x="{padding}" y="20" font-family="sans-serif" font-size="13"
        font-weight="bold" fill="white">Process Diagram (stub)</text>
{text_elements}
</svg>"""

    return svg
