import os
import discord
import asyncio
from discord import app_commands
from discord.ext import commands
from notion_client import Client
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize Discord bot with intents
intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix='-', intents=intents)

# Initialize Notion client
notion = Client(auth=os.getenv("NOTION_SECRET"))
NOTION_DB_ID = os.getenv("NOTION_DATABASE_ID")

# Define choices for command options
TASK_TYPES = ["Custom", "App", "Feature", "Bug"]
SEVERITY_LEVELS = ["Very Low", "Low", "Medium", "High", "Severe"]
ZONES = ["Full-Stack", "CLI", "Database", "Backend", "Website", "Other"]

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('------')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
        bot.loop.create_task(monitor_notion_changes())
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.tree.command(name="add_task", description="Add a new task to the SunriseDB")
@app_commands.describe(
    title="Title of the task",
    task_type="Type of task",
    description="Description of the task",
    bounty="Bounty amount (optional)",
    severity="Severity level",
    zone="Zone/Area of the task"
)
@app_commands.choices(
    task_type=[app_commands.Choice(name=t, value=t) for t in TASK_TYPES],
    severity=[app_commands.Choice(name=s, value=s) for s in SEVERITY_LEVELS],
    zone=[app_commands.Choice(name=z, value=z) for z in ZONES]
)
async def add_task(
    interaction: discord.Interaction,
    title: str,
    task_type: app_commands.Choice[str],
    description: str,
    severity: app_commands.Choice[str],
    zone: app_commands.Choice[str],
    bounty: str = None
):
    """Add a new task to the Notion database"""
    await interaction.response.defer(ephemeral=True)
    
    try:
        print(f"[DEBUG] Adding task to Notion DB: {NOTION_DB_ID}")
        print(f"[DEBUG] Task details - Title: {title}, Type: {task_type.value}")
        
        new_page = {
            "parent": {"database_id": NOTION_DB_ID},
            "properties": {
                "Name": {"title": [{"text": {"content": title}}]},
                "Type": {"select": {"name": task_type.value}},
                "Description": {"rich_text": [{"text": {"content": description}}]},
                "Severity": {"select": {"name": severity.value}},
                "Zone": {"select": {"name": zone.value}},
                "Submitted By": {"rich_text": [{"text": {"content": str(interaction.user)}}]},
                "Date": {"date": {"start": datetime.now().isoformat()}}
            }
        }
        
        if bounty:
            new_page["properties"]["Bounty"] = {"rich_text": [{"text": {"content": bounty}}]}
        
        print(f"[DEBUG] Sending to Notion API: {new_page}")
        
        try:
            created_page = notion.pages.create(**new_page)
            print(f"[DEBUG] Task created successfully! Page ID: {created_page.get('id')}")
            await interaction.followup.send(f"✅ Task '{title}' has been added to the database!")
        except Exception as api_error:
            print(f"[ERROR] Notion API error: {str(api_error)}")
            if hasattr(api_error, 'response') and hasattr(api_error.response, 'content'):
                print(f"[ERROR] API response: {api_error.response.content}")
            raise
            
    except Exception as e:
        error_msg = f"❌ Error adding task: {str(e)}"
        print(f"[ERROR] {error_msg}")
        await interaction.followup.send(error_msg)
        print(f"Error: {str(e)}")

@bot.tree.command(name="my_tasks", description="View all tasks you've submitted")
async def my_tasks(interaction: discord.Interaction):
    """List all tasks submitted by the user"""
    await interaction.response.defer(ephemeral=True)
    
    try:
        response = notion.databases.query(
            database_id=NOTION_DB_ID,
            filter={
                "property": "Submitted By",
                "rich_text": {
                    "contains": str(interaction.user)
                }
            }
        )
        
        if not response["results"]:
            await interaction.followup.send("You haven't submitted any tasks yet!")
            return
        
        tasks = []
        for task in response["results"]:
            task_name = task["properties"]["Name"]["title"][0]["plain_text"]
            task_type = task["properties"]["Type"]["select"]["name"]
            task_status = task["properties"]["Status"]["status"]["name"] if task["properties"].get("Status") else "No status"
            tasks.append(f"• {task_name} [{task_type}] - {task_status}")
        
        response_message = "**Your submitted tasks:**\n" + "\n".join(tasks[:25])  # Limit to 25 tasks to avoid message limits
        if len(tasks) > 25:
            response_message += "\n... and more (showing 25 most recent)"
            
        await interaction.followup.send(response_message)
    except Exception as e:
        await interaction.followup.send(f"❌ Error retrieving tasks: {str(e)}")
        print(f"Error: {str(e)}")

