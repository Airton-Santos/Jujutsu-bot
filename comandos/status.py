import os
import discord
from discord import app_commands
from discord.ext import commands
from supabase import create_client, Client
from typing import Literal
from dotenv import load_dotenv

load_dotenv()

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

class StatusSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_player_status(self, user_id: str):
        """Busca o JSON de status do player no banco"""
        res = supabase.table("player_status").select("stats").eq("user_id", user_id).execute()
        return res.data[0]["stats"] if res.data else None

    async def save_player_status(self, user_id: str, stats: dict):
        """Salva ou atualiza os status no banco (Upsert)"""
        supabase.table("player_status").upsert({"user_id": user_id, "stats": stats}).execute()

    def criar_barra_aura(self, atual, maximo, tamanho=15):
        if maximo <= 0: return "░" * tamanho
        porcentagem = max(0, min(1, atual / maximo))
        cheios = int(porcentagem * tamanho)
        vazios = tamanho - cheios
        return f"**[{'▉' * cheios}{'░' * vazios}]**"

    @app_commands.command(name="status", description="Exibe status com aura visual")
    async def status(self, interaction: discord.Interaction, usuario: discord.Member = None):
        await interaction.response.defer()
        target = usuario or interaction.user
        user_id = str(target.id)
        
        stats = await self.get_player_status(user_id)
        
        if not stats:
            return await interaction.followup.send(
                f"❌ {target.mention} não possui registros de status.", 
                ephemeral=True
            )

        hp_a, hp_m = stats.get("hp_atual", 100), stats.get("hp_max", 100)
        en_a, en_m = stats.get("en_atual", 100), stats.get("en_max", 100)

        embed = discord.Embed(
            title=f"🌀 Aura de Feiticeiro: {target.display_name}",
            description="Status atuais de combate e energia amaldiçoada.",
            color=0x00ffff
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        barra_hp = self.criar_barra_aura(hp_a, hp_m)
        embed.add_field(
            name=f"❤️ Vitalidade: {hp_a} / {hp_m}",
            value=f"{barra_hp} `{int((hp_a/hp_m)*100)}%`",
            inline=False
        )
        
        barra_en = self.criar_barra_aura(en_a, en_m)
        embed.add_field(
            name=f"✨ Energia: {en_a} / {en_m}",
            value=f"{barra_en} `{int((en_a/en_m)*100)}%`",
            inline=False
        )

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="set_status", description="Define os limites máximos de status")
    async def set_status(self, interaction: discord.Interaction, 
                         vida_maxima: int, 
                         energia_maxima: int,
                         usuario: discord.Member = None):
        await interaction.response.defer(ephemeral=True)

        # Apenas admin pode setar status de outros ou de si mesmo (para evitar trapaça)
        if not interaction.user.guild_permissions.administrator:
            return await interaction.followup.send("❌ Apenas administradores podem definir status base.", ephemeral=True)

        target = usuario or interaction.user
        new_stats = {
            "hp_max": vida_maxima, "hp_atual": vida_maxima,
            "en_max": energia_maxima, "en_atual": energia_maxima
        }

        await self.save_player_status(str(target.id), new_stats)
        await interaction.followup.send(f"✅ Status de {target.mention} configurados no banco de dados!")

    @app_commands.command(name="modificar_status", description="Modifica vida ou energia de um jogador")
    async def modificar_status(self, interaction: discord.Interaction, 
                               alvo: discord.Member,
                               tipo: Literal["Vida", "Energia"], 
                               quantidade: int, 
                               modo: Literal["Número Fixo", "Porcentagem (%)"]):
        """
        alvo: @usuario que receberá a alteração
        quantidade: valor positivo para curar/ganhar, valor negativo para tirar vida/energia
        """
        await interaction.response.defer()
        
        # Opcional: Trava para que apenas quem tem permissão de gerenciar mensagens (Mestre) possa usar em outros
        if alvo != interaction.user and not interaction.user.guild_permissions.manage_messages:
            return await interaction.followup.send("❌ Você não tem permissão para modificar o status de outros jogadores.", ephemeral=True)

        user_id = str(alvo.id)
        stats = await self.get_player_status(user_id)

        if not stats:
            return await interaction.followup.send(f"❌ Status de {alvo.mention} não encontrados no banco.", ephemeral=True)

        chave_atual = "hp_atual" if tipo == "Vida" else "en_atual"
        chave_max = "hp_max" if tipo == "Vida" else "en_max"
        
        valor_base = stats[chave_max]
        modificador = quantidade
        
        if modo == "Porcentagem (%)":
            modificador = int(valor_base * (quantidade / 100))

        # Aplica a lógica e limita entre 0 e o Máximo
        stats[chave_atual] = max(0, min(valor_base, stats[chave_atual] + modificador))
        
        await self.save_player_status(user_id, stats)

        emoji = "❤️" if tipo == "Vida" else "✨"
        verbo = "reduzido" if quantidade < 0 else "aumentado"
        
        await interaction.followup.send(
            f"✅ **Update de {tipo} para {alvo.mention}!**\n{emoji} Novo Valor: `{stats[chave_atual]} / {stats[chave_max]}` (Valor {verbo} em: `{modificador}`)"
        )

async def setup(bot):
    await bot.add_cog(StatusSystem(bot))