import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Carregar o token
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Intents: Para Slash puro, o 'message_content' é opcional, 
# mas recomendo manter se for usar log de mensagens ou filtros.
intents = discord.Intents.default()
intents.members = True 

class JujutsuBot(commands.Bot):
    def __init__(self):
        # Usamos o prefixo commands.when_mentioned para que o bot 
        # NÃO responda a exclamações (!), apenas a comandos '/'
        super().__init__(
            command_prefix=commands.when_mentioned, 
            intents=intents,
            help_command=None # Remove o comando !help padrão
        )

    async def setup_hook(self):
        print("--- 🔮 Carregando Técnicas Amaldiçoadas ---")
        
        # Garante que a pasta existe para não dar erro
        if not os.path.exists('./comandos'):
            os.makedirs('./comandos')

        for filename in os.listdir('./comandos'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'comandos.{filename[:-3]}')
                    print(f'✅ Técnica: {filename[:-3]}')
                except Exception as e:
                    print(f'❌ Falha em {filename[:-3]}: {e}')
        
        # Sincroniza os Slash Commands com o Discord globalmente
        await self.tree.sync()
        print("🌀 Expansões de Domínio (Slash) Sincronizadas!")

    async def on_ready(self):
        print('---' * 10)
        print(f'🛡️ Feiticeiro Logado: {self.user.name}')
        print(f'⚙️ Versão: 100% Slash Commands')
        print('---' * 10)

bot = JujutsuBot()

if __name__ == "__main__":
    bot.run(TOKEN)