import os
import sys
from cryptography.fernet import Fernet

def get_app_path():
    """Retorna o diretório onde o EXE está ou a raiz do projeto em DEV"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

KEY_FILE = os.path.join(get_app_path(), "secret.key")

def load_or_generate_key():
    """Garante que existe APENAS UMA chave para todo o sistema"""
    if os.path.exists(KEY_FILE):
        try:
            with open(KEY_FILE, "rb") as kf:
                key = kf.read()
                if len(key) > 0:
                    return key
        except:
            pass
    
    # Se não existir, cria uma nova
    key = Fernet.generate_key()
    try:
        with open(KEY_FILE, "wb") as kf:
            kf.write(key)
    except Exception as e:
        print(f"[SECURITY] Erro fatal ao salvar chave: {e}")
    
    return key

# Instância Global da Chave e do Cipher
# Ao importar 'global_cipher', todos os arquivos usarão a MESMA chave.
global_key = load_or_generate_key()
global_cipher = Fernet(global_key)