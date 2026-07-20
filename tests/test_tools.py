from server.tools import SearchApplicationsInput, reassign_reviewer


def test_rejects_invalid_amount_range():
    try:
        SearchApplicationsInput(minAmount=10, maxAmount=5)
        assert False, "Expected validation failure"
    except ValueError:
        pass


def test_reassign_requires_scope():
    class Db: pass
    try:
        reassign_reviewer(Db(), "rev_001", "rev_002")
        assert False, "Expected validation failure before database access"
    except ValueError as error:
        assert "cycle_id or status_filter" in str(error)
