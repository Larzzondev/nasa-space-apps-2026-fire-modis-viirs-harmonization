"""CSV readers for the extracted FIRMS archives."""

from __future__ import annotations

import csv
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def read_archive(path: Path) -> Iterator[tuple[list[str], Iterator[tuple[int, list[str]]]]]:
    """Yield the header and ``(line_number, fields)`` for each data row.

    The header is line 1. The file is closed when the caller leaves the context,
    including when the row iterator is not fully consumed.
    """

    handle = path.open(newline="", encoding="utf-8-sig")
    reader = csv.reader(handle)
    try:
        try:
            header = next(reader)
        except StopIteration:
            raise ValueError(f"{path.name} has no header row") from None

        def rows() -> Iterator[tuple[int, list[str]]]:
            for line_number, row in enumerate(reader, start=2):
                yield line_number, row

        yield header, rows()
    finally:
        handle.close()
