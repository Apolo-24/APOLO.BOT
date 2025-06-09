import discord
from discord.ext import commands
from io import BytesIO
import requests
import asyncio
import os
import webserver
import yt_dlp
import re 


DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

   
# Importación segura de gTTS
try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
    print("✅ gTTS importado correctamente")
except ImportError as e:
    print(f"❌ Error al importar gTTS: {e}")
    print("💡 Instala gTTS con: pip install gTTS")
    GTTS_AVAILABLE = False

# Importación segura de yt-dlp
try:
    import yt_dlp
    YTDL_AVAILABLE = True
    print("✅ yt-dlp importado correctamente")
except ImportError as e:
    print(f"❌ Error al importar yt-dlp: {e}")
    print("💡 Instala yt-dlp con: pip install yt-dlp")
    YTDL_AVAILABLE = False

# Configuración del bot
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.members = True
intents.presences = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Diccionario para almacenar configuraciones de TTS por servidor
tts_settings = {}

# Diccionario de idiomas disponibles
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

# Configuración de yt-dlp (solo si está disponible)
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
        'extract_flat': False
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

        @classmethod
        async def from_url(cls, url, *, loop=None, stream=False):
            loop = loop or asyncio.get_event_loop()
            try:
                data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

                # Si es una lista de resultados (como ytsearch:...), revisamos los primeros válidos
                if 'entries' in data:
                    for entry in data['entries']:
                        if not entry:
                            continue
                        try:
                            filename = entry['url'] if stream else ytdl.prepare_filename(entry)
                            return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=entry)
                        except Exception as inner_e:
                            print(f"[WARNING] Error con entrada: {entry.get('title', 'sin título')} - {inner_e}")
                    raise Exception("❌ Ningún resultado válido encontrado.")
                else:
                    # Si no es una búsqueda, es una URL directa
                    filename = data['url'] if stream else ytdl.prepare_filename(data)
                    return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

            except Exception as e:
                print(f"[ERROR] Error en YTDLSource.from_url: {e}")
                raise e

@bot.event
async def on_ready():
    bot.add_view(AceptarReglas())
    print(f'🤖 {bot.user} ha iniciado sesión!')
    print(f'🆔 ID del bot: {bot.user.id}')
    print(f'🗣️ gTTS disponible: {"✅" if GTTS_AVAILABLE else "❌"}')
    print(f'🎵 yt-dlp disponible: {"✅" if YTDL_AVAILABLE else "❌"}')
    print('🚀 Bot listo para usar!')

def is_url(string):
    """Verifica si una cadena es una URL válida"""
    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(string) is not None

def check_voice_permissions(voice_channel, guild_member):
    """Verifica permisos de voz"""
    permissions = voice_channel.permissions_for(guild_member)
    if not permissions.connect:
        return False, "No tengo permisos para conectarme a ese canal de voz"
    if not permissions.speak:
        return False, "No tengo permisos para hablar en ese canal de voz"
    return True, "OK"

@bot.command(name='join')
async def join_voice(ctx):
    """Hace que el bot se una al canal de voz del usuario"""
    if not ctx.author.voice:
        await ctx.send("❌ ¡Necesitas estar en un canal de voz!")
        return
    
    channel = ctx.author.voice.channel
    can_connect, message = check_voice_permissions(channel, ctx.guild.me)
    
    if not can_connect:
        await ctx.send(f"❌ {message}")
        return
    
    try:
        if ctx.voice_client is not None:
            await ctx.voice_client.move_to(channel)
            await ctx.send(f"✅ Movido al canal: **{channel.name}**")
        else:
            await channel.connect(timeout=10.0)
            await ctx.send(f"✅ Conectado al canal: **{channel.name}**")
    except asyncio.TimeoutError:
        await ctx.send("❌ Tiempo de espera agotado al conectar")
    except Exception as e:
        await ctx.send(f"❌ Error al conectar: {str(e)}")

@bot.command(name='leave')
async def leave_voice(ctx):
    """Hace que el bot abandone el canal de voz"""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Desconectado del canal de voz")
    else:
        await ctx.send("❌ No estoy en ningún canal de voz")

