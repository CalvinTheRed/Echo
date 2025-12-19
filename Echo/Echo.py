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
        "`!save <name> <target YouTube url>` – Save a link\n"
        "`!rename <old name> <new name>` – Rename a saved link\n"
        "`!delete <name>` – Delete a saved link\n"
        "`!list <fragment>` – List all saved audio matching fragment (optional)\n"
        "`!play <name>` – Play saved audio\n"
        "`!loop <name>` – Loop audio until stopped\n"
        "`!stop` – Stop playback"
    )

@bot.command()
async def save(ctx, name: str, url: str):
    data = load_audio_map()
    gid = str(ctx.guild.id)

    data.setdefault(gid, {})[name] = url
    save_audio_map(data)

    await ctx.send(f"Saved `{name}`.")


@bot.command()
async def rename(ctx, old_name: str, new_name: str):
    data = load_audio_map()
    gid = str(ctx.guild.id)

    if gid not in data or old_name not in data[gid]:
        await ctx.send(f"Audio `{old_name}` not found.")
        return

    if new_name in data[gid]:
        await ctx.send(f"Audio `{new_name}` already exists.")
        return

    data[gid][new_name] = data[gid].pop(old_name)
    save_audio_map(data)

    await ctx.send(f"Renamed `{old_name}` to `{new_name}`.")


@bot.command()
async def delete(ctx, name: str):
    data = load_audio_map()
    gid = str(ctx.guild.id)

    if gid not in data or name not in data[gid]:
        await ctx.send("Audio name not found.")
        return

    del data[gid][name]
    save_audio_map(data)

    await ctx.send(f"Deleted `{name}`.")


@bot.command()
async def play(ctx, name: str):
    data = load_audio_map()
    gid = str(ctx.guild.id)

    if gid not in data or name not in data[gid]:
        await ctx.send("Audio name not found.")
        return

    vc = await ensure_voice(ctx)
    if not vc:
        return

    stream_url = await get_stream_url(data[gid][name])

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
async def loop(ctx, name: str):
    data = load_audio_map()
    gid = str(ctx.guild.id)

    if gid not in data or name not in data[gid]:
        await ctx.send("Audio name not found.")
        return

    vc = await ensure_voice(ctx)
    if not vc:
        return

    stream_url = await get_stream_url(data[gid][name])
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
async def list_audio(ctx, fragment: str = None):
    data = load_audio_map()
    gid = str(ctx.guild.id)
    if gid not in data or not data[gid]:
        await ctx.send("No audio saved for this server.")
        return

    names = data[gid].keys()
    if fragment:
        fragment = fragment.lower()
        names = [name for name in names if fragment in name.lower()]
    else:
        names = list(names)

    sorted_names = sorted(names, key=str.lower)
    await ctx.send("Saved audio names:\n" + "\n".join(sorted_names))


# --- Main ---

if __name__ == "__main__":
    bot.run(BOT_TOKEN)
