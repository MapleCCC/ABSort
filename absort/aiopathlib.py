from __future__ import annotations

import shutil
from collections.abc import AsyncIterator
from os import stat_result
from pathlib import Path as SyncPath
from typing import Union

import aiofiles

from .async_utils import run_async


__all__ = ["AsyncPath"]


# TODO it's inefficent to delegate all including some lightweight tiny system calls to the thread pool executor. It might very likely hurt the performance instead. Profile to compare.


class AsyncPath:
    """ A thin wrapper on top of the pathlib.Path """

    def __init__(self, s: Union[str, SyncPath]) -> None:
        self._path = SyncPath(s)

    __slots__ = ("_path",)

    def __str__(self) -> str:
        return str(self._path)

    def __repr__(self) -> str:
        return repr(self._path)

    def with_name(self, name: str) -> AsyncPath:
        return AsyncPath(self._path.with_name(name))

    async def stat(self) -> stat_result:
        return await run_async(self._path.stat)

    async def unlink(self, missing_ok=False) -> None:
        await run_async(self._path.unlink, missing_ok)

    async def is_dir(self) -> bool:
        return await run_async(self._path.is_dir)

    async def is_file(self) -> bool:
        return await run_async(self._path.is_file)

    async def exists(self) -> bool:
        return await run_async(self._path.exists)

    async def rmdir(self) -> None:
        await run_async(self._path.rmdir)

    async def rglob(self, pattern: str) -> AsyncIterator[AsyncPath]:
        async for p in run_async(self._path.rglob, pattern):
            yield AsyncPath(p)

    async def glob(self, pattern: str) -> AsyncIterator[AsyncPath]:
        async for p in run_async(self._path.glob, pattern):
            yield AsyncPath(p)

    @classmethod
    async def home(cls: type) -> AsyncPath:
        return AsyncPath(await run_async(SyncPath.home))

    @classmethod
    def sync_home(cls: type) -> AsyncPath:
        return AsyncPath(SyncPath.home())

    def __truediv__(self, other: Union[str, SyncPath]) -> AsyncPath:
        return AsyncPath(self._path / other)

    def __rtruediv__(self, other: Union[str, SyncPath]) -> AsyncPath:
        return AsyncPath(other / self._path)

    async def mkdir(self, mode=0o777, parents=False, exist_ok=False) -> None:
        await run_async(self._path.mkdir, mode, parents, exist_ok)

    async def iterdir(self) -> AsyncIterator[AsyncPath]:
        async for p in run_async(self._path.iterdir):
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
        await run_async(shutil.copy, self._path, dst, follow_symlinks=follow_symlinks)

    async def copy2(self, dst: Union[str, AsyncPath], *, follow_symlinks=True) -> None:
        if isinstance(dst, AsyncPath):
            dst = str(dst)

        await run_async(shutil.copy2, self._path, dst, follow_symlinks=follow_symlinks)

    async def dirsize(self) -> int:
        """ Return the total size of a directory, in bytes """

        if not await self.is_dir():
            raise NotADirectoryError(f"{self} is not a directory")

        size = 0
        async for f in self.rglob("*"):
            if await f.is_file():
                stat = await f.stat()
                size += stat.st_size
        return size

    async def removedirs(self) -> None:
        """ Remove a directory, also removing files and subdirectories inside. """

        if await self.is_dir():
            raise NotADirectoryError(f"{self} is not a directory")

        async for file in self.rglob("*"):
            await file.unlink()

        await self.rmdir()
