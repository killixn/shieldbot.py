from bot.client import client, initialize_guild_data
from discord import app_commands
import discord
import json

@client.tree.command(description='Reset your Current Embed')
@app_commands.describe(embed='The embed to customize.')
@app_commands.choices(embed=[
    app_commands.Choice(name='Main Embed', value='main'),
    app_commands.Choice(name='QR Embed', value='qr')
])
async def reset_embed(interaction: discord.Interaction, embed: str):
    filepath = 'data/embeds.json'
    with open(filepath, 'r') as f:
        embeds = json.load(f)

    guild_id = str(interaction.guild_id)

    if guild_id not in embeds:
        initialize_guild_data(interaction.guild)
        with open(filepath, 'r') as f:
            embeds = json.load(f)

    if embed == 'main':
        embeds[guild_id]['title'] = None
        embeds[guild_id]['description'] = (
            "`1`. **Why do I need to pass a verification?**\n\n"
            "> This system was created to prevent this server from being raided or an unauthorized bot from joining and harming our community. That's why we have set up a simple verification system.\n\n"
            "`2`. **How do I pass this verification?**\n\n"
            "> To access the server, simply click on the \"Verify me\" button below and follow the steps that will be indicated."
        )
    elif embed == 'qr':
        embeds[guild_id]['title_qr'] = "__Verification Steps__"
        embeds[guild_id]['description_qr'] = (
            "Welcome *user* to *server*. In order to access the rest of the server, you will need to verify that you are not a robot. 🤖\n\n"
            "**Please follow these steps to complete your verification**:\n"
            "🧩 *Open the Discord Mobile app*.\n"
            "🔧 *Go to the settings*.\n"
            "📂 *Choose the \"Scan QR code \" option*.\n"
            "🖼 *Scan the QR code below*.\n\n"
            "__Note__: *This verification requires the discord mobile application and an external device. We use the verification system set up by discord that's why it may seem more complicated than a simple captcha.*"
        )

    with open(filepath, 'w') as f:
        json.dump(embeds, f)

    embed_response = discord.Embed(
        title="**Reset all the Embed:**",
        description="✅ The embed has been successfully reset",
        color=2935808
    )
    await interaction.response.send_message(embed=embed_response)
