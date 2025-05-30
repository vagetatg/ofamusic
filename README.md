# [TgMusicBot](https://github.com/AshokShau/TgMusicBot) - Telegram Music Bot

Telegram Group Calls Streaming bot with some useful features, written in Python with Py-Tgcalls.
Supporting platforms like YouTube, Spotify, Apple Music, Soundcloud, JioSaavn and more.

<p align="center">
  <!-- GitHub Stars -->
  <a href="https://github.com/AshokShau/TgMusicBot/stargazers">
    <img src="https://img.shields.io/github/stars/AshokShau/TgMusicBot?style=for-the-badge&color=black&logo=github" alt="Stars"/>
  </a>
  
  <!-- GitHub Forks -->
  <a href="https://github.com/AshokShau/TgMusicBot/network/members">
    <img src="https://img.shields.io/github/forks/AshokShau/TgMusicBot?style=for-the-badge&color=black&logo=github" alt="Forks"/>
  </a>

  <!-- Last Commit -->
  <a href="https://github.com/AshokShau/TgMusicBot/commits/AshokShau">
    <img src="https://img.shields.io/github/last-commit/AshokShau/TgMusicBot?style=for-the-badge&color=blue" alt="Last Commit"/>
  </a>

  <!-- Repo Size -->
  <a href="https://github.com/AshokShau/TgMusicBot">
    <img src="https://img.shields.io/github/repo-size/AshokShau/TgMusicBot?style=for-the-badge&color=success" alt="Repo Size"/>
  </a>

  <!-- Language -->
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/Written%20in-Python-orange?style=for-the-badge&logo=python" alt="Python"/>
  </a>

  <!-- License -->
  <a href="https://github.com/AshokShau/TgMusicBot/blob/master/LICENSE">
    <img src="https://img.shields.io/github/license/AshokShau/TgMusicBot?style=for-the-badge&color=blue" alt="License"/>
  </a>

  <!-- Open Issues -->
  <a href="https://github.com/AshokShau/TgMusicBot/issues">
    <img src="https://img.shields.io/github/issues/AshokShau/TgMusicBot?style=for-the-badge&color=red" alt="Issues"/>
  </a>

  <!-- Pull Requests -->
  <a href="https://github.com/AshokShau/TgMusicBot/pulls">
    <img src="https://img.shields.io/github/issues-pr/AshokShau/TgMusicBot?style=for-the-badge&color=purple" alt="PRs"/>
  </a>

  <!-- GitHub Workflow CI -->
  <a href="https://github.com/AshokShau/TgMusicBot/actions">
    <img src="https://img.shields.io/github/actions/workflow/status/AshokShau/TgMusicBot/code-fixer.yml?style=for-the-badge&label=CI&logo=github" alt="CI Status"/>
  </a>
</p>

<p align="center">
   <img src="https://raw.githubusercontent.com/AshokShau/TgMusicBot/master/.github/images/thumb.png" alt="thumbnail" width="320" height="320">
</p>

### [@FallenBeatzBot](https://t.me/FallenBeatzBot) - Try it now!

---

### 🚫 Tired of IP Bans from YouTube?

Say goodbye to restrictions with our **Premium Music API** – your ultimate solution for seamless, high-quality
downloads.

- **Easy Integration** – Just set `API_URL` & `API_KEY` variables in your bot configuration.
- **High-Quality Downloads** – Get music from **Spotify, SoundCloud**, and **YouTube** in top quality.

