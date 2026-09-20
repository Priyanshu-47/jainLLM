"""Hierarchical segmentation into citation-addressable text units."""

from svk_corpus.segmentation.text_units import (  # noqa: F401
    PageSlice,
    SegmentationStats,
    segment_document,
    split_pages,
)

__all__ = ["PageSlice", "SegmentationStats", "segment_document", "split_pages"]
