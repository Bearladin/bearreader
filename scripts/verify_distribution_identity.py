from lncrawl.config import APP_DIR
from lncrawl.distribution import DISTRIBUTION


def main() -> None:
    assert DISTRIBUTION.display_name == "BearReader"
    assert DISTRIBUTION.internal_name == "xiaoxiong-novel"
    assert DISTRIBUTION.source_languages == ("zh",)
    assert DISTRIBUTION.remote_source_sync is False
    assert DISTRIBUTION.external_specs is False
    assert DISTRIBUTION.generic_fallback is False
    assert APP_DIR.name == "XiaoXiongNovel"


if __name__ == "__main__":
    main()
