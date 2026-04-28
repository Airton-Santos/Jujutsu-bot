import discord
from discord import app_commands
from discord.ext import commands

class CalculadoraPorcentagem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="porcentagem", 
        description="Calcula a porcentagem de um valor (ex: 3% de 1000)"
    )
    @app_commands.describe(
        porcentagem="O valor da porcentagem (ex: 3)",
        total="O valor total (ex: 1000)"
    )
    async def porcentagem(self, interaction: discord.Interaction, porcentagem: float, total: float):
        """Calcula X% de Y de forma simples"""
        
        # Realiza o cálculo
        resultado = (porcentagem / 100) * total
        
        # Formatação para evitar muitas casas decimais desnecessárias
        resultado_formatado = f"{resultado:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        if resultado_formatado.endswith(",00"):
            resultado_formatado = resultado_formatado[:-3]

        embed = discord.Embed(
            title="🧮 Calculadora de Energia",
            description=f"Calculando bónus/eficiência de combate.",
            color=0x2ecc71 # Verde para cálculos e sucesso
        )
        
        embed.add_field(
            name="Equação",
            value=f"**{porcentagem}%** de **{total}**",
            inline=False
        )
        
        embed.add_field(
            name="Resultado",
            value=f"✨ `{resultado_formatado}`",
            inline=False
        )
        
        embed.set_footer(text=f"Solicitado por {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(CalculadoraPorcentagem(bot))