"""Pytest compatibility helpers for the integrated workspace."""

import asyncio
import inspect
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv


def _load_nearest_env() -> None:
    for parent in Path(__file__).resolve().parents:
        env_path = parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            return


_load_nearest_env()

_ENV_ALIASES = {
    "LLM_MODEL_ID": "MODEL_ID",
    "LLM_API_KEY": "API_KEY",
    "LLM_BASE_URL": "BASE_URL",
}

for new_name, old_name in _ENV_ALIASES.items():
    if not os.getenv(new_name) and os.getenv(old_name):
        os.environ[new_name] = os.environ[old_name]


def pytest_configure(config):
    config.addinivalue_line("markers", "asyncio: run coroutine tests with asyncio.run")


@pytest.hookimpl(tryfirst=True)
def pytest_pyfunc_call(pyfuncitem):
    test_func = pyfuncitem.obj
    if not inspect.iscoroutinefunction(test_func):
        return None

    kwargs = {
        name: pyfuncitem.funcargs[name]
        for name in pyfuncitem._fixtureinfo.argnames
        if name in pyfuncitem.funcargs
    }
    asyncio.run(test_func(**kwargs))
    return True
