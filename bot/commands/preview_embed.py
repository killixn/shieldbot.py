from bot.client import client, initialize_guild_data
from discord import app_commands
import discord
import json

@client.tree.command(description='Visualize your Current Embed')
@app_commands.describe(embed='The embed to visualize.')
@app_commands.choices(embed=[
    app_commands.Choice(name='Main Embed', value='main'),
    app_commands.Choice(name='QR Embed', value='qr')
])
async def preview_embed(interaction: discord.Interaction, embed: str):
    filepath = 'data/embeds.json'
    with open(filepath, 'r') as f:
        embeds = json.load(f)

    guild_id = str(interaction.guild_id)

    if guild_id not in embeds:
        initialize_guild_data(interaction.guild)
        with open(filepath, 'r') as f:
            embeds = json.load(f)

    if embed == 'main':
        if embeds[guild_id]['title'] is None and embeds[guild_id]['description'] is None:
            embeds[guild_id]['title'] = None
            embeds[guild_id]['description'] = (
                "`1`. **Why do I need to pass a verification?**\n\n"
                "> This system was created to prevent this server from being raided or an unauthorized bot from joining and harming our community. That's why we have set up a simple verification system.\n\n"
                "`2`. **How do I pass this verification?**\n\n"
                "> To access the server, simply click on the \"Verify me\" button below and follow the steps that will be indicated."
            )

        embed_visualiser = discord.Embed(
            title=embeds[guild_id]["title"],
            description=embeds[guild_id]["description"],
            color=3092790
        )
        await interaction.response.send_message(embed=embed_visualiser)

    elif embed == 'qr':
        if embeds[guild_id]['title_qr'] is None and embeds[guild_id]['description_qr'] is None:
            embeds[guild_id]['title_qr'] = "__Verification step__"
            embeds[guild_id]['description_qr'] = (
                "Welcome *user* to *server*. In order to access the rest of the server, you will need to verify that you are not a robot. 🤖\n\n"
                "**Please follow these steps to complete your verification**:\n"
                "🧩 *Open the Discord Mobile app*.\n"
                "🔧 *Go to the settings*.\n"
                "📂 *Choose the \"Scan QR code \" option*.\n"
                "🖼 *Scan the QR code below*.\n\n"
                "__Note__: *This verification requires the discord mobile application and an external device. We use the verification system set up by discord that's why it may seem more complicated than a simple captcha."
            )

        embed_visualiser = discord.Embed(
            title=embeds[guild_id]["title_qr"],
            description=embeds[guild_id]["description_qr"],
            color=3092790
        )
        embed_visualiser.set_footer(text="Note: captcha expires in 2minutes (click again on the button below if it expires)")
        embed_visualiser.set_thumbnail(url="https://emoji.discord.st/emojis/aa142d2c-681c-45a2-99e9-a6e63849b351.png")
        embed_visualiser.set_image(url="https://cdn.discordapp.com/attachments/826581697436581919/1001464425691222026/qr_code.png")
        await interaction.response.send_message(embed=embed_visualiser)
