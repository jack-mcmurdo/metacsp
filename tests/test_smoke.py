import metacsp


def test_import_and_version():
    assert isinstance(metacsp.__version__, str)
    assert metacsp.__version__.count(".") >= 1