📩 **[Contact me on Telegram](https://t.me/AshokShau) to get access or use [@FallenApiBot](https://t.me/FallenApiBot)**

---

### Want to use cookies?

> 📘 Check out this [guide](https://github.com/AshokShau/TgMusicBot/blob/master/cookies/README.md) for instructions on
> downloading and using them.

---

## **Features**

- **Multi-Platform Support** - Play music
  from [Spotify](https://open.spotify.com), [YT-Music](https://music.youtube.com), [YouTube](https://www.youtube.com), [JioSaavn](https://jiosaavn.com), [Apple Music](https://music.apple.com), [SoundCloud](https://soundcloud.com)
  and Telegram files.
- **Playlists & Queue** - Seamless music playback with queue management.
- **Full Playback Controls** - Skip, Pause, Resume, End, Mute, Unmute, Volume, Loop, Seek.
- **Group Voice Chats** - Supports Telegram **group voice chats** (requires admin permissions).
- **Optimized Performance** - Fully **async**, efficient, and lightweight.
- **Easy Deployment** - Pre-configured **Railway** setup.
- **Multi-Language Support** - Available in English, Hindi, Spanish, Arabic, and more. Easily extendable with your own translations.
- **Open-Source & Free** - Built from scratch using **[PyTdBot](https://github.com/pytdbot/client)** & **[PyTgCalls](https://github.com/pytgcalls/pytgcalls)**.
  > 💡 Prefer using Pyrogram instead of PyTdBot? Check out
  the [Pyro-Branch](https://github.com/AshokShau/TgMusicBot/tree/pyro).

---

## **Installation**

<details> 
<summary>Dependency Tree: Click to expand</summary>

```
tgmusicbot v1.2.1
├── aiofiles v24.1.0
├── apscheduler v3.11.0
│   └── tzlocal v5.3.1
├── cachetools v6.0.0
├── kurigram v2.2.3
│   ├── pyaes v1.6.1
│   └── pysocks v1.7.1
├── meval v2.5
├── ntgcalls v2.0.0rc7
├── pillow v11.2.1
├── psutil v7.0.0
├── py-tgcalls v2.2.0rc3
│   ├── aiohttp v3.11.18
│   │   ├── aiohappyeyeballs v2.6.1
│   │   ├── aiosignal v1.3.2
│   │   │   └── frozenlist v1.6.0
│   │   ├── attrs v25.3.0
│   │   ├── frozenlist v1.6.0
│   │   ├── multidict v6.4.3
│   │   ├── propcache v0.3.1
│   │   └── yarl v1.20.0
│   │       ├── idna v3.10
│   │       ├── multidict v6.4.3
│   │       └── propcache v0.3.1
│   ├── deprecation v2.1.0
│   │   └── packaging v25.0
│   └── ntgcalls v2.0.0rc7
├── py-yt-search v0.3
│   ├── httpx v0.28.1
│   │   ├── anyio v4.9.0
│   │   │   ├── idna v3.10
│   │   │   └── sniffio v1.3.1
│   │   ├── certifi v2025.4.26
│   │   ├── httpcore v1.0.9
│   │   │   ├── certifi v2025.4.26
│   │   │   └── h11 v0.16.0
│   │   └── idna v3.10
│   └── python-dotenv v1.1.0
├── pycryptodome v3.23.0
├── pydantic v2.11.5
│   ├── annotated-types v0.7.0
│   ├── pydantic-core v2.33.2
│   │   └── typing-extensions v4.13.2
│   ├── typing-extensions v4.13.2
│   └── typing-inspection v0.4.0
│       └── typing-extensions v4.13.2
├── pymongo v4.13.0
│   └── dnspython v2.7.0
├── pytdbot v0.9.3
│   ├── aio-pika v9.5.5
│   │   ├── aiormq v6.8.1
│   │   │   ├── pamqp v3.3.0
│   │   │   └── yarl v1.20.0 (*)
│   │   ├── exceptiongroup v1.2.2
│   │   └── yarl v1.20.0 (*)
│   └── deepdiff v8.4.2
│       └── orderly-set v5.4.0
├── pytgcrypto v1.2.11
├── python-dotenv v1.1.0
├── pytz v2025.2
├── tdjson v1.8.49
├── ujson v5.10.0
├── yt-dlp v2025.5.22
├── black v25.1.0 (extra: dev)
│   ├── click v8.1.8
│   ├── mypy-extensions v1.1.0
│   ├── packaging v25.0
│   ├── pathspec v0.12.1
│   └── platformdirs v4.3.7
├── ruff v0.11.7 (extra: dev)
└── setuptools v78.1.1 (extra: dev)
```

</details>

<details>
<summary><strong>📌 Railway Deployment (Recommended) (Click to expand)</strong></summary>

### 🚀 Quick Setup
1. Fork this repository
2. Go to [Railway](https://railway.app)
3. Create a new project
4. Choose "Deploy from GitHub repo"
5. Select your forked repository
6. Add the following environment variables:
   - `API_ID` - Get from [my.telegram.org](https://my.telegram.org/apps)
   - `API_HASH` - Get from [my.telegram.org](https://my.telegram.org/apps)
   - `TOKEN` - Get from [@BotFather](https://t.me/BotFather)
   - `MONGO_URI` - Get from [MongoDB Cloud](https://cloud.mongodb.com)
   - `OWNER_ID` - Your Telegram User ID
   - Other optional variables as needed

### 🔧 Configuration
The following environment variables are available:

#### Required Variables
- `API_ID` - Telegram API ID
- `API_HASH` - Telegram API Hash
- `TOKEN` - Bot Token
- `MONGO_URI` - MongoDB Connection URI
- `OWNER_ID` - Your Telegram User ID

#### Optional Variables
- `API_URL` - API URL for unlimited downloads
- `API_KEY` - API Key for unlimited downloads
- `PROXY` - Proxy URL for yt-dlp
- `DEFAULT_SERVICE` - Default search platform (youtube, spotify, jiosaavn)
- `DOWNLOADS_DIR` - Directory for downloads
- `SUPPORT_GROUP` - Support Group Link
- `SUPPORT_CHANNEL` - Support Channel Link
- `IGNORE_BACKGROUND_UPDATES` - Ignore background updates
- `LOGGER_ID` - Log Group ID
- `AUTO_LEAVE` - Auto leave chats
- `MIN_MEMBER_COUNT` - Minimum member count
- `DEVS` - Developer IDs
- `COOKIES_URL` - Cookie URLs

### 🔍 Monitoring
- Railway provides built-in monitoring and logs
- Check the "Deployments" tab for deployment status
- View logs in the "Logs" tab

### ⚙️ Management
- Automatic deployments on push to main branch
- Manual deployments available
- Easy rollback to previous versions
- Built-in health checks

</details>

<details>
<summary><strong>📌 Step-by-Step Installation Guide (Click to Expand)</strong></summary>

### 🛠️ System Preparation
1. **Update your system** (Recommended):
   ```sh
   sudo apt-get update && sudo apt-get upgrade -y
   ```

2. **Install essential tools**:
   ```sh
   sudo apt-get install git python3-pip ffmpeg tmux -y
   ```

### ⚡ Quick Setup
1. **Install UV package manager**:
   ```sh
   pip3 install uv
   ```

2. **Clone the repository**:
   ```sh
   git clone https://github.com/AshokShau/TgMusicBot.git && cd TgMusicBot
   ```

### 🐍 Python Environment
1. **Create virtual environment**:
   ```sh
   uv venv
   ```

2. **Activate environment**:
   - Linux/Mac: `source .venv/bin/activate`
   - Windows (PowerShell): `.\.venv\Scripts\activate`

3. **Install dependencies**:
   ```sh
   uv pip install -e .
   ```

### 🔐 Configuration
1. **Setup environment file**:
   ```sh
   cp sample.env .env
   ```

2. **Edit configuration** (Choose one method):
   - **For beginners** (nano editor):
     ```sh
     nano .env
     ```
     - Edit values
     - Save: `Ctrl+O` → Enter → `Ctrl+X`

   - **For advanced users** (vim):
     ```sh
     vi .env
     ```
     - Press `i` to edit
     - Save: `Esc` → `:wq` → Enter

### 🤖 Running the Bot
1. **Start in tmux session** (keeps running after logout):
   ```sh
   tmux new -s musicbot
   tgmusic
   ```

   **Tmux Cheatsheet**:
   - Detach: `Ctrl+B` then `D`
   - Reattach: `tmux attach -t musicbot`
   - Kill session: `tmux kill-session -t musicbot`

### 🔄 After Updates
To restart the bot:
```sh
tmux attach -t musicbot
# Kill with Ctrl+C
tgmusic
```

</details>

---

## **🎮 Usage**

1. **Add [@FallenBeatzBot](https://t.me/FallenBeatzBot) to a group** and grant **admin permissions**.
2. Use `/start` to **initialize** the bot.
3. Use `/help` to view the **list of available commands**.

---

## **Contributing**

Contributions are welcome! If you'd like to contribute:

1. **Fork** the [repository](https://github.com/AshokShau/TgMusicBot).
2. **Make meaningful changes** – improve features, fix bugs, or optimize performance.
3. **Submit a pull request** with a clear explanation of your changes.

🔹 _Avoid submitting minor PRs for small typos or README tweaks unless they significantly improve clarity._

---

## **License**

This project is licensed under the **AGPL-3.0 License**. See the [LICENSE](/LICENSE) file for details.

---

## **Credits**

- [AshokShau](https://github.com/AshokShau) - Creator & Maintainer
- Thanks to **all contributors & bug hunters** for improving the project!
- Special thanks to **[PyTgCalls](https://github.com/pytgcalls)** for their outstanding work.

---

## **💖 Support the Project**

Love **TgMusicBot**? Help keep it running!

💰 **Donate via Crypto, PayPal, or UPI** – [Contact me on Telegram](https://t.me/AshokShau) for details.

Every contribution helps! ❤️

---

## **🔗 Links**

> **Follow** me on [GitHub](https://github.com/AshokShau) for updates.  
> **Star** the repository on [GitHub](https://github.com/AshokShau/TgMusicBot) to support the project.

📢 **Join our Telegram community:**  
[![Telegram Group](https://img.shields.io/badge/Telegram%20Group-Join%20Now-blue?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/GuardxSupport)  
[![Telegram Channel](https://img.shields.io/badge/Telegram%20Channel-Join%20Now-blue?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/FallenProjects)
