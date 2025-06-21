from bot.client import client, initialize_guild_data
from discord import app_commands
import discord
import json

@client.tree.command(description='Customize the BOT embeds')
@app_commands.describe(embed='The embed to customize.', part='The part of the embed to customize.', text='The text to use for the part.')
@app_commands.choices(embed=[
    app_commands.Choice(name='Main Embed', value='main'),
    app_commands.Choice(name='QR Embed', value='qr')
])
@app_commands.choices(part=[
    app_commands.Choice(name='Title', value='title'),
    app_commands.Choice(name='Description', value='description')
])
async def customize_embed(interaction: discord.Interaction, embed: str, part: str, text: str):
    filepath = 'data/embeds.json'
    with open(filepath, 'r') as f:
        embeds = json.load(f)

    guild_id = str(interaction.guild_id)

    if guild_id not in embeds:
        initialize_guild_data(interaction.guild)
        with open(filepath, 'r') as f:
            embeds = json.load(f)

    key_map = {
        ('main', 'title'): "title",
        ('main', 'description'): "description",
        ('qr', 'title'): "title_qr",
        ('qr', 'description'): "description_qr"
    }
    embed_key = key_map.get((embed, part))

    if embed_key:
        embeds[guild_id][embed_key] = text
        with open(filepath, 'w') as f:
            json.dump(embeds, f)

        part_name = "Title" if part == "title" else "Description"
        embed_response = discord.Embed(
            title=f"**Custom {part_name}:**",
            description=f"✅ The {embed.capitalize()} Embed {part_name.lower()} has been successfully changed",
            color=2935808
        )
        await interaction.response.send_message(embed=embed_response)
