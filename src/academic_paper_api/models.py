"""Data models for representing paper structure."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Figure:
    """An image/figure from the paper."""

    url: str
    local_path: str = ""
    caption: str = ""
    figure_id: str = ""


@dataclass
class Section:
    """A section of the paper with heading, content blocks, and figures."""

    heading: str
    level: int  # 1 = h1, 2 = h2, etc.
    content: list[str | Figure] = field(default_factory=list)


@dataclass
class Paper:
    """Complete representation of a scraped academic paper."""

    doi: str
    title: str = ""
    authors: list[str] = field(default_factory=list)
    abstract: str = ""
    sections: list[Section] = field(default_factory=list)
    publisher: str = ""
    url: str = ""
    keywords: list[str] = field(default_factory=list)
