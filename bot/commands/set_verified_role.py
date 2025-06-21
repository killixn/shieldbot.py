from bot.client import client, initialize_guild_data
from discord import app_commands
import discord
import json

@client.tree.command(description='Setup the Verified Role.')
@app_commands.describe(role='The role to give to the user passing the verification.')
async def set_verified_role(interaction: discord.Interaction, role: discord.Role):
    filepath = 'data/roles.json'
    with open(filepath, 'r') as f:
        roles = json.load(f)
    
    guild_id = str(interaction.guild_id)

    if guild_id not in roles:
        initialize_guild_data(interaction.guild)
        with open(filepath, 'r') as f:
            roles = json.load(f)

    roles[guild_id] = role.id

    with open(filepath, 'w') as f:
        json.dump(roles, f)

    embed = discord.Embed(description=f'✅ The role has been set on **{role}**', color=2935808)
    await interaction.response.send_message(embed=embed)
