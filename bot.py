"""
🌊 Ripple by rusty.fae
24/7 music bot for some discord server
"""

import discord
from discord.ext import commands, tasks
import asyncio
import yt_dlp
import datetime
import time
import os
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────
BOT_TOKEN             = os.getenv("BOT_TOKEN")
VOICE_CHANNEL_ID      = int(os.getenv("VOICE_CHANNEL_ID"))
TEXT_CHANNEL_ID       = int(os.getenv("TEXT_CHANNEL_ID"))       # vc text chat — commands go here
NOW_PLAYING_CHANNEL_ID = int(os.getenv("NOW_PLAYING_CHANNEL_ID")) # dedicated now playing channel

LOFI_STREAMS = [
    {
        "url": "https://www.youtube.com/watch?v=jfKfPfyJRdk",
        "title": "lofi hip hop radio - beats to relax/study to",
        "artist": "Lofi Girl",
        "thumbnail": "https://i.ytimg.com/vi/jfKfPfyJRdk/maxresdefault.jpg",
    },
    {
        "url": "https://www.youtube.com/watch?v=4xDzrJKXOOY",
        "title": "synthwave radio - beats to chill/game to",
        "artist": "Lofi Girl",
        "thumbnail": "https://i.ytimg.com/vi/4xDzrJKXOOY/maxresdefault.jpg",
    },
    {
        "url": "https://www.youtube.com/watch?v=7NOSDKb0HlU",
        "title": "chillhop radio",
        "artist": "Chillhop Music",
        "thumbnail": "https://i.ytimg.com/vi/7NOSDKb0HlU/maxresdefault.jpg",
    },
    {
        "url": "https://www.youtube.com/watch?v=Dx5qFachd3A",
        "title": "vocal lofi hip hop radio",
        "artist": "College Music",
        "thumbnail": "https://i.ytimg.com/vi/Dx5qFachd3A/maxresdefault.jpg",
    },
    {
        "url": "https://www.youtube.com/watch?v=28KRPhVzCus",
        "title": "lofi hip hop radio 💤 beats to sleep/chill to",
        "artist": "Lofi Girl",
        "thumbnail": "https://i.ytimg.com/vi/28KRPhVzCus/maxresdefault.jpg",
    },
    {
        "url": "https://www.youtube.com/watch?v=TxOfaEwLhD4",
        "title": "Snowy Night ❄️ 24/7 Winter Lofi Beats to Relax & Study ❄️ Winter Café Radio to Feel Good",
        "artist": "Lofi on the Rooftop",
        "thumbnail": "https://i.ytimg.com/vi/TxOfaEwLhD4/maxresdefault.jpg",
    },
    {
        "url": "https://www.youtube.com/watch?v=blAFxjhg62k",
        "title": "Coffee Shop Radio - 24/7 Chill Lo-Fi & Jazzy Beats",
        "artist": "STEEZYASF##K",
        "thumbnail": "https://i.ytimg.com/vi/blAFxjhg62k/maxresdefault.jpg",
    },
    {
        "url": "https://www.youtube.com/watch?v=Lcdi9O2XB4E",
        "title": "tokyo night drive - lofi hiphop + chill + beats to sleep/relax/study to ✨",
        "artist": "TOKYO TONES",
        "thumbnail": "https://i.ytimg.com/vi/Lcdi9O2XB4E/maxresdefault.jpg",
    },
    {
        "url": "https://www.youtube.com/watch?v=vYIYIVmOo3Q",
        "title": "Calming Lofi Rain 🌧️ Chill Beats for Focus, Study & Sleep",
        "artist": "Lofi Tone Art",
        "thumbnail": "https://i.ytimg.com/vi/vYIYIVmOo3Q/maxresdefault.jpg",
    },
    {
        "url": "https://www.youtube.com/watch?v=TfmECBzmOn4",
        "title": "Lofi Hip Hop Radio 🍉 Relaxing Beats to Study, Sleep, Chill to 24/7",
        "artist": "Lofi Fruits",
        "thumbnail": "https://i.ytimg.com/vi/TfmECBzmOn4/maxresdefault.jpg",
    },
]

STREAM_ROTATION_HOURS = 1       # rotate every hour
PRESENCE_ROTATION_MINUTES = 60

