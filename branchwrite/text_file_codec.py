"""Explicit text lines -> one UTF-8 file payload, without normalization.

These are tool inputs, never another history/snapshot representation. CR/LF
inside an element is rejected: boundaries and the final terminator are explicit.
"""
from .execution import ToolRejected

MAX_TEXT_BYTES=32768
MAX_TEXT_LINES=4096

def encode_lines(lines,line_ending,final_newline):
    if type(lines) is not list or len(lines)>MAX_TEXT_LINES:
        raise ToolRejected("lines must be a bounded array")
    if type(line_ending) is not str or line_ending not in ("LF","CRLF"):
        raise ToolRejected("line_ending must explicitly be LF or CRLF")
    if type(final_newline) is not bool:
        raise ToolRejected("final_newline must be an exact boolean")
    if not lines and final_newline:
        raise ToolRejected("empty lines cannot request a terminator; use one empty line")
    if not final_newline and len(lines)>1 and lines[-1]=='':
        raise ToolRejected('a trailing empty line requires final_newline=true')
    separator=b"\n" if line_ending=="LF" else b"\r\n"
    total=len(separator)*max(0,len(lines)-1+int(final_newline))
    parts=[]
    for line in lines:
        if type(line) is not str:
            raise ToolRejected("each line must have the exact string type")
        if "\r" in line or "\n" in line:
            raise ToolRejected("line elements cannot contain CR or LF; use separate lines")
        try:body=line.encode("utf8")
        except UnicodeEncodeError as exc:
            raise ToolRejected("line contains an invalid Unicode scalar") from exc
        total+=len(body)
        if total>MAX_TEXT_BYTES:
            raise ToolRejected("text file exceeds the registered byte limit")
        parts.append(body)
    return separator.join(parts)+(separator if final_newline else b"")
