import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import math

SUB_HAB_PATH = "./player_sub_skills.json"

def load_data():
    if not os.path.exists(SUB_HAB_PATH): return {}
    try:
        with open(SUB_HAB_PATH, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}

def save_data(data):
    with open(SUB_HAB_PATH, "w", encoding="utf-8") as f: 
        json.dump(data, f, indent=4, ensure_ascii=False)

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
            description=f"Página {self.current_page + 1} de {self.max_pages}\nNível de domínio sobre técnicas secundárias.",
            color=0x2b2d31
        )
        embed.set_thumbnail(url=self.target.display_avatar.url)

        for skill in current_skills:
            info = skill['info']
            barra = self.cog.criar_barra_progresso(info["exp"])
            texto = f"```md\n# Progresso para o próximo nível\n{barra}\n```"
            embed.add_field(
                name=f"{info['emoji']} {info['nome']} (Nível {info['nivel']}/{info['max_nivel']})",
                value=texto,
                inline=False
            )
        
        embed.set_footer(text="Jujutsu Golden Age • Use os botões para navegar")
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

    def criar_barra_progresso(self, atual, max_exp=10):
        tamanho_barra = 10
        progresso = max(0, min(max_exp, atual))
        cheios = int((progresso / max_exp) * tamanho_barra)
        vazios = tamanho_barra - cheios
        return f"[{'▉' * cheios}{'░' * vazios}] {progresso}/{max_exp}"

    def inicializar_usuario(self, user_id, data):
        if user_id not in data:
            data[user_id] = {
                "skills": {
                    "reserva_de_energia": {
                        "nome": "Maestria de Reserva de Energia",
                        "nivel": 1,
                        "max_nivel": 100,
                        "exp": 0,
                        "emoji": "✨"
                    }
                }
            }
        return data

    @app_commands.command(name="sub_habilidades", description="Consulta suas sub-habilidades e maestrias")
    async def sub_habilidades(self, interaction: discord.Interaction, usuario: discord.Member = None):
        target = usuario or interaction.user
        user_id = str(target.id)
        data = load_data()
        data = self.inicializar_usuario(user_id, data)
        save_data(data)

        skills_dict = data[user_id]["skills"]
        
        if not skills_dict:
            return await interaction.response.send_message(f"O usuário {target.display_name} não possui sub-habilidades.")

        # Converte o dicionário em uma lista para facilitar a paginação
        skills_list = [{"key": k, "info": v} for k, v in skills_dict.items()]
        
        view = SubHabilidadesPaginator(target, skills_list, self)
        await interaction.response.send_message(embed=view.create_embed(), view=view)

    @app_commands.command(name="add_sub_habilidade", description="[MESTRE] Adiciona uma nova sub-habilidade a um jogador")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_sub_habilidade(self, interaction: discord.Interaction, usuario: discord.Member, nome: str, emoji: str = "🔹"):
        user_id = str(usuario.id)
        data = load_data()
        data = self.inicializar_usuario(user_id, data)

        skill_key = nome.lower().replace(" ", "_")
        if skill_key in data[user_id]["skills"]:
            return await interaction.response.send_message("❌ O jogador já possui essa sub-habilidade.", ephemeral=True)

        data[user_id]["skills"][skill_key] = {
            "nome": nome,
            "nivel": 0,
            "max_nivel": 10,
            "exp": 0,
            "emoji": emoji
        }
        
        save_data(data)
        await interaction.response.send_message(f"✅ Sub-habilidade **{nome}** adicionada para {usuario.mention}!")

    @app_commands.command(name="add_maestria_sub", description="[MESTRE] Adiciona progresso a uma sub-habilidade")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_maestria_sub(self, interaction: discord.Interaction, usuario: discord.Member, nome_da_sub: str, quantidade: int):
        user_id = str(usuario.id)
        data = load_data()
        
        if user_id not in data:
            return await interaction.response.send_message("❌ Usuário sem sub-habilidades.", ephemeral=True)

        target_skill = None
        for key, info in data[user_id]["skills"].items():
            if nome_da_sub.lower() in info["nome"].lower() or nome_da_sub.lower() == key:
                target_skill = info
                break
        
        if not target_skill:
            return await interaction.response.send_message(f"❌ Sub-habilidade '{nome_da_sub}' não encontrada.", ephemeral=True)

        if target_skill["nivel"] >= target_skill["max_nivel"]:
            return await interaction.response.send_message("⭐ Esta habilidade já está no nível máximo!", ephemeral=True)

        target_skill["exp"] += quantidade
        msg_up = ""

        while target_skill["exp"] >= 10:
            if target_skill["nivel"] < target_skill["max_nivel"]:
                target_skill["exp"] -= 10
                target_skill["nivel"] += 1
                msg_up = f"\n🎊 **LEVEL UP!** {target_skill['nome']} subiu para o nível {target_skill['nivel']}!"
            else:
                target_skill["exp"] = 0
                break

        save_data(data)
        barra = self.criar_barra_progresso(target_skill["exp"])
        await interaction.response.send_message(
            f"📈 **Maestria Atualizada!** ({usuario.display_name})\n{target_skill['emoji']} **{target_skill['nome']}**: {barra}{msg_up}"
        )

async def setup(bot):
    await bot.add_cog(SubHabilidadesSystem(bot))