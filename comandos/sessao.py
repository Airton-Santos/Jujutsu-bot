import os
import discord
from discord import app_commands
from discord.ext import commands
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

class SessionView(discord.ui.View):
    """View que contém o botão de entrar na sessão"""
    def __init__(self, guild_id: str):
        super().__init__(timeout=None) # Sem timeout para o botão não parar de funcionar
        self.guild_id = guild_id

    @discord.ui.button(label="Participar da Sessão", style=discord.ButtonStyle.green, custom_id="join_session_btn")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        
        # Busca a sessão atual
        res = supabase.table("sessions").select("players").eq("guild_id", str(interaction.guild_id)).eq("status", "ativa").execute()
        
        if not res.data:
            return await interaction.response.send_message("❌ Não há nenhuma sessão ativa no momento.", ephemeral=True)
        
        players = res.data[0]["players"]
        
        # Verifica se o player já está na lista
        if any(p['id'] == str(user.id) for p in players):
            return await interaction.response.send_message("⚠️ Você já está nesta sessão!", ephemeral=True)
        
        # Adiciona o novo player
        players.append({"id": str(user.id), "nome": user.display_name})
        
        # Salva no banco
        supabase.table("sessions").update({"players": players}).eq("guild_id", str(interaction.guild_id)).execute()
        
        await interaction.response.send_message(f"✅ {user.mention}, você entrou na sessão!", ephemeral=True)

class SessaoSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="sessao_iniciar", description="Inicia uma nova sessão de RPG")
    async def iniciar(self, interaction: discord.Interaction):
        # Verifica se o usuário é mestre/admin
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message("❌ Apenas Mestres podem iniciar sessões.", ephemeral=True)

        guild_id = str(interaction.guild_id)
        
        # Verifica se já existe sessão ativa
        check = supabase.table("sessions").select("*").eq("guild_id", guild_id).eq("status", "ativa").execute()
        if check.data:
            return await interaction.response.send_message("⚠️ Já existe uma sessão em andamento neste servidor!", ephemeral=True)

        # Cria no banco
        data = {
            "guild_id": guild_id,
            "mestre_id": str(interaction.user.id),
            "players": [],
            "status": "ativa"
        }
        supabase.table("sessions").insert(data).execute()

        embed = discord.Embed(
            title="⚔️ NOVA SESSÃO INICIADA!",
            description=f"O Mestre {interaction.user.mention} abriu as cortinas de uma nova aventura!\n\nClique no botão abaixo para participar.",
            color=0x5865F2
        )
        embed.set_footer(text="Jujutsu Golden Age • Sistema de Sessão")
        
        view = SessionView(guild_id)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="sessao_add_player", description="Adiciona um jogador manualmente à sessão")
    async def add_player(self, interaction: discord.Interaction, player: discord.Member):
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message("❌ Apenas Mestres podem adicionar jogadores.", ephemeral=True)

        res = supabase.table("sessions").select("players").eq("guild_id", str(interaction.guild_id)).eq("status", "ativa").execute()
        
        if not res.data:
            return await interaction.response.send_message("❌ Nenhuma sessão ativa encontrada.", ephemeral=True)

        players = res.data[0]["players"]
        
        if any(p['id'] == str(player.id) for p in players):
            return await interaction.response.send_message(f"⚠️ {player.display_name} já está na sessão.", ephemeral=True)

        players.append({"id": str(player.id), "nome": player.display_name})
        supabase.table("sessions").update({"players": players}).eq("guild_id", str(interaction.guild_id)).execute()

        await interaction.response.send_message(f"✅ {player.mention} foi adicionado à sessão pelo mestre!")

    @app_commands.command(name="sessao_lista", description="Mostra quem está na sessão atual")
    async def lista(self, interaction: discord.Interaction):
        res = supabase.table("sessions").select("players", "mestre_id").eq("guild_id", str(interaction.guild_id)).eq("status", "ativa").execute()
        
        if not res.data:
            return await interaction.response.send_message("📭 Nenhuma sessão ativa.", ephemeral=True)

        players = res.data[0]["players"]
        mestre_id = res.data[0]["mestre_id"]
        
        lista_nomes = "\n".join([f"👤 {p['nome']}" for p in players]) if players else "Nenhum jogador ainda."
        
        embed = discord.Embed(title="📜 PARTICIPANTES DA SESSÃO", color=0x2b2d31)
        embed.add_field(name="🎙️ Mestre", value=f"<@{mestre_id}>", inline=False)
        embed.add_field(name="👥 Jogadores", value=f"```\n{lista_nomes}\n```", inline=False)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="sessao_heal_all", description="Cura todos os jogadores da sessão ao máximo (HP e EN)")
    async def heal_all(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message("❌ Apenas Mestres podem curar todos.", ephemeral=True)

        # Defer para evitar timeout
        await interaction.response.defer()

        guild_id = str(interaction.guild_id)
        res = supabase.table("sessions").select("players").eq("guild_id", guild_id).eq("status", "ativa").execute()

        if not res.data or not res.data[0]["players"]:
            return await interaction.followup.send("❌ Nenhuma sessão ativa ou nenhum jogador na sessão.")

        players = res.data[0]["players"]
        count = 0

        for p in players:
            p_id = p['id']
            # Busca status do player na tabela de fichas (player_status)
            stats_res = supabase.table("player_status").select("stats").eq("user_id", p_id).execute()
            
            if stats_res.data:
                current_stats = stats_res.data[0]["stats"]
                # Seta o atual para o máximo
                current_stats["hp_atual"] = current_stats.get("hp_max", 100)
                current_stats["en_atual"] = current_stats.get("en_max", 100)
                
                # Salva de volta
                supabase.table("player_status").update({"stats": current_stats}).eq("user_id", p_id).execute()
                count += 1

        await interaction.followup.send(f"✨ **Cura Total!** {count} jogadores da sessão foram restaurados ao máximo pelo mestre.")

    @app_commands.command(name="sessao_encerrar", description="Finaliza a sessão atual")
    async def encerrar(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message("❌ Apenas Mestres podem encerrar sessões.", ephemeral=True)

        supabase.table("sessions").update({"status": "encerrada"}).eq("guild_id", str(interaction.guild_id)).eq("status", "ativa").execute()
        
        # Deletar para simplificar o 'unique' por servidor:
        supabase.table("sessions").delete().eq("guild_id", str(interaction.guild_id)).execute()

        await interaction.response.send_message("🏁 Sessão encerrada e registros limpos!")

async def setup(bot):
    await bot.add_cog(SessaoSystem(bot))