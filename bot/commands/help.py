from bot.client import client, initialize_guild_data
from discord import app_commands
import discord

@client.tree.command(description='Help command.')
@app_commands.describe(command='Get help on a specific order.')
@app_commands.choices(command=[
    app_commands.Choice(name='Setup Logs Channel', value='logs'),
    app_commands.Choice(name='Setup Verified Role', value='role'),
    app_commands.Choice(name='Setup Embeds', value='embed'),
    app_commands.Choice(name='Verification', value='verif')
])
async def help(interaction: discord.Interaction, command: str = None):
    if command is None:
        embed = discord.Embed(
            title='🏠 Help command',
            description=(
                'Use `/help <command>` to see the details of a command.\n'
                'Use `/command None` to disable the command.\n\n'
                '**Some useful links:**\n'
                '> [Support Discord](https://discord.gg/qrcode)\n\n'
                '**All commands:**\n'
                '> `/logs #channel` - change the logs channel\n'
                '> `/role @role` - change the role given to the players passing the verification\n'
                '> `/embed` - display or modify the embeds used during the verification process\n'
                '> `/verif` - sends a verification message allowing people to check themselves'
            ),
            color=5003474
        )
        embed.set_thumbnail(url=client.user.avatar)
        embed.set_footer(text="Made by Astraa")

    elif command == "logs":
        embed = discord.Embed(
            title='🛠 Logs command',
            description='Display or change the logs channel.\n\n**Format**: `/logs #channel`',
            color=5003474
        )

    elif command == "role":
        embed = discord.Embed(
            title='🛠 Role command',
            description='Display or change the role given to the players passing the verification.\n\n**Format**: `/role @role`',
            color=5003474
        )

    elif command == "embed":
        embed = discord.Embed(
            title='🛠 Embed command',
            description='Display or modify the embeds used during the verification process\n\n**Format**: `/embed`',
            color=5003474
        )

    elif command == "verif":
        embed = discord.Embed(
            title='🛠 Verification command',
            description=(
                'Sends a verification message allowing people to check themselves.\n'
                '__Note__: *To use this command, you must first have set up a log room and a role to give after the verification.*\n\n'
                '**Format**: `/verif`'
            ),
            color=5003474
        )

    else:
        embed = discord.Embed(
            title='❌ Unknown command',
            description='The specified command does not exist.',
            color=13500416
        )

    await interaction.response.send_message(embed=embed)
