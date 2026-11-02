import os
import re

from fastapi import Request
from fastapi.responses import StreamingResponse

CHUNK_SIZE = 1024 * 1024  # 1 МБ


def range_file_response(path: str, request: Request, media_type: str = "audio/mpeg"):
    file_size = os.path.getsize(path)
    range_header = request.headers.get("range")

    start = 0
    end = file_size - 1

    if range_header:
        match = re.match(r"bytes=(\d+)-(\d*)", range_header)
        if match:
            start = int(match.group(1))
            if match.group(2):
                end = int(match.group(2))

    end = min(end, file_size - 1)
    length = end - start + 1

    def iter_file():
        with open(path, "rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(CHUNK_SIZE, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(length),
    }

    status_code = 206 if range_header else 200
    return StreamingResponse(iter_file(), status_code=status_code, headers=headers, media_type=media_type)