@bot.command(name='tts')
async def text_to_speech(ctx, *, text):
    """Convierte texto a voz y lo reproduce en el canal de voz"""
    # Verificar si gTTS está disponible
    if not GTTS_AVAILABLE:
        await ctx.send("❌ gTTS no está instalado. Ejecuta: `pip install gTTS`")
        return
    
    if not ctx.author.voice:
        await ctx.send("❌ ¡Necesitas estar en un canal de voz para usar TTS!")
        return
    
    if not text or len(text.strip()) == 0:
        await ctx.send("❌ ¡Necesitas proporcionar texto para convertir a voz!")
        return
    
    # Limitar longitud del texto
    if len(text) > 500:
        await ctx.send("❌ El texto es demasiado largo (máximo 500 caracteres)")
        return
    
    voice_channel = ctx.author.voice.channel
    can_connect, message = check_voice_permissions(voice_channel, ctx.guild.me)
    
    if not can_connect:
        await ctx.send(f"❌ {message}")
        return
    
    guild_id = ctx.guild.id
    language = tts_settings.get(guild_id, 'es')
    temp_filename = f"tts_temp_{ctx.guild.id}_{ctx.message.id}.mp3"
    
    processing_msg = None
    try:
        processing_msg = await ctx.send("🗣️ Generando audio TTS...")
        print(f"[DEBUG] Generando TTS para: '{text}' en idioma: {language}")
        
        # Crear el audio TTS con manejo de errores mejorado
        try:
            tts = gTTS(text=text, lang=language, slow=False)
            tts.save(temp_filename)
            print(f"[DEBUG] Archivo TTS guardado: {temp_filename}")
        except Exception as tts_error:
            print(f"[ERROR] Error en gTTS al guardar: {tts_error}")
            await processing_msg.edit(content=f"❌ Error al generar TTS: {str(tts_error)}")
            return
        
        # Verificar que el archivo se creó correctamente y tiene contenido
        if not os.path.exists(temp_filename):
            await processing_msg.edit(content="❌ Error: No se pudo crear el archivo de audio")
            print("[ERROR] Archivo TTS no existe después de gTTS.save()")
            return
        
        file_size = os.path.getsize(temp_filename)
        print(f"[DEBUG] Tamaño del archivo TTS: {file_size} bytes")
        
        if file_size < 1000:  # Archivo muy pequeño, probablemente corrupto (ajustar según pruebas)
            await processing_msg.edit(content="❌ Error: El archivo de audio generado es demasiado pequeño o está corrupto")
            print(f"[ERROR] Archivo TTS muy pequeño: {file_size} bytes")
            return
        
        # Conectar al canal de voz
        if ctx.voice_client is None:
            try:
                print(f"[DEBUG] Conectando al canal: {voice_channel.name}")
                voice_client = await voice_channel.connect(timeout=15.0)
                await asyncio.sleep(2)  # Pausa más larga para estabilizar
                print("[DEBUG] Conexión establecida")
            except asyncio.TimeoutError:
                await processing_msg.edit(content="❌ Tiempo de espera agotado al conectar")
                return
            except Exception as e:
                print(f"[ERROR] Error de conexión al canal de voz: {e}")
                await processing_msg.edit(content=f"❌ Error de conexión: {str(e)}")
                return
        else:
            voice_client = ctx.voice_client
            if voice_client.channel != voice_channel:
                print(f"[DEBUG] Moviendo al canal: {voice_channel.name}")
                await voice_client.move_to(voice_channel)
                await asyncio.sleep(2)
        
        # Verificar conexión múltiples veces (reasegurar estado)
        if not voice_client.is_connected():
            await processing_msg.edit(content="❌ Error: No se pudo establecer conexión estable al canal de voz")
            print("[ERROR] VoiceClient no conectado después de intentos")
            return
        
        print(f"[DEBUG] Bot conectado al canal: {voice_client.channel.name}")
        
        # Detener reproducción actual para asegurar el canal libre
        if voice_client.is_playing():
            print("[DEBUG] Deteniendo reproducción actual antes de TTS")
            voice_client.stop()
            await asyncio.sleep(1) # Dar tiempo para que se detenga
        
        # Reproducir audio con configuración más robusta (simplificada para archivos locales)
        try:
            print("[DEBUG] Creando fuente de audio para TTS")
            
            # **CAMBIO CLAVE AQUÍ**: Simplificando las opciones de FFmpeg para gTTS.
            # Las opciones de reconexión no son relevantes para un archivo local.
            # Mantenemos solo lo esencial para audio y control de volumen.
            audio_source = discord.FFmpegPCMAudio(
                temp_filename,
                options='-vn -loglevel quiet -af "volume=0.8"' # Solo opciones de audio
            )
            
            # Función de callback para debugging (mejorada para imprimir el error)
            def after_playing(error):
                if error:
                    print(f'[ERROR] Error durante reproducción del TTS: {error}')
                    # Considera loggear o enviar un mensaje si es crítico
                else:
                    print('[DEBUG] Reproducción TTS completada exitosamente')
            
            print("[DEBUG] Iniciando reproducción del TTS")
            voice_client.play(audio_source, after=after_playing)
            
            # Verificar que la reproducción comenzó
            await asyncio.sleep(0.75) # Un poco más de espera
            if not voice_client.is_playing():
                await processing_msg.edit(content="❌ Error: No se pudo iniciar la reproducción del TTS. Verifique el log del bot.")
                print("[ERROR] voice_client.is_playing() es False justo después de play()")
                return
            
            preview_text = text[:100] + ('...' if len(text) > 100 else '')
            await processing_msg.edit(content=f"🗣️ **Reproduciendo TTS** (idioma: {language})\n> {preview_text}")
            print(f"[DEBUG] Reproduciendo TTS: {preview_text}")
            
            # Esperar reproducción con timeout
            timeout_counter = 0
            max_timeout_seconds = 30 # Aumentado a 30 segundos máximo para TTS
            sleep_interval = 0.5
            while voice_client.is_playing() and timeout_counter < (max_timeout_seconds / sleep_interval):
                await asyncio.sleep(sleep_interval)
                timeout_counter += 1
            
            if timeout_counter >= (max_timeout_seconds / sleep_interval):
                print(f"[WARNING] Timeout en reproducción del TTS ({max_timeout_seconds}s), forzando stop")
                voice_client.stop()
            
            print("[DEBUG] Espera por reproducción TTS finalizada")
            
        except discord.errors.OpusNotLoaded:
            await processing_msg.edit(content="❌ Error: Opus no está cargado. Instala discord.py[voice]")
            print("[ERROR] Opus no está cargado")
        except FileNotFoundError:
            await processing_msg.edit(content="❌ Error: FFmpeg no encontrado. Asegúrese de que FFmpeg esté en su PATH.")
            print("[ERROR] FFmpeg no encontrado durante la reproducción de TTS")
        except Exception as e:
            await processing_msg.edit(content=f"❌ Error al reproducir TTS: {str(e)}")
            print(f"[ERROR] Error en reproducción de TTS: {e}")
        
    except Exception as e:
        error_msg = f"❌ Error general en TTS: {str(e)}"
        if processing_msg:
            await processing_msg.edit(content=error_msg)
        else:
            await ctx.send(error_msg)
        print(f"[ERROR] Error general detallado TTS: {e}")
    
    finally:
        # **CAMBIO CLAVE AQUÍ**: Comentado temporalmente para depuración.
        # Descomenta esta línea una vez que el TTS funcione.
        # try:
        #     if os.path.exists(temp_filename):
        #         os.remove(temp_filename)
        #         print(f"[DEBUG] Archivo temporal eliminado: {temp_filename}")
        # except Exception as e:
        #     print(f"[ERROR] Error al eliminar archivo temporal: {e}")
        pass # Mantener pass si os.remove está comentado