STREAMING_PRESENCES = [
    (discord.ActivityType.listening, "lofi beats"),
    (discord.ActivityType.watching, "the waves flow"),
    (discord.ActivityType.playing, "chill vibes 24/7"),
]

STOPPED_PRESENCE = (discord.ActivityType.playing, "radio silence...")


# ─────────────────────────────────────────
#  YTDL + FFMPEG OPTIONS
# ─────────────────────────────────────────
YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",
    "cookiesfrombrowser": ("firefox",),
}

FFMPEG_OPTIONS = {
    "before_options": (
        "-reconnect 1 "
        "-reconnect_streamed 1 "
        "-reconnect_delay_max 5"
    ),
    "options": "-vn -bufsize 4096k",
}

# ─────────────────────────────────────────
#  BOT SETUP
# ─────────────────────────────────────────
intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.message_content = True

bot = commands.Bot(command_prefix="!wave ", intents=intents, help_command=None)

# ─────────────────────────────────────────
#  SILENCE DETECTOR — the silent death fix 🔧
# ─────────────────────────────────────────
class SilenceDetector(discord.PCMVolumeTransformer):
    """
    Wraps the audio source and tracks the last time
    audio bytes actually flowed. If nothing moves for
    silent_threshold seconds, the watchdog will catch it.
    """
    def __init__(self, source, volume=0.5):
        super().__init__(source, volume=volume)
        self.last_read = time.time()
        self.silent_threshold = 30  # seconds — bump to 45/60 if false positives

    def read(self):
        data = super().read()
        if data:
            self.last_read = time.time()
        return data

# ─────────────────────────────────────────
#  STATE
# ─────────────────────────────────────────
class BotState:
    def __init__(self):
        self.current_stream_index = 0
        self.voice_client: discord.VoiceClient | None = None
        self.now_playing_message: discord.Message | None = None
        self.start_time: datetime.datetime | None = None
        self.stream_url: str | None = None
        self.retries = 0
        self.MAX_RETRIES = 5
        self.stopped = False
        self.stop_task: asyncio.Task | None = None
        self.audio_source: SilenceDetector | None = None  # 🔧 track audio source

state = BotState()

# ─────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────
async def resolve_stream_url(youtube_url: str) -> str:
    loop = asyncio.get_event_loop()
    def _extract():
        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            return info["url"]
    return await loop.run_in_executor(None, _extract)


def current_stream_info() -> dict:
    return LOFI_STREAMS[state.current_stream_index]


def next_stream_index() -> int:
    return (state.current_stream_index + 1) % len(LOFI_STREAMS)


def make_now_playing_embed() -> discord.Embed:
    info = current_stream_info()

    if state.stopped:
        embed = discord.Embed(
            title="😔 Ripple is taking a break...",
            description="*The bot is eagerly and willingly waiting to come back!*",
            color=0x6b7280,
        )
        embed.set_footer(text="chill beats, big goals 🎧")
        embed.timestamp = datetime.datetime.utcnow()
        return embed

    uptime = ""
    if state.start_time:
        delta = datetime.datetime.utcnow() - state.start_time
        h, rem = divmod(int(delta.total_seconds()), 3600)
        m, s   = divmod(rem, 60)
        uptime = f"{h:02d}:{m:02d}:{s:02d}"

    embed = discord.Embed(
        title="🎵  Now Streaming",
        description=f"**{info['title']}**\n*by {info['artist']}*",
        color=0x8b5cf6,
    )
    embed.set_thumbnail(url=info["thumbnail"])
    embed.add_field(name="⏱  Session Uptime", value=uptime if uptime else "just started", inline=True)
    embed.add_field(name="📻  Stream", value=f"{state.current_stream_index + 1} of {len(LOFI_STREAMS)}", inline=True)
    embed.add_field(name="🔁  Rotates every", value=f"{STREAM_ROTATION_HOURS}h", inline=True)
    embed.set_footer(text="chill beats, big goals 🎧")
    embed.timestamp = datetime.datetime.utcnow()
    return embed


