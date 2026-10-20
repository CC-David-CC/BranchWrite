"""Strict literal-text result contract for a host-registered operation.

The model supplies only framed text. The host owns the contract name and checks
UTF-8 byte bounds after parsing; the generated grammar constrains framing and
character/line counts but does not contain the task's expected answer.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re


_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}\Z", re.ASCII)


@dataclass(frozen=True)
class LiteralValue:
    """Validated source bytes and their stable identity."""

    payload: bytes
    source_sha256: str


@dataclass(frozen=True)
class LiteralContract:
    """Host-owned bounds and framing for `TEXT <name>` literal output.

    Each prefixed source line contributes its content and its terminating LF.
    Therefore this minimal text contract represents LF-terminated UTF-8 text;
    non-LF-terminated byte artifacts use a separate immutable artifact path.
    """

    name: str
    max_bytes: int
    max_lines: int
    max_line_bytes: int

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or _NAME.fullmatch(self.name) is None:
            raise ValueError("contract name must be a short ASCII identifier")
        for field in ("max_bytes", "max_lines", "max_line_bytes"):
            value = getattr(self, field)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{field} must be a positive exact integer")

    def parse(self, text: str) -> LiteralValue:
        """Parse exact protocol text to UTF-8 bytes; never repair malformed output."""
        if not isinstance(text, str):
            raise ValueError("literal result must be text")
        header = f"TEXT {self.name}\n"
        # Bound allocation before UTF-8 encoding. Every source line has one
        # protocol prefix; payload bytes already include each source LF.
        wire_char_limit = (len(header) + len("END\n") + self.max_bytes + self.max_lines)
        if len(text) > wire_char_limit:
            raise ValueError("literal result exceeds its framing and byte bound")
        try:
            wire = text.encode("utf-8", "strict")
        except UnicodeEncodeError as exc:
            raise ValueError("literal result is not valid Unicode scalar text") from exc
        if b"\x00" in wire or b"\r" in wire:
            raise ValueError("literal result may not contain NUL or CR")

        header_bytes = header.encode("ascii")
        if not wire.startswith(header_bytes) or not wire.endswith(b"\n"):
            raise ValueError("literal result has an invalid header or truncated framing")
        records = wire[:-1].split(b"\n")
        if not records or records[0] != header_bytes[:-1] or records[-1] != b"END":
            raise ValueError("literal result has an invalid header, terminator, or extra record")

        body = records[1:-1]
        if len(body) > self.max_lines:
            raise ValueError("literal result exceeds its line-count bound")
        chunks: list[bytes] = []
        total = 0
        for line in body:
            if not line.startswith(b"|"):
                raise ValueError("every literal source line must have exactly one prefix")
            payload_line = line[1:] + b"\n"
            if b"\x00" in payload_line or b"\r" in payload_line:
                raise ValueError("literal source lines may not contain NUL or CR")
            if len(payload_line) > self.max_line_bytes:
                raise ValueError("literal source line exceeds its UTF-8 byte bound")
            total += len(payload_line)
            if total > self.max_bytes:
                raise ValueError("literal source exceeds its UTF-8 byte bound")
            chunks.append(payload_line)

        payload = b"".join(chunks)
        # The full wire was strict UTF-8, but keep the returned-value invariant
        # explicit if framing rules change later.
        payload.decode("utf-8", "strict")
        return LiteralValue(payload, hashlib.sha256(payload).hexdigest())

    def gbnf(self) -> str:
        """Return GBNF that bounds framing, line count and characters per line.

        GBNF counts Unicode characters, while `parse` enforces the stricter
        UTF-8 byte limits. The grammar contains no task-specific solution data.
        """
        header = f'TEXT {self.name}\\n'
        # Each payload line contains its terminating LF, so at most
        # max_line_bytes - 1 non-newline characters precede that LF.
        max_characters = self.max_line_bytes - 1
        return (
            f'root ::= "{header}" ("|" line "\\n"){{0,{self.max_lines}}} "END\\n"\n'
            f'line ::= [^\\x00\\r\\n]{{0,{max_characters}}}\n'
        )
