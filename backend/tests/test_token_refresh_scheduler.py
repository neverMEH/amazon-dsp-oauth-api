"""
Tests for Token Refresh Scheduler
"""
import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from app.services.token_refresh_scheduler import TokenRefreshScheduler


@pytest.fixture
def mock_supabase_client():
    """Create a mock Supabase client"""
    client = Mock()

    # Mock table method returns self for chaining
    mock_table = Mock()
    mock_table.select = Mock(return_value=mock_table)
    mock_table.lte = Mock(return_value=mock_table)
    mock_table.eq = Mock(return_value=mock_table)
    mock_table.lt = Mock(return_value=mock_table)
    mock_table.update = Mock(return_value=mock_table)
    mock_table.insert = Mock(return_value=mock_table)
    mock_table.delete = Mock(return_value=mock_table)
    mock_table.execute = Mock()

    client.table = Mock(return_value=mock_table)

    return client


@pytest.fixture
def mock_token_service():
    """Create a mock token service"""
    service = Mock()
    service.refresh_oauth_token = AsyncMock()
    return service


@pytest.fixture
def scheduler(mock_supabase_client, mock_token_service):
    """Create a TokenRefreshScheduler instance with mocks"""
    scheduler = TokenRefreshScheduler(supabase_client=mock_supabase_client)
    scheduler.token_service = mock_token_service
    return scheduler


@pytest.mark.asyncio
async def test_scheduler_start_stop(scheduler):
    """Test starting and stopping the scheduler"""
    # Test start
    await scheduler.start()
    assert scheduler.is_running is True
    assert scheduler.scheduler.running is True

    # Test double start (should not error)
    await scheduler.start()
    assert scheduler.is_running is True

    # Test stop
    await scheduler.stop()
    assert scheduler.is_running is False


@pytest.mark.asyncio
async def test_check_and_refresh_tokens_no_tokens(scheduler, mock_supabase_client):
    """Test token refresh when no tokens need refreshing"""
    # Mock no tokens returned
    mock_supabase_client.table().execute.return_value = Mock(data=[])

    await scheduler._check_and_refresh_tokens()

    # Verify query was made
    mock_supabase_client.table.assert_called_with('oauth_tokens')
    mock_supabase_client.table().select.assert_called()


@pytest.mark.asyncio
async def test_check_and_refresh_tokens_with_expiring_tokens(scheduler, mock_supabase_client, mock_token_service):
    """Test token refresh with expiring tokens"""
    # Mock expiring tokens
    expiring_tokens = [
        {
            'id': 'token-1',
            'user_id': 'user-1',
            'access_token': 'old_access_token',
            'refresh_token': 'refresh_token_1',
            'expires_at': (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
            'refresh_failure_count': 0,
            'proactive_refresh_enabled': True
        }
    ]
    mock_supabase_client.table().execute.return_value = Mock(data=expiring_tokens)

    # Mock successful refresh
    mock_token_service.refresh_oauth_token.return_value = {
        'access_token': 'new_access_token',
        'refresh_token': 'new_refresh_token',
        'expires_at': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    }

    # Mock account lookup for history logging
    mock_supabase_client.table().execute.side_effect = [
        Mock(data=expiring_tokens),  # First call for getting tokens
        Mock(data=[{'id': 'account-1'}]),  # Second call for account lookup
        Mock(),  # Update call
        Mock()   # History insert
    ]

    await scheduler._check_and_refresh_tokens()

    # Verify refresh was called
    mock_token_service.refresh_oauth_token.assert_called_once_with(
        user_id='user-1',
        refresh_token='refresh_token_1'
    )


@pytest.mark.asyncio
async def test_refresh_single_token_success(scheduler, mock_supabase_client, mock_token_service):
    """Test successful single token refresh"""
    token_data = {
        'id': 'token-1',
        'user_id': 'user-1',
        'refresh_token': 'refresh_token_1',
        'expires_at': (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
        'refresh_failure_count': 0
    }

    # Mock successful refresh
    new_tokens = {
        'access_token': 'new_access_token',
        'refresh_token': 'new_refresh_token',
        'expires_at': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    }
    mock_token_service.refresh_oauth_token.return_value = new_tokens

    # Mock account lookup
    mock_supabase_client.table().execute.return_value = Mock(data=[{'id': 'account-1'}])

    result = await scheduler._refresh_single_token(token_data)

    assert result is True
    mock_token_service.refresh_oauth_token.assert_called_once()


@pytest.mark.asyncio
async def test_refresh_single_token_failure(scheduler, mock_supabase_client, mock_token_service):
    """Test failed single token refresh"""
    token_data = {
        'id': 'token-1',
        'user_id': 'user-1',
        'refresh_token': 'refresh_token_1',
        'expires_at': (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
        'refresh_failure_count': 1
    }

    # Mock refresh failure
    mock_token_service.refresh_oauth_token.side_effect = Exception("Refresh failed")

    result = await scheduler._refresh_single_token(token_data)

    assert result is False

    # Verify failure count was incremented
    update_calls = mock_supabase_client.table().update.call_args_list
    assert any('refresh_failure_count' in call[0][0] for call in update_calls)


@pytest.mark.asyncio
async def test_refresh_disables_after_max_failures(scheduler, mock_supabase_client, mock_token_service):
    """Test that proactive refresh is disabled after 3 failures"""
    token_data = {
        'id': 'token-1',
        'user_id': 'user-1',
        'refresh_token': 'refresh_token_1',
        'expires_at': (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
        'refresh_failure_count': 2  # One more failure will disable
    }

    # Mock refresh failure
    mock_token_service.refresh_oauth_token.side_effect = Exception("Refresh failed")

    result = await scheduler._refresh_single_token(token_data)

    assert result is False

    # Verify proactive refresh was disabled
    update_calls = mock_supabase_client.table().update.call_args_list
    for call in update_calls:
        if 'proactive_refresh_enabled' in call[0][0]:
            assert call[0][0]['proactive_refresh_enabled'] is False
            break
    else:
        pytest.fail("proactive_refresh_enabled was not set to False")


@pytest.mark.asyncio
async def test_manual_refresh_success(scheduler, mock_supabase_client, mock_token_service):
    """Test manual token refresh"""
    user_id = 'user-1'

    # Mock token lookup
    mock_supabase_client.table().execute.return_value = Mock(data=[{
        'id': 'token-1',
        'access_token': 'old_access',
        'refresh_token': 'refresh_1',
        'expires_at': (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
    }])

    # Mock successful refresh
    mock_token_service.refresh_oauth_token.return_value = {
        'access_token': 'new_access',
        'refresh_token': 'new_refresh',
        'expires_at': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    }

    result = await scheduler.manual_refresh(user_id)

    assert result['success'] is True
    assert result['token_id'] == 'token-1'
    assert 'successfully' in result['message'].lower()


@pytest.mark.asyncio
async def test_manual_refresh_no_tokens(scheduler, mock_supabase_client):
    """Test manual refresh when user has no tokens"""
    user_id = 'user-1'

    # Mock no tokens found
    mock_supabase_client.table().execute.return_value = Mock(data=[])

    result = await scheduler.manual_refresh(user_id)

    assert result['success'] is False
    assert 'No tokens found' in result['error']


@pytest.mark.asyncio
async def test_cleanup_old_history(scheduler, mock_supabase_client):
    """Test cleanup of old sync history"""
    # Mock deletion
    mock_supabase_client.table().delete().lt().execute.return_value = Mock(data=[
        {'id': 'old-1'},
        {'id': 'old-2'}
    ])

    await scheduler._cleanup_old_history()

    # Verify delete was called
    mock_supabase_client.table.assert_called_with('account_sync_history')
    mock_supabase_client.table().delete().lt.assert_called()


@pytest.mark.asyncio
async def test_log_refresh_history(scheduler, mock_supabase_client):
    """Test logging refresh history"""
    # Create separate mock tables for account lookup and history insert
    account_table = Mock()
    account_table.select = Mock(return_value=account_table)
    account_table.eq = Mock(return_value=account_table)
    account_table.limit = Mock(return_value=account_table)
    account_table.execute = Mock(return_value=Mock(data=[{'id': 'account-1'}]))

    history_table = Mock()
    history_table.insert = Mock(return_value=history_table)
    history_table.execute = Mock()

    # Setup table method to return different mocks based on table name
    def table_side_effect(table_name):
        if table_name == 'user_accounts':
            return account_table
        elif table_name == 'account_sync_history':
            return history_table
        return Mock()

    mock_supabase_client.table = Mock(side_effect=table_side_effect)

    await scheduler._log_refresh_history(
        user_id='user-1',
        token_id='token-1',
        success=True,
        error=None
    )

    # Verify history was logged
    history_table.insert.assert_called_once()

    # Check the logged data
    logged_data = history_table.insert.call_args[0][0]
    assert logged_data['user_account_id'] == 'account-1'
    assert logged_data['sync_status'] == 'success'
    assert logged_data['sync_type'] == 'scheduled'


@pytest.mark.asyncio
async def test_concurrent_refresh_tasks(scheduler, mock_supabase_client, mock_token_service):
    """Test handling multiple concurrent refresh tasks"""
    # Mock multiple expiring tokens
    expiring_tokens = [
        {
            'id': f'token-{i}',
            'user_id': f'user-{i}',
            'refresh_token': f'refresh_{i}',
            'expires_at': (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat(),
            'refresh_failure_count': 0,
            'proactive_refresh_enabled': True
        }
        for i in range(5)
    ]

    mock_supabase_client.table().execute.return_value = Mock(data=expiring_tokens)

    # Mock successful refreshes
    mock_token_service.refresh_oauth_token.return_value = {
        'access_token': 'new_access',
        'refresh_token': 'new_refresh',
        'expires_at': (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    }

    await scheduler._check_and_refresh_tokens()

    # Verify all tokens were processed
    assert mock_token_service.refresh_oauth_token.call_count == 5


@pytest.mark.asyncio
async def test_scheduler_exception_handling(scheduler, mock_supabase_client):
    """Test scheduler handles exceptions gracefully"""
    # Mock exception during token check
    mock_supabase_client.table.side_effect = Exception("Database error")

    # Should not raise exception
    await scheduler._check_and_refresh_tokens()

    # Reset for cleanup test
    mock_supabase_client.table.side_effect = None
    mock_supabase_client.table().delete().lt().execute.side_effect = Exception("Cleanup error")

    # Should not raise exception
    await scheduler._cleanup_old_history()