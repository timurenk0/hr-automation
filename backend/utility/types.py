from dataclasses import dataclass


@dataclass(slots=True)
class ExtractedLink:
    url: str
    platform: str | None = None
    category: str | None = None
