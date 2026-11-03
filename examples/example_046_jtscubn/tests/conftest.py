import pytest


def pytest_collection_modifyitems(config, items):
    """Automatically add asyncio marker to all async test functions."""
    for item in items:
        if item.get_closest_marker("asyncio") is None:
            if hasattr(item, "function") and asyncio_test(item.function):
                item.add_marker(pytest.mark.asyncio)


def asyncio_test(func):
    import asyncio
    return asyncio.iscoroutinefunction(func)
