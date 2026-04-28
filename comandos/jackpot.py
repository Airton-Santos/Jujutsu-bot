import os
import discord
from discord import app_commands
from discord.ext import commands
import random
import asyncio
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Configuração do Supabase
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

GIF_HAKARI_DANCE = "https://media.tenor.com/7Y-j_rP9l_QAAAAd/hakari-dance-hakari-kinji.gif"

FALAS_GIRO = [
    "A febre... está começando a subir!",
    "Eu sou um viciado em azar, sabia?",
    "A sorte é apenas uma questão de técnica!",
    "Role os dados e deixe a música tocar!",
    "É tudo ou nada, baby!"
]

FALAS_JACKPOT = [
    "JACKPOT! A música não para por 4 minutos e 11 segundos!",
    "É preciso habilidade para ganhar com a sorte!",
    "A febre atingiu o ápice! Dance comigo!",
    "Estou no meu auge! Ninguém pode me parar agora!"
]

class ComandoJackpot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_passiva(self, user_id: str):
        """Busca a passiva atual do jogador no banco"""
        res = supabase.table("jackpot_data").select("passiva_atual").eq("user_id", user_id).execute()
        return res.data[0]["passiva_atual"] if res.data else "padrao"

    async def save_passiva(self, user_id: str, passiva: str):
        """Salva a nova passiva no banco"""
        supabase.table("jackpot_data").upsert({"user_id": user_id, "passiva_atual": passiva}).execute()

    async def realizar_giro(self, interaction, passiva_ativa, is_second_roll=False):
        # Lógica de Pesos
        pesos = [60, 25, 12, 3]
        if passiva_ativa == "sorte":
            pesos = [15, 45, 35, 5] 

        moedas_info = [
            {"nome": "Bronze", "raridade": "Comum", "cor": 0xcd7f32, "chance": 5},
            {"nome": "Prata", "raridade": "Incomum", "cor": 0xc0c0c0, "chance": 15},
            {"nome": "Ouro", "raridade": "Raro", "cor": 0xffd700, "chance": 75},
            {"nome": "Platina", "raridade": "Extremamente Rara", "cor": 0xe5e4e2, "chance": 100}
        ]

        sorteio_moeda = random.choices(moedas_info, weights=pesos, k=1)[0]
        sucesso_moeda = random.randint(1, 100) <= sorteio_moeda["chance"]
        
        # Sorteio dos Dados
        if sorteio_moeda["nome"] == "Platina":
            d1, d2, d3 = 7, 7, 7
        elif sucesso_moeda:
            face = random.randint(1, 7)
            d1, d2, d3 = face, face, face
        else:
            d1, d2, d3 = random.randint(1, 7), random.randint(1, 7), random.randint(1, 7)

        prefixo = "🔄 [SEGUNDO GIRO] " if is_second_roll else "🎰 [GIRO] "
        
        embed = discord.Embed(
            title=f"{prefixo} Girando a moeda...", 
            description=f"Usuário: {interaction.user.mention}\nPassiva: **{passiva_ativa.upper()}**",
            color=0x2b2d31
        )
        
        # Gerenciamento da resposta (Interaction vs Followup)
        if not is_second_roll:
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=embed)
            msg = await interaction.original_response()
        else:
            msg = await interaction.followup.send(embed=embed, wait=True)

        await asyncio.sleep(0.7)
        embed.title = f"{prefixo} Moeda {sorteio_moeda['nome']}!"
        embed.color = sorteio_moeda["cor"]
        await msg.edit(embed=embed)

        # Animação de sorteio
        for _ in range(3):
            f1, f2, f3 = random.randint(1, 7), random.randint(1, 7), random.randint(1, 7)
            embed.clear_fields()
            embed.add_field(name="🎰 Sorteando...", value=f"🎲 **{f1}** | 🎲 **{f2}** | 🎲 **{f3}**")
            await msg.edit(embed=embed)
            await asyncio.sleep(0.4)

        is_jackpot = (d1 == d2 == d3)
        res_visual = f"🎲 **{d1}** | 🎲 **{d2}** | 🎲 **{d3}**"
        
        embed.clear_fields()
        if is_jackpot:
            res_visual = f"🌟 ✨ **{d1} {d2} {d3}** ✨ 🌟"
            embed.title = f"🔥 {random.choice(FALAS_JACKPOT)}"
            embed.color = 0xff00ff
            embed.set_image(url=GIF_HAKARI_DANCE)
        else:
            embed.title = f"{prefixo} {random.choice(FALAS_GIRO)}"
        
        embed.add_field(name="Resultado Final", value=res_visual, inline=False)
        embed.add_field(name="Moeda", value=f"{sorteio_moeda['nome']} ({sorteio_moeda['raridade']})", inline=True)
        
        await msg.edit(embed=embed)
        return (d1, d2, d3), is_jackpot

    @app_commands.command(name="jackpot", description="Gira a roleta do Hakari")
    async def jackpot(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        
        # Busca passiva no Supabase
        passiva_atual = await self.get_passiva(user_id)
        resultados_finais = []
        
        if passiva_atual == "duplo":
            # Primeiro Giro
            res1, jack1 = await self.realizar_giro(interaction, "duplo", is_second_roll=False)
            resultados_finais.append(res1)
            
            if jack1:
                await interaction.followup.send(f"💎 {interaction.user.mention} ACERTOU O JACKPOT DE PRIMEIRA! Sorte absoluta!")
            else:
                # Segundo Giro (Passiva Duplo)
                res2, jack2 = await self.realizar_giro(interaction, "duplo", is_second_roll=True)
                resultados_finais.append(res2)
        else:
            res, jack = await self.realizar_giro(interaction, passiva_atual)
            resultados_finais.append(res)

        # Lógica de atualização de passiva baseada no ÚLTIMO dado sorteado
        d1, d2, d3 = resultados_finais[-1]
        todos_pares = (d1 % 2 == 0 and d2 % 2 == 0 and d3 % 2 == 0)
        todos_impares = (d1 % 2 != 0 and d2 % 2 != 0 and d3 % 2 != 0)

        nova_passiva = passiva_atual
        msg_passiva = f"ℹ️ Dados mistos. Sua passiva (**{passiva_atual.upper()}**) continua ativa."

        if todos_pares:
            nova_passiva = "duplo"
            msg_passiva = f"✨ {interaction.user.mention} conseguiu uma **TRINCA DE PARES!** Próxima passiva: **DUPLO**"
        elif todos_impares:
            nova_passiva = "sorte"
            msg_passiva = f"✨ {interaction.user.mention} conseguiu uma **TRINCA DE ÍMPARES!** Próxima passiva: **SORTE**"

        # Salva a nova passiva no Supabase
        await self.save_passiva(user_id, nova_passiva)
        await interaction.followup.send(msg_passiva)

async def setup(bot):
    await bot.add_cog(ComandoJackpot(bot))