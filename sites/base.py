from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Dict, Any


@dataclass(frozen=True)
class SiteConfig:
    """Loaded from sites/<site>/flow.yaml and sites/<site>/locators.yaml."""
    name: str
    base_url: str
    flows: Dict[str, Any]
    locators: Dict[str, Any]


class SiteAdapter(Protocol):
    """Optional Python hook layer for sites that need custom behavior."""

    config: SiteConfig

    def prepare(self, page) -> None:
        """Optional: cookies, locale, dismiss banners, etc."""
        ...

    def login(self, page, creds: Dict[str, str]) -> None:
        """Perform login. Default implementation is via FlowRunner."""
        ...

    def assert_logged_in(self, page) -> None:
        """Assert we reached a logged-in state."""
        ...
