import json
import os
import sys  # Necessário para o EXE
import threading
# from core.path_finder import get_file_path # Removido
from core.cloud_sync import cloud_sync

# --- FUNÇÃO DE CAMINHO SEGURO ---
def get_app_path():
    """Retorna o diretório onde o EXE está ou a raiz do projeto em DEV"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        # Sobe 2 níveis (core/settings_manager.py -> raiz)
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Define o caminho absoluto do arquivo de configurações
SETTINGS_FILE = os.path.join(get_app_path(), "global_settings.json")

DEFAULT_SETTINGS = {
    "min_interval": 3,
    "max_interval": 5,
    "farm_priority": False,
    "storage_priority": False,
    "reserve_for_building": True
}

class SettingsManager:
    def __init__(self):
        self.settings = self.load_settings()

    def load_settings(self):
        # 1. Tentar carregar do servidor primeiro
        if cloud_sync.enabled:
            try:
                server_settings = cloud_sync.load_settings()
                if server_settings is not None and len(server_settings) > 0:
                    print("✅ Configurações carregadas do SERVIDOR")
                    merged = DEFAULT_SETTINGS.copy()
                    merged.update(server_settings)
                    return merged
            except Exception as e:
                print(f"Erro ao carregar settings da nuvem: {e}")

        # 2. Fallback: carregar local
        if not os.path.exists(SETTINGS_FILE):
            print("📁 Usando configurações PADRÃO")
            return DEFAULT_SETTINGS.copy()

        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                merged = DEFAULT_SETTINGS.copy()
                merged.update(data)
                print("📁 Configurações carregadas LOCALMENTE")
                return merged
        except Exception as e:
            print(f"Erro ao ler settings locais: {e}")
            return DEFAULT_SETTINGS.copy()

    def save_settings(self, new_settings):
        self.settings = new_settings
        try:
            # 1. Salvar localmente
            with open(SETTINGS_FILE, "w") as f:
                json.dump(self.settings, f, indent=4)

            # 2. Sincronizar com servidor (ASSÍNCRONO)
            if cloud_sync.enabled:
                threading.Thread(
                    target=cloud_sync.save_settings,
                    args=(self.settings,),
                    daemon=True
                ).start()

        except Exception as e:
            print(f"Erro ao salvar configurações: {e}")

    def get(self, key, default=None):
        if default is None:
            default = DEFAULT_SETTINGS.get(key)
        return self.settings.get(key, default)

global_settings = SettingsManager()