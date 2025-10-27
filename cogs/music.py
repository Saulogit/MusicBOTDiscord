import discord
from discord import app_commands
from discord.ext import commands
from yt_dlp import YoutubeDL


class Music(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.is_playing = False
        self.music_queue = []
        self.YDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': 'True'}
        self.FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }
        self.vc: discord.VoiceClient | None = None

    def search_yt(self, item):
        with YoutubeDL(self.YDL_OPTIONS) as ydl:
            try:
                info = ydl.extract_info(f"ytsearch:{item}", download=False)['entries'][0]
                return {'source': info['url'], 'title': info['title']}
            except Exception:
                return False

    def play_next(self):
        if len(self.music_queue) > 0:
            self.is_playing = True
            m_url = self.music_queue[0][0]['source']
            self.music_queue.pop(0)
            self.vc.play(
                discord.FFmpegPCMAudio(m_url, **self.FFMPEG_OPTIONS),
                after=lambda e: self.play_next()
            )
        else:
            self.is_playing = False

    async def play_music(self):
        if len(self.music_queue) > 0:
            self.is_playing = True
            m_url = self.music_queue[0][0]['source']

            if self.vc is None or not self.vc.is_connected():
                self.vc = await self.music_queue[0][1].connect()
            else:
                await self.vc.move_to(self.music_queue[0][1])

            self.music_queue.pop(0)
            self.vc.play(
                discord.FFmpegPCMAudio(m_url, **self.FFMPEG_OPTIONS),
                after=lambda e: self.play_next()
            )
        else:
            self.is_playing = False
            if self.vc:
                await self.vc.disconnect()

    @app_commands.command(name="ajuda", description="Show a help menu.")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        helptxt = (
            "`/ajuda` - See this guide!\n"
            "`/play` - Play a YouTube song!\n"
            "`/fila` - Show the current queue.\n"
            "`/pular` - Skip to the next song."
        )
        embedhelp = discord.Embed(
            colour=1646116,
            title=f'{self.client.user.name} Commands',
            description=helptxt
        )
        if self.client.user.avatar:
            embedhelp.set_thumbnail(url=self.client.user.avatar.url)

        await interaction.followup.send(embed=embedhelp)

    @app_commands.command(name="play", description="Play a song from YouTube.")
    @app_commands.describe(busca="Enter the song name or YouTube URL")
    async def play(self, interaction: discord.Interaction, busca: str):
        await interaction.response.defer(thinking=True)

        try:
            voice_channel = interaction.user.voice.channel
        except AttributeError:
            embed = discord.Embed(
                colour=1646116,
                description='You must be in a voice channel to play music.'
            )
            await interaction.followup.send(embed=embed)
            return

        song = self.search_yt(busca)
        if song is False:
            embed = discord.Embed(
                colour=12255232,
                description='Something went wrong! Try another song or URL.'
            )
            await interaction.followup.send(embed=embed)
        else:
            self.music_queue.append([song, voice_channel])
            embed = discord.Embed(
                colour=32768,
                description=f"Added **{song['title']}** to the queue!"
            )
            await interaction.followup.send(embed=embed)
            if not self.is_playing:
                await self.play_music()

    @app_commands.command(name="fila", description="Show the current queue.")
    async def fila(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        if len(self.music_queue) == 0:
            embed = discord.Embed(
                colour=1646116,
                description='There are no songs in the queue.'
            )
        else:
            desc = "\n".join(
                [f"**{i+1} -** {song[0]['title']}" for i, song in enumerate(self.music_queue)]
            )
            embed = discord.Embed(colour=12255232, description=desc)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="pular", description="Skip the current song.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def pular(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        if self.vc and self.vc.is_connected():
            self.vc.stop()
            await self.play_music()
            embed = discord.Embed(
                colour=1646116,
                description="You skipped the song."
            )
        else:
            embed = discord.Embed(
                colour=12255232,
                description="No song is currently playing."
            )
        await interaction.followup.send(embed=embed)


async def setup(client):
    await client.add_cog(Music(client))
