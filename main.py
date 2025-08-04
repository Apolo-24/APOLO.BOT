import discord
from discord.ext import commands
from io import BytesIO
import requests
import asyncio
import os
import re


DISCORD_TOKEN = os.getenv("DISCORD_TOKEN") #new codigo

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

try:
    import yt_dlp
    YTDL_AVAILABLE = True
except ImportError:
    YTDL_AVAILABLE = False

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.members = True
intents.presences = True
bot = commands.Bot(command_prefix='!', intents=intents)

tts_settings = {}

LANGUAGES = {
    'español': 'es',
    'español_latino': 'es-us',
    'español_spain': 'es-es',
    'ingles': 'en',
    'english': 'en',
    'portugues': 'pt',
    'portuguese': 'pt',
    'frances': 'fr',
    'italiano': 'it',
    'aleman': 'de',
    'japones': 'ja',
    'coreano': 'ko',
    'chino': 'zh'
}

if YTDL_AVAILABLE:
    ytdl_format_options = {
        'format': 'bestaudio/best',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0',
        'extract_flat': False,
    }

    ffmpeg_options = {
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn -loglevel quiet'
    }

    ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

    class YTDLSource(discord.PCMVolumeTransformer):
        def __init__(self, source, *, data, volume=0.5):
            super().__init__(source, volume)
            self.data = data
            self.title = data.get('title')
            self.url = data.get('url')
            self.webpage_url = data.get('webpage_url')

        @classmethod
        async def from_url(cls, url, *, loop=None, stream=False):
            loop = loop or asyncio.get_event_loop()
            if not is_url(url):
                url = f"ytsearch:{url}"

            data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

            if 'entries' in data:
                entry = next((e for e in data['entries'] if e), None)
                if not entry:
                    raise ValueError("No se encontraron resultados válidos para la búsqueda.")
            else:
                entry = data

            filename = entry['url'] if stream else ytdl.prepare_filename(entry)
            return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=entry)

@bot.event
async def on_ready():
    print(f'🤖 {bot.user} ha iniciado sesión!')
    print(f'🆔 ID del bot: {bot.user.id}')
    print(f'🗣️ gTTS disponible: {"✅" if GTTS_AVAILABLE else "❌"}')
    print(f'🎵 yt-dlp disponible: {"✅" if YTDL_AVAILABLE else "❌"}')
    print('🚀 Bot listo para usar!')

def is_url(string):
    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(string) is not None

def check_voice_permissions(voice_channel, guild_member):
    permissions = voice_channel.permissions_for(guild_member)
    if not permissions.connect:
        return False, "No tengo permisos para conectarme a ese canal de voz."
    if not permissions.speak:
        return False, "No tengo permisos para hablar en ese canal de voz."
    return True, "OK"

@bot.command(name='join')
async def join_voice(ctx):
    if not ctx.author.voice:
        await ctx.send("❌ ¡Necesitas estar en un canal de voz para que el bot se una!")
        return

    channel = ctx.author.voice.channel
    can_connect, message = check_voice_permissions(channel, ctx.guild.me)

    if not can_connect:
        await ctx.send(f"❌ {message}")
        return

    try:
        if ctx.voice_client is not None:
            if ctx.voice_client.channel.id == channel.id:
                await ctx.send(f"✅ Ya estoy en el canal: **{channel.name}**")
            else:
                await ctx.voice_client.move_to(channel)
                await ctx.send(f"✅ Movido al canal: **{channel.name}**")
        else:
            await channel.connect(timeout=10.0)
            await ctx.send(f"✅ Conectado al canal: **{channel.name}**")
    except asyncio.TimeoutError:
        await ctx.send("❌ Tiempo de espera agotado al intentar conectar o moverme al canal de voz.")
    except Exception as e:
        await ctx.send(f"❌ Error al conectar al canal de voz: {str(e)}")

@bot.command(name='leave')
async def leave_voice(ctx):
    if ctx.voice_client:
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Desconectado del canal de voz.")
    else:
        await ctx.send("❌ No estoy en ningún canal de voz.")

