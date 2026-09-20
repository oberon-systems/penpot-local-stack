import pytest

from libs import prompts


@pytest.mark.parametrize("name", ["base", "web-ui", "a1"])
def test_valid_accepts_template_names(name):
    assert prompts.valid(name)


@pytest.mark.parametrize("name", ["", "-base", "Base", "web ui", "web/ui"])
def test_valid_rejects_everything_else(name):
    assert not prompts.valid(name)
