import asyncio
import os
import pytest

from application.agents.shared.process_manager import CLIProcessManager, get_process_manager


@pytest.fixture
def process_manager():
    """Create a fresh process manager for each test."""
    return CLIProcessManager(max_concurrent_processes=3)


@pytest.mark.asyncio
async def test_can_start_process_within_limit(process_manager):
    """Test that processes can be started within the limit."""
    assert await process_manager.can_start_process(skip_cleanup=True)
    assert await process_manager.can_start_process(skip_cleanup=True)
    assert await process_manager.can_start_process(skip_cleanup=True)


@pytest.mark.asyncio
async def test_register_process_within_limit(process_manager):
    """Test registering processes within the limit."""
    assert await process_manager.register_process(1001, skip_cleanup=True)
    assert await process_manager.register_process(1002, skip_cleanup=True)
    assert await process_manager.register_process(1003, skip_cleanup=True)
    assert len(process_manager.active_pids) == 3


@pytest.mark.asyncio
async def test_register_process_exceeds_limit(process_manager):
    """Test that registration fails when limit is exceeded."""
    await process_manager.register_process(1001, skip_cleanup=True)
    await process_manager.register_process(1002, skip_cleanup=True)
    await process_manager.register_process(1003, skip_cleanup=True)

    # Fourth registration should fail
    assert not await process_manager.register_process(1004, skip_cleanup=True)
    assert len(process_manager.active_pids) == 3


@pytest.mark.asyncio
async def test_can_start_process_respects_limit(process_manager):
    """Test that can_start_process respects the limit."""
    await process_manager.register_process(1001, skip_cleanup=True)
    await process_manager.register_process(1002, skip_cleanup=True)
    await process_manager.register_process(1003, skip_cleanup=True)

    # Should not be able to start more
    assert not await process_manager.can_start_process(skip_cleanup=True)


@pytest.mark.asyncio
async def test_unregister_process(process_manager):
    """Test unregistering a process."""
    await process_manager.register_process(1001, skip_cleanup=True)
    await process_manager.register_process(1002, skip_cleanup=True)
    assert len(process_manager.active_pids) == 2

    await process_manager.unregister_process(1001)
    assert len(process_manager.active_pids) == 1
    assert 1001 not in process_manager.active_pids


@pytest.mark.asyncio
async def test_cleanup_dead_processes(process_manager):
    """Test that dead processes are cleaned up."""
    # Register a real process (current process)
    current_pid = os.getpid()
    await process_manager.register_process(current_pid, skip_cleanup=True)

    # Register a fake dead process
    fake_pid = 999999
    process_manager.active_pids.add(fake_pid)  # Add directly to avoid cleanup

    assert len(process_manager.active_pids) == 2

    # Cleanup should remove the fake process
    await process_manager._cleanup_dead_processes()
    assert len(process_manager.active_pids) == 1
    assert current_pid in process_manager.active_pids
    assert fake_pid not in process_manager.active_pids


@pytest.mark.asyncio
async def test_get_active_pids(process_manager):
    """Test getting active PIDs."""
    await process_manager.register_process(1001, skip_cleanup=True)
    await process_manager.register_process(1002, skip_cleanup=True)

    assert process_manager.active_pids == {1001, 1002}


@pytest.mark.asyncio
async def test_singleton_instance():
    """Test that get_process_manager returns a singleton."""
    manager1 = get_process_manager(max_concurrent=5)
    manager2 = get_process_manager(max_concurrent=10)
    
    # Should be the same instance
    assert manager1 is manager2
    # max_concurrent parameter should be ignored for existing instance
    assert manager1.max_concurrent_processes == 5

