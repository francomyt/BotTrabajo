import discord
from discord.ext import commands
from discord.ui import View, Button
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os

# --- CONFIGURACIÓN DE GOOGLE SHEETS ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Intentar conectar con el nombre de archivo que tienes en tu carpeta
try:
    # Según tu imagen, el archivo se llama 'credentials.json'
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    # IMPORTANTE: El nombre del Excel en Drive debe ser este exactamente
    sheet = client.open("Control de Asistencia").sheet1
    print("✅ Conexión a Google Sheets exitosa")
except Exception as e:
    print(f"❌ ERROR DE CONEXIÓN: {e}")
    sheet = None

# --- CONFIGURACIÓN DEL BOT ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

class FichajeView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Entrar", style=discord.ButtonStyle.green, custom_id="entrada")
    async def entrada(self, interaction: discord.Interaction, button: discord.ui.Button):
        if sheet is None:
            return await interaction.response.send_message("❌ Error: No hay conexión con el Excel.", ephemeral=True)
        
        user = interaction.user
        ahora = datetime.now()
        fecha = ahora.strftime("%d/%m/%Y")
        hora_entrada = ahora.strftime("%H:%M:%S")

        registros = sheet.get_all_values()
        for fila in registros:
            if fila[0] == str(user.id) and (len(fila) < 5 or fila[4] == ""):
                return await interaction.response.send_message("⚠️ Ya tienes una entrada activa.", ephemeral=True)

        sheet.append_row([str(user.id), user.display_name, fecha, hora_entrada])
        await interaction.response.send_message(f"✅ Entrada registrada: {hora_entrada}", ephemeral=True)

    @discord.ui.button(label="Salir", style=discord.ButtonStyle.red, custom_id="salida")
    async def salida(self, interaction: discord.Interaction, button: discord.ui.Button):
        if sheet is None:
            return await interaction.response.send_message("❌ Error: No hay conexión con el Excel.", ephemeral=True)

        user = interaction.user
        ahora = datetime.now()
        hora_salida = ahora.strftime("%H:%M:%S")

        registros = sheet.get_all_values()
        fila_encontrada = None
        for i, fila in enumerate(registros, start=1):
            if fila[0] == str(user.id) and (len(fila) < 5 or fila[4] == ""):
                fila_encontrada = i

        if fila_encontrada:
            hora_entrada_str = registros[fila_encontrada-1][3]
            t1 = datetime.strptime(hora_entrada_str, "%H:%M:%S")
            t2 = datetime.strptime(hora_salida, "%H:%M:%S")
            diff = (t2 - t1).total_seconds() / 3600
            if diff < 0: diff += 24

            sheet.update_cell(fila_encontrada, 5, hora_salida)
            sheet.update_cell(fila_encontrada, 6, round(diff, 2))
            await interaction.response.send_message(f"🛑 Salida: {hora_salida}. Total: {round(diff, 2)} hs.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No tienes una entrada activa.", ephemeral=True)

@bot.event
async def on_ready():
    print(f'Bot online como {bot.user}')
    bot.add_view(FichajeView())

@bot.command()
@commands.has_permissions(administrator=True)
async def panel(ctx):
    await ctx.send("### 🏢 REGISTRO LABORAL", view=FichajeView())

# Usar variable de entorno para el token (Seguridad Railway)
token = os.getenv('DISCORD_TOKEN')
bot.run(token)


