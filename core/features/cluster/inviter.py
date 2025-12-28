import time
import re
from core.request_engine import GameClient 

class ClusterInviter:
    def __init__(self, log_func):
        self.log = log_func

    def invite_player(self, account_data, target_username):
        """
        Envia convite de amizade usando o form HTML padrão.
        Extremamente simples - é um POST com name + CSRF.
        """
        try:
            client = GameClient(account_data)
            if not client.ensure_connection():
                self.log(f"Falha ao conectar na conta {account_data['username']}", "error")
                return False

            # 1. Acessa tela de amigos para sincronizar sessão e obter village_id
            resp = client.safe_get("buddies")
            if not resp:
                self.log(f"Falha ao acessar tela de amigos", "error")
                return False

            # 2. Valida se já é amigo ou convite já foi enviado
            if target_username.lower() in resp.text.lower():
                self.log(f"⚠️ {target_username} já é amigo ou convite pendente de {account_data['username']}.", "warn")
                return True

            # 3. Extrai village_id do HTML (se não estiver em account_data)
            village_id = account_data.get('village_id', '4053')
            if village_id == '1':  # Default, tenta extrair
                match = re.search(r'village=(\d+)', resp.text)
                if match:
                    village_id = match.group(1)

            self.log(f"🏘️ Village ID: {village_id}", "info")

            # 4. Monta a requisição correta
            # URL: /game.php?village=XXXX&screen=buddies&action=add_buddy
            # POST data: name=target&h=csrf_token
            
            params = {
                "village": village_id,
                "screen": "buddies",
                "action": "add_buddy"
            }
            
            payload = {
                "name": target_username
                # O safe_post adiciona 'h' (csrf_token) automaticamente
            }
            
            self.log(f"📨 Enviando convite para {target_username}...", "info")
            
            resp_post = client.safe_post("buddies", payload, params=params)
            
            if not resp_post:
                self.log(f"❌ Resposta vazia ao enviar convite", "error")
                return False
            
            # 5. Valida a resposta
            resp_text = resp_post.text.lower()
            
            # Sinais de sucesso
            if any(word in resp_text for word in ["sucesso", "success", "adicionado", "added", "friend"]):
                self.log(f"✅ Convite enviado com sucesso por {account_data['username']}.", "success")
                return True
            
            # Sinais de erro comuns
            if "já é amigo" in resp_text or "already friend" in resp_text:
                self.log(f"⚠️ {target_username} já é amigo.", "warn")
                return True
            
            if "não existe" in resp_text or "does not exist" in resp_text or "not found" in resp_text:
                self.log(f"❌ Jogador {target_username} não existe.", "error")
                return False
            
            if "pode adicionar a si mesmo" in resp_text or "cannot add yourself" in resp_text:
                self.log(f"❌ Não pode adicionar a si mesmo.", "error")
                return False
            
            # Status 200+ geralmente indica sucesso no form submit
            if resp_post.status_code in [200, 201]:
                self.log(f"✅ Convite enviado (HTTP {resp_post.status_code}).", "success")
                return True
            
            # Fallback: mostra a resposta para debug
            self.log(f"⚠️ Resposta ambígua (HTTP {resp_post.status_code}): {resp_text[:100]}", "warn")
            return True  # Assume sucesso para não bloquear

        except Exception as e:
            self.log(f"Erro técnico no Inviter ({account_data['username']}): {e}", "error")
            import traceback
            traceback.print_exc()
            return False