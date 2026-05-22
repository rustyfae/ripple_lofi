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
BOT_TOKEN              = os.getenv("BOT_TOKEN")
VOICE_CHANNEL_ID       = int(os.getenv("VOICE_CHANNEL_ID"))
NOW_PLAYING_CHANNEL_ID = int(os.getenv("NOW_PLAYING_CHANNEL_ID"))

# Multiple command channels — comma separated in .env
# e.g. TEXT_CHANNEL_IDS=123456789,987654321,111222333
_raw_ids = os.getenv("TEXT_CHANNEL_IDS", "")
TEXT_CHANNEL_IDS: set[int] = {int(x.strip()) for x in _raw_ids.split(",") if x.strip()}

LOFI_STREAMS = [
    
    {
        "url": "https://www.youtube.com/watch?v=Dx5qFachd3A",
        "title": "vocal lofi hip hop radio",
        "artist": "College Music",
        "thumbnail": "https://i.ytimg.com/vi/Dx5qFachd3A/maxresdefault.jpg",
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
        "url": "https://www.youtube.com/watch?v=TxOfaEwLhD4",
        "title": "Snowy Night ❄️ 24/7 Winter Lofi Beats to Relax & Study",
        "artist": "Lofi on the Rooftop",
        "thumbnail": "https://i.ytimg.com/vi/TxOfaEwLhD4/maxresdefault.jpg",
    },
    {
        "url": "https://www.youtube.com/watch?v=blAFxjhg62k",
        "title": "Coffee Shop Radio - 24/7 Chill Lo-Fi & Jazzy Beats",
        "artist": "STEEZYASFK",
        "thumbnail": "https://i.ytimg.com/vi/blAFxjhg62k/maxresdefault.jpg",
    },
    {
        "url": "https://www.youtube.com/watch?v=Lcdi9O2XB4E",
        "title": "tokyo night drive - lofi hiphop + chill beats",
        "artist": "TOKYO TONES",
        "thumbnail": "https://i.ytimg.com/vi/Lcdi9O2XB4E/maxresdefault.jpg",
    },
    {
        "url": "https://www.youtube.com/watch?v=vYIYIVmOo3Q",
        "title": "Calming Lofi Rain - Chill Beats for Focus & Sleep",
        "artist": "Lofi Tone Art",
        "thumbnail": "https://i.ytimg.com/vi/vYIYIVmOo3Q/maxresdefault.jpg",
    },
    {
        "url": "https://www.youtube.com/watch?v=TfmECBzmOn4",
        "title": "Lofi Hip Hop Radio - Relaxing Beats 24/7",
        "artist": "Lofi Fruits",
        "thumbnail": "https://i.ytimg.com/vi/TfmECBzmOn4/maxresdefault.jpg",
    },
]

STREAM_ROTATION_HOURS    = 1
PRESENCE_ROTATION_MINUTES = 60

