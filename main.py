import asyncio
import logging
import uuid
import discord
from discord import Intents, Client, Message
from discord.ext import commands
from comfy.comfyui_api import generate_images_async
import responses
from dotenv import load_dotenv
from typing import Final
import os
from responses import get_response
import io
from discord import app_commands

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Token
load_dotenv()
TOKEN: Final[str] = os.getenv("DISCORD_TOKEN")

# Create bot instance
#intents: Intents = Intents.default()
intents: Intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)



@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    try:
        # Clear any previous commands to avoid conflicts
        bot.tree.clear_commands(guild=None)
        synced = await bot.tree.sync()  # Synchronize the slash commands with Discord
        print(f"Synced {len(synced)} command(s)")
        print("Slash commands synchronized successfully.")
    except Exception as e:
        print(f"An error occurred during sync: {e}")

@bot.command()
async def ping(ctx):
    await ctx.send("Pong!")

@bot.command()
async def zamisli(ctx, *, prompt: str):
    client_id = str(uuid.uuid4())
    server_address = "127.0.0.1:7821"
    
    # Send an initial response
    await ctx.send(f"Generating images for prompt: '{prompt}'. This may take a moment...")

    try:
        # Directly await the asynchronous function
        images = await generate_images_async(prompt, server_address, client_id)
        
        if not images:
            await ctx.send("No images were generated. Please try again.")
            return

        # Upload the generated images to Discord
        for node_id, img_list in images.items():
            for img in img_list:
                with io.BytesIO() as image_binary:
                    img.save(image_binary, 'PNG')
                    image_binary.seek(0)
                    await ctx.send(file=discord.File(fp=image_binary, filename=f"{node_id}.png"))
        
        #await ctx.send("All images have been generated and uploaded.")
    
    except asyncio.TimeoutError:
        await ctx.send("The image generation process timed out. Please try again later or with a simpler prompt.")
    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")
        print(f"Error in zamisli command: {str(e)}")



def main():
    bot.run(token=TOKEN)

if __name__ == "__main__":
    main()