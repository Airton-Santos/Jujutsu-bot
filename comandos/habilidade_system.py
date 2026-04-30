import os
import discord
from discord import app_commands
from discord.ext import commands
from supabase import create_client, Client
from typing import Literal, Optional
from dotenv import load_dotenv

load_dotenv()

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

class HabilidadesSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_player_data(self, user_id: str):
        """Busca o documento único do player"""
        res = supabase.table("player_skills").select("skills").eq("user_id", user_id).execute()
        return res.data[0]["skills"] if res.data else None

    async def save_player_data(self, user_id: str, skills: dict):
        """Salva o pacote de habilidades (Upsert)"""
        supabase.table("player_skills").upsert({"user_id": user_id, "skills": skills}).execute()

    def criar_barra_progresso(self, atual, maximo=10):
        tamanho_barra = 10
        progresso = max(0, min(maximo, atual))
        cheios = int((progresso / maximo) * tamanho_barra)
        vazios = tamanho_barra - cheios
        return f"[{'▉' * cheios}{'░' * vazios}] {progresso}/{maximo}"

    @app_commands.command(name="habilidades", description="Consulta as técnicas de um feiticeiro")
    async def habilidades(self, interaction: discord.Interaction, usuario: Optional[discord.Member] = None):
        await interaction.response.defer()
        target = usuario or interaction.user
        user_id = str(target.id)
        
        skills = await self.get_player_data(user_id)

        if not skills:
            # Inicializa dados caso não existam
            skills = {
                "Habilidade 1": {"nome": "Habilidade 1", "nivel": 0, "exp": 0, "emoji": "🟢"},
                "Habilidade 2": {"nome": "Habilidade 2", "nivel": 0, "exp": 0, "emoji": "🔵"},
                "Habilidade 3": {"nome": "Habilidade 3", "nivel": 0, "exp": 0, "emoji": "🟡"},
                "Habilidade 4": {"nome": "Habilidade 4", "nivel": 0, "exp": 0, "emoji": "🔴"},
                "Passiva": {"nome": "Passiva", "nivel": 0, "exp": 0, "emoji": "🌀"},
                "Expansão": {"nome": "Expansão de Domínio", "nivel": 0, "exp": 0, "emoji": "👁️"}
            }
            await self.save_player_data(user_id, skills)

        embed = discord.Embed(title=f"🎭 TÉCNICAS INATAS: {target.display_name.upper()}", color=0x2b2d31)
        embed.set_thumbnail(url=target.display_avatar.url)

        for key in ["Habilidade 1", "Habilidade 2", "Habilidade 3", "Habilidade 4", "Passiva", "Expansão"]:
            info = skills[key]
            barra = self.criar_barra_progresso(info["exp"])
            embed.add_field(
                name=f"{info['emoji']} {info['nome']} (Nível {info['nivel']}/10)",
                value=f"```md\n# Progresso para o próximo nível\n{barra}\n```",
                inline=False
            )

        embed.set_footer(text="Jujutsu Golden Age • Bagre System")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="set_nome_habilidade", description="Altera o nome de uma técnica")
    async def set_nome_habilidade(self, interaction: discord.Interaction, 
                                   slot: Literal["Habilidade 1", "Habilidade 2", "Habilidade 3", "Habilidade 4", "Passiva", "Expansão"], 
                                   nome: str,
                                   usuario: Optional[discord.Member] = None):
        """Permite mudar o nome das próprias habilidades ou de terceiros (se for admin)"""
        target = usuario or interaction.user
        
        # Trava de segurança: se mudar de outro, precisa ser admin
        if target != interaction.user and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Você só pode renomear suas próprias habilidades.", ephemeral=True)

        user_id = str(target.id)
        skills = await self.get_player_data(user_id)
        
        if not skills:
            return await interaction.response.send_message(f"❌ {target.mention} não possui registros. Use `/habilidades` primeiro.", ephemeral=True)

        skills[slot]["nome"] = nome
        await self.save_player_data(user_id, skills)
        await interaction.response.send_message(f"✅ Slot **{slot}** de {target.mention} agora se chama **{nome}**!")

    @app_commands.command(name="add_maestria", description="Adiciona experiência a uma técnica específica")
    async def add_maestria(self, interaction: discord.Interaction, 
                            alvo: discord.Member,
                            slot: Literal["Habilidade 1", "Habilidade 2", "Habilidade 3", "Habilidade 4", "Passiva", "Expansão"], 
                            quantidade: int):
        """Adiciona progresso a um jogador específico"""
        
        # Trava para apenas Mestres/Admins usarem
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message("❌ Apenas Mestres podem atribuir maestria.", ephemeral=True)

        user_id = str(alvo.id)
        skills = await self.get_player_data(user_id)

        if not skills:
            return await interaction.response.send_message(f"❌ {alvo.mention} não tem dados de habilidades.", ephemeral=True)

        skill = skills[slot]
        if skill["nivel"] >= 10:
            return await interaction.response.send_message(f"⭐ **{skill['nome']}** de {alvo.mention} já está no nível máximo!", ephemeral=True)

        skill["exp"] += quantidade
        msg_up = ""

        # Lógica de Level Up (10 exp = 1 nível)
        while skill["exp"] >= 10:
            if skill["nivel"] < 10:
                skill["exp"] -= 10
                skill["nivel"] += 1
                msg_up += f"\n🎊 **LEVEL UP!** {alvo.mention}: {skill['nome']} subiu para nível {skill['nivel']}!"
            
            if skill["nivel"] >= 10:
                skill["exp"] = 0
                break

        await self.save_player_data(user_id, skills)
        barra = self.criar_barra_progresso(skill["exp"])
        
        await interaction.response.send_message(
            f"📈 **Maestria Adicionada para {alvo.mention}!**\n"
            f"{skill['emoji']} **{skill['nome']}**: {barra}{msg_up}"
        )

async def setup(bot):
    await bot.add_cog(HabilidadesSystem(bot))