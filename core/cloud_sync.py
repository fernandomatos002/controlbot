# core/cloud_sync.py
import requests
import json
from typing import Optional, Dict, Any

class CloudSync:
    """Gerencia sincronização de configurações com o servidor"""

    def __init__(self, api_url: str = "http://162.220.14.199"):
        self.api_url = api_url
        self.user_id = None
        self.enabled = False

    def set_user(self, user_id: int):
        """Define o usuário logado"""
        self.user_id = user_id
        self.enabled = True
        print(f"☁️ Sincronização ativada para user_id: {user_id}")

    def disable(self):
        """Desativa sincronização"""
        self.enabled = False
        self.user_id = None

    # ==================== CONTAS ====================

    def save_accounts(self, accounts: list) -> bool:
        """Salva contas no servidor"""
        if not self.enabled:
            return False

        try:
            response = requests.post(
                f"{self.api_url}/api/sync/save_accounts",
                json={"user_id": self.user_id, "accounts": accounts},
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print("☁️ Contas sincronizadas com sucesso")
                    return True

            print(f"❌ Erro ao sincronizar contas: {response.text}")
            return False

        except Exception as e:
            print(f"❌ Erro de conexão ao sincronizar contas: {e}")
            return False

    def load_accounts(self) -> Optional[list]:
        """Carrega contas do servidor"""
        if not self.enabled:
            return None

        try:
            response = requests.get(
                f"{self.api_url}/api/sync/load_accounts/{self.user_id}",
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    accounts = result.get("accounts", [])
                    print(f"☁️ {len(accounts)} contas carregadas do servidor")
                    return accounts

            return None

        except Exception as e:
            print(f"❌ Erro ao carregar contas: {e}")
            return None

    # ==================== PROXIES ====================

    def save_proxies(self, proxies: list) -> bool:
        """Salva proxies no servidor"""
        if not self.enabled:
            return False

        try:
            response = requests.post(
                f"{self.api_url}/api/sync/save_proxies",
                json={"user_id": self.user_id, "proxies": proxies},
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print("☁️ Proxies sincronizados com sucesso")
                    return True

            return False

        except Exception as e:
            print(f"❌ Erro ao sincronizar proxies: {e}")
            return False

    def load_proxies(self) -> Optional[list]:
        """Carrega proxies do servidor"""
        if not self.enabled:
            return None

        try:
            response = requests.get(
                f"{self.api_url}/api/sync/load_proxies/{self.user_id}",
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    proxies = result.get("proxies", [])
                    print(f"☁️ {len(proxies)} proxies carregados do servidor")
                    return proxies

            return None

        except Exception as e:
            print(f"❌ Erro ao carregar proxies: {e}")
            return None

    # ==================== TEMPLATES ====================

    def save_templates(self, template_type: str, templates: list) -> bool:
        """
        Salva templates no servidor
        template_type: 'build' ou 'recruit'
        """
        if not self.enabled:
            return False

        try:
            response = requests.post(
                f"{self.api_url}/api/sync/save_templates",
                json={
                    "user_id": self.user_id,
                    "template_type": template_type,
                    "templates": templates
                },
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print(f"☁️ Templates {template_type} sincronizados")
                    return True

            return False

        except Exception as e:
            print(f"❌ Erro ao sincronizar templates: {e}")
            return False

    def load_templates(self, template_type: str) -> Optional[list]:
        """Carrega templates do servidor"""
        if not self.enabled:
            return None

        try:
            response = requests.get(
                f"{self.api_url}/api/sync/load_templates/{self.user_id}/{template_type}",
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    templates = result.get("templates", [])
                    print(f"☁️ Templates {template_type} carregados do servidor")
                    return templates

            return None

        except Exception as e:
            print(f"❌ Erro ao carregar templates: {e}")
            return None

    # ==================== CONFIGURAÇÕES ====================

    def save_settings(self, settings: dict) -> bool:
        """Salva configurações globais no servidor"""
        if not self.enabled:
            return False

        try:
            response = requests.post(
                f"{self.api_url}/api/sync/save_settings",
                json={"user_id": self.user_id, "settings": settings},
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    print("☁️ Configurações sincronizadas com sucesso")
                    return True

            return False

        except Exception as e:
            print(f"❌ Erro ao sincronizar configurações: {e}")
            return False

    def load_settings(self) -> Optional[dict]:
        """Carrega configurações do servidor"""
        if not self.enabled:
            return None

        try:
            response = requests.get(
                f"{self.api_url}/api/sync/load_settings/{self.user_id}",
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    settings = result.get("settings", {})
                    print("☁️ Configurações carregadas do servidor")
                    return settings

            return None

        except Exception as e:
            print(f"❌ Erro ao carregar configurações: {e}")
            return None

    # ==================== CARREGAR TUDO ====================

    # (Seu código atual já deve ter isso, apenas confirme)
    def load_all(self) -> Optional[Dict[str, Any]]:
        """Carrega TODAS as configurações de uma vez"""
        if not self.enabled:
            return None

        try:
            response = requests.get(
                f"{self.api_url}/api/sync/load_all/{self.user_id}",
                timeout=15
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    configs = result.get("configs", {})
                    print(f"☁️ Todas as configurações carregadas ({len(configs)} tipos)")
                    return configs

            return None

        except Exception as e:
            print(f"❌ Erro ao carregar todas as configurações: {e}")
            return None

# Instância global
cloud_sync = CloudSync()