@bot.command(name='changevc')
async def change_voice(ctx, *, idioma):
    """Cambia el idioma del TTS para el servidor"""
    if not GTTS_AVAILABLE:
        await ctx.send("❌ gTTS no está disponible")
        return
    
    idioma_lower = idioma.lower().replace(' ', '_')
    
    if idioma_lower not in LANGUAGES:
        available_langs = ', '.join(LANGUAGES.keys())
        await ctx.send(f"❌ Idioma no disponible.\n📋 **Idiomas disponibles:** {available_langs}")
        return
    
    guild_id = ctx.guild.id
    tts_settings[guild_id] = LANGUAGES[idioma_lower]
    
    await ctx.send(f"✅ Idioma de TTS cambiado a: **{idioma}** ({LANGUAGES[idioma_lower]})")

@bot.command(name='play')
async def play_music(ctx, *, query):
    """Reproduce música desde YouTube o otras fuentes"""
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
    
    try:
        loading_msg = await ctx.send("🔍 Buscando música...")
        
        # Conectar al canal de voz
        if ctx.voice_client is None:
            try:
                voice_client = await voice_channel.connect(timeout=10.0)
                await asyncio.sleep(1)
            except asyncio.TimeoutError:
                await loading_msg.edit(content="❌ Tiempo de espera agotado al conectar")
                return
        else:
            voice_client = ctx.voice_client
            if voice_client.channel != voice_channel:
                await voice_client.move_to(voice_channel)
                await asyncio.sleep(1)
        
        # Preparar búsqueda
        if not is_url(query):
            query = f"ytsearch:{query}"
        
        # Obtener audio
        try:
            player = await YTDLSource.from_url(query, loop=bot.loop, stream=True)
        except Exception as e:
            await loading_msg.edit(content=f"❌ Error al obtener audio: {str(e)}")
            return
        
        # Reproducir
        if voice_client.is_playing():
            voice_client.stop()
            await asyncio.sleep(0.5)
        
        voice_client.play(player, after=lambda e: print(f'Error del reproductor: {e}') if e else None)
        await loading_msg.edit(content=f"🎵 **Reproduciendo:** {player.title}")
        
    except Exception as e:
        await ctx.send(f"❌ Error al reproducir música: {str(e)}")
        print(f"Error detallado: {e}")

