from cli.db.init import create_db_schemas


def test_create_db_schemas(tmp_path):
    test_db_path = tmp_path / "test_db" / ".lancedb"
    chunks = create_db_schemas(test_db_path)

    # 検証
    assert len(chunks) == 2
    assert chunks[0] == "A" * 40
    assert chunks[1] == "B" * 40
