import os
import discord
from discord import app_commands
from discord.ext import commands
from supabase import create_client, Client
from typing import Literal
import math
from dotenv import load_dotenv

load_dotenv()

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# --- SISTEMA DE PAGINAÇÃO ---
class SubHabilidadesPaginator(discord.ui.View):
    def __init__(self, target, skills_list, cog, timeout=60):
        super().__init__(timeout=timeout)
        self.target = target
        self.skills_list = skills_list
        self.cog = cog
        self.current_page = 0
        self.per_page = 5
        self.max_pages = math.ceil(len(skills_list) / self.per_page)

    def create_embed(self):
        start = self.current_page * self.per_page
        end = start + self.per_page
        current_skills = self.skills_list[start:end]

        embed = discord.Embed(
            title=f"📜 SUB-HABILIDADES: {self.target.display_name.upper()}",
            description=f"Página {self.current_page + 1} de {self.max_pages}\nDomínio sobre técnicas secundárias.",
            color=0x2b2d31
        )
        embed.set_thumbnail(url=self.target.display_avatar.url)

        for skill in current_skills:
            info = skill['info']
            barra = self.cog.criar_barra_progresso(info["exp"])
            embed.add_field(
                name=f"{info['emoji']} {info['nome']} (Nível {info['nivel']}/{info['max_nivel']})",
                value=f"```md\n# Progresso\n{barra}\n```",
                inline=False
            )
        
        embed.set_footer(text="Jujutsu Golden Age • Navegue pelos botões")
        return embed

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.gray)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.gray)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.max_pages - 1:
            self.current_page += 1
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.defer()

class SubHabilidadesSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_sub_data(self, user_id: str):
        res = supabase.table("player_sub_skills").select("data").eq("user_id", user_id).execute()
        return res.data[0]["data"] if res.data else None

    async def save_sub_data(self, user_id: str, data: dict):
        supabase.table("player_sub_skills").upsert({"user_id": user_id, "data": data}).execute()

    def criar_barra_progresso(self, atual, max_exp=10):
        tamanho_barra = 10
        progresso = max(0, min(max_exp, atual))
        cheios = int((progresso / max_exp) * tamanho_barra)
        vazios = tamanho_barra - cheios
        return f"[{'▉' * cheios}{'░' * vazios}] {progresso}/{max_exp}"

    @app_commands.command(name="sub_habilidades", description="Consulta sub-habilidades")
    async def sub_habilidades(self, interaction: discord.Interaction, usuario: discord.Member = None):
        target = usuario or interaction.user
        user_id = str(target.id)
        
        user_data = await self.get_sub_data(user_id)

        if not user_data:
            # Inicializa com a reserva de energia padrão
            user_data = {
                "skills": {
                    "reserva_de_energia": {
                        "nome": "Maestria de Reserva de Energia",
                        "nivel": 1, "max_nivel": 100, "exp": 0, "emoji": "✨"
                    }
                }
            }
            await self.save_sub_data(user_id, user_data)

        skills_dict = user_data["skills"]
        skills_list = [{"key": k, "info": v} for k, v in skills_dict.items()]
        
        view = SubHabilidadesPaginator(target, skills_list, self)
        await interaction.response.send_message(embed=view.create_embed(), view=view)

    @app_commands.command(name="add_sub_habilidade", description="[ADM] Adiciona sub-habilidade")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_sub_habilidade(self, interaction: discord.Interaction, usuario: discord.Member, nome: str, emoji: str = "🔹", max_nivel: int = 10):
        user_id = str(usuario.id)
        user_data = await self.get_sub_data(user_id) or {"skills": {}}

        skill_key = nome.lower().replace(" ", "_")
        if skill_key in user_data["skills"]:
            return await interaction.response.send_message("❌ O jogador já possui essa técnica.", ephemeral=True)

        user_data["skills"][skill_key] = {
            "nome": nome, "nivel": 0, "max_nivel": max_nivel, "exp": 0, "emoji": emoji
        }
        
        await self.save_sub_data(user_id, user_data)
        await interaction.response.send_message(f"✅ **{nome}** vinculada a {usuario.mention}!")

    @app_commands.command(name="add_maestria_sub", description="[ADM] Adiciona EXP em sub-habilidade")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_maestria_sub(self, interaction: discord.Interaction, usuario: discord.Member, nome_da_sub: str, quantidade: int):
        user_id = str(usuario.id)
        user_data = await self.get_sub_data(user_id)
        
        if not user_data or "skills" not in user_data:
            return await interaction.response.send_message("❌ Usuário sem registros.", ephemeral=True)

        # Busca flexível pelo nome ou key
        target_skill = None
        search_term = nome_da_sub.lower()
        for key, info in user_data["skills"].items():
            if search_term in info["nome"].lower() or search_term == key:
                target_skill = info
                break
        
        if not target_skill:
            return await interaction.response.send_message(f"❌ Técnica '{nome_da_sub}' não encontrada.", ephemeral=True)

        if target_skill["nivel"] >= target_skill["max_nivel"]:
            return await interaction.response.send_message("⭐ Nível máximo já alcançado!", ephemeral=True)

        target_skill["exp"] += quantidade
        msg_up = ""

        while target_skill["exp"] >= 10:
            if target_skill["nivel"] < target_skill["max_nivel"]:
                target_skill["exp"] -= 10
                target_skill["nivel"] += 1
                msg_up = f"\n🎊 **LEVEL UP!** {target_skill['nome']} foi para o nível {target_skill['nivel']}!"
            else:
                target_skill["exp"] = 0
                break

        await self.save_sub_data(user_id, user_data)
        barra = self.criar_barra_progresso(target_skill["exp"])
        await interaction.response.send_message(
            f"📈 **Maestria Atualizada!** ({usuario.display_name})\n{target_skill['emoji']} **{target_skill['nome']}**: {barra}{msg_up}"
        )

async def setup(bot):
    await bot.add_cog(SubHabilidadesSystem(bot))