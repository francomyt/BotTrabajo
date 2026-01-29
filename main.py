import discord
from discord.ext import commands
from discord.ui import View, Button
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# --- CONFIGURACIÓN DE GOOGLE SHEETS ---
# El código ahora buscará el archivo que renombraste o el original
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
    client = gspread.authorize(creds)
    # IMPORTANTE: Asegúrate de que tu Excel se llame exactamente "Control de Asistencia"
    sheet = client.open("Control de Asistencia").sheet1 
except Exception as e:
    print(f"Error al conectar con Google Sheets: {e}")

# --- CONFIGURACIÓN DEL BOT ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

class FichajeView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Entrar", style=discord.ButtonStyle.green, custom_id="entrada")
    async def entrada(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        ahora = datetime.now()
        fecha = ahora.strftime("%d/%m/%Y")
        hora_entrada = ahora.strftime("%H:%M:%S")

        # Verificar si ya tiene una entrada sin salida (revisando la última fila del usuario)
        registros = sheet.get_all_values()
        en_turno = False
        for fila in registros:
            if fila[0] == str(user.id) and (len(fila) < 5 or fila[4] == ""):
                en_turno = True
                break

        if en_turno:
            await interaction.response.send_message("⚠️ Ya tienes una entrada activa. ¡Marca salida primero!", ephemeral=True)
            return

        # Registrar nueva entrada: ID, Nombre, Fecha, Entrada
        sheet.append_row([str(user.id), user.display_name, fecha, hora_entrada])
        await interaction.response.send_message(f"✅ Entrada registrada: {hora_entrada}", ephemeral=True)

    @discord.ui.button(label="Salir", style=discord.ButtonStyle.red, custom_id="salida")
    async def salida(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        ahora = datetime.now()
        hora_salida = ahora.strftime("%H:%M:%S")

        registros = sheet.get_all_values()
        fila_encontrada = None
        
        # Buscamos de abajo hacia arriba la última entrada abierta
        for i, fila in enumerate(registros, start=1):
            if fila[0] == str(user.id) and (len(fila) < 5 or fila[4] == ""):
                fila_encontrada = i

        if fila_encontrada:
            hora_entrada_str = registros[fila_encontrada-1][3]
            # Calculamos la diferencia de tiempo
            fmt = "%H:%M:%S"
            t1 = datetime.strptime(hora_entrada_str, fmt)
            t2 = datetime.strptime(hora_salida, fmt)
            
            diferencia_horas = (t2 - t1).total_seconds() / 3600
            
            if diferencia_horas < 0: # Por si trabaja después de medianoche
                diferencia_horas += 24

            # Actualizamos Columna E (Salida) y F (Total)
            sheet.update_cell(fila_encontrada, 5, hora_salida)
            sheet.update_cell(fila_encontrada, 6, round(diferencia_horas, 2))
            
            await interaction.response.send_message(f"🛑 Salida registrada. Total: {round(diferencia_horas, 2)} hs.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ No tienes ninguna entrada activa.", ephemeral=True)

@bot.event
async def on_ready():
    print(f'Bot conectado como {bot.user}')
    bot.add_view(FichajeView()) # Mantiene los botones activos si el bot se reinicia

@bot.command()
@commands.has_permissions(administrator=True)
async def panel(ctx):
    embed = discord.Embed(title="Control de Asistencia", description="Presiona el botón para registrar tu jornada laboral.", color=discord.Color.blue())
    await ctx.send(embed=embed, view=FichajeView())

@bot.command()
@commands.has_permissions(administrator=True)
async def reporte(ctx, miembro: discord.Member):
    registros = sheet.get_all_values()
    total_horas = 0.0
    for fila in registros:
        if fila[0] == str(miembro.id) and len(fila) >= 6:
            try:
                total_horas += float(fila[5].replace(',', '.'))
            except:
                continue
    
    await ctx.send(f"📊 **{miembro.display_name}** ha acumulado un total de **{round(total_horas, 2)} horas**.")

# TOKEN R

bot.run('MTQ2NjQ5MjExMjkyNDA0OTYwMQ.GUBC0b.z5z36kWDuZs2AMqkbm_V6aOK9YbPk_d45YEmkQ')
