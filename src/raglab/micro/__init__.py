"""CPU-first ultra-small RAG experiments. No model downloads at import time."""

from raglab.micro.registry import CANDIDATES, get_candidate
from raglab.micro.spans import EvidencePack, EvidenceSpan, pack_evidence

__all__ = ["CANDIDATES", "get_candidate", "EvidencePack", "EvidenceSpan", "pack_evidence"]
