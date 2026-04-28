import discord
from discord import app_commands
from discord.ext import commands
import json
import os
from typing import Literal

# Caminho para salvar os dados
HABILIDADES_PATH = "./player_skills.json"

def load_skills():
    if not os.path.exists(HABILIDADES_PATH): return {}
    try:
        with open(HABILIDADES_PATH, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def save_skills(data):
    with open(HABILIDADES_PATH, "w", encoding="utf-8") as f: 
        json.dump(data, f, indent=4, ensure_ascii=False)

class HabilidadesSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def criar_barra_progresso(self, atual, maximo=10):
        """Cria a barra visual [▉▉▉░░░]"""
        tamanho_barra = 10
        progresso = max(0, min(maximo, atual))
        cheios = int((progresso / maximo) * tamanho_barra)
        vazios = tamanho_barra - cheios
        return f"[{'▉' * cheios}{'░' * vazios}] {progresso}/{maximo}"

    @app_commands.command(name="habilidades", description="Consulta o nível de maestria das suas técnicas")
    async def habilidades(self, interaction: discord.Interaction, usuario: discord.Member = None):
        target = usuario or interaction.user
        user_id = str(target.id)
        data = load_skills()

        if user_id not in data:
            # Inicializa dados básicos se não existirem
            data[user_id] = {
                "Habilidade 1": {"nome": "Habilidade 1", "nivel": 0, "exp": 0, "emoji": "🟢"},
                "Habilidade 2": {"nome": "Habilidade 2", "nivel": 0, "exp": 0, "emoji": "🔵"},
                "Habilidade 3": {"nome": "Habilidade 3", "nivel": 0, "exp": 0, "emoji": "🟡"},
                "Habilidade 4": {"nome": "Habilidade 4", "nivel": 0, "exp": 0, "emoji": "🔴"},
                "Passiva": {"nome": "Passiva", "nivel": 0, "exp": 0, "emoji": "🌀"},
                "Expansão": {"nome": "Expansão de Domínio", "nivel": 0, "exp": 0, "emoji": "👁️"}
            }
            save_skills(data)

        skills = data[user_id]
        embed = discord.Embed(
            title=f"🎭 TÉCNICAS INATAS: {target.display_name.upper()}",
            description="Consulte o nível de maestria das suas técnicas amaldiçoadas.",
            color=0x2b2d31
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        for key, info in skills.items():
            barra = self.criar_barra_progresso(info["exp"])
            # Formatação igual à imagem enviada
            texto_habilidade = (
                f"```md\n"
                f"# Progresso para o próximo nível\n"
                f"{barra}\n"
                f"```"
            )
            embed.add_field(
                name=f"{info['emoji']} {info['nome']} (Nível {info['nivel']}/10)",
                value=texto_habilidade,
                inline=False
            )

        embed.set_footer(text="Jujutsu Golden Age • Bagre System")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="set_nome_habilidade", description="Define o nome personalizado de uma habilidade")
    async def set_nome_habilidade(self, interaction: discord.Interaction, 
                                   slot: Literal["Habilidade 1", "Habilidade 2", "Habilidade 3", "Habilidade 4", "Passiva", "Expansão"], 
                                   nome: str):
        user_id = str(interaction.user.id)
        data = load_skills()
        
        if user_id not in data:
            return await interaction.response.send_message("❌ Use `/habilidades` primeiro para inicializar.", ephemeral=True)

        data[user_id][slot]["nome"] = nome
        save_skills(data)
        await interaction.response.send_message(f"✅ Slot **{slot}** agora se chama **{nome}**!", ephemeral=True)

    @app_commands.command(name="add_maestria", description="Adiciona progresso de maestria a uma habilidade")
    @app_commands.describe(quantidade="Quantidade de EXP (0 a 10) para adicionar")
    async def add_maestria(self, interaction: discord.Interaction, 
                            slot: Literal["Habilidade 1", "Habilidade 2", "Habilidade 3", "Habilidade 4", "Passiva", "Expansão"], 
                            quantidade: int):
        user_id = str(interaction.user.id)
        data = load_skills()

        if user_id not in data:
            return await interaction.response.send_message("❌ Status não encontrados.", ephemeral=True)

        skill = data[user_id][slot]
        
        if skill["nivel"] >= 10:
            return await interaction.response.send_message(f"⭐ A habilidade **{skill['nome']}** já atingiu o nível máximo!", ephemeral=True)

        skill["exp"] += quantidade
        msg_up = ""

        # Lógica de Level Up
        while skill["exp"] >= 10:
            skill["exp"] -= 10
            skill["nivel"] += 10 if skill["nivel"] + 1 > 10 else skill["nivel"] + 1
            msg_up = f"\n🎊 **LEVEL UP!** Sua habilidade **{skill['nome']}** subiu para o nível {skill['nivel']}!"
            
            if skill["nivel"] >= 10:
                skill["exp"] = 0
                break

        save_skills(data)
        barra = self.criar_barra_progresso(skill["exp"])
        await interaction.response.send_message(
            f"📈 **Maestria Adicionada!**\n{skill['emoji']} **{skill['nome']}**: {barra}{msg_up}"
        )

async def setup(bot):
    await bot.add_cog(HabilidadesSystem(bot))