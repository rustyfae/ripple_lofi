<div align="center">

<!-- Replace this with your bot's pfp when you have one -->
<!-- <img src="your-pfp-url-here" width="120" height="120" style="border-radius: 50%"/> -->

# 🌊 Ripple
### *24/7 lofi music bot for some discord server*

![Python](https://img.shields.io/badge/Python-3.10+-8b5cf6?style=for-the-badge&logo=python&logoColor=white)
![discord.py](https://img.shields.io/badge/discord.py-2.3+-8b5cf6?style=for-the-badge&logo=discord&logoColor=white)
![Status](https://img.shields.io/badge/status-24%2F7-10b981?style=for-the-badge)

 *chill beats, big goals 🎧*

**Made with 💜 by rusty.fae**

</div>

---

## ✨ What is Ripple?

Ripple is a lightweight 24/7 lofi music bot that streams directly to a dedicated voice channel. No downloads, no heavy libraries — just pure lofi vibes piped straight to Discord.

- 🎵 Streams multiple lofi sources, rotating every hour automatically
- 🔁 Watchdog system — auto restarts if anything goes wrong
- 📻 Live "Now Playing" embed that updates every minute
- 🌊 Super lightweight — runs on as little as 50MB RAM
- 🍓 Raspberry Pi friendly!

---

## 🎛️ Commands

All commands use the `!wave` prefix and only work in the Silent Study Room text chat.

### Public
| Command | Description |
|---|---|
| `!wave resume` | Bring Ripple back early from a break |
| `!wave stop` | Give Ripple a break (custom time in minutes) |
| `!wave help` | Show the help menu |

### 🔒 Mod Only
| Command | Description |
|---|---|
| `!wave skip` | Skip to the next stream in rotation |
| `!wave status` | Bot health check — playback, uptime, retries |

 Mod = anyone with **Manage Server** permission in Discord

---

## ⚙️ Setup

### Prerequisites
- Python 3.10+
- FFmpeg installed and in PATH
- A Discord bot token

### 1. Clone the repo
```bash
git clone https://github.com/rustyfae/ripple.git
cd ripple
```

### 2. Create virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
```bash
cp .env.example .env
```

Fill in your `.env`:
```env
BOT_TOKEN=your_bot_token_here
VOICE_CHANNEL_ID=your_voice_channel_id
TEXT_CHANNEL_ID=your_text_channel_id
NOW_PLAYING_CHANNEL_ID=your_now_playing_channel_id
```

### 5. Run!
```bash
python bot.py
```

---

## 📁 Project Structure

```
ripple/
├── bot.py              ← main bot code
├── requirements.txt    ← dependencies
├── .env.example        ← environment variables template
├── .env                ← your secrets (never commit this!)
├── .gitignore
└── lofi-bot.service    ← systemd service for Raspberry Pi
```

---

## 🍓 Raspberry Pi Setup

Ripple runs perfectly on a Raspberry Pi Zero 2W (512MB RAM)!

```bash
# Install dependencies
sudo apt update && sudo apt install python3 python3-pip ffmpeg -y

# Set up bot (same as above)

# Auto-start on boot
sudo cp lofi-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ripple
sudo systemctl start ripple

# Check logs
sudo journalctl -u ripple -f
```

---

## 🔧 Customization

### Add/remove streams
Edit `LOFI_STREAMS` in `bot.py`:
```python
{
    "url": "https://www.youtube.com/watch?v=XXXXXXXXXXX",
    "title": "your stream title",
    "artist": "channel name",
    "thumbnail": "https://i.ytimg.com/vi/XXXXXXXXXXX/maxresdefault.jpg",
},
```

### Change rotation interval
```python
STREAM_ROTATION_HOURS = 1  # change to any number of hours
```

### Change browser for cookies
```python
"cookiesfrombrowser": ("chrome",),  # chrome, firefox, edge
```

---

## 🛠️ Troubleshooting

| Problem | Fix |
|---|---|
| `ffmpeg not found` | Install FFmpeg and add to PATH |
| `yt-dlp cookie error` | Make sure your browser is closed, then retry |
| Bot not joining voice | Check `VOICE_CHANNEL_ID` in `.env` |
| Stream keeps stopping | Run `pip install -U yt-dlp` to update |
| Commands not working | Make sure you're in the correct text channel |

---

<div align="center">

*built for* **some discord server** 🌙

</div>
