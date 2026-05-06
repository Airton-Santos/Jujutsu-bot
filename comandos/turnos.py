import os
import discord
from discord import app_commands
from discord.ext import commands
from supabase import create_client, Client
from dotenv import load_dotenv
import random
import math

load_dotenv()

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# Configuração de Dano por Nível (Abaixo de 20 total)
DANO_EFEITOS = {
    "Queimação": {1: (2, 4), 2: (5, 8), 3: (10, 15)},
    "Sangramento": {1: (2, 4), 2: (5, 8), 3: (10, 15)},
    "Veneno": {1: (2, 4), 2: (5, 8), 3: (10, 15)},
    "Perca de Sanidade": {1: (3, 5), 2: (6, 9), 3: (12, 18)},
    "Hemorragia": {1: (4, 6), 2: (8, 12), 3: (15, 20)},
    "Toxico": {1: (3, 5), 2: (7, 10), 3: (13, 19)}
}

EMOJIS = {
    "Queimação": "🔥", "Sangramento": "🩸", "Veneno": "🧪",
    "Perca de Sanidade": "🧠", "Hemorragia": "💉", "Toxico": "☣️"
}

class TurnoSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="debuff_add", description="Adiciona um debuff a um jogador")
    @app_commands.choices(
        efeito=[app_commands.Choice(name=k, value=k) for k in DANO_EFEITOS.keys()],
        nivel=[app_commands.Choice(name=str(i), value=i) for i in [1, 2, 3]]
    )
    async def add_debuff(self, interaction: discord.Interaction, player: discord.Member, efeito: str, nivel: int):
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message("❌ Apenas Mestres podem aplicar debuffs.", ephemeral=True)

        user_id = str(player.id)
        res = supabase.table("player_conditions").select("*").eq("user_id", user_id).execute()
        
        effects = res.data[0]["effects"] if res.data else []
        
        found = False
        for e in effects:
            if e["nome"] == efeito:
                e["nivel"] = nivel
                found = True
                break
        
        if not found:
            effects.append({"nome": efeito, "nivel": nivel})
            
        if not res.data:
            supabase.table("player_conditions").insert({"user_id": user_id, "effects": effects, "turn_count": 0}).execute()
        else:
            supabase.table("player_conditions").update({"effects": effects}).eq("user_id", user_id).execute()

        await interaction.response.send_message(f"✅ {EMOJIS[efeito]} {efeito} {nivel} aplicado a {player.mention}!")

    @app_commands.command(name="turno", description="Passa o turno, aplica danos e recupera energia")
    async def passar_turno(self, interaction: discord.Interaction, player: discord.Member):
        user_id = str(player.id)

        # 1. Buscar Status e Condições
        status_res = supabase.table("player_status").select("stats").eq("user_id", user_id).execute()
        cond_res = supabase.table("player_conditions").select("*").eq("user_id", user_id).execute()

        if not status_res.data:
            return await interaction.response.send_message("❌ Jogador não encontrado.", ephemeral=True)
        
        # Garantir que a tabela de condições exista para o player
        if not cond_res.data:
            supabase.table("player_conditions").insert({"user_id": user_id, "effects": [], "turn_count": 0}).execute()
            cond_res = supabase.table("player_conditions").select("*").eq("user_id", user_id).execute()

        stats = status_res.data[0]["stats"]
        effects = cond_res.data[0]["effects"]
        turn_count = cond_res.data[0]["turn_count"] + 1
        
        dano_total = 0
        logs = []

        # 2. Processar Debuffs
        for e in effects:
            nome = e["nome"]
            lvl = e["nivel"]
            min_d, max_d = DANO_EFEITOS[nome][lvl]
            dano = random.randint(min_d, max_d)
            dano_total += dano
            logs.append(f"{EMOJIS[nome]} **{nome} {lvl}**: -{dano} HP")

        # 3. Aplicar Dano no HP
        stats["hp_atual"] = max(0, stats.get("hp_atual", 0) - dano_total)

        # 4. Lógica de Energia (A cada 3 turnos)
        recuperou_energia = False
        energia_recuperada = 0
        
        if turn_count >= 3:
            en_max = stats.get("en_max", 0)
            en_atual = stats.get("en_atual", 0)
            # Recupera 10% do total
            energia_recuperada = math.floor(en_max * 0.10)
            stats["en_atual"] = min(en_max, en_atual + energia_recuperada)
            turn_count = 0 # Reseta o contador
            recuperou_energia = True

        # 5. Salvar no Banco
        supabase.table("player_status").update({"stats": stats}).eq("user_id", user_id).execute()
        supabase.table("player_conditions").update({"turn_count": turn_count}).eq("user_id", user_id).execute()

        # 6. Feedback Visual
        embed = discord.Embed(
            title=f"🔄 Turno de {player.display_name}",
            description=f"**Contador de Turnos:** `{turn_count}/3`",
            color=discord.Color.dark_red() if dano_total > 0 else discord.Color.blue()
        )
        
        if logs:
            embed.add_field(name="📉 Efeitos Negativos", value="\n".join(logs), inline=False)
        else:
            embed.add_field(name="✨ Efeitos", value="Nenhum efeito negativo ativo.", inline=False)

        if recuperou_energia:
            embed.add_field(name="⚡ Regeneração (3º Turno)", 
                            value=f"Recuperou **{energia_recuperada}** de energia (10% do total)!", inline=False)

        embed.add_field(name="❤️ HP Atual", value=f"`{stats['hp_atual']}/{stats['hp_max']}`", inline=True)
        embed.add_field(name="🧪 EN Atual", value=f"`{stats['en_atual']}/{stats['en_max']}`", inline=True)
        
        if stats["hp_atual"] <= 0:
            embed.description = "💀 **O JOGADOR CAIU!**"
            supabase.table("player_conditions").update({"effects": []}).eq("user_id", user_id).execute()

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="turno_reset", description="Reseta o contador de turnos de um jogador")
    async def reset_turno(self, interaction: discord.Interaction, player: discord.Member):
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message("❌ Apenas Mestres.", ephemeral=True)
            
        supabase.table("player_conditions").update({"turn_count": 0}).eq("user_id", str(player.id)).execute()
        await interaction.response.send_message(f"🔄 Contador de turnos de {player.mention} resetado para 0.")

async def setup(bot):
    await bot.add_cog(TurnoSystem(bot))