# Real-time voice to voice Gemini discord chat bot

Chat voice to voice live with Google's Gemini 2.0 AI with google search capabilities.


## Demo
https://github.com/user-attachments/assets/a1fd75ce-15d4-4d5a-8fe2-55c9d43ff656

## Prerequisites

- Python 3.8 or higher
- Discord Bot Token
- Free GEMINI API Key: https://aistudio.google.com/
- Discord Server with voice channels enabled

## Installation

1. Clone the repository:
```bash
git clone https://github.com/2187Nick/discord-voice-to-voice-gemini
cd discord-voice-to-voice-gemini
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with the following variables:
```env
DISCORD_TOKEN=your_discord_bot_token
GEMINI_API_KEY=your_gemini_api_key
```

4. Options:
- Set the voice to use in `main.py` line 22.
```env
voice="aoede"
```
- Set the persona to use in `main.py` line 23.
```env
persona="Take on the persona of an overly excited motivational speaker"
```

## Usage

1. Start the bot:
```bash
python main.py
```

2. In Discord, join a voice channel and use the following command:
```
/chat
```
3. Enable push-to-talk in Discord and hold the key while speaking.

4. Interrupt the response by pressing the key again and start speaking.


## Commands

- `/chat` - Initiates a voice chat session with the bot
- `/stop` - Stops the current voice chat session

## Support
https://x.com/2187Nick

http://discord.gg/vxKepZ6XNC


## Project Structure

```
├── main.py # Bot initialization and command handling
└── src/ 
    ├── record.py # Audio processing and speech-to-text conversion 
    ├── stream.py # Custom audio streaming implementation 
    └── gemini.py # Gemini AI WebSocket client integration
```


## Technical Details

- Uses Discord.py for bot functionality
- Implements custom audio streaming for real-time voice processing
- Uses WebSocket connection to Gemini AI for real-time responses
- Handles both synchronous and asynchronous operations for optimal performance