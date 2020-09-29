from __future__ import annotations

import shutil
from os import stat_result
from pathlib import Path as SyncPath
from typing import AsyncIterator, Type, Union

import aiofiles

from .async_utils import asyncify


__all__ = ["AsyncPath"]


class AsyncPath:
    """ A thin wrapper on top of the pathlib.Path """

    def __init__(self, s: Union[str, SyncPath]) -> None:
        self._path = SyncPath(s)

    __slots__ = ["_path"]

    async def stat(self) -> stat_result:
        return await asyncify(self._path.stat)()

    async def unlink(self, missing_ok=False) -> None:
        await asyncify(self._path.unlink)(missing_ok)

    async def is_dir(self) -> bool:
        return await asyncify(self._path.is_dir)()

    async def is_file(self) -> bool:
        return await asyncify(self._path.is_file)()

    async def exists(self) -> bool:
        return await asyncify(self._path.exists)()

    async def rmdir(self) -> None:
        await asyncify(self._path.rmdir)()

    async def rglob(self, pattern: str) -> AsyncIterator[AsyncPath]:
        async for p in asyncify(self._path.rglob)(pattern):
            yield AsyncPath(p)

    @classmethod
    async def home(cls: Type) -> AsyncPath:
        return AsyncPath(await asyncify(SyncPath.home)())

    @classmethod
    def sync_home(cls: Type) -> AsyncPath:
        return AsyncPath(SyncPath.home())

    def __truediv__(self, other: Union[str, SyncPath]) -> AsyncPath:
        return AsyncPath(self._path / other)

    def __rtruediv__(self, other: Union[str, SyncPath]) -> AsyncPath:
        return AsyncPath(other / self._path)

    async def mkdir(self, mode=0o777, parents=False, exist_ok=False) -> None:
        await asyncify(self._path.mkdir)(mode, parents, exist_ok)

    async def iterdir(self) -> AsyncIterator[AsyncPath]:
        async for p in asyncify(self._path.iterdir)():
            yield AsyncPath(p)

    @property
    def name(self) -> str:
        return self._path.name

    # TODO add return type annotation, e.g. typing.IO
    def open(self, mode="r", buffering=-1, encoding=None, errors=None, newline=None):
        return aiofiles.open(
            self._path,
            mode=mode,
            buffering=buffering,
            encoding=encoding,
            errors=errors,
            newline=newline,
        )

    async def read_text(self, encoding=None, errors=None) -> str:
        async with self.open(mode="r", encoding=encoding, errors=errors) as fp:
            return await fp.read()

    async def read_bytes(self, encoding=None, errors=None) -> str:
        async with self.open(mode="rb", encoding=encoding, errors=errors) as fp:
            return await fp.read()

    async def write_text(self, data: str, encoding=None, errors=None) -> None:
        async with self.open(mode="w", encoding=encoding, errors=errors) as fp:
            await fp.write(data)

    async def write_bytes(self, data: bytes, encoding=None, errors=None) -> None:
        async with self.open(mode="wb", encoding=encoding, errors=errors) as fp:
            await fp.write(data)

    async def copy(self, dst: Union[str, AsyncPath], *, follow_symlinks=True) -> None:
        await asyncify(shutil.copy)(self._path, dst, follow_symlinks=follow_symlinks)

    async def copy2(self, dst: Union[str, AsyncPath], *, follow_symlinks=True) -> None:
        await asyncify(shutil.copy2)(self._path, dst, follow_symlinks=follow_symlinks)
