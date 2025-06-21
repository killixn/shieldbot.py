from bot.client import client, initialize_guild_data, PersistentView
import discord
import json

@client.tree.command(description='Send the Verification Message.')
async def send_verification(interaction: discord.Interaction):
    filepath = 'data/embeds.json'
    with open(filepath, 'r') as f:
        embeds = json.load(f)

    guild_id = str(interaction.guild_id)

    if guild_id not in embeds:
        initialize_guild_data(interaction.guild)
        with open(filepath, 'r') as f:
            embeds = json.load(f)

    embed_main = discord.Embed(
        title=embeds[guild_id]['title'],
        description=embeds[guild_id]['description'],
        color=3092790
    )
    channel = client.get_channel(interaction.channel_id)
    await channel.send(embed=embed_main, view=PersistentView())

    embed_response = discord.Embed(
        title="**Verification Message Sent:**",
        description="✅ The verification message has been successfully sent",
        color=2935808
    )
    await interaction.response.send_message(embed=embed_response, ephemeral=True)