@bot.tree.command(name="remove_task", description="Remove one of your tasks")
@app_commands.describe(task_name="Name of the task to remove")
async def remove_task(interaction: discord.Interaction, task_name: str):
    """Remove a task that you've submitted"""
    await interaction.response.defer(ephemeral=True)
    
    try:
        # First, find the task
        response = notion.databases.query(
            database_id=NOTION_DB_ID,
            filter={
                "and": [
                    {"property": "Name", "title": {"equals": task_name}},
                    {"property": "Submitted By", "rich_text": {"contains": str(interaction.user)}}
                ]
            }
        )
        
        if not response["results"]:
            await interaction.followup.send("❌ No matching task found or you don't have permission to delete it.")
            return
        
        # Archive the page (Notion doesn't actually delete pages, it archives them)
        notion.pages.update(
            page_id=response["results"][0]["id"],
            archived=True
        )
        
        await interaction.followup.send(f"✅ Task '{task_name}' has been removed.")
    except Exception as e:
        await interaction.followup.send(f"❌ Error removing task: {str(e)}")
        print(f"Error: {str(e)}")

@bot.tree.command(name="update_task", description="Update a task")
@app_commands.describe(task_name="Name of the task to update")
async def update_task(interaction: discord.Interaction, task_name: str):
    """Update a task that you've submitted"""
    await interaction.response.defer(ephemeral=True)
    
    try:
        # First, find the task
        response = notion.databases.query(
            database_id=NOTION_DB_ID,
            filter={
                "and": [
                    {"property": "Name", "title": {"equals": task_name}},
                    {"property": "Submitted By", "rich_text": {"contains": str(interaction.user)}}
                ]
            }
        )
        
        if not response["results"]:
            await interaction.followup.send("❌ No matching task found or you don't have permission to update it.")
            return
        
        # Update the page
        notion.pages.update(
            page_id=response["results"][0]["id"],
            archived=False
        )
        
        await interaction.followup.send(f"✅ Task '{task_name}' has been updated.")
    except Exception as e:
        await interaction.followup.send(f"❌ Error updating task: {str(e)}")
        print(f"Error: {str(e)}")

async def monitor_notion_changes():
    await bot.wait_until_ready()
    
    # Store the last cursor to only get new changes
    last_cursor = None
    
    while not bot.is_closed():
        try:
            # Get all pages from the database
            response = notion.databases.query(
                database_id=NOTION_DB_ID,
                start_cursor=last_cursor
            )
            
            for page in response.get("results", []):
                try:
                    # Get the current page with all properties
                    current_page = notion.pages.retrieve(page_id=page["id"])
                    properties = current_page.get("properties", {})
                    
                    # Check if task was marked as completed
                    completed = properties.get("Completed", {}).get("checkbox", False)
                    if completed:
                        # Get task details before deleting
                        title = properties.get("Name", {}).get("title", [{}])[0].get("text", {}).get("content", "Untitled")
                        discord_user_id = properties.get("Discord User ID", {}).get("rich_text", [{}])[0].get("plain_text")
                        channel_id = properties.get("Channel ID", {}).get("rich_text", [{}])[0].get("plain_text")
                        
                        # Delete the completed task
                        notion.pages.update(
                            page_id=page["id"],
                            archived=True
                        )
                        
                        # Debug print to check values
                        print(f"Task completed - Title: {title}, Channel ID: {channel_id}, User ID: {discord_user_id}")
                        
                        # Notify in the original channel
                        if channel_id and channel_id.strip():
                            try:
                                channel_id_int = int(channel_id)
                                print(f"Attempting to get channel with ID: {channel_id_int}")
                                channel = bot.get_channel(channel_id_int)
                                if channel:
                                    print(f"Found channel: {channel.name} in guild: {getattr(channel.guild, 'name', 'DM')}")
                                    await channel.send(f"✅ Task completed and removed: **{title}**")
                                    print("Successfully sent message to channel")
                                else:
                                    print(f"Could not find channel with ID: {channel_id_int}")
                            except ValueError as ve:
                                print(f"Invalid channel ID format: {channel_id} - {ve}")
                            except Exception as channel_error:
                                print(f"Failed to send channel message: {channel_error}")
                        else:
                            print("No channel ID found or empty channel ID")
                        
                        # Send DM to the user who created the task
                        if discord_user_id:
                            try:
                                user = await bot.fetch_user(int(discord_user_id))
                                await user.send(f"✅ Your task has been completed and removed: **{title}**")
                            except Exception as dm_error:
                                print(f"Failed to send DM: {dm_error}")
                        
                        print(f"Deleted completed task: {title}")
                        
                except Exception as page_error:
                    print(f"Error processing page {page.get('id')}: {page_error}")
            
            # Update the cursor for the next iteration
            last_cursor = response.get("next_cursor")
            if not last_cursor:
                break  # No more pages to process
            
        except Exception as e:
            print(f"Error monitoring Notion changes: {e}")
        
        # Wait before checking again
        await asyncio.sleep(60)  # Check every 1 hour


# Run the bot
if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_BOT_TOKEN"))