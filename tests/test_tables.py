from types import SimpleNamespace

from dataplatform.glue.tables import check_partitions, inspect_table


class _Glue:
    def __init__(self, table):
        self._table = table
        self.get_partitions_called = False

    def get_table(self, DatabaseName, Name):
        return {"Table": self._table}

    def get_partitions(self, DatabaseName, TableName, Expression, MaxResults):
        self.get_partitions_called = True
        return {"Partitions": [{"Values": ["2026-07-01"]}]}


def _session(glue):
    return SimpleNamespace(client=lambda _s: glue)


_HIVE = {
    "Parameters": {},
    "StorageDescriptor": {"Location": "s3://x/", "Columns": [{"Name": "id", "Type": "string"}]},
    "PartitionKeys": [{"Name": "dt", "Type": "string"}],
}
_ICEBERG = {"Parameters": {"table_type": "ICEBERG"}, "StorageDescriptor": {}}


def test_inspect_table_detects_iceberg():
    assert inspect_table(_session(_Glue(_ICEBERG)), "db", "t")["table_format"] == "iceberg"


def test_inspect_table_hive_schema():
    info = inspect_table(_session(_Glue(_HIVE)), "db", "t")
    assert info["table_format"] == "hive"
    assert info["partition_keys"] == [{"name": "dt", "type": "string"}]


def test_check_partitions_refuses_iceberg():
    glue = _Glue(_ICEBERG)
    result = check_partitions(_session(glue), "db", "t", "dt='2026-07-01'")
    assert result["supported"] is False
    assert glue.get_partitions_called is False


def test_check_partitions_hive_reports_existence():
    result = check_partitions(_session(_Glue(_HIVE)), "db", "t", "dt='2026-07-01'")
    assert result["supported"] is True
    assert result["exists"] is True
    assert result["matched_count"] == 1