@bot.command(name='tts')
async def text_to_speech(ctx, *, text: str):
    if not GTTS_AVAILABLE:
        await ctx.send("❌ gTTS no está instalado. Ejecuta: `pip install gTTS`")
        return

    if not ctx.author.voice:
        await ctx.send("❌ ¡Necesitas estar en un canal de voz para usar TTS!")
        return

    if not text or len(text.strip()) == 0:
        await ctx.send("❌ ¡Necesitas proporcionar texto para convertir a voz!")
        return

    if len(text) > 500:
        await ctx.send("❌ El texto es demasiado largo (máximo 500 caracteres).")
        return

    voice_channel = ctx.author.voice.channel
    can_connect, message = check_voice_permissions(voice_channel, ctx.guild.me)

    if not can_connect:
        await ctx.send(f"❌ {message}")
        return

    guild_id = ctx.guild.id
    language = tts_settings.get(guild_id, 'es')
    audio_buffer = BytesIO()

    processing_msg = None
    try:
        processing_msg = await ctx.send("🗣️ Generando audio TTS...")

        try:
            tts = gTTS(text=text, lang=language, slow=False)
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
        except Exception as tts_error:
            await processing_msg.edit(content=f"❌ Error al generar TTS: {str(tts_error)}")
            return

        if len(audio_buffer.getvalue()) < 1000:
            await processing_msg.edit(content="❌ Error: El audio generado es demasiado pequeño o está corrupto.")
            return

        if ctx.voice_client is None:
            try:
                voice_client = await voice_channel.connect(timeout=15.0)
                await asyncio.sleep(1)
            except asyncio.TimeoutError:
                await processing_msg.edit(content="❌ Tiempo de espera agotado al conectar al canal de voz.")
                return
            except Exception as e:
                await processing_msg.edit(content=f"❌ Error de conexión: {str(e)}")
                return
        else:
            voice_client = ctx.voice_client
            if voice_client.channel != voice_channel:
                await voice_client.move_to(voice_channel)
                await asyncio.sleep(1)

        if not voice_client.is_connected():
            await processing_msg.edit(content="❌ Error: No se pudo establecer una conexión estable al canal de voz.")
            return

        if voice_client.is_playing():
            voice_client.stop()
            await asyncio.sleep(0.5)

        try:
            audio_source = discord.FFmpegPCMAudio(audio_buffer, pipe=True, options='-vn -loglevel quiet -af "volume=0.8"')

            def after_playing(error):
                if error:
                    print(f'Error durante reproducción del TTS: {error}')

            voice_client.play(audio_source, after=after_playing)

            await asyncio.sleep(0.75)
            if not voice_client.is_playing():
                await processing_msg.edit(content="❌ Error: No se pudo iniciar la reproducción del TTS. Verifique el log del bot.")
                return

            preview_text = text[:100] + ('...' if len(text) > 100 else '')
            await processing_msg.edit(content=f"🗣️ **Reproduciendo TTS** (idioma: {language})\n> {preview_text}")

            timeout_counter = 0
            max_timeout_seconds = 30
            sleep_interval = 0.5
            while voice_client.is_playing() and timeout_counter < (max_timeout_seconds / sleep_interval):
                await asyncio.sleep(sleep_interval)
                timeout_counter += 1

            if timeout_counter >= (max_timeout_seconds / sleep_interval):
                if voice_client.is_playing():
                    voice_client.stop()

        except discord.errors.OpusNotLoaded:
            await processing_msg.edit(content="❌ Error: La biblioteca Opus no está cargada. Asegúrate de haber instalado `discord.py[voice]` y tener Opus configurado correctamente.")
        except FileNotFoundError:
            await processing_msg.edit(content="❌ Error: FFmpeg no encontrado. Asegúrese de que FFmpeg esté en su PATH.")
        except Exception as e:
            await processing_msg.edit(content=f"❌ Error al reproducir TTS: {str(e)}")

    except Exception as e:
        error_msg = f"❌ Error general en TTS: {str(e)}"
        if processing_msg:
            await processing_msg.edit(content=error_msg)
        else:
            await ctx.send(error_msg)

@bot.command(name='changevc')
async def change_voice(ctx, *, idioma: str):
    if not GTTS_AVAILABLE:
        await ctx.send("❌ gTTS no está disponible. No se puede cambiar el idioma.")
        return

    idioma_lower = idioma.lower().replace(' ', '_')

    if idioma_lower not in LANGUAGES:
        available_langs = ', '.join(LANGUAGES.keys())
        await ctx.send(f"❌ Idioma no disponible.\n📋 **Idiomas disponibles:** {available_langs}")
        return

    guild_id = ctx.guild.id
    tts_settings[guild_id] = LANGUAGES[idioma_lower]

    await ctx.send(f"✅ Idioma de TTS cambiado a: **{idioma}** (`{LANGUAGES[idioma_lower]}`) para este servidor.")

