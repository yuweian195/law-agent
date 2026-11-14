"""Small, dependency-free BM25 implementation."""

from __future__ import annotations

import math
from collections import Counter


class BM25Index:
    def __init__(self, documents: list[list[str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.documents = documents
        self.k1 = k1
        self.b = b
        self.doc_count = len(documents)
        self.doc_lengths = [len(document) for document in documents]
        self.average_length = sum(self.doc_lengths) / max(1, self.doc_count)
        self.term_frequencies = [Counter(document) for document in documents]
        self.document_frequency: Counter[str] = Counter()
        for document in documents:
            self.document_frequency.update(set(document))
        self.idf = {
            term: math.log(1 + (self.doc_count - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in self.document_frequency.items()
        }

    def search(self, query: list[str], top_k: int = 10) -> list[tuple[int, float, list[str]]]:
        if not query or not self.documents:
            return []
        query_terms = list(dict.fromkeys(query))
        scores: list[tuple[int, float, list[str]]] = []
        for index, frequencies in enumerate(self.term_frequencies):
            score = 0.0
            for term in query_terms:
                frequency = frequencies.get(term, 0)
                if not frequency:
                    continue
                idf = self.idf.get(term, 0.0)
                denominator = frequency + self.k1 * (
                    1 - self.b + self.b * self.doc_lengths[index] / max(1e-9, self.average_length)
                )
                score += idf * frequency * (self.k1 + 1) / denominator
            if score > 0:
                matched = [term for term in query_terms if term in frequencies]
                scores.append((index, score, matched))
        scores.sort(key=lambda item: item[1], reverse=True)
        return scores[:top_k]
