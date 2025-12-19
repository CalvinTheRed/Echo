import discord
from discord.ext import commands
from dotenv import load_dotenv
import yt_dlp
import json
import os

# --- Load environment variables ---

load_dotenv()
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
AUDIO_MAP_PATH = os.getenv("AUDIO_MAP_PATH")
BOT_MESSAGE = os.getenv("BOT_MESSAGE")

# --- Bot setup ---

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)
looping = {}

# --- Storage helpers ---

if not os.path.exists(AUDIO_MAP_PATH):
    with open(AUDIO_MAP_PATH, "w") as f:
        json.dump({}, f)


def load_audio_map():
    with open(AUDIO_MAP_PATH, "r") as f:
        return json.load(f)


def save_audio_map(data):
    with open(AUDIO_MAP_PATH, "w") as f:
        json.dump(data, f, indent=2)

# --- Voice helpers ---

async def ensure_voice(ctx):
    if not ctx.author.voice:
        await ctx.send("You're not in a voice channel.")
        return None

    if ctx.voice_client is None:
        return await ctx.author.voice.channel.connect()

    return ctx.voice_client


async def get_stream_url(url):
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "noplaylist": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return info["url"]

# --- Events ---

@bot.event
async def on_ready():
    await bot.change_presence(
        activity=discord.Game(name=BOT_MESSAGE)
    )
    print(f"Bot is online as {bot.user}")

# --- Commands ---

@bot.command()
async def help(ctx):
    await ctx.send(
        "**Commands:**\n"
        "`!save <alias> <target YouTube url>` – Save a link\n"
        "`!rename <old alias> <new alias>` – Rename a saved link\n"
        "`!delete <alias>` – Delete a saved link\n"
        "`!list [partial alias]` – List all saved audio matching provided partial alias (optional)\n"
        "`!play <alias>` – Play saved audio\n"
        "`!loop <alias>` – Loop audio until stopped\n"
        "`!stop` – Stop playback"
    )

@bot.command()
async def save(ctx, alias: str, url: str):
    data = load_audio_map()
    gid = str(ctx.guild.id)

    data.setdefault(gid, {})[alias] = url
    save_audio_map(data)

    await ctx.send(f"Saved `{alias}`.")


@bot.command()
async def rename(ctx, old_alias: str, new_alias: str):
    data = load_audio_map()
    gid = str(ctx.guild.id)

    if gid not in data or old_alias not in data[gid]:
        await ctx.send(f"Audio `{old_alias}` not found.")
        return

    if new_alias in data[gid]:
        await ctx.send(f"Audio `{new_alias}` already exists.")
        return

    data[gid][new_alias] = data[gid].pop(old_alias)
    save_audio_map(data)

    await ctx.send(f"Renamed `{old_alias}` to `{new_alias}`.")


@bot.command()
async def delete(ctx, alias: str):
    data = load_audio_map()
    gid = str(ctx.guild.id)

    if gid not in data or alias not in data[gid]:
        await ctx.send("Audio alias not found.")
        return

    del data[gid][alias]
    save_audio_map(data)

    await ctx.send(f"Deleted `{alias}`.")


@bot.command()
async def play(ctx, alias: str):
    data = load_audio_map()
    gid = str(ctx.guild.id)

    if gid not in data or alias not in data[gid]:
        await ctx.send("Audio alias not found.")
        return

    vc = await ensure_voice(ctx)
    if not vc:
        return

    stream_url = await get_stream_url(data[gid][alias])

    audio = discord.FFmpegPCMAudio(
        stream_url,
        before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
    )

    def after_play(err):
        bot.loop.call_soon_threadsafe(
            lambda: bot.loop.create_task(vc.disconnect())
        )

    vc.stop()
    vc.play(audio, after=after_play)


@bot.command()
async def loop(ctx, alias: str):
    data = load_audio_map()
    gid = str(ctx.guild.id)

    if gid not in data or alias not in data[gid]:
        await ctx.send("Audio alias not found.")
        return

    vc = await ensure_voice(ctx)
    if not vc:
        return

    stream_url = await get_stream_url(data[gid][alias])
    looping[gid] = True

    def loop_audio(err=None):
        if not vc.is_connected() or not looping.get(gid):
            return

        audio = discord.FFmpegPCMAudio(
            stream_url,
            before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
        )
        vc.play(audio, after=loop_audio)

    vc.stop()
    loop_audio()


@bot.command()
async def stop(ctx):
    gid = str(ctx.guild.id)
    looping[gid] = False

    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.voice_client.disconnect()


@bot.command(name="list")
async def list_audio(ctx, partial_alias: str = None):
    data = load_audio_map()
    gid = str(ctx.guild.id)
    if gid not in data or not data[gid]:
        await ctx.send("No audio saved for this server.")
        return

    aliases = data[gid].keys()
    if partial_alias:
        partial_alias = partial_alias.lower()
        aliases = [alias for alias in aliases if partial_alias in alias.lower()]
    else:
        aliases = list(aliases)

    sorted_aliases = sorted(aliases, key=str.lower)
    await ctx.send("Saved audio:\n" + "\n".join(sorted_aliases))


# --- Main ---

if __name__ == "__main__":
    bot.run(BOT_TOKEN)
