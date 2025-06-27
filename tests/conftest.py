import os
import pytest
from unittest.mock import AsyncMock, MagicMock
import discord
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Mock Discord objects
@pytest.fixture
def mock_interaction():
    interaction = AsyncMock()
    interaction.user = MagicMock()
    interaction.user.id = 1234567890
    interaction.user.name = "TestUser"
    interaction.user.mention = "@TestUser"
    interaction.response = AsyncMock()
    interaction.followup = AsyncMock()
    return interaction

# Mock Notion client
@pytest.fixture
def mock_notion():
    notion = MagicMock()
    notion.pages = MagicMock()
    notion.databases = MagicMock()
    return notion
