import PyInstaller.__main__
import shutil
import os

# 1. Executa o PyInstaller usando o teu spec atual
print("🔨 Compilando...")
PyInstaller.__main__.run([
    'main.spec'
])

# 2. Define caminhos
dist_folder = os.path.join(os.getcwd(), 'dist', 'main') # Se for onedir
# Se for onefile (apenas um .exe), a pasta é apenas 'dist'
if not os.path.exists(dist_folder):
    dist_folder = os.path.join(os.getcwd(), 'dist')

# 3. Arquivos essenciais para copiar
files_to_copy = [
    'secret.key',
    'accounts.encrypted',
    'proxies.encrypted',
    'global_settings.json',
    'recruitment_templates.json',
    'templates.json',
    'version.txt' # Importante para o atualizador [cite: 63]
]

print("📂 Copiando dados do usuário para a pasta dist...")

for file in files_to_copy:
    if os.path.exists(file):
        try:
            # Se for onefile, copia para o lado do exe
            # Se for onedir (pasta), copia para dentro da pasta main
            if os.path.isdir(dist_folder) and 'main.exe' not in os.listdir(dist_folder):
                 # Caso dist/main/main.exe (modo onedir padrão)
                 target = os.path.join(dist_folder, 'main', file)
            else:
                 # Caso dist/main.exe (modo onefile)
                 target = os.path.join(dist_folder, file)
            
            shutil.copy2(file, target)
            print(f"   ✅ Copiado: {file}")
        except Exception as e:
            print(f"   ❌ Erro ao copiar {file}: {e}")
    else:
        print(f"   ⚠️ Arquivo não encontrado (será criado no primeiro uso): {file}")

print("\n🚀 Build Concluído! Pode executar o main.exe na pasta dist.")