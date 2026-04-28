import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from typing import Literal

# Caminho para salvar os dados de status
STATUS_PATH = "./player_status.json"

def load_status():
    if not os.path.exists(STATUS_PATH): return {}
    try:
        with open(STATUS_PATH, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def save_status(data):
    with open(STATUS_PATH, "w", encoding="utf-8") as f: 
        json.dump(data, f, indent=4, ensure_ascii=False)

class StatusSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def criar_barra_aura(self, atual, maximo, tamanho=15):
        """Gera uma barra visual azulada e moderna."""
        if maximo <= 0: return "░" * tamanho
        porcentagem = max(0, min(1, atual / maximo))
        cheios = int(porcentagem * tamanho)
        vazios = tamanho - cheios
        
        # Design moderno usando tons de azul (▉)
        barra = "▉" * cheios + "░" * vazios
        return f"**[{barra}]**"

    @app_commands.command(name="status", description="Exibe seus status com aura visual")
    async def status(self, interaction: discord.Interaction, usuario: discord.Member = None):
        # Damos um "defer" para evitar o erro de 3 segundos (Unknown Interaction)
        await interaction.response.defer()
        
        target = usuario or interaction.user
        user_id = str(target.id)
        data = load_status()
        
        if user_id not in data:
            return await interaction.followup.send(
                f"❌ {target.mention} não possui registros. Use `/set_status` primeiro!", 
                ephemeral=True
            )

        stats = data[user_id]
        hp_a, hp_m = stats.get("hp_atual", 100), stats.get("hp_max", 100)
        en_a, en_m = stats.get("en_atual", 100), stats.get("en_max", 100)

        embed = discord.Embed(
            title=f"🌀 Aura de Feiticeiro: {target.display_name}",
            description="Status atuais de combate e energia amaldiçoada.",
            color=0x00ffff # Ciano brilhante
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        # Campo de Vida
        barra_hp = self.criar_barra_aura(hp_a, hp_m)
        embed.add_field(
            name=f"❤️ Vitalidade: {hp_a} / {hp_m}",
            value=f"{barra_hp} `{int((hp_a/hp_m)*100)}%`",
            inline=False
        )
        
        # Campo de Energia
        barra_en = self.criar_barra_aura(en_a, en_m)
        embed.add_field(
            name=f"✨ Energia: {en_a} / {en_m}",
            value=f"{barra_en} `{int((en_a/en_m)*100)}%`",
            inline=False
        )

        # Como usamos defer(), usamos followup.send agora
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="set_status", description="Define os limites máximos de status")
    async def set_status(self, interaction: discord.Interaction, 
                         vida_maxima: int, 
                         energia_maxima: int,
                         usuario: discord.Member = None):
        await interaction.response.defer(ephemeral=True)

        if usuario and not interaction.user.guild_permissions.administrator:
            return await interaction.followup.send("❌ Permissão insuficiente.", ephemeral=True)

        target = usuario or interaction.user
        data = load_status()
        data[str(target.id)] = {
            "hp_max": vida_maxima, "hp_atual": vida_maxima,
            "en_max": energia_maxima, "en_atual": energia_maxima
        }

        save_status(data)
        await interaction.followup.send(f"✅ Status iniciais de {target.mention} configurados com sucesso!")

    @app_commands.command(name="modificar_status", description="Modifica vida ou energia")
    @app_commands.describe(
        tipo="Escolha o status para modificar",
        quantidade="Valor a somar (+) ou subtrair (-)",
        modo="Se o valor é um número fixo ou uma porcentagem do total"
    )
    async def modificar_status(self, interaction: discord.Interaction, 
                               tipo: Literal["Vida", "Energia"], 
                               quantidade: int, 
                               modo: Literal["Número Fixo", "Porcentagem (%)"]):
        await interaction.response.defer()
        
        user_id = str(interaction.user.id)
        data = load_status()

        if user_id not in data:
            return await interaction.followup.send("❌ Status não encontrados.", ephemeral=True)

        stats = data[user_id]
        chave_atual = "hp_atual" if tipo == "Vida" else "en_atual"
        chave_max = "hp_max" if tipo == "Vida" else "en_max"
        
        valor_base = stats[chave_max]
        modificador = quantidade
        
        if modo == "Porcentagem (%)":
            modificador = int(valor_base * (quantidade / 100))

        # Aplica a mudança
        stats[chave_atual] = max(0, min(valor_base, stats[chave_atual] + modificador))
        save_status(data)

        emoji = "❤️" if tipo == "Vida" else "✨"
        await interaction.followup.send(
            f"✅ **Update de {tipo}!**\n{emoji} Novo Valor: `{stats[chave_atual]} / {stats[chave_max]}`"
        )

async def setup(bot):
    await bot.add_cog(StatusSystem(bot))