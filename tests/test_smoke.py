import pathlib
import sys


def test_imports():
    """
    Minimal smoke test to ensure core modules can be imported.
    """
    # Add repo root to sys.path at runtime
    sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

    import app
    import cleanup
    import storage

    assert app is not None
    assert storage is not None
    assert cleanup is not None
