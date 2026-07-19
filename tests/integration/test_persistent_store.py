from kylin_aiops_api.store import InMemoryStore


def test_store_reloads_nodes_and_incidents_from_database(tmp_path) -> None:
    url = f"sqlite+pysqlite:///{tmp_path / 'ops.db'}"
    first = InMemoryStore(seed_demo=True, database_url=url)
    first.persist_all()

    second = InMemoryStore(seed_demo=False, database_url=url)

    assert second.nodes["app-01"]["service"] == "java"
    assert second.incidents["inc-db-pool"]["diagnosis"]["evidence_refs"] == [
        "ev-db-connections",
        "ev-db-log",
    ]
