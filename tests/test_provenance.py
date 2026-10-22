import json
from pathlib import Path

from colx.provenance import LENS_SHA256, collect, write_meta


def test_collect_records_required_fields() -> None:
    record = collect("col test", extra_field=1)
    for key in ("seed", "versions", "model_revision", "narcbench_commit", "lens_sha256"):
        assert key in record
    assert record["lens_sha256"] == LENS_SHA256
    assert record["extra_field"] == 1


def test_write_meta(tmp_path: Path) -> None:
    path = write_meta(tmp_path / "x.parquet", {"a": 1})
    assert path.name == "x.parquet.meta.json"
    assert json.loads(path.read_text()) == {"a": 1}
