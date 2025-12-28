import os

# --- CONFIGURAÇÕES ---
# Nome do arquivo final que será gerado
OUTPUT_FILE = 'projeto_completo.txt'

# Pastas que o script DEVE ignorar
IGNORE_DIRS = {
    '.git', '__pycache__', 'venv', 'env', '.idea', '.vscode', 
    'node_modules', 'dist', 'build', 'migrations', 'browsers','Nova pasta','documentacao.txt','backup', 'venv', '.spec','juntar.py'
}

# Arquivos específicos que o script DEVE ignorar
IGNORE_FILES = {
    OUTPUT_FILE, '.DS_Store', 'poetry.lock', 'package-lock.json', '.gitignore' 'juntar.py'
}

# Extensões que você quer IGNORAR (opcional, para evitar imagens, dbs, etc)
IGNORE_EXTENSIONS = {
    '.pyc', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.exe', '.dll', '.so', '.sqlite3', '.db', '.encrypted'
}

def is_text_file(filepath):
    """Tenta ler um pedaço do arquivo para ver se é texto ou binário."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            f.read(1024)
            return True
    except (UnicodeDecodeError, PermissionError):
        return False

def collect_project_code():
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as outfile:
        # Escreve um cabeçalho
        outfile.write(f"# CONTEXTO DO PROJETO\n")
        outfile.write(f"# Gerado automaticamente\n")
        outfile.write("="*50 + "\n\n")

        # Caminha por todas as pastas
        for root, dirs, files in os.walk('.'):
            # Remove pastas ignoradas da lista de navegação
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

            for file in files:
                file_path = os.path.join(root, file)
                extension = os.path.splitext(file)[1].lower()

                # Verificações de filtro
                if file in IGNORE_FILES:
                    continue
                if extension in IGNORE_EXTENSIONS:
                    continue
                
                # Verifica se é binário antes de escrever
                if not is_text_file(file_path):
                    print(f"Ignorando arquivo binário: {file_path}")
                    continue

                # Escreve o conteúdo no arquivo final
                try:
                    with open(file_path, 'r', encoding='utf-8') as infile:
                        content = infile.read()
                        
                        # Formatação visual para identificar o arquivo
                        outfile.write(f"\n{'='*20} INICIO ARQUIVO: {file_path} {'='*20}\n")
                        outfile.write(content)
                        outfile.write(f"\n{'='*20} FIM ARQUIVO: {file_path} {'='*20}\n\n")
                        
                    print(f"Adicionado: {file_path}")
                except Exception as e:
                    print(f"Erro ao ler {file_path}: {e}")

    print(f"\n--- Concluído! Todo o projeto foi salvo em '{OUTPUT_FILE}' ---")

if __name__ == "__main__":
    collect_project_code()