@bot.command(name='play')
async def play_music(ctx, *, query: str):
    if not YTDL_AVAILABLE:
        await ctx.send("❌ yt-dlp no está instalado. Ejecuta: `pip install yt-dlp`")
        return

    if not ctx.author.voice:
        await ctx.send("❌ ¡Necesitas estar en un canal de voz para reproducir música!")
        return

    voice_channel = ctx.author.voice.channel
    can_connect, message = check_voice_permissions(voice_channel, ctx.guild.me)

    if not can_connect:
        await ctx.send(f"❌ {message}")
        return

    loading_msg = None
    try:
        loading_msg = await ctx.send(f"🔍 Buscando: **{query}**...")

        if ctx.voice_client is None:
            try:
                voice_client = await voice_channel.connect(timeout=10.0)
                await asyncio.sleep(1)
            except asyncio.TimeoutError:
                await loading_msg.edit(content="❌ Tiempo de espera agotado al conectar al canal de voz.")
                return
            except Exception as e:
                await loading_msg.edit(content=f"❌ Error de conexión al canal de voz: {str(e)}")
                return
        else:
            voice_client = ctx.voice_client
            if voice_client.channel != voice_channel:
                await voice_client.move_to(voice_channel)
                await asyncio.sleep(1)

        if voice_client.is_playing():
            voice_client.stop()
            await asyncio.sleep(0.5)

        player = None
        try:
            player = await YTDLSource.from_url(query, loop=bot.loop, stream=True)
        except Exception as e:
            await loading_msg.edit(content=f"❌ Error al obtener el audio: {str(e)}. Intenta con una URL o una búsqueda más específica.")
            return

        def after_playing_music(error):
            if error:
                print(f'Error del reproductor de música: {error}')

        voice_client.play(player, after=after_playing_music)
        await loading_msg.edit(content=f"🎵 **Reproduciendo:** `{player.title}`")

    except discord.errors.OpusNotLoaded:
        if loading_msg:
            await loading_msg.edit(content="❌ Error: La biblioteca Opus no está cargada. Asegúrate de haber instalado `discord.py[voice]` y tener Opus configurado correctamente.")
        else:
            await ctx.send("❌ Error: Opus no cargado.")
    except FileNotFoundError:
        if loading_msg:
            await loading_msg.edit(content="❌ Error: FFmpeg no encontrado. Asegúrese de que FFmpeg esté en su PATH.")
        else:
            await ctx.send("❌ Error: FFmpeg no encontrado.")
    except Exception as e:
        error_msg = f"❌ Ocurrió un error inesperado al reproducir música: {str(e)}"
        if loading_msg:
            await loading_msg.edit(content=error_msg)
        else:
            await ctx.send(error_msg)

@bot.command(name='stop')
async def stop_music(ctx):
    if ctx.voice_client:
        if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
            ctx.voice_client.stop()
            await asyncio.sleep(0.5)
        await ctx.voice_client.disconnect()
        await ctx.send("⏹️ Música detenida y desconectado del canal de voz.")
    else:
        await ctx.send("❌ No estoy conectado a ningún canal de voz.")

