"""Composable research adapters; each returns original-document SearchResult IDs."""

from raglab.architectures.adaptive import AdaptiveRetriever
from raglab.architectures.contextual import ContextualRetriever
from raglab.architectures.corrective import CorrectiveRetriever
from raglab.architectures.hyde import HyDERetriever
from raglab.architectures.multi_query import MultiQueryRetriever
from raglab.architectures.parent_child import ParentChildRetriever

__all__ = [
    "AdaptiveRetriever",
    "ContextualRetriever",
    "CorrectiveRetriever",
    "HyDERetriever",
    "MultiQueryRetriever",
    "ParentChildRetriever",
]
