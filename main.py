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

JOIN_CHANNEL_ID = 1365583231508021300  # Canal donde se anuncian nuevos miembros
BOOST_CHANNEL_ID = 1365860209188147200  # Canal donde se anuncian boosts


@bot.event                                  #Biembenida
async def on_member_join(member):
    canal = bot.get_channel(JOIN_CHANNEL_ID)
    if canal:
        await canal.send(f"👋 ¡Bienvenido/a {member.mention} al servidor!")

@bot.event                                #Agradecimiento por bost
async def on_member_update(before, after):
    if before.premium_since is None and after.premium_since is not None:
        canal = bot.get_channel(BOOST_CHANNEL_ID)
        if canal:
            await canal.send(f"🚀 {after.mention} acaba de boostear el servidor. ¡Gracias!")

@bot.command()            #comando para eliminar mensages !limpiar
async def limpiar(ctx):
    await ctx.channel.purge(limit=100)
    await asyncio.sleep(1) 
    await ctx.send("mensajes eliminados", delete_after=5)



@bot.event
async def on_ready():
    print(f"Estamos drentro! {bot.user}")

bot.run(secrets.TOKEN)