@bot.command(name='stop')
async def stop_music(ctx):
    """Detiene la música y desconecta el bot del canal de voz"""
    if ctx.voice_client:
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()
        await ctx.voice_client.disconnect()
        await ctx.send("⏹️ Música detenida y desconectado del canal de voz.")
    else:
        await ctx.send("❌ No estoy conectado a ningún canal de voz.")

@bot.command(name='pause')
async def pause_music(ctx):
    """Pausa la música actual"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ Música pausada.")
    else:
        await ctx.send("❌ No hay música reproduciéndose.")

@bot.command(name='resume')
async def resume_music(ctx):
    """Reanuda la música pausada"""
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ Música reanudada.")
    else:
        await ctx.send("❌ No hay música pausada.")

@bot.command(name='volume')
async def change_volume(ctx, volume: int):
    """Cambia el volumen de la música (0-100)"""
    if not ctx.voice_client:
        await ctx.send("❌ No estoy conectado a ningún canal de voz.")
        return
    
    if not 0 <= volume <= 100:
        await ctx.send("❌ El volumen debe estar entre 0 y 100.")
        return
    
    if ctx.voice_client.source and hasattr(ctx.voice_client.source, 'volume'):
        ctx.voice_client.source.volume = volume / 100
        await ctx.send(f"🔊 Volumen cambiado a {volume}%")
    else:
        await ctx.send("❌ No hay música reproduciéndose o no se puede ajustar el volumen.")

@bot.command(name='skip')
async def skip_music(ctx):
    """Salta la canción actual"""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Canción saltada.")
    else:
        await ctx.send("❌ No hay música reproduciéndose.")

@bot.command(name='test_audio')
async def test_audio(ctx):
    """Prueba de audio básica para diagnosticar problemas"""
    if not ctx.author.voice:
        await ctx.send("❌ ¡Necesitas estar en un canal de voz!")
        return
    
    voice_channel = ctx.author.voice.channel
    can_connect, message = check_voice_permissions(voice_channel, ctx.guild.me)
    
    if not can_connect:
        await ctx.send(f"❌ {message}")
        return
    
    try:
        # Conectar al canal
        if ctx.voice_client is None:
            voice_client = await voice_channel.connect(timeout=15.0)
        else:
            voice_client = ctx.voice_client
        
        # Crear un tono de prueba simple usando FFmpeg
        test_msg = await ctx.send("🔊 Generando tono de prueba...")
        
        # Generar un tono de 1 segundo usando FFmpeg
        audio_source = discord.FFmpegPCMAudio(
            'anullsrc=channel_layout=mono:sample_rate=48000',
            before_options='-f lavfi -t 2',
            options='-vn -loglevel quiet'
        )
        
        def after_test(error):
            if error:
                print(f'[ERROR] Error en prueba de audio: {error}')
            else:
                print('[DEBUG] Prueba de audio completada')
        
        voice_client.play(audio_source, after=after_test)
        
        await test_msg.edit(content="🔊 **Reproduciendo tono de prueba...** (2 segundos de silencio)")
        
        # Esperar a que termine
        while voice_client.is_playing():
            await asyncio.sleep(0.1)
        
        await test_msg.edit(content="✅ **Prueba de audio completada**\nSi no escuchaste nada, hay un problema con FFmpeg o los permisos de voz.")
        
    except Exception as e:
        await ctx.send(f"❌ Error en prueba de audio: {str(e)}")
        print(f"[ERROR] Error en test_audio: {e}")

@bot.command(name='debug_tts')
async def debug_tts(ctx, *, text="Hola mundo de depuración"):
    """Versión de debug del TTS con información detallada"""
    if not GTTS_AVAILABLE:
        await ctx.send("❌ gTTS no disponible")
        return
    
    debug_info = []
    # Usamos un nombre de archivo más robusto para debug, y no lo eliminamos para inspección
    temp_filename = f"debug_tts_output_{ctx.guild.id}_{ctx.message.id}.mp3"
    
    try:
        debug_info.append("🔍 **Debug TTS iniciado**")
        debug_msg = await ctx.send("\n".join(debug_info))
        
        # 1. Probar generación de gTTS
        debug_info.append("📝 Generando archivo TTS...")
        await debug_msg.edit(content="\n".join(debug_info))
        
        try:
            tts = gTTS(text=text, lang='es', slow=False)
            tts.save(temp_filename)
        except Exception as e:
            debug_info.append(f"❌ Error al generar TTS con gTTS: {e}")
            await debug_msg.edit(content="\n".join(debug_info))
            return
        
        if os.path.exists(temp_filename):
            file_size = os.path.getsize(temp_filename)
            debug_info.append(f"✅ Archivo creado: `{temp_filename}` ({file_size} bytes)")
            if file_size < 1000:
                debug_info.append("⚠️ Archivo muy pequeño, podría estar corrupto.")
        else:
            debug_info.append("❌ Archivo no se creó, a pesar de gTTS.save() no dar error.")
            await debug_msg.edit(content="\n".join(debug_info))
            return
        
        # 2. Verificar conexión de voz
        if not ctx.author.voice:
            debug_info.append("❌ Usuario no está en canal de voz.")
            await debug_msg.edit(content="\n".join(debug_info))
            return
        
        debug_info.append(f"🎤 Canal de voz del usuario: {ctx.author.voice.channel.name}")
        await debug_msg.edit(content="\n".join(debug_info))
        
        # 3. Conectar al canal de voz
        voice_client = ctx.voice_client
        if voice_client is None:
            try:
                debug_info.append("🔗 Conectando al canal de voz...")
                await debug_msg.edit(content="\n".join(debug_info))
                voice_client = await ctx.author.voice.channel.connect(timeout=15.0)
                debug_info.append(f"✅ Conectado al canal: {voice_client.channel.name}")
                await asyncio.sleep(1) # Pausa para estabilizar
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
                await asyncio.sleep(1) # Pausa para estabilizar
            else:
                debug_info.append("🔗 Ya estaba conectado al canal correcto.")
        
        if not voice_client.is_connected():
            debug_info.append("❌ Error: VoiceClient no está conectado.")
            await debug_msg.edit(content="\n".join(debug_info))
            return

        # 4. Detener cualquier reproducción existente
        if voice_client.is_playing():
            debug_info.append("🎵 Deteniendo reproducción actual del bot...")
            await debug_msg.edit(content="\n".join(debug_info))
            voice_client.stop()
            await asyncio.sleep(1) # Dar tiempo para que se detenga

        # 5. Probar reproducción del archivo TTS
        debug_info.append("🎵 Iniciando reproducción del TTS...")
        await debug_msg.edit(content="\n".join(debug_info))
        
        # **CAMBIO CLAVE AQUÍ**: Opciones simplificadas para debug_tts también.
        audio_source = discord.FFmpegPCMAudio(
            temp_filename,
            options='-vn -loglevel quiet -af "volume=0.8"' # Solo opciones de audio
        )
        
        # Función de callback para capturar y mostrar el error
        playback_error = None
        def after_playing_debug(error):
            nonlocal playback_error # Necesario para modificar la variable externa
            if error:
                playback_error = error
                print(f'[ERROR] Error durante reproducción en debug_tts: {error}')
            else:
                print('[DEBUG] Reproducción de debug_tts completada exitosamente')
        
        voice_client.play(audio_source, after=after_playing_debug)
        
        await asyncio.sleep(0.75) # Un poco más de espera
        if not voice_client.is_playing():
            debug_info.append("❌ La reproducción NO se inició. Posible problema con FFmpeg o la fuente de audio.")
            await debug_msg.edit(content="\n".join(debug_info))
            return

        debug_info.append(f"✅ Reproducción iniciada del TTS: '{text}'")
        await debug_msg.edit(content="\n".join(debug_info))
        
        # Esperar reproducción con timeout
        timeout_counter = 0
        max_wait = 30 # segundos
        while voice_client.is_playing() and timeout_counter < (max_wait / 0.5):
            await asyncio.sleep(0.5)
            timeout_counter += 1
        
        if timeout_counter >= (max_wait / 0.5):
            debug_info.append(f"⚠️ Timeout de {max_wait}s alcanzado, forzando stop de reproducción.")
            voice_client.stop()
        
        if playback_error:
            debug_info.append(f"❌ Error final de reproducción (callback): {playback_error}")
        else:
            debug_info.append("🏁 Reproducción terminada.")
            
        await debug_msg.edit(content="\n".join(debug_info))
        
    except Exception as e:
        debug_info.append(f"❌ Error general en debug_tts: {str(e)}")
        await ctx.send("\n".join(debug_info))
        print(f"[ERROR] Error general en debug_tts: {e}")
    
    finally:
        # **NO** eliminamos el archivo temporal en debug_tts para que puedas inspeccionarlo.
        debug_info.append(f"💡 Archivo de audio temporal (`{temp_filename}`) se ha dejado para inspección.")
        await debug_msg.edit(content="\n".join(debug_info))

@bot.command(name='status')
async def status_command(ctx): # Cambié el nombre para evitar conflictos si existe otro comando "status"
    """Muestra el estado del bot y las dependencias"""
    embed = discord.Embed(title="🤖 Estado del Bot", color=0x00ff00)
    
    embed.add_field(
        name="📦 Dependencias",
        value=f"gTTS: {'✅ Disponible' if GTTS_AVAILABLE else '❌ No disponible'}\nyt-dlp: {'✅ Disponible' if YTDL_AVAILABLE else '❌ No disponible'}",
        inline=False
    )
    
    if ctx.voice_client:
        embed.add_field(
            name="🔊 Estado de Voz",
            value=f"Conectado a: **{ctx.voice_client.channel.name}**\nReproduciendo: {'✅' if ctx.voice_client.is_playing() else '❌'}",
            inline=False
        )
    else:
        embed.add_field(
            name="🔊 Estado de Voz",
            value="No conectado a ningún canal",
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
    """Muestra la ayuda del bot"""
    embed = discord.Embed(title="🤖 Comandos del Bot", color=0x00ff00)
    
    embed.add_field(
        name="🎤 Comandos de Voz",
        value="`!join` - Conectar a tu canal de voz\n`!leave` - Desconectar del canal\n`!status` - Ver estado del bot\n`!test_audio` - Prueba de audio\n`!debug_tts` - Debug del TTS",
        inline=False
    )
    
    if GTTS_AVAILABLE:
        embed.add_field(
            name="🗣️ Comandos de TTS",
            value="`!tts <texto>` - Convierte texto a voz\n`!changevc <idioma>` - Cambia idioma del TTS",
            inline=False
        )
    else:
        embed.add_field(
            name="🗣️ Comandos de TTS",
            value="❌ TTS no disponible - instala gTTS",
            inline=False
        )
    
    if YTDL_AVAILABLE:
        embed.add_field(
            name="🎵 Comandos de Música",
            value="`!play <nombre/url>` - Reproduce música\n`!stop` - Detiene y desconecta\n`!pause` - Pausa música\n`!resume` - Reanuda música\n`!skip` - Salta canción\n`!volume <0-100>` - Cambia volumen",
            inline=False
        )
    else:
        embed.add_field(
            name="🎵 Comandos de Música",
            value="❌ Música no disponible - instala yt-dlp",
            inline=False
        )
    
    embed.add_field(
        name="🌍 Idiomas disponibles para TTS",
        value=", ".join(LANGUAGES.keys()),
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Comando no encontrado. Usa `!help_bot` para ver los comandos disponibles.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Faltan argumentos para este comando. Uso: `{ctx.command.signature}`")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Argumento incorrecto. Revisa el formato del comando.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("❌ No tengo los permisos necesarios para ejecutar este comando.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ No tienes los permisos necesarios para ejecutar este comando.")
    else:
        print(f"Error no manejado: {type(error).__name__}: {error}")
        await ctx.send(f"❌ Ocurrió un error inesperado al ejecutar el comando. Consulte la consola del bot para más detalles.")

# Ejecutar el bot
if __name__ == "__main__":
    print("🚀 Iniciando bot...")
    print("📋 Verifica que tengas instalado:")
    print("   - discord.py[voice]")
    print("   - gTTS (para text-to-speech)")  
    print("   - yt-dlp (para música)")
    print("   - FFmpeg (para audio y TTS)")


role_message_id_1 = 1381020934676156446
role_message_id_2 = 1381020944264597574

JOIN_CHANNEL_ID = 1365583231508021300  # Canal de bienvenidas
BOOST_CHANNEL_ID = 1365860209188147200  # Canal de boosts
ROL_MIEMBRO_ID = 1365512945551020062 
ROL_AUTORIZADO_ID = 1380054848598442015
ADMIN_IDS = [1268620891412107264]

@bot.command()
async def hola(ctx):
    await ctx.send('¡Hola!')
    
@bot.event  # 🎉 Bienvenida mejorada con embed
async def on_member_join(member):
    canal = bot.get_channel(JOIN_CHANNEL_ID)
    if canal:
        embed = discord.Embed(
            title="¡Bienvenido/a!",
            description=f"{member.mention} acaba de unirse al servidor. 🎉 ¡Disfruta tu estancia!",
            color=discord.Color.purple()
        )
        embed.set_image(url="https://i.imgur.com/sMo35vf.jpeg")  # Sin espacios al final
        await canal.send(embed=embed)

class AceptarReglas(discord.ui.View):  #boton de aceptar reglas
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Aceptar Reglas", style=discord.ButtonStyle.success, custom_id="aceptar_reglas")  #boton de verificacion
    async def aceptar(self, interaction: discord.Interaction, button: discord.ui.Button):
        rol = interaction.guild.get_role(ROL_MIEMBRO_ID)
        if rol:
            await interaction.user.add_roles(rol)
            await interaction.response.send_message("✅ ¡Has aceptado las reglas y ahora tienes acceso completo!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No se encontró el rol para asignar.", ephemeral=True)

@bot.command() #mensage de reglas
async def reglas(ctx):
    if ctx.author.id not in ADMIN_IDS:
        return await ctx.send("❌ Solo el administrador puede usar este comando.")
    
    await ctx.message.delete()  # Borra el mensaje "!reglas"

    embed = discord.Embed(
        title="📜 REGLAS DEL SERVIDOR – LÉELAS O PERDERÁS EL ACCESO",
        description=(
            "⚠️ Estas normas aplican para todos los canales, incluyendo texto y voz.\n"
            "Ignorarlas no te exime de sanciones. Cualquier falta será moderada por el Staff."
        ),
        color=discord.Color.dark_purple()
    )
    embed.set_footer(text="Haz clic en el botón para aceptar las reglas")

    embed.add_field(
        name="1️⃣ Respeto ante todo",
        value=(
            "✦ Todos los miembros deben tratarse con respeto y empatía.\n"
            "❌ No se permite insultar, burlarse, provocar ni acosar a otras personas.\n\n"
            "🔇 Comentarios ofensivos o imitaciones con intención de burla no serán tolerados.\n\n"
            "🚫 Faltas graves = BANEO INMEDIATO."
        ),
        inline=False
    )

    embed.add_field(
        name="2️⃣ Prohibido contenido NSFW y Gore",
        value=(
            "✦ Está totalmente prohibido compartir contenido sexual explícito, violento o perturbador.\n\n"
            "⚠️ Esto incluye nombres, apodos, imágenes de perfil y stickers.\n\n"
            "🚫 Infracción grave = Expulsión directa o aislamiento."
        ),
        inline=False
    )

    embed.add_field(
        name="3️⃣ Cero odio o discriminación",
        value=(
            "✦ No se permite ningún tipo de discurso de odio: racismo, homofobia, machismo, xenofobia, capacitismo, etc.\n\n"
            "✦ Usar palabras, emojis o imágenes con connotaciones discriminatorias será castigado.\n\n"
            "🚫 Sanción: Aislamiento o expulsión definitiva."
        ),
        inline=False
    )

    embed.add_field(
        name="4️⃣ No spam ni publicidad",
        value=(
            "✦ No se permite enviar mensajes repetitivos ni hacer publicidad sin autorización.\n\n"
            "✦ Publicar enlaces externos sin permiso también será sancionado."
        ),
        inline=False
    )

    embed.add_field(
        name="5️⃣ Respeto a la privacidad",
        value=(
            "✦ No compartas datos personales propios ni de otros usuarios.\n\n"
            "✦ Cuida tu seguridad y la de los demás en todo momento."
        ),
        inline=False
    )

    embed.set_image(url="https://i.pinimg.com/736x/73/ed/80/73ed80b0807339301f45ae7fe844ac75.jpg")

    await ctx.send(embed=embed, view=AceptarReglas())

@bot.event  # 🚀 Mensaje de boost
async def on_member_update(before, after):
    if before.premium_since is None and after.premium_since is not None:
        canal = bot.get_channel(BOOST_CHANNEL_ID)
        if canal:
            embed = discord.Embed(
                title="¡Nuevo Boost!",
                description=f"{after.mention} acaba de boostear el servidor. 🚀 ¡Gracias por el apoyo!",
                color=discord.Color.fuchsia()
            )
            await canal.send(embed=embed)
            
@bot.command()   # mensaje de los roles
async def roles(ctx):
    global role_message_id_1, role_message_id_2  # IDs para uso en eventos

    # Embed 1 – Pronombres
    embed1 = discord.Embed(title="🎭 Elige tus pronombres", color=0x6a0dad)
    embed1.set_footer(text="Reacciona a los emojis para asignarte o quitarte un rol")

    embed1.add_field(
        name="Pronombres disponibles",
        value=(
            "🟥 – She/Her\n"
            "🟦 – He/Him\n"
            "🟪 – They/Them\n"
            "🎭 – Any pronouns"
        ),
        inline=False
    )

    msg1 = await ctx.send(embed=embed1)

    # Reacciones para pronombres
    await msg1.add_reaction("🟥")
    await msg1.add_reaction("🟦")
    await msg1.add_reaction("🟪")
    await msg1.add_reaction("🎭")

    # Embed 2 – Roles Generales
    embed2 = discord.Embed(title="📌 Elige tus roles generales", color=0x6a0dad)
    embed2.set_footer(text="Reacciona a los emojis para asignarte o quitarte un rol")

    embed2.add_field(
        name="Roles disponibles",
        value=(
            "🎮 – Gamer\n"
            "🧑‍🎓 – Estudiante\n"
            "🎨 – Artista\n"
            "🔔 – - Notificaciones"
        ),
        inline=False
    )

    msg2 = await ctx.send(embed=embed2)

    # Reacciones para roles generales
    await msg2.add_reaction("🎮")
    await msg2.add_reaction("🧑‍🎓")
    await msg2.add_reaction("🎨")
    await msg2.add_reaction("🔔")

    # Guardar los IDs
    role_message_id_1 = msg1.id
    role_message_id_2 = msg2.id
    print(f"Mensaje 1 ID: {msg1.id}")
    print(f"Mensaje 2 ID: {msg2.id}")

emoji_to_role = {
    "🟥": 1380970786990325870,  # She/Her
    "🟦": 1380970321645010974,  # He/Him
    "🟪": 1380970970742788176,  # They/Them
    "🎭": 1381007942316195850,  # Any pronouns
    "🎮": 1365807316896710857,  # Gamer
    "🧑‍🎓": 1366159992645750935,  # Estudiante
    "🎨": 1366165077727903814,  # Artista
    "🔔": 1380058154213183488   # Notificaciones
}

@bot.event  #asignar roles
async def on_raw_reaction_add(payload):
    print(f"➕ Reacción añadida: emoji={payload.emoji}, mensaje={payload.message_id}, usuario={payload.user_id}")

    if payload.user_id == bot.user.id or payload.message_id not in (role_message_id_1, role_message_id_2):
        return

    guild = bot.get_guild(payload.guild_id)
    member = await guild.fetch_member(payload.user_id)

    emoji = str(payload.emoji)
    role_id = emoji_to_role.get(emoji)

    if role_id:
        role = guild.get_role(role_id)
        if role:
            await member.add_roles(role)
            print(f"✅ Rol '{role.name}' asignado a {member.display_name}")
        else:
            print(f"❌ No se encontró el rol con ID {role_id}")
    else:
        print(f"❌ Emoji no mapeado: {emoji}")

@bot.event  #quitar roles
async def on_raw_reaction_remove(payload):
    print(f"🗑️ Reacción removida: emoji={payload.emoji}, mensaje={payload.message_id}, usuario={payload.user_id}")

    if payload.message_id not in (role_message_id_1, role_message_id_2):
        return

    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        print("❌ No se encontró el servidor.")
        return

    try:
        member = await guild.fetch_member(payload.user_id)
    except Exception as e:
        print(f"❌ Error al obtener miembro: {e}")
        return

    emoji = str(payload.emoji)
    role_id = emoji_to_role.get(emoji)

    if role_id:
        role = guild.get_role(role_id)
        if role:
            await member.remove_roles(role)
            print(f"❌ Rol '{role.name}' removido de {member.display_name}")
        else:
            print(f"❌ No se encontró el rol con ID {role_id}")
    else:
        print(f"❌ Emoji no mapeado: {emoji}")

@bot.command()  # 🧹 Comando para limpiar mensajes
async def limpiar(ctx):
    rol = discord.utils.get(ctx.author.roles, id=ROL_AUTORIZADO_ID)
    if rol:
        await ctx.channel.purge(limit=100)
        await asyncio.sleep(1)
        await ctx.send("✅ Mensajes eliminados", delete_after=5)
    else:
        await ctx.send("❌ No tienes permiso para usar este comando.")


webserver.keep_alive()
bot.run(DISCORD_TOKEN)
