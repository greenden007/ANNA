import os
import discord
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

# Run the bot
if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_BOT_TOKEN"))