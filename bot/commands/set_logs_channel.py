from bot.client import client, initialize_guild_data
from discord import app_commands
import discord
import json

@client.tree.command(description='Setup the Logs Channel.')
@app_commands.describe(channel='The channel to use for the logs.')
async def set_logs_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    filepath = 'data/logs_channels.json'
    with open(filepath, 'r') as f:
        channels = json.load(f)
    
    guild_id = str(interaction.guild_id)

    if guild_id not in channels:
        initialize_guild_data(interaction.guild)
        with open(filepath, 'r') as f:
            channels = json.load(f)

    channels[guild_id] = channel.id

    with open(filepath, 'w') as f:
        json.dump(channels, f)

    embed = discord.Embed(description=f'✅ The logs channel has been set to **{channel}**', color=2935808)
    await interaction.response.send_message(embed=embed)
