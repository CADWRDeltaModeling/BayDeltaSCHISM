import pytest

@pytest.mark.postrun
def test_sometthing():
    assert 1==2


@pytest.mark.prerun
def test_sometthing():
    assert 1==2