async def update_now_playing_embed():
    """Edit existing now playing message, or send a new one."""
    channel = bot.get_channel(NOW_PLAYING_CHANNEL_ID)
    if channel is None:
        return
    embed = make_now_playing_embed()
    if state.now_playing_message:
        try:
            await state.now_playing_message.edit(embed=embed)
            return
        except discord.NotFound:
            state.now_playing_message = None
    if state.now_playing_message:
        try:
            await state.now_playing_message.delete()
        except discord.NotFound:
            pass
    state.now_playing_message = await channel.send(embed=embed)


async def post_new_now_playing():
    """Always send a brand new now playing message (on stream change)."""
    channel = bot.get_channel(NOW_PLAYING_CHANNEL_ID)
    if channel is None:
        return
    if state.now_playing_message:
        try:
            await state.now_playing_message.delete()
        except discord.NotFound:
            pass
    embed = make_now_playing_embed()
    state.now_playing_message = await channel.send(embed=embed)


async def start_stream(stream_index: int | None = None, new_message: bool = False):
    """Connect to voice and start streaming."""
    if stream_index is not None:
        state.current_stream_index = stream_index

    info = current_stream_info()
    print(f"[Ripple] Resolving stream: {info['title']} ...")

    try:
        state.stream_url = await resolve_stream_url(info["url"])
    except Exception as e:
        print(f"[Ripple] yt-dlp error: {e}")
        await handle_stream_error()
        return

    voice_channel = bot.get_channel(VOICE_CHANNEL_ID)
    if voice_channel is None:
        print(f"[Ripple] ERROR: voice channel {VOICE_CHANNEL_ID} not found!")
        return

    if state.voice_client and state.voice_client.is_connected():
        if state.voice_client.channel.id != VOICE_CHANNEL_ID:
            await state.voice_client.move_to(voice_channel)
    else:
        try:
            state.voice_client = await voice_channel.connect()
        except Exception as e:
            print(f"[Ripple] Connect error: {e}")
            await handle_stream_error()
            return

    if state.voice_client.is_playing():
        state.voice_client.stop()

    # 🔧 use SilenceDetector instead of plain PCMVolumeTransformer
    raw_source = discord.FFmpegPCMAudio(state.stream_url, **FFMPEG_OPTIONS)
    source = SilenceDetector(raw_source, volume=0.5)
    state.audio_source = source  # 🔧 save reference for watchdog

    state.start_time = datetime.datetime.utcnow()
    state.retries = 0
    state.stopped = False
    activity_type, name = STREAMING_PRESENCES[presence_index % len(STREAMING_PRESENCES)]
    await bot.change_presence(status=discord.Status.idle, activity=discord.Activity(type=activity_type, name=name))

    def after_play(error):
        if error:
            print(f"[Ripple] Playback error: {error}")
            asyncio.run_coroutine_threadsafe(handle_stream_error(), bot.loop)

    state.voice_client.play(source, after=after_play)
    print(f"[Ripple] ▶ Now Streaming: {info['title']} by {info['artist']} (Stream {state.current_stream_index + 1}/{len(LOFI_STREAMS)})")

    if new_message:
        await post_new_now_playing()
    else:
        await update_now_playing_embed()


async def handle_stream_error():
    if state.stopped:
        return
    state.retries += 1
    if state.retries > state.MAX_RETRIES:
        print(f"[Ripple] Too many retries — rotating to next stream")
        state.retries = 0
        state.current_stream_index = next_stream_index()

    wait = min(2 ** state.retries, 60)
    print(f"[Ripple] Retrying in {wait}s (attempt {state.retries})")
    await asyncio.sleep(wait)
    await start_stream()


async def auto_resume(minutes: int):
    """Wait then auto resume after stop."""
    await asyncio.sleep(minutes * 60)
    if state.stopped:
        print(f"[Ripple] Auto resuming after {minutes} min break")
        await start_stream(new_message=True)


