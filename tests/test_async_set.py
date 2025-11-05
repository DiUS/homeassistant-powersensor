import asyncio
import pytest
import pytest_asyncio
from asyncmock import AsyncMock

from AsyncSet import AsyncSet

class MockLock:
  """Helper to count lock enter/exit calls.
  AsyncMock was no help due to the weird way python handles "async with",
  ignoring the lock instance and instead looking up __aenter__/__aexit__ on
  the class. As such, we resort to class variables and careful resetting of
  those in fixtures."""

  aenter = 0
  aexit = 0

  async def __aenter__(self):
    MockLock.aenter += 1
  async def __aexit__(self, typ, exc, tb):
    MockLock.aexit += 1

  @staticmethod
  def reset():
    MockLock.aenter = 0
    MockLock.aexit = 0

  @staticmethod
  def expect_called(call_count):
    assert MockLock.aenter == call_count
    assert MockLock.aexit == call_count


### Fixtures #############################################

@pytest.fixture
def mocklocked_asyncset(monkeypatch):
  MockLock.reset()
  a = AsyncSet()
  monkeypatch.setattr(a, "_lock", MockLock())
  return a


@pytest_asyncio.fixture
async def preset(mocklocked_asyncset):
  a = mocklocked_asyncset
  for v in [ 1, 2, 3, 5, 8, 11 ]:
    await a.add(v)
  a._lock.expect_called(6)
  MockLock.reset()
  return a


### Tests ################################################

@pytest.mark.asyncio
async def test_basics(mocklocked_asyncset):
  a = mocklocked_asyncset
  await a.add(1)
  await a.add(3)

  assert 1 in a
  assert 2 not in a
  assert 3 in a
  assert len(a) == 2
  a._lock.expect_called(2)

@pytest.mark.asyncio
async def test_discard(preset):
  assert 3 in preset
  await preset.discard(3)
  assert 3 not in preset
  preset._lock.expect_called(1)

@pytest.mark.asyncio
async def test_discard_missing(preset):
  assert 31 not in preset
  await preset.discard(31)
  preset._lock.expect_called(1)

@pytest.mark.asyncio
async def test_remove(preset):
  assert 5 in preset
  await preset.remove(5)
  assert 5 not in preset
  preset._lock.expect_called(1)

@pytest.mark.asyncio
async def test_remove_missing(preset):
  assert 51 not in preset
  with pytest.raises(KeyError):
    await preset.remove(51)
  preset._lock.expect_called(1)

@pytest.mark.asyncio
async def test_pop(preset):
  l = len(preset)
  x = await preset.pop()
  assert x not in preset
  assert len(preset) == l - 1
  preset._lock.expect_called(1)

@pytest.mark.asyncio
async def test_clear(preset):
  assert len(preset) > 0
  await preset.clear()
  assert len(preset) == 0
  preset._lock.expect_called(1)

@pytest.mark.asyncio
async def test_copy(preset):
  plain = await preset.copy()
  assert preset._items == plain
  assert preset._items is not plain
  preset._lock.expect_called(1)

def test_empty(preset):
  assert preset
  assert not AsyncSet()
