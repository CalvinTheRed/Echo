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
TMP_FILENAME = os.getenv("TMP_FILENAME")

# --- Bot setup ---

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Load or initialize JSON storage ---

if not os.path.exists(AUDIO_MAP_PATH):
    with open(AUDIO_MAP_PATH, "w") as f:
        json.dump({}, f)


def load_audio_map():
    with open(AUDIO_MAP_PATH, "r") as f:
        return json.load(f)


def save_audio_map(data):
    with open(AUDIO_MAP_PATH, "w") as f:
        json.dump(data, f, indent=2)

# --- Helper functions ---

async def ensure_voice(ctx):
    if not ctx.author.voice:
        await ctx.send("You're not in a voice channel.")
        return None

    channel = ctx.author.voice.channel
    permissions = channel.permissions_for(ctx.guild.me)

    if not permissions.connect:
        await ctx.send("I don't have permission to connect to this voice channel.")
        return None
    if not permissions.speak:
        await ctx.send("I can join, but I don't have permission to speak in this channel.")
        return None

    if ctx.voice_client is None:
        return await channel.connect()
    return ctx.voice_client


async def get_audio_stream(ctx, url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'noplaylist': True,
        'socket_timeout': 10,
        'outtmpl': 'tmp.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    try:
        await ctx.send("Extracting audio info...")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            duration = info.get("duration", 0)

            if info.get("format_note") == "DRM":
                await ctx.send("Warning - This video may be DRM-protected. Playback could fail.")

            if duration < 300:
                await ctx.send("Downloading audio file...")
                ydl.download([url])
                await ctx.send("Download complete.")
                return TMP_FILENAME
            else:
                return info['url']
    except Exception as e:
        await ctx.send(f"Failed to fetch audio: `{e}`")
        return None


def delete_tmp_file():
    print(f"Deleting {TMP_FILENAME}...")
    try:
        if os.path.exists(TMP_FILENAME):
            os.remove(TMP_FILENAME)
            print(f"Successfully deleted {TMP_FILENAME}.")
        else:
            print(f"Error deleting {TMP_FILENAME}: does not exist.")
    except Exception as e:
        print(f"Error deleting {TMP_FILENAME}: {e}")

# --- Utility ---

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")


# --- Commands ---

@bot.command()
async def save(ctx, name: str, url: str):
    data = load_audio_map()
    gid = str(ctx.guild.id)
    if gid not in data:
        data[gid] = {}
    data[gid][name] = url
    save_audio_map(data)
    await ctx.send(f"Saved `{name}` for this server.")


@bot.command()
async def delete(ctx, name: str):
    data = load_audio_map()
    gid = str(ctx.guild.id)
    if gid in data and name in data[gid]:
        del data[gid][name]
        save_audio_map(data)
        await ctx.send(f"Deleted `{name}` from this server.")
    else:
        await ctx.send("Audio name not found.")



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


@bot.command()
async def play(ctx, name: str):
    data = load_audio_map()
    gid = str(ctx.guild.id)
    if gid not in data or name not in data[gid]:
        await ctx.send("Audio name not found for this server.")
        return

    vc = await ensure_voice(ctx)
    if not vc:
        return

    source = await get_audio_stream(ctx, data[gid][name])
    if not source:
        await ctx.send("Failed to get audio stream.")
        return

    if os.path.exists(source):
        audio_source = discord.FFmpegPCMAudio(source)
    else:
        audio_source = discord.FFmpegPCMAudio(source, before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5")


    def after_play(err):
        delete_tmp_file()
        bot.loop.call_soon_threadsafe(lambda: bot.loop.create_task(vc.disconnect()))

    vc.stop()
    vc.play(audio_source, after=after_play)


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

    source = await get_audio_stream(ctx, data[gid][name])
    if not source:
        await ctx.send("Failed to get audio stream.")
        return

    is_local = os.path.exists(source)

    def loop_audio(err=None):
        if not vc.is_connected():
            if is_local and os.path.exists(source):
                os.remove(source)
            return

        if is_local:
            audio_source = discord.FFmpegPCMAudio(source)
        else:
            audio_source = discord.FFmpegPCMAudio(
                source,
                before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
            )

        vc.play(audio_source, after=loop_audio)

    vc.stop()
    loop_audio()


@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.voice_client.disconnect()
    delete_tmp_file()


# --- Main ---

if __name__ == "__main__":
    bot.run(BOT_TOKEN)
