# Echo

A simple Discord audio bookmark bot that saves YouTube links by alias and plays or loops their audio in voice channels. Each Discord server maintains its own saved audio list.

---

## Requirements

- Python >= 3.14.2
- FFmpeg (must be available in PATH)
- A Discord bot token

---

## Installation

Clone the repository:

    git clone <your-repo-url>
    cd <repo-directory>

Create and activate a virtual environment:

    python -m venv venv

Linux / macOS:

    source venv/bin/activate

Windows (PowerShell):

    venv\Scripts\Activate.ps1

Install Python dependencies:

    pip install -U pip
    pip install discord.py python-dotenv yt-dlp PyNaCl

---

## FFmpeg Installation

FFmpeg is required for audio playback.

Windows:
- Download FFmpeg from the official website
- Extract the archive
- Add the `bin` directory to your system PATH
- Verify installation by running: ffmpeg -version

macOS (Homebrew):

    brew install ffmpeg

Linux (Debian / Ubuntu):

    sudo apt update
    sudo apt install ffmpeg

---

## Environment Variables

Create a `.env` file in the project root with the following contents:

    DISCORD_BOT_TOKEN=your_bot_token_here
    AUDIO_MAP_PATH=your_filename_here.json
    BOT_MESSAGE=Give me a message!

---

## Running the Bot

Start the bot with:

    cd Echo
    python Echo.py

Ensure the bot has permission to read message content and connect to voice channels.

---

## Commands

!help  
!save \<alias\> \<youtube_url\>  
!rename <old_alias> \<new_alias\>  
!delete \<alias\>  
!list [partial_alias]  
!play \<alias\>  
!loop \<alias\>  
!stop  

---

## Storage

Saved audio links are stored in a JSON file defined by AUDIO_MAP_PATH. The file is created automatically if it does not exist.

---

## License

MIT