STREAMING_PRESENCES = [
    (discord.ActivityType.listening, "lofi beats"),
    (discord.ActivityType.watching, "the waves flow"),
    (discord.ActivityType.playing,   "chill vibes 24/7"),
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
    # "cookiesfrombrowser": ("firefox",),  # uncomment if YouTube blocks without cookies
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
intents.voice_states  = True
intents.guilds        = True
intents.message_content = True

bot = commands.Bot(command_prefix="!wave ", intents=intents, help_command=None)

# ─────────────────────────────────────────
#  SILENCE DETECTOR
# ─────────────────────────────────────────
class SilenceDetector(discord.PCMVolumeTransformer):
    def __init__(self, source, volume=0.5):
        super().__init__(source, volume=volume)
        self.last_read = time.time()
        self.silent_threshold = 45

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
        self.current_stream_index  = 0
        self.voice_client: discord.VoiceClient | None = None
        self.now_playing_message: discord.Message | None = None
        self.bot_start_time: datetime.datetime | None = None   # when bot came online
        self.stream_start_time: datetime.datetime | None = None  # when current stream started
        self.stream_url: str | None = None
        self.retries    = 0
        self.MAX_RETRIES = 5
        self.stopped    = False
        self.stopped_by: str | None = None          # who stopped it
        self.stop_resume_time: datetime.datetime | None = None  # when it will auto resume
        self.stop_task: asyncio.Task | None = None
        self.audio_source: SilenceDetector | None = None
        self.connecting = False

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
    now  = datetime.datetime.now(datetime.timezone.utc)

    # ── Bot uptime ──────────────────────────────────
    bot_uptime = ""
    if state.bot_start_time:
        delta = now - state.bot_start_time
        h, rem = divmod(int(delta.total_seconds()), 3600)
        m, s   = divmod(rem, 60)
        bot_uptime = f"{h:02d}:{m:02d}:{s:02d}"

    # ── STOPPED embed ───────────────────────────────
    if state.stopped:
        remaining_str = "calculating..."
        if state.stop_resume_time:
            remaining = state.stop_resume_time - now
            total_secs = max(0, int(remaining.total_seconds()))
            rm, rs = divmod(total_secs, 60)
            remaining_str = f"{rm}m {rs:02d}s"

        embed = discord.Embed(
            title="😔 Ripple is taking a break...",
            description=(
                f"Stopped by **{state.stopped_by or 'someone'}**\n"
                f"⏱ **{remaining_str}** remaining"
            ),
            color=0x6b7280,
        )
        embed.add_field(name="🤖 Bot Uptime", value=bot_uptime if bot_uptime else "N/A", inline=True)
        embed.set_footer(text="chill beats, big goals 🎧")
        embed.timestamp = now
        return embed

    # ── PLAYING embed ───────────────────────────────
    embed = discord.Embed(
        title="🎵  Now Streaming",
        description=f"**{info['title']}**\n*by {info['artist']}*",
        color=0x8b5cf6,
    )
    embed.set_thumbnail(url=info["thumbnail"])
    embed.add_field(name="🤖 Bot Uptime",   value=bot_uptime if bot_uptime else "just started", inline=True)
    embed.add_field(name="📻  Stream",      value=f"{state.current_stream_index + 1} of {len(LOFI_STREAMS)}", inline=True)
    embed.add_field(name="🔁  Rotates every", value=f"{STREAM_ROTATION_HOURS}h", inline=True)
    embed.set_footer(text="chill beats, big goals 🎧")
    embed.timestamp = now
    return embed


async def update_now_playing_embed():
    """Always edit the existing message. Send a new one only if it doesn't exist."""
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
        except Exception:
            return  # silently skip on other errors
    # Only send new message if we genuinely don't have one (e.g. bot restart)
    state.now_playing_message = await channel.send(embed=embed)


async def play_source_on_existing_connection(stream_url: str):
    """
    Swap the audio source without disconnecting from VC.
    Returns True on success, False on failure.
    """
    vc = state.voice_client
    if vc is None or not vc.is_connected():
        return False

    if vc.is_playing():
        vc.stop()
        await asyncio.sleep(0.5)

    raw_source = discord.FFmpegPCMAudio(stream_url, **FFMPEG_OPTIONS)
    source = SilenceDetector(raw_source, volume=0.5)
    state.audio_source = source

    def after_play(error):
        if error:
            print(f"[Ripple] Playback error: {error}")
            asyncio.run_coroutine_threadsafe(handle_stream_error(), bot.loop)

    vc.play(source, after=after_play)
    return True


async def start_stream(stream_index: int | None = None, new_message: bool = False):
    if state.connecting:
        print("[Ripple] Already connecting, skipping...")
        return
    state.connecting = True

    try:
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

        state.stream_start_time = datetime.datetime.now(datetime.timezone.utc)
        state.retries  = 0
        state.stopped  = False

        # Try to reuse existing connection first (no disconnect/reconnect)
        if state.voice_client and state.voice_client.is_connected():
            success = await play_source_on_existing_connection(state.stream_url)
            if success:
                print(f"[Ripple] ▶ Now Streaming: {info['title']} by {info['artist']} (Stream {state.current_stream_index + 1}/{len(LOFI_STREAMS)})")
                activity_type, name = STREAMING_PRESENCES[presence_index % len(STREAMING_PRESENCES)]
                await bot.change_presence(
                    status=discord.Status.idle,
                    activity=discord.Activity(type=activity_type, name=name)
                )
                await update_now_playing_embed()
                return

        # Not connected — do a fresh connect
        if state.voice_client:
            try:
                await state.voice_client.disconnect(force=True)
            except:
                pass
            state.voice_client = None
            await asyncio.sleep(2)

        try:
            state.voice_client = await voice_channel.connect()
        except Exception as e:
            print(f"[Ripple] Connect error: {e}")
            await handle_stream_error()
            return

        await play_source_on_existing_connection(state.stream_url)

        print(f"[Ripple] ▶ Now Streaming: {info['title']} by {info['artist']} (Stream {state.current_stream_index + 1}/{len(LOFI_STREAMS)})")

        activity_type, name = STREAMING_PRESENCES[presence_index % len(STREAMING_PRESENCES)]
        await bot.change_presence(
            status=discord.Status.idle,
            activity=discord.Activity(type=activity_type, name=name)
        )
        await update_now_playing_embed()

    finally:
        state.connecting = False


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
    await asyncio.sleep(minutes * 60)
    if state.stopped:
        print(f"[Ripple] Auto resuming after {minutes} min break")
        state.stopped_by        = None
        state.stop_resume_time  = None
        await start_stream()


# ─────────────────────────────────────────
#  WATCHDOG
# ─────────────────────────────────────────
@tasks.loop(minutes=1)
async def watchdog():
    if state.stopped:
        await update_now_playing_embed()   # keeps countdown fresh every minute
        return

    if state.connecting:
        return

    if state.audio_source and state.voice_client and state.voice_client.is_playing():
        silent_for = time.time() - state.audio_source.last_read
        if silent_for > state.audio_source.silent_threshold:
            print(f"[Ripple] Silent death detected ({silent_for:.0f}s) — restarting...")
            await start_stream()
            return

    if state.stream_start_time:
        elapsed = datetime.datetime.now(datetime.timezone.utc) - state.stream_start_time
        if elapsed >= datetime.timedelta(hours=STREAM_ROTATION_HOURS):
            print(f"[Ripple] Rotating stream after {STREAM_ROTATION_HOURS}h")
            await start_stream(next_stream_index())
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
    await asyncio.sleep(15)


# ─────────────────────────────────────────
#  CHANNEL GUARD
# ─────────────────────────────────────────
@bot.check
async def only_in_text_channel(ctx):
    return ctx.channel.id in TEXT_CHANNEL_IDS


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

        now = datetime.datetime.now(datetime.timezone.utc)
        state.stopped          = True
        state.stopped_by       = f"{interaction.user.display_name}"
        state.stop_resume_time = now + datetime.timedelta(minutes=minutes)
        state.audio_source     = None

        await bot.change_presence(
            status=discord.Status.idle,
            activity=discord.Activity(type=STOPPED_PRESENCE[0], name=STOPPED_PRESENCE[1])
        )
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
            f"😔 Ripple is taking a **{minutes} minute** break!\n"
            f"Use `!wave resume` if you change your mind.",
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
    await ctx.send("⏸️ How long should Ripple take a break?", view=view, delete_after=10)


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

    state.stopped_by       = None
    state.stop_resume_time = None

    print(f"[Ripple] ▶️ Resumed by {ctx.author.name} ({ctx.author.id})")
    await ctx.send("🎵 Ripple is back! *The bot missed you* 🌊", delete_after=8)
    await start_stream()


@bot.command(name="skip")
@commands.has_permissions(manage_guild=True)
async def skip(ctx):
    await ctx.message.delete()
    next_index = next_stream_index()
    print(f"[Ripple] ⏭️ Skipped by {ctx.author.name} ({ctx.author.id})")
    await ctx.send("⏭️ Skipping to next stream...", delete_after=5)
    await start_stream(next_index)


@bot.command(name="status")
@commands.has_permissions(manage_guild=True)
async def status(ctx):
    await ctx.message.delete()
    vc = state.voice_client
    now = datetime.datetime.now(datetime.timezone.utc)

    bot_uptime = ""
    if state.bot_start_time:
        delta = now - state.bot_start_time
        h, rem = divmod(int(delta.total_seconds()), 3600)
        m, s   = divmod(rem, 60)
        bot_uptime = f"{h:02d}:{m:02d}:{s:02d}"

    playing   = "✅ Streaming" if (vc and vc.is_playing()) else ("⏸️ Stopped" if state.stopped else "❌ Not playing")
    connected = "✅ Connected" if (vc and vc.is_connected()) else "❌ Disconnected"

    last_audio = ""
    if state.audio_source:
        secs = int(time.time() - state.audio_source.last_read)
        last_audio = f"{secs}s ago"

    embed = discord.Embed(title="🤖 Ripple Status", color=0x10b981)
    embed.add_field(name="Playback",      value=playing,    inline=True)
    embed.add_field(name="Voice",         value=connected,  inline=True)
    embed.add_field(name="Bot Uptime",    value=bot_uptime if bot_uptime else "N/A", inline=True)
    embed.add_field(name="Retries",       value=str(state.retries), inline=True)
    embed.add_field(name="Last Audio",    value=last_audio if last_audio else "N/A", inline=True)
    embed.add_field(name="Current Stream", value=current_stream_info()["title"], inline=False)
    embed.set_footer(text="chill beats, big goals 🎧")
    await ctx.send(embed=embed, delete_after=15)


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
    await ctx.send(embed=embed, delete_after=10)


presence_index = 0


@tasks.loop(minutes=PRESENCE_ROTATION_MINUTES)
async def presence_rotator():
    global presence_index
    if state.stopped:
        activity = discord.Activity(type=STOPPED_PRESENCE[0], name=STOPPED_PRESENCE[1])
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
        await ctx.send("❌ Ripple commands only work in the allowed channels!", delete_after=5)


@bot.event
async def on_ready():
    print(f"[Ripple] Logged in as {bot.user} ({bot.user.id})")
    state.bot_start_time = datetime.datetime.now(datetime.timezone.utc)
    activity = discord.Activity(type=discord.ActivityType.listening, name="lofi beats")
    await bot.change_presence(status=discord.Status.idle, activity=activity)
    watchdog.start()
    presence_rotator.start()
    await start_stream()


@bot.event
async def on_voice_state_update(member, before, after):
    if member.id != bot.user.id:
        return
    if before.channel and not after.channel and not state.stopped:
        if state.connecting:
            return
        await asyncio.sleep(3)
        if state.connecting:
            return
        print("[Ripple] Disconnected from voice — rejoining in 5s...")
        await asyncio.sleep(5)
        await start_stream()


# ─────────────────────────────────────────
#  RUN
# ─────────────────────────────────────────
if __name__ == "__main__":
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN not set in .env file!")
    if not VOICE_CHANNEL_ID or not NOW_PLAYING_CHANNEL_ID:
        raise ValueError("Channel IDs not set in .env file!")
    if not TEXT_CHANNEL_IDS:
        raise ValueError("TEXT_CHANNEL_IDS not set in .env file!")
    bot.run(BOT_TOKEN)
