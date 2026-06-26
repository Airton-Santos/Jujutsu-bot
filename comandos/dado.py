import discord
from discord import app_commands
from discord.ext import commands
import secrets  # Mais seguro e imprevisível que o 'random'
import re
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

# Configuração Supabase para verificar sessão
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

class DiceSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def check_session_membership(self, guild_id: int, user_id: int):
        """Verifica se o usuário está na sessão ativa e retorna seus pontos, se houver"""
        try:
            res = supabase.table("sessions").select("players").eq("guild_id", str(guild_id)).eq("status", "ativa").execute()
            if res.data:
                players = res.data[0]["players"]
                for p in players:
                    if p['id'] == str(user_id):
                        # Retorna os pontos do jogador (padrão 0 caso a chave ainda não exista)
                        return p.get('pontos', 0)
            return None # Nenhuma sessão ativa ou jogador não encontrado
        except:
            return None

    @app_commands.command(name="dado", description="Lança dados de RPG (Ex: 1d20, 2d10)")
    async def dado(self, interaction: discord.Interaction, lancamento: str):
        # Regex aprimorada
        match = re.match(r"(\d+)?d?(\d+)", lancamento.lower().strip())
        
        if not match:
            return await interaction.response.send_message("❌ Formato inválido! Use algo como `1d20`.", ephemeral=True)

        quantidade = int(match.group(1)) if match.group(1) else 1
        lados = int(match.group(2))

        if lados < 2 or lados > 1000 or quantidade > 20:
            return await interaction.response.send_message("❌ Limites: Máximo 20 dados e 1000 lados.", ephemeral=True)

        # Usando secrets.choice para aleatoriedade criptográfica (sem vício)
        resultados = [secrets.choice(range(1, lados + 1)) for _ in range(quantidade)]
        total_dados = sum(resultados)
        
        # Verifica se o jogador está na sessão e resgata seus pontos de bônus
        pontos_bonus = await self.check_session_membership(interaction.guild_id, interaction.user.id)
        is_in_session = pontos_bonus is not None
        
        # Calcula o total final aplicando o bônus se o jogador estiver em uma sessão ativa
        bonus_aplicado = pontos_bonus if is_in_session else 0
        total_final = total_dados + bonus_aplicado
        
        embed = discord.Embed(color=0x9b59b6)
        
        # Status de Sessão no Embed
        if is_in_session:
            embed.set_author(name=f"🎲 Lançamento de Sessão - {interaction.user.display_name}")
        else:
            embed.set_author(name=f"🎲 Lançamento Casual - {interaction.user.display_name}")

        resultado_texto = ", ".join([f"`{r}`" for r in resultados])
        
        # Formatação do texto do Total exibindo o cálculo do bônus se for maior que 0
        if bonus_aplicado > 0:
            total_exibicao = f"`{total_dados}` + `{bonus_aplicado}` (Bônus) = **{total_final}**"
        else:
            total_exibicao = f"`{total_final}`"
        
        extra_info = ""
        # Verificação de crítico avalia apenas o dado puro para manter as regras tradicionais do d20
        if quantidade == 1 and lados == 20:
            if total_dados == 20:
                extra_info = "\n✨ **CRÍTICO!** Energia amaldiçoada em fluxo perfeito!"
                embed.color = 0xffd700 
            elif total_dados == 1:
                extra_info = "\n💀 **FALHA CRÍTICA!** Você se atrapalhou com sua própria energia..."
                embed.color = 0xff0000

        embed.description = f"**Dados:** {quantidade}d{lados}\n**Resultados:** {resultado_texto}\n**Total:** {total_exibicao}{extra_info}"
        
        if is_in_session is False:
            embed.set_footer(text="⚠️ Você não está na lista da sessão ativa!")

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(DiceSystem(bot))