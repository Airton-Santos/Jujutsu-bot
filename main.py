import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Configuração de Intents (Permissões do Bot)
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True  # Ative se precisar ler conteúdo de mensagens

class JujutsuBot(commands.Bot):
    def __init__(self):
        # O prefixo é configurado para menção para focar 100% em comandos Slash (/)
        super().__init__(
            command_prefix=commands.when_mentioned, 
            intents=intents,
            help_command=None  # Remove o comando !help clássico
        )

    async def setup_hook(self):
        print("\n--- 🔮 Carregando Técnicas Amaldiçoadas (Cogs) ---")
        
        # Cria a pasta de comandos caso ela não exista no clone do repositório
        if not os.path.exists('./comandos'):
            os.makedirs('./comandos')
            print("📁 Pasta './comandos' criada automaticamente. Adicione seus arquivos de comando nela!")

        # Varre a pasta de comandos para carregar cada extensão do bot
        for filename in os.listdir('./comandos'):
            if filename.endswith('.py') and not filename.startswith('__'):
                try:
                    await self.load_extension(f'comandos.{filename[:-3]}')
                    print(f'✅ Técnica carregada: {filename[:-3]}')
                except Exception as e:
                    print(f'❌ Falha ao carregar {filename[:-3]}: {e}')
        
        # Sincroniza os Slash Commands diretamente com a API do Discord
        print("\n🌀 Sincronizando Expansões de Domínio (Slash Commands)...")
        try:
            await self.tree.sync()
            print("✨ Todos os comandos Slash foram sincronizados globalmente!")
        except Exception as e:
            print(f'❌ Erro ao sincronizar comandos com o Discord: {e}')

    async def on_ready(self):
        print('=' * 40)
        print(f'🛡️ Feiticeiro Logado com sucesso: {self.user.name}')
        print(f'⚙️ Status: 100% pronto para usar Slash Commands (/)')
        print('=' * 40)

bot = JujutsuBot()

if __name__ == "__main__":
    if not TOKEN:
        print("🚨 ERRO: O 'DISCORD_TOKEN' não foi encontrado!")
        print("👉 Verifique se você criou o arquivo '.env' na raiz do projeto com as suas credenciais.")
    else:
        bot.run(TOKEN)