# ─────────────────────────────────────────
#  WATCHDOG
# ─────────────────────────────────────────
@tasks.loop(minutes=1)
async def watchdog():
    if state.stopped:
        await update_now_playing_embed()
        return

    # 🔧 silent death check — is audio actually flowing?
    if state.audio_source and state.voice_client and state.voice_client.is_playing():
        silent_for = time.time() - state.audio_source.last_read
        if silent_for > state.audio_source.silent_threshold:
            print(f"[Ripple] 💀 Silent death detected ({silent_for:.0f}s no audio) — restarting...")
            await start_stream()
            return

    if state.start_time:
        elapsed = datetime.datetime.utcnow() - state.start_time
        if elapsed >= datetime.timedelta(hours=STREAM_ROTATION_HOURS):
            print(f"[Ripple] Rotating stream after {STREAM_ROTATION_HOURS}h")
            await start_stream(next_stream_index(), new_message=True)
            return

    if state.voice_client is None or not state.voice_client.is_connected():
        print("[Ripple] Watchdog: disconnected — reconnecting...")
        await start_stream()
        return

    if not state.voice_client.is_playing() and not state.voice_client.is_paused():
        print("[Ripple] Watchdog: not playing — restarting stream...")
        await start_stream()
        return

    await update_now_playing_embed()


@watchdog.before_loop
async def before_watchdog():
    await bot.wait_until_ready()


# ─────────────────────────────────────────
#  CHANNEL GUARD
# ─────────────────────────────────────────
@bot.check
async def only_in_text_channel(ctx):
    """Bot only responds to commands in the VC text channel."""
    return ctx.channel.id == TEXT_CHANNEL_ID


# ─────────────────────────────────────────
#  STOP MODAL
# ─────────────────────────────────────────
class StopModal(discord.ui.Modal, title="⏸️ Stop Ripple"):
    duration = discord.ui.TextInput(
        label="How long to stop? (in minutes)",
        placeholder="e.g. 30",
        min_length=1,
        max_length=4,
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            minutes = int(self.duration.value)
            if minutes <= 0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message(
                "❌ Please enter a valid number of minutes!", ephemeral=True
            )
            return

        state.stopped = True
        state.audio_source = None  # 🔧 clear audio source on stop
        await bot.change_presence(status=discord.Status.idle, activity=discord.Activity(type=STOPPED_PRESENCE[0], name=STOPPED_PRESENCE[1]))
        print(f"[Ripple] ⏸️ Stopped by {interaction.user.name} ({interaction.user.id}) for {minutes} minutes")
        if state.voice_client and state.voice_client.is_playing():
            state.voice_client.stop()
        if state.voice_client and state.voice_client.is_connected():
            await state.voice_client.disconnect()
            state.voice_client = None

        if state.stop_task and not state.stop_task.done():
            state.stop_task.cancel()

        state.stop_task = asyncio.create_task(auto_resume(minutes))

        await update_now_playing_embed()

        await interaction.response.send_message(
            f"😔 Ripple is taking a **{minutes} minute** break...\n"
            f"*The bot is eagerly and willingly waiting to come back!*\n"
            f"Use `!wave resume` if you change your mind!",
            delete_after=10,
        )


# ─────────────────────────────────────────
#  COMMANDS
# ─────────────────────────────────────────
@bot.command(name="stop")
async def stop(ctx):
    await ctx.message.delete()
    if state.stopped:
        await ctx.send("⏸️ Ripple is already on a break! Use `!wave resume` to bring it back.", delete_after=8)
        return
    view = StopButtonView()
    await ctx.send(
        "⏸️ How long should Ripple take a break?",
        view=view,
        delete_after=30,
    )


class StopButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)

    @discord.ui.button(label="Set break time", style=discord.ButtonStyle.danger, emoji="⏸️")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(StopModal())


@bot.command(name="resume")
async def resume(ctx):
    await ctx.message.delete()
    if not state.stopped:
        await ctx.send("▶️ Ripple is already playing!", delete_after=8)
        return

    if state.stop_task and not state.stop_task.done():
        state.stop_task.cancel()

    print(f"[Ripple] ▶️ Resumed by {ctx.author.name} ({ctx.author.id})")
    await ctx.send("🎵 Ripple is back! *The bot missed you* 🌊", delete_after=8)
    await start_stream(new_message=True)


@bot.command(name="skip")
@commands.has_permissions(manage_guild=True)
async def skip(ctx):
    await ctx.message.delete()
    next_index = next_stream_index()
    print(f"[Ripple] ⏭️ Skipped by {ctx.author.name} ({ctx.author.id})")
    await ctx.send(f"⏭️ Skipping to next stream...", delete_after=5)
    await start_stream(next_index, new_message=True)


@bot.command(name="status")
@commands.has_permissions(manage_guild=True)
async def status(ctx):
    await ctx.message.delete()
    vc = state.voice_client
    uptime = ""
    if state.start_time:
        delta = datetime.datetime.utcnow() - state.start_time
        h, rem = divmod(int(delta.total_seconds()), 3600)
        m, s   = divmod(rem, 60)
        uptime = f"{h:02d}:{m:02d}:{s:02d}"

    playing = "✅ Streaming" if (vc and vc.is_playing()) else ("⏸️ Stopped" if state.stopped else "❌ Not playing")
    connected = "✅ Connected" if (vc and vc.is_connected()) else "❌ Disconnected"

    # 🔧 show silence detector info in status
    silent_for = ""
    if state.audio_source:
        secs = int(time.time() - state.audio_source.last_read)
        silent_for = f"{secs}s ago"

    embed = discord.Embed(title="🤖 Ripple Status", color=0x10b981)
    embed.add_field(name="Playback", value=playing, inline=True)
    embed.add_field(name="Voice", value=connected, inline=True)
    embed.add_field(name="Uptime", value=uptime if uptime else "N/A", inline=True)
    embed.add_field(name="Retries", value=str(state.retries), inline=True)
    embed.add_field(name="Last Audio", value=silent_for if silent_for else "N/A", inline=True)
    embed.add_field(name="Current Stream", value=current_stream_info()["title"], inline=False)
    embed.set_footer(text="chill beats, big goals 🎧")
    await ctx.send(embed=embed)


@status.error
async def status_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You need **Manage Server** permission for this.", delete_after=8)


@bot.command(name="help")
async def help_command(ctx):
    await ctx.message.delete()
    embed = discord.Embed(
        title="🌊 Ripple by rusty.fae",
        description="24/7 music bot for some discord server",
        color=0x8b5cf6,
    )
    embed.add_field(
        name="📻 Commands",
        value=(
            "`!wave resume`\n"
            "Bring Ripple back early from a break\n\n"
            "`!wave stop`\n"
            "Give Ripple a break (with custom time)\n\n"
            "`!wave help`\n"
            "Shows this menu"
        ),
        inline=False,
    )
    embed.set_footer(text="chill beats, big goals 🎧")
    await ctx.send(embed=embed)


presence_index = 0

@tasks.loop(minutes=PRESENCE_ROTATION_MINUTES)
async def presence_rotator():
    global presence_index
    if state.stopped:
        activity = discord.Activity(
            type=STOPPED_PRESENCE[0],
            name=STOPPED_PRESENCE[1]
        )
    else:
        activity_type, name = STREAMING_PRESENCES[presence_index % len(STREAMING_PRESENCES)]
        activity = discord.Activity(type=activity_type, name=name)
        presence_index += 1
    await bot.change_presence(status=discord.Status.idle, activity=activity)

@presence_rotator.before_loop
async def before_presence_rotator():
    await bot.wait_until_ready()


# ─────────────────────────────────────────
#  EVENTS
# ─────────────────────────────────────────
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        await ctx.message.delete()
        await ctx.send("❌ Ripple commands only work in the Silent Study Room chat!", delete_after=5)

@bot.event
async def on_ready():
    print(f"[Ripple] Logged in as {bot.user} ({bot.user.id})")
    activity = discord.Activity(type=discord.ActivityType.listening, name="lofi beats")
    await bot.change_presence(status=discord.Status.idle, activity=activity)
    watchdog.start()
    presence_rotator.start()
    await start_stream(new_message=True)


@bot.event
async def on_voice_state_update(member, before, after):
    if member.id != bot.user.id:
        return
    if before.channel and not after.channel and not state.stopped:
        print("[Ripple] Disconnected from voice — rejoining in 5s...")
        await asyncio.sleep(5)
        await start_stream()


# ─────────────────────────────────────────
#  RUN
# ─────────────────────────────────────────
if __name__ == "__main__":
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN not set in .env file!")
    if not VOICE_CHANNEL_ID or not TEXT_CHANNEL_ID or not NOW_PLAYING_CHANNEL_ID:
        raise ValueError("Channel IDs not set in .env file!")
    bot.run(BOT_TOKEN)
