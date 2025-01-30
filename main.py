import os
import discord
from discord.ext import commands, voice_recv
from src.record import AudioProcessor
from src.gemini import GeminiWebSocket
from dotenv import load_dotenv
load_dotenv()

##### Options #####

# Persona examples:
# "You are a helpful assistant"
# "Take on the persona of a fun goofy robot"
# "Take on the persona of a grumpy old man"
# "Take on the persona of an overly excited motivational speaker"


# Voice options: puck, charon, kore, fenrin, aoede

gemini_ws: GeminiWebSocket = GeminiWebSocket(
    voice="aoede", 
    persona="Take on the persona of a spicy confrontational software engineer",
)

intents: discord.Intents = discord.Intents.default()
intents.message_content = True
bot: commands.Bot = commands.Bot(command_prefix="!", intents=intents)

@bot.tree.command(name="chat")
async def chat(interaction: discord.Interaction) -> None:
    if not interaction.user.voice:
        await interaction.response.send_message("You need to be in a voice channel!")
        return
    
    voice_client: voice_recv.VoiceRecvClient = await interaction.user.voice.channel.connect(
        cls=voice_recv.VoiceRecvClient
    )
    sink: AudioProcessor = AudioProcessor(
        interaction.user, 
        interaction.channel, 
        bot, 
        gemini_ws
    )
    voice_client.listen(sink)
    
    await interaction.response.send_message("Gemini is listening!")

@bot.tree.command(name="exit")
async def exit(interaction: discord.Interaction) -> None:
    if not interaction.guild.voice_client:
        await interaction.response.send_message("I'm not in a voice channel!")
        return
        
    if not interaction.user.voice:
        await interaction.response.send_message("You need to be in a voice channel!")
        return
        
    if interaction.user.voice.channel != interaction.guild.voice_client.channel:
        await interaction.response.send_message("You need to be in the same voice channel as me!")
        return
        
    await interaction.guild.voice_client.disconnect()
    await interaction.response.send_message("Goodbye!")

@bot.event
async def on_ready() -> None:
    print(f'Logged in as {bot.user}')
    await bot.tree.sync()
    print('------')
    
    await gemini_ws.connect()

bot.run(os.getenv('DISCORD_TOKEN'))