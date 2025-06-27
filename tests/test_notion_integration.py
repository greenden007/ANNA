import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os
from datetime import datetime

# Test data
class MockChoice:
    def __init__(self, value):
        self.value = value

SAMPLE_TASK = {
    "title": "Test Task",
    "task_type": MockChoice("Feature"),
    "description": "Test description",
    "bounty": "100",
    "severity": MockChoice("Medium"),
    "zone": MockChoice("Backend")
}

SAMPLE_NOTION_RESPONSE = {
    "results": [
        {
            "id": "test-id-123",
            "properties": {
                "Name": {"title": [{"text": {"content": "Test Task"}}]},
                "Status": {"select": {"name": "To Do"}},
                "Created": {"date": {"start": "2023-01-01"}},
                "Submitter": {"rich_text": [{"text": {"content": "TestUser"}}]}
            }
        }
    ]
}

@pytest.mark.asyncio
async def test_add_task_success(mock_interaction, mock_notion):
    # Arrange
    from main import add_task
    
    # Set up mock interaction
    mock_interaction.response.defer = AsyncMock()
    mock_interaction.followup.send = AsyncMock()
    
    # Mock Notion response
    mock_notion.pages.create.return_value = {"id": "test-id-123"}
    
    # Act
    with patch('main.notion', mock_notion):
        await add_task.callback(
            interaction=mock_interaction,
            title=SAMPLE_TASK["title"],
            task_type=SAMPLE_TASK["task_type"],
            description=SAMPLE_TASK["description"],
            bounty=SAMPLE_TASK["bounty"],
            severity=SAMPLE_TASK["severity"],
            zone=SAMPLE_TASK["zone"]
        )
    
    # Assert
    mock_interaction.response.defer.assert_called_once()
    
    # Check that the Notion API was called with the correct parameters
    mock_notion.pages.create.assert_called_once()
    
    # Get the arguments passed to the Notion API
    call_args = mock_notion.pages.create.call_args[1]
    assert call_args["parent"]["database_id"] == os.getenv("NOTION_DATABASE_ID")
    
    # Check the task properties
    properties = call_args["properties"]
    assert properties["Name"]["title"][0]["text"]["content"] == "Test Task"
    assert properties["Type"]["select"]["name"] == "Feature"
    assert properties["Description"]["rich_text"][0]["text"]["content"] == "Test description"
    assert properties["Severity"]["select"]["name"] == "Medium"
    assert properties["Zone"]["select"]["name"] == "Backend"
    
    # Check that the success message was sent
    args, kwargs = mock_interaction.followup.send.call_args
    assert "✅ Task 'Test Task' has been added to the database!" in args[0]

@pytest.mark.asyncio
async def test_add_task_error(mock_interaction, mock_notion):
    # Arrange
    from main import add_task
    
    mock_interaction.response.defer = AsyncMock()
    mock_interaction.followup.send = AsyncMock()
    
    # Make Notion raise an exception
    mock_notion.pages.create.side_effect = Exception("Notion API error")
    
    # Act & Assert
    with patch('main.notion', mock_notion):
        await add_task.callback(
            interaction=mock_interaction,
            title=SAMPLE_TASK["title"],
            task_type=SAMPLE_TASK["task_type"],
            description=SAMPLE_TASK["description"],
            bounty=SAMPLE_TASK["bounty"],
            severity=SAMPLE_TASK["severity"],
            zone=SAMPLE_TASK["zone"]
        )
    
    # Check that the error message was sent
    args, kwargs = mock_interaction.followup.send.call_args
    assert "❌ Error adding task" in args[0]

@pytest.mark.asyncio
async def test_remove_task_success(mock_interaction, mock_notion):
    # Arrange
    from main import remove_task
    
    mock_interaction.response.defer = AsyncMock()
    mock_interaction.followup.send = AsyncMock()
    
    # Mock Notion response
    mock_notion.databases.query.return_value = SAMPLE_NOTION_RESPONSE
    
    # Act
    with patch('main.notion', mock_notion):
        await remove_task.callback(
            interaction=mock_interaction,
            task_name="Test Task"
        )
    
    # Assert
    mock_notion.pages.update.assert_called_once()
    
    # Check that the success message was sent
    args, kwargs = mock_interaction.followup.send.call_args
    assert "✅ Task 'Test Task' has been removed." in args[0]

@pytest.mark.asyncio
async def test_remove_task_not_found(mock_interaction, mock_notion):
    # Arrange
    from main import remove_task
    
    mock_interaction.response.defer = AsyncMock()
    mock_interaction.followup.send = AsyncMock()
    
    # Mock empty Notion response
    mock_notion.databases.query.return_value = {"results": []}
    
    # Act
    with patch('main.notion', mock_notion):
        await remove_task.callback(
            interaction=mock_interaction,
            task_name="Nonexistent Task"
        )
    
    # Assert that the Notion API was not called successfully
    mock_notion.pages.create.assert_not_called()
    
    # Check that the error message was sent
    args, kwargs = mock_interaction.followup.send.call_args
    assert "❌ No matching task found or you don't have permission to delete it." in args[0]
