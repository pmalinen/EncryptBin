def test_imports():
    """
    Minimal smoke test to ensure core modules can be imported.
    This prevents pytest from exiting with code 5 (no tests collected)
    and gives us >0% coverage even before real tests are added.
    """
    import app
    import cleanup
    import storage

    # Just assert that modules loaded
    assert app is not None
    assert storage is not None
    assert cleanup is not None
