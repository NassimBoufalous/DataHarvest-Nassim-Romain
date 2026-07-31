import os

import pytest

from dataharvest.config import Config
from dataharvest.orchestrator import Orchestrator


@pytest.mark.integration
def test_orchestrator_end_to_end_on_real_site():
    config = Config("configs/example_blog.yaml")
    if os.path.isfile(config.store.path):
        os.remove(config.store.path)

    orchestrator = Orchestrator(config)
    report = orchestrator.run()

    assert report["items_stockes"] >= 5
    assert os.path.isfile(config.store.path)
    assert os.path.getsize(config.store.path) > 0
