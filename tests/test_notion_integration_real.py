"""Integration tests for Notion API interactions.

These tests make actual API calls to Notion and require valid credentials.
Set NOTION_SECRET and NOTION_DATABASE_ID environment variables to run these tests.
"""
import os
import pytest
from notion_client import Client
from datetime import datetime

# Skip these tests if we don't have the required environment variables
pytestmark = pytest.mark.skipif(
    not all([os.getenv("NOTION_SECRET"), os.getenv("NOTION_DATABASE_ID")]),
    reason="Notion credentials not provided"
)

# Test data
TEST_TASK = {
    "title": f"Test Task - {datetime.now().isoformat()}",
    "task_type": "Feature",
    "description": "This is a test task created by the test suite",
    "bounty": "100",
    "severity": "Medium",
    "zone": "Backend"
}

@pytest.fixture(scope="module")
def notion_client():
    """Create a Notion client for testing."""
    return Client(auth=os.getenv("NOTION_SECRET"))

@pytest.fixture
def cleanup_tasks(notion_client):
    """Clean up test tasks after each test."""
    # This will run after the test completes
    yield
    
    # Clean up any test tasks
    response = notion_client.databases.query(
        database_id=os.getenv("NOTION_DATABASE_ID"),
        filter={
            "property": "Name",
            "title": {"contains": "Test Task -"}
        }
    )
    
    for page in response.get("results", []):
        notion_client.pages.update(
            page_id=page["id"],
            archived=True
        )

@pytest.mark.integration
def test_create_and_retrieve_task(notion_client, cleanup_tasks):
    """Test creating a task in Notion and then retrieving it."""
    # Create a new page in the database
    new_page = {
        "parent": {"database_id": os.getenv("NOTION_DATABASE_ID")},
        "properties": {
            "Name": {"title": [{"text": {"content": TEST_TASK["title"]}}]},
            "Type": {"select": {"name": TEST_TASK["task_type"]}},
            "Description": {"rich_text": [{"text": {"content": TEST_TASK["description"]}}]},
            "Severity": {"select": {"name": TEST_TASK["severity"]}},
            "Zone": {"select": {"name": TEST_TASK["zone"]}},
            "Bounty": {"rich_text": [{"text": {"content": TEST_TASK["bounty"]}}]},
            "Submitted By": {"rich_text": [{"text": {"content": "Test User"}}]},
            "Date": {"date": {"start": datetime.now().isoformat()}}
        }
    }
    
    # Create the page
    created_page = notion_client.pages.create(**new_page)
    assert created_page is not None
    assert created_page["id"] is not None
    
    # Retrieve the page to verify
    retrieved_page = notion_client.pages.retrieve(page_id=created_page["id"])
    assert retrieved_page["id"] == created_page["id"]
    
    # Verify properties
    props = retrieved_page["properties"]
    assert props["Name"]["title"][0]["text"]["content"] == TEST_TASK["title"]
    assert props["Type"]["select"]["name"] == TEST_TASK["task_type"]
    assert props["Description"]["rich_text"][0]["text"]["content"] == TEST_TASK["description"]
    assert props["Severity"]["select"]["name"] == TEST_TASK["severity"]
    assert props["Zone"]["select"]["name"] == TEST_TASK["zone"]
    assert props["Bounty"]["rich_text"][0]["text"]["content"] == TEST_TASK["bounty"]

@pytest.mark.integration
def test_query_tasks(notion_client, cleanup_tasks):
    """Test querying tasks from the Notion database."""
    # First, create a test task
    new_page = {
        "parent": {"database_id": os.getenv("NOTION_DATABASE_ID")},
        "properties": {
            "Name": {"title": [{"text": {"content": TEST_TASK["title"]}}]},
            "Type": {"select": {"name": TEST_TASK["task_type"]}},
            "Description": {"rich_text": [{"text": {"content": TEST_TASK["description"]}}]},
            "Severity": {"select": {"name": TEST_TASK["severity"]}},
            "Zone": {"select": {"name": TEST_TASK["zone"]}},
            "Submitted By": {"rich_text": [{"text": {"content": "Test User"}}]},
            "Date": {"date": {"start": datetime.now().isoformat()}}
        }
    }
    created_page = notion_client.pages.create(**new_page)
    
    # Query the database for the task we just created
    response = notion_client.databases.query(
        database_id=os.getenv("NOTION_DATABASE_ID"),
        filter={
            "property": "Name",
            "title": {"equals": TEST_TASK["title"]}
        }
    )
    
    # Verify we found the task
    results = response.get("results", [])
    assert len(results) > 0
    assert results[0]["id"] == created_page["id"]
    assert results[0]["properties"]["Name"]["title"][0]["text"]["content"] == TEST_TASK["title"]

@pytest.mark.integration
def test_update_task(notion_client, cleanup_tasks):
    """Test updating a task in Notion."""
    # First, create a test task
    new_page = {
        "parent": {"database_id": os.getenv("NOTION_DATABASE_ID")},
        "properties": {
            "Name": {"title": [{"text": {"content": TEST_TASK["title"]}}]},
            "Type": {"select": {"name": TEST_TASK["task_type"]}},
            "Description": {"rich_text": [{"text": {"content": TEST_TASK["description"]}}]},
            "Severity": {"select": {"name": TEST_TASK["severity"]}},
            "Zone": {"select": {"name": TEST_TASK["zone"]}},
            "Submitted By": {"rich_text": [{"text": {"content": "Test User"}}]},
            "Date": {"date": {"start": datetime.now().isoformat()}}
        }
    }
    created_page = notion_client.pages.create(**new_page)
    
    # Update the task
    updated_description = "This is an updated description"
    notion_client.pages.update(
        page_id=created_page["id"],
        properties={
            "Description": {"rich_text": [{"text": {"content": updated_description}}]}
        }
    )
    
    # Retrieve the updated page
    updated_page = notion_client.pages.retrieve(page_id=created_page["id"])
    
    # Verify the update
    assert updated_page["properties"]["Description"]["rich_text"][0]["text"]["content"] == updated_description
