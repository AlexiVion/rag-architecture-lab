from __future__ import annotations

import hashlib
from collections.abc import Sequence

from raglab.core.types import Document


def fingerprint_documents(documents: Sequence[Document]) -> str:
    """Hash ordered document IDs *and contents* to detect in-place corpus edits.

    Framing by UTF-8 byte length prevents ambiguity between concatenated fields.
    This deliberately trades O(corpus bytes) reindex checks for correctness in
    small in-memory experiments; large-corpus incremental indexes are future work.
    """
    digest = hashlib.sha256()
    for document in documents:
        for value in (document.id, document.title, document.text):
            encoded = value.encode("utf-8")
            digest.update(len(encoded).to_bytes(8, byteorder="big"))
            digest.update(encoded)
    return digest.hexdigest()