@bot.command(name='pause')
async def pause_music(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ Música pausada.")
    else:
        await ctx.send("❌ No hay música reproduciéndose para pausar.")

@bot.command(name='resume')
async def resume_music(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ Música reanudada.")
    else:
        await ctx.send("❌ No hay música pausada para reanudar.")

@bot.command(name='volume')
async def change_volume(ctx, volume: int):
    if not ctx.voice_client:
        await ctx.send("❌ No estoy conectado a ningún canal de voz.")
        return

    if not 0 <= volume <= 100:
        await ctx.send("❌ El volumen debe estar entre 0 y 100.")
        return

    if ctx.voice_client.source:
        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"🔊 Volumen cambiado a {volume}%.")
    else:
        await ctx.send("❌ No hay música reproduciéndose para ajustar el volumen.")

@bot.command(name='skip')
async def skip_music(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Canción saltada.")
    else:
        await ctx.send("❌ No hay música reproduciéndose para saltar.")

@bot.command(name='test_audio')
async def test_audio(ctx):
    if not ctx.author.voice:
        await ctx.send("❌ ¡Necesitas estar en un canal de voz para la prueba de audio!")
        return

    voice_channel = ctx.author.voice.channel
    can_connect, message = check_voice_permissions(voice_channel, ctx.guild.me)

    if not can_connect:
        await ctx.send(f"❌ {message}")
        return

    test_msg = None
    try:
        if ctx.voice_client is None:
            voice_client = await voice_channel.connect(timeout=15.0)
        else:
            voice_client = ctx.voice_client

        test_msg = await ctx.send("🔊 Generando tono de prueba (2 segundos de ruido blanco)...")

        audio_source = discord.FFmpegPCMAudio(
            'anullsrc=channel_layout=mono:sample_rate=48000',
            before_options='-f lavfi -i "sine=frequency=440:duration=2"',
            options='-vn -loglevel quiet'
        )

        def after_test(error):
            if error:
                print(f'Error en prueba de audio: {error}')

        if voice_client.is_playing():
            voice_client.stop()
            await asyncio.sleep(0.5)

        voice_client.play(audio_source, after=after_test)

        await test_msg.edit(content="🔊 **Reproduciendo tono de prueba...** (deberías escuchar un tono)")

        while voice_client.is_playing():
            await asyncio.sleep(0.1)

        await test_msg.edit(content="✅ **Prueba de audio completada.**\nSi no escuchaste nada, hay un problema con FFmpeg, Opus o los permisos de voz.")

    except discord.errors.OpusNotLoaded:
        if test_msg:
            await test_msg.edit(content="❌ Error: La biblioteca Opus no está cargada. Asegúrate de haber instalado `discord.py[voice]` y tener Opus configurado correctamente.")
        else:
            await ctx.send("❌ Error: Opus no cargado.")
    except FileNotFoundError:
        if test_msg:
            await test_msg.edit(content="❌ Error: FFmpeg no encontrado. Asegúrese de que FFmpeg esté en su PATH.")
        else:
            await ctx.send("❌ Error: FFmpeg no encontrado.")
    except Exception as e:
        error_msg = f"❌ Error en prueba de audio: {str(e)}"
        if test_msg:
            await test_msg.edit(content=error_msg)
        else:
            await ctx.send(error_msg)

@bot.command(name='debug_tts')
async def debug_tts(ctx, *, text="Hola mundo de depuración"):
    if not GTTS_AVAILABLE:
        await ctx.send("❌ gTTS no disponible.")
        return

    debug_info = []
    debug_msg = await ctx.send("🔍 **Debug TTS iniciado...**")

    try:
        debug_info.append("📝 **Paso 1: Generación de archivo TTS en memoria.**")
        await debug_msg.edit(content="\n".join(debug_info))

        audio_buffer = BytesIO()
        try:
            tts = gTTS(text=text, lang='es', slow=False)
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            file_size = len(audio_buffer.getvalue())
            debug_info.append(f"✅ Audio TTS generado. Tamaño: {file_size} bytes.")
            if file_size < 1000:
                debug_info.append("⚠️ ¡Advertencia! El archivo de audio es muy pequeño, podría estar corrupto.")
        except Exception as e:
            debug_info.append(f"❌ Error al generar TTS con gTTS: {e}")
            await debug_msg.edit(content="\n".join(debug_info))
            return

        debug_info.append("\n🔗 **Paso 2: Verificación y conexión al canal de voz.**")
        await debug_msg.edit(content="\n".join(debug_info))

        if not ctx.author.voice:
            debug_info.append("❌ Error: El usuario no está en un canal de voz.")
            await debug_msg.edit(content="\n".join(debug_info))
            return

        debug_info.append(f"🎤 Canal de voz del usuario: {ctx.author.voice.channel.name}")

        voice_client = ctx.voice_client
        if voice_client is None:
            try:
                debug_info.append("🔗 Conectando al canal de voz...")
                await debug_msg.edit(content="\n".join(debug_info))
                voice_client = await ctx.author.voice.channel.connect(timeout=15.0)
                debug_info.append(f"✅ Conectado al canal: {voice_client.channel.name}")
                await asyncio.sleep(1)
            except asyncio.TimeoutError:
                debug_info.append("❌ Tiempo de espera agotado al conectar.")
                await debug_msg.edit(content="\n".join(debug_info))
                return
            except Exception as e:
                debug_info.append(f"❌ Error al conectar al canal de voz: {e}")
                await debug_msg.edit(content="\n".join(debug_info))
                return
        else:
            if voice_client.channel != ctx.author.voice.channel:
                debug_info.append(f"🔗 Moviendo al canal de voz: {ctx.author.voice.channel.name}...")
                await debug_msg.edit(content="\n".join(debug_info))
                await voice_client.move_to(ctx.author.voice.channel)
                debug_info.append(f"✅ Movido al canal: {voice_client.channel.name}")
                await asyncio.sleep(1)
            else:
                debug_info.append("🔗 Ya estaba conectado al canal correcto.")

        if not voice_client.is_connected():
            debug_info.append("❌ Error: VoiceClient no está conectado.")
            await debug_msg.edit(content="\n".join(debug_info))
            return

        debug_info.append("\n🎵 **Paso 3: Preparación y reproducción del audio.**")
        await debug_msg.edit(content="\n".join(debug_info))

        if voice_client.is_playing():
            debug_info.append("🎵 Deteniendo reproducción actual del bot...")
            await debug_msg.edit(content="\n".join(debug_info))
            voice_client.stop()
            await asyncio.sleep(0.5)

        playback_error = None
        def after_playing_debug(error):
            nonlocal playback_error
            if error:
                playback_error = error
                print(f'[ERROR] Error durante reproducción en debug_tts (callback): {error}')

        try:
            audio_source = discord.FFmpegPCMAudio(audio_buffer, pipe=True, options='-vn -loglevel quiet -af "volume=0.8"')
            voice_client.play(audio_source, after=after_playing_debug)
            await asyncio.sleep(0.75)

            if not voice_client.is_playing():
                debug_info.append("❌ ¡La reproducción NO se inició! Posible problema con FFmpeg, Opus o la fuente de audio.")
                await debug_msg.edit(content="\n".join(debug_info))
                return

            debug_info.append(f"✅ Reproducción iniciada del TTS para: '{text[:50]}...'")
            await debug_msg.edit(content="\n".join(debug_info))

            timeout_counter = 0
            max_wait = 30
            while voice_client.is_playing() and timeout_counter < (max_wait / 0.5):
                await asyncio.sleep(0.5)
                timeout_counter += 1

            if timeout_counter >= (max_wait / 0.5):
                if voice_client.is_playing():
                    voice_client.stop()

            if playback_error:
                debug_info.append(f"❌ Error final de reproducción (callback): {playback_error}")
            else:
                debug_info.append("🏁 Reproducción terminada.")

        except discord.errors.OpusNotLoaded:
            debug_info.append("❌ Error: Opus no está cargado. Asegúrate de instalar `discord.py[voice]`.")
        except FileNotFoundError:
            debug_info.append("❌ Error: FFmpeg no encontrado. Asegúrate de que FFmpeg esté en tu PATH.")
        except Exception as e:
            debug_info.append(f"❌ Error inesperado durante la reproducción: {e}")

        debug_info.append("\n✅ **Debug TTS finalizado.**")
        await debug_msg.edit(content="\n".join(debug_info))

    except Exception as e:
        debug_info.append(f"❌ Error general en debug_tts: {str(e)}")
        await debug_msg.edit(content="\n".join(debug_info))

@bot.command(name='status')
async def status_command(ctx):
    embed = discord.Embed(title="🤖 Estado del Bot", color=0x00ff00)

    embed.add_field(
        name="📦 Dependencias",
        value=(f"gTTS: {'✅ Disponible' if GTTS_AVAILABLE else '❌ No disponible'}\n"
               f"yt-dlp: {'✅ Disponible' if YTDL_AVAILABLE else '❌ No disponible'}"),
        inline=False
    )

    if ctx.voice_client:
        embed.add_field(
            name="🔊 Estado de Voz",
            value=(f"Conectado a: **{ctx.voice_client.channel.name}**\n"
                   f"Reproduciendo: {'✅ Sí' if ctx.voice_client.is_playing() else '❌ No'}\n"
                   f"Pausado: {'⏸️ Sí' if ctx.voice_client.is_paused() else '❌ No'}"),
            inline=False
        )
    else:
        embed.add_field(
            name="🔊 Estado de Voz",
            value="No conectado a ningún canal de voz.",
            inline=False
        )

    guild_lang = tts_settings.get(ctx.guild.id, 'es')
    embed.add_field(
        name="🗣️ Configuración TTS",
        value=f"Idioma actual: **{guild_lang}**",
        inline=False
    )

    await ctx.send(embed=embed)

@bot.command(name='help_bot')
async def help_command(ctx):
    embed = discord.Embed(title="🤖 Comandos del Bot", color=0x00ff00)

    embed.add_field(
        name="🎤 Comandos de Voz",
        value="`!join` - Conectar a tu canal de voz\n"
              "`!leave` - Desconectar del canal\n"
              "`!status` - Ver estado actual del bot\n"
              "`!test_audio` - Ejecuta una prueba de audio para diagnosticar problemas\n"
              "`!debug_tts` - Ejecuta una prueba de TTS detallada para depuración",
        inline=False
    )

    if GTTS_AVAILABLE:
        embed.add_field(
            name="🗣️ Comandos de TTS",
            value="`!tts <texto>` - Convierte texto a voz y lo reproduce\n"
                  "`!changevc <idioma>` - Cambia el idioma del TTS para este servidor",
            inline=False
        )
    else:
        embed.add_field(
            name="🗣️ Comandos de TTS",
            value="❌ Comandos de TTS no disponibles - instala `gTTS` (`pip install gTTS`)",
            inline=False
        )

    if YTDL_AVAILABLE:
        embed.add_field(
            name="🎵 Comandos de Música",
            value="`!play <nombre/url>` - Reproduce música o un video (busca si no es URL)\n"
                  "`!stop` - Detiene la música y desconecta el bot\n"
                  "`!pause` - Pausa la música actual\n"
                  "`!resume` - Reanuda la música pausada\n"
                  "`!skip` - Salta la canción actual\n"
                  "`!volume <0-100>` - Cambia el volumen de la música",
            inline=False
        )
    else:
        embed.add_field(
            name="🎵 Comandos de Música",
            value="❌ Comandos de Música no disponibles - instala `yt-dlp` (`pip install yt-dlp`) y `FFmpeg`",
            inline=False
        )

    embed.add_field(
        name="🌍 Idiomas disponibles para TTS (`!changevc`)",
        value="```\n" + ", ".join(LANGUAGES.keys()) + "\n```",
        inline=False
    )

    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return

    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ ¡Falta un argumento! Uso correcto: `!{ctx.command.name} {ctx.command.signature.split(' ', 1)[1]}`")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Tipo de argumento incorrecto. Revisa el valor que proporcionaste para este comando.")
    elif isinstance(error, commands.BotMissingPermissions):
        perms_needed = ", ".join(error.missing_permissions)
        await ctx.send(f"❌ Necesito los siguientes permisos para ejecutar esto: `{perms_needed}`.")
    elif isinstance(error, commands.MissingPermissions):
        perms_needed = ", ".join(error.missing_permissions)
        await ctx.send(f"❌ No tienes los permisos necesarios para ejecutar este comando. Necesitas: `{perms_needed}`.")
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("❌ Este comando no puede ser usado en mensajes privados.")
    elif isinstance(error, commands.DisabledCommand):
        await ctx.send("❌ Este comando ha sido deshabilitado.")
    else:
        print(f"Error no manejado: {type(error).__name__}: {error}")
        await ctx.send(f"❌ Ocurrió un error inesperado al ejecutar el comando: `{type(error).__name__}`. Consulta la consola del bot para más detalles.")

if __name__ == "__main__":
    print("\n--- Iniciando Bot de Discord ---")
    print("Asegúrate de que las siguientes dependencias estén instaladas y FFmpeg esté en tu PATH:")
    print("  - `pip install discord.py[voice]`")
    print("  - `pip install gTTS`")
    print("  - `pip install yt-dlp`")
    print("  - FFmpeg (https://ffmpeg.org/download.html)\n")

    try:
        bot.run(DISCORD_TOKEN)
    except discord.LoginFailure:
        print("❌ Fallo de inicio de sesión: Token de Discord inválido o no configurado. "
              "Asegúrate de que la variable de entorno 'DISCORD_TOKEN' esté configurada correctamente.")
    except Exception as e:
        print(f"❌ Error al iniciar el bot: {e}")
