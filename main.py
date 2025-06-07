import discord
from discord.ext import commands
import requests
import bot_secrets as secrets
import asyncio

intents = discord.Intents.default()
intents.guilds = True
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix='!', intents=intents)

JOIN_CHANNEL_ID = 1365583231508021300  # Canal de bienvenidas
BOOST_CHANNEL_ID = 1365860209188147200  # Canal de boosts
ROL_MIEMBRO_ID = 1365512945551020062 
ROL_AUTORIZADO_ID = 1380054848598442015


class AceptarReglas(discord.ui.View):  
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

@bot.command()    #mensage de reglas
async def reglas(ctx):
    if ctx.author.id != 1268620891412107264:
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

role_message_id_1 = 1381020934676156446
role_message_id_2 = 1381020944264597574

@bot.event
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

@bot.event
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
   


@bot.event  # ✅ Confirmación de que el bot está listo
async def on_ready():
    bot.add_view(AceptarReglas())
    print(f"Estamos dentro como {bot.user}")



bot.run(secrets.TOKEN)
