from dataclasses import dataclass
from pathlib import Path
from typing import Tuple


@dataclass(frozen=True)
class Distribution:
    display_name: str
    internal_name: str
    data_dir_name: str
    source_languages: Tuple[str, ...]
    remote_source_sync: bool
    external_specs: bool
    generic_fallback: bool

    def local_sources(self, root: Path) -> Path:
        return root / "sources" / self.source_languages[0]

    def user_sources(self, app_dir: Path) -> Path:
        return app_dir / "sources" / self.source_languages[0]


DISTRIBUTION = Distribution(
    display_name="BearReader",
    internal_name="xiaoxiong-novel",
    data_dir_name="XiaoXiongNovel",
    source_languages=("zh",),
    remote_source_sync=False,
    external_specs=False,
    generic_fallback=False,
)


def allowed_local_sources(root: Path) -> Path:
    return DISTRIBUTION.local_sources(root)


def allowed_user_sources(app_dir: Path) -> Path:
    return DISTRIBUTION.user_sources(app_dir)
