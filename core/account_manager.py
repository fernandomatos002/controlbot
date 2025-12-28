import uuid
import json
import os
import threading
from core.proxy_manager import manager as proxy_manager
from core.cloud_sync import cloud_sync
from core.security import get_app_path, global_cipher


# Definição do caminho do arquivo de dados (Usa o caminho seguro do security.py)
DATA_FILE = os.path.join(get_app_path(), "accounts.encrypted")

class AccountManager:
    def __init__(self):
        self.file_path = DATA_FILE
        self.cipher = global_cipher 
        self.accounts = self.load()
        self._save_lock = threading.Lock()

    def save(self):
        with self._save_lock:
            try:
                if self.accounts is None: self.accounts = []
            
                json_str = json.dumps(self.accounts)
                encrypted_data = self.cipher.encrypt(json_str.encode())

                with open(DATA_FILE, "wb") as df:
                    df.write(encrypted_data)

                if cloud_sync.enabled:
                    accounts_copy = [acc.copy() for acc in self.accounts]
                    threading.Thread(
                        target=cloud_sync.save_accounts,
                        args=(self.accounts,), 
                        daemon=True
                    ).start()

            except Exception as e:
                print(f"Erro ao salvar contas: {e}")

    def load(self):
        """Carrega contas priorizando a nuvem, com fallback para o arquivo local"""
        # 1. Tentar carregar do servidor primeiro (se ativado)
        if cloud_sync.enabled:
            try:
                server_accounts = cloud_sync.load_accounts()
                if server_accounts is not None and len(server_accounts) > 0:
                    print("✅ Contas carregadas do SERVIDOR")
                    return server_accounts
            except Exception as e:
                print(f"Erro ao carregar da nuvem: {e}")

        # 2. Fallback: carregar do arquivo local 
        if not os.path.exists(DATA_FILE):
            return []

        try:
            with open(DATA_FILE, "rb") as df:
                encrypted_data = df.read()
            
            # Se arquivo vazio
            if not encrypted_data: return []

            # Descriptografia usando a chave global
            decrypted_data = self.cipher.decrypt(encrypted_data).decode()
            print("🔒 Contas carregadas LOCALMENTE")
            return json.loads(decrypted_data)
        except Exception as e:
            print(f"Erro ao carregar contas locais: {e}")
            # Retorna lista vazia em vez de erro para não travar a UI
            return []

    def add_account(self, world, username, proxy_id, server_region, password=None):
        """
        Adiciona uma nova conta e atribui proxy se necessário
        """
        new_account = {
            "id": str(uuid.uuid4()),
            "server": server_region,
            "world": world,
            "username": username,
            "password": password, 
            "proxy_id": proxy_id,
            "status": "stopped", 
            "next_run": None,
            "group": "ungrouped"
        }
        self.accounts.append(new_account)
        self.save()

        if proxy_id and proxy_id != "none":
            account_label = f"[{server_region}] {username} - {world}"
            proxy_manager.assign_proxy(proxy_id, account_label)

        return new_account

    def delete_account(self, account_id):
        """Remove a conta e libera o proxy associado"""
        account = self.get_account(account_id)
        if account:
            if account.get('proxy_id') and account['proxy_id'] != "none":
                proxy_manager.assign_proxy(account['proxy_id'], None)

            self.accounts.remove(account)
            self.save()

    def get_account(self, account_id):
        """Retorna o dicionário da conta baseada no ID"""
        for acc in self.accounts:
            if acc['id'] == account_id:
                return acc
        return None

# Instância global para o projeto
account_manager = AccountManager()