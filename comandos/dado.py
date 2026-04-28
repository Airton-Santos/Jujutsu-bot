import discord
from discord import app_commands
from discord.ext import commands
import random
import re

class DiceSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def safe_defer(self, interaction: discord.Interaction):
        try:
            if not interaction.response.is_done():
                await interaction.response.defer()
        except Exception:
            pass

    @app_commands.command(name="dado", description="Lança dados (ex: 1d20, 2d10, 1d1000)")
    @app_commands.describe(lancamento="O dado a ser lançado (ex: 1d20 ou apenas 20)")
    async def dado(self, interaction: discord.Interaction, lancamento: str):
        """Comando de dados versátil para RPG"""
        await self.safe_defer(interaction)

        # Regex para identificar formatos como '1d20', 'd100' ou apenas '20'
        match = re.match(r"(\d+)?d?(\d+)", lancamento.lower().strip())
        
        if not match:
            return await interaction.followup.send("❌ Formato inválido! Tente algo como `1d20` ou `d100`.")

        quantidade = int(match.group(1)) if match.group(1) else 1
        lados = int(match.group(2))

        # Limites de segurança
        if lados < 2 or lados > 1000:
            return await interaction.followup.send("❌ O dado deve ter entre 2 e 1000 lados.")
        if quantidade < 1 or quantidade > 20:
            return await interaction.followup.send("❌ Podes lançar no máximo 20 dados de uma vez.")

        resultados = [random.randint(1, lados) for _ in range(quantidade)]
        total = sum(resultados)
        
        # Construção da mensagem
        embed = discord.Embed(
            title="🎲 Resultado do Lançamento",
            color=0x9b59b6 # Roxo tema Jujutsu/Energia
        )
        
        resultado_texto = ", ".join([f"`{r}`" for r in resultados])
        
        # Lógica especial para 1d20 (Críticos)
        extra_info = ""
        if quantidade == 1 and lados == 20:
            if total == 20:
                extra_info = "\n✨ **CRÍTICO!** Você canalizou energia negra perfeitamente!"
                embed.color = 0xffd700 # Dourado
            elif total == 1:
                extra_info = "\n💀 **FALHA CRÍTICA!** Sua energia oscilou no pior momento..."
                embed.color = 0xff0000 # Vermelho

        embed.add_field(
            name=f"Dados: {quantidade}d{lados}",
            value=f"**Resultados:** {resultado_texto}\n**Total:** `{total}`{extra_info}",
            inline=False
        )
        
        embed.set_footer(text=f"Lançado por {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)

        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(DiceSystem(bot))