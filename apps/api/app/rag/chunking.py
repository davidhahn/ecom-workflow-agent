import re
from dataclasses import dataclass
from pathlib import Path

_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_H2_RE = re.compile(r"^##\s+(.*)$")


@dataclass
class Chunk:
    content: str
    source_doc: str
    rule_number: int | None


def _strip_html_comments(text: str) -> str:
    return _HTML_COMMENT_RE.sub("", text).strip()


def chunk_markdown(path: Path, *, numbered: bool) -> list[Chunk]:
    """Split a policy markdown file into one chunk per H2 section.

    Deliberately not fixed-size/sliding-window or semantic-similarity
    chunking — each policy doc was hand-authored with one self-contained
    rule per H2 section (see docs/policies/refund_policy.md's intro), so the
    document's own structure is the chunk boundary.

    `numbered=True` (refund_policy.md) assigns rule_number as the 1-indexed
    order of H2 headings, matching the rule numbering the doc was authored
    with. `numbered=False` (shipping_policy.md, support_playbook.md) leaves
    rule_number as None — those docs are organized by heading, not numbered
    rules. The H1 title and intro paragraph before the first H2 are not
    chunked; only H2 sections are.
    """
    lines = path.read_text().splitlines()
    sections: list[tuple[str, list[str]]] = []  # (heading, body_lines)
    current_heading: str | None = None
    current_body: list[str] = []

    for line in lines:
        match = _H2_RE.match(line)
        if match:
            if current_heading is not None:
                sections.append((current_heading, current_body))
            current_heading = match.group(1).strip()
            current_body = []
        elif current_heading is not None:
            current_body.append(line)
    if current_heading is not None:
        sections.append((current_heading, current_body))

    chunks: list[Chunk] = []
    for i, (heading, body_lines) in enumerate(sections, start=1):
        body = _strip_html_comments("\n".join(body_lines).strip())
        content = f"{heading}\n\n{body}" if body else heading
        chunks.append(
            Chunk(
                content=content,
                source_doc=path.name,
                rule_number=i if numbered else None,
            )
        )
    return chunks
