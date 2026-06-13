import pytest
from pydantic import ValidationError

from paperwise.infrastructure.config import Settings


def test_worker_concurrency_defaults_to_celery_default() -> None:
    assert Settings(_env_file=None).worker_concurrency is None


def test_worker_concurrency_accepts_positive_integer() -> None:
    assert Settings(_env_file=None, worker_concurrency=2).worker_concurrency == 2


@pytest.mark.parametrize("value", [0, -1])
def test_worker_concurrency_rejects_non_positive_values(value: int) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, worker_concurrency=value)


def test_worker_concurrency_reads_paperwise_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PAPERWISE_WORKER_CONCURRENCY", "3")

    assert Settings(_env_file=None).worker_concurrency == 3
