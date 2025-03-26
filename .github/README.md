# 🎶 [TgMusicBot](https://github.com/AshokShau/TgMusicBot) - Telegram MusicBot

A powerful Telegram bot for streaming music in voice chats.

<p align="center">
   <img src="/.github/images/thumb.png" alt="thumbnail" width="320" height="320">
</p>

### 👇 [@FallenBeatzBot](https://t.me/FallenBeatzBot) - Get started with TgMusicBot today!

---

## Facing IP Ban Issues from YouTube?

We've got a permanent solution for you, buy **Spotify api key** from us and enjoy unlimited songs, albums and playlist
downloading for a seamless experience.

### Why Choose Our API?

✅ **Easy Integration** – Just set `API_URL` in your bot configuration.  
✅ **Spotify Downloader** – Download high-quality music directly from Spotify.  
✅ **Unlimited Access** – No download limits, no interruptions.

> [Click here for more details](https://gist.github.com/AshokShau/7528cddc5b264035dee40523a44ff153)

🚀 **Get started today!**  
👉 [Contact on Telegram](https://t.me/AshokShau) to get access!

---

## ✨ Features

👉 **Multi-Platform Support** - Play music from **[Spotify](https://open.spotify.com), [YT-Music](https://music.youtube.com), [YouTube](https://www.youtube.com), [JioSaavn](https://jiosaavn.com), and Telegram audio files**.
👉 **Playlists & Queue** - Seamless music playback with a queue system.  
👉 **Full Playback Controls** - **Skip, Pause, Resume, End, Mute, Unmute, Volume, Loop, Seek**.  
👉 **Group Voice Chats** - Supports Telegram **group voice chats** (requires admin permissions).  
👉 **User-Friendly Interface** - Simple and intuitive commands for easy interaction.  
👉 **Optimized Performance** - Fully **async**, efficient, and **lightweight**.  
👉 **Easy Deployment** - Comes with a **Docker** container setup.  
👉 **Open-Source & Free** - Built using **[PyTdBot](https://github.com/pytdbot/client)** and **[PyTgCalls](https://github.com/pytgcalls/pytgcalls)**. (if you need only pyrogram use `pyro` branch)

## 📝 Requirements

- **Python 3.12** or higher
- **MongoDB** for storing chat data

### 🛠️ Configuration
<details>
<summary><strong>📌 Environment Variables (Click to expand)</strong></summary>

### 🔑 Required Variables

- **API_ID** – Get from [my.telegram.org](https://my.telegram.org/apps)  
- **API_HASH** – Get from [my.telegram.org](https://my.telegram.org/apps)  
- **TOKEN** – Get from [@BotFather](https://t.me/BotFather)  

### 🔗 String Sessions

- **STRING** - Pyrogram String Session
- **STRING2** - Pyrogram String Session
- **STRING3** - Pyrogram String Session
- **STRING4** - Pyrogram String Session
.
.
- **STRING10** - Pyrogram String Session

### 🛠️ Additional Configuration

- **OWNER_ID** – Your Telegram User ID  
- **MONGO_URI** – Get from [MongoDB Cloud](https://cloud.mongodb.com)  
- **API_URL** – Buy from [@AshokShau](https://t.me/AshokShau) (Spotify API for unlimited downloads)  
- **API_KEY** – Required for API_URL

### 🎵 Music Download Options

- **PROXY_URL** – Optional; Proxy URL for yt-dlp  
- **DEFAULT_SERVICE** – Default search platform (Options: `youtube`, `spotify`, `jiosaavn`)  
- **DOWNLOADS_DIR** – Directory for downloads and TDLib database  

### 🖼️ Thumbnails & Cookies

- **IMG_URL** – Fallback thumbnail (if no song thumbnail is found)  
- **COOKIES_URL** – URLs for downloading cookies (More info [here](https://github.com/AshokShau/TgMusicBot/blob/master/cookies/README.md))  

</details>


## ‍🛠️ Installation

> First [Fork](https://github.com/AshokShau/TgMusicBot/fork) the repository.

### 🚀 Using Docker (Recommended)

1. Clone the repository:
   ```sh
   git clone https://github.com/AshokShau/TgMusicBot.git && cd TgMusicBot
   ```

2. Build the Docker image:
   ```sh
   docker build -t tgmusicbot .
   ```

3. Set up environment variables:
   ```sh
   cp sample.env .env && vi .env
   ```

4. Run the Docker container:
   ```sh
   docker run -d --name tgmusicbot --env-file .env tgmusicbot
   ```

#### 🚀 Manual Installation
<details>
<summary>Manual Installation (Click to expand)</summary>

1. Clone the repository:
   ```sh
   git clone https://github.com/AshokShau/TgMusicBot.git && cd TgMusicBot
   ```

2. Create a Python virtual environment:
   ```sh
   python3 -m venv venv
   ```

3. Activate the virtual environment:
    - Windows: `venv/Scripts/activate`
    - Linux/Mac: `source venv/bin/activate`

4. Install required dependencies:
   ```sh
   pip install -r requirements.txt
   ```

5. Set up environment variables:
   ```sh
   cp sample.env .env && vi .env
   ```

6. Install FFmpeg:
   ```sh
   sudo apt-get install ffmpeg
   ```

7. Start the bot:
   ```bash
   bash start
   ```

</details>

---

#### 🚀 Deploy on Heroku

<details>
  <summary>Deploy on Heroku (Click to expand)</summary>
  <p align="center">
    <a href="https://heroku.com/deploy?template=https://github.com/AshokShau/TgMusicBot">
      <img src="https://img.shields.io/badge/Deploy%20On%20Heroku-black?style=for-the-badge&logo=heroku" width="220" height="38.45" alt="Deploy">
    </a>
  </p>
</details>

---

## 🎮 Usage

1. **Add [@FallenBeatzBot](https://t.me/FallenBeatzBot) to a group** and grant **admin permissions**.
2. Use `/start` to **initialize** the bot.
3. Use `/help` to view the **list of available commands**.

---

## 🤝 Contributing

Contributions are welcome! 🚀 If you'd like to contribute:

1. **Fork** the [repository](https://github.com/AshokShau/TgMusicBot).
2. **Make meaningful changes** – improve features, fix bugs, or optimize performance.
3. **Submit a pull request** with a clear explanation of your changes.

💡 _Please avoid submitting PRs for minor edits like fixing typos or tweaking the README unless they improve clarity
significantly._ Let's keep contributions valuable and impactful! 💪

---

## 🐟 License

This project is licensed under the **AGPL-3.0 License**. See the [LICENSE](/LICENSE) file for details.

---

## 🙏 Credits

- [AshokShau](https://github.com/AshokShau) - Creator & Maintainer

- **Shoutout to all the bug hunters** - Finding issues faster than I can pretend they don’t exist. 🐞🔍
- **Shoutout to all the contributors** - Your contributions make this project possible. 💖

---

## 💖 Support the Project

Love **TgMusicBot**? ☕ Help keep it running by supporting development!

Your contributions allow me to maintain, improve, and add new features to the bot.

💰 **Donate via Crypto, PayPal, or UPI** – [Contact me on Telegram for details](https://t.me/AshokShau).

Every bit of support is truly appreciated! ❤️

---

## 🔗 Links

> **Follow** me on [GitHub](https://github.com/AshokShau) to stay updated.

> **Star** the repository on [GitHub](https://github.com/AshokShau/TgMusicBot) to show your support.

For any questions, suggestions, or feedback, please contact me on [Telegram](https://t.me/AshokShau).

[![Telegram Group](https://img.shields.io/badge/Telegram%20Group-Join%20Now-blue?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/GuardxSupport)
[![Telegram Channel](https://img.shields.io/badge/Telegram%20Channel-Join%20Now-blue?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/FallenProjects)

---
