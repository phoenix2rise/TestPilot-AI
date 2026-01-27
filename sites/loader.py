from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Any

try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # type: ignore

from .base import SiteConfig

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SITES_DIR = PROJECT_ROOT / "sites"


def _require_yaml() -> None:
    if yaml is None:
        raise RuntimeError("PyYAML is required. Install with: pip install pyyaml")


def load_yaml(path: Path) -> Dict[str, Any]:
    _require_yaml()
    data = yaml.safe_load(path.read_text(encoding="utf-8"))  # type: ignore
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping in {path}")
    return data


def load_site_config(site_name: str) -> SiteConfig:
    flow_path = SITES_DIR / site_name / "flow.yaml"
    loc_path = SITES_DIR / site_name / "locators.yaml"

    if not flow_path.exists():
        raise FileNotFoundError(f"Missing {flow_path}")
    if not loc_path.exists():
        raise FileNotFoundError(f"Missing {loc_path}")

    flow = load_yaml(flow_path)
    loc = load_yaml(loc_path)

    base_url = str(flow.get("base_url", "")).strip()
    if not base_url:
        raise ValueError(f"'base_url' missing in {flow_path}")

    flows = flow.get("flows", {})
    if not isinstance(flows, dict):
        raise ValueError(f"'flows' must be a mapping in {flow_path}")

    locators = loc.get("locators", {})
    if not isinstance(locators, dict):
        raise ValueError(f"'locators' must be a mapping in {loc_path}")

    return SiteConfig(name=site_name, base_url=base_url, flows=flows, locators=locators)


def resolve_site_name(cli_value: str | None = None) -> str:
    if cli_value:
        return cli_value
    if os.getenv("TP_SITE"):
        return os.environ["TP_SITE"]
    return "demo"
