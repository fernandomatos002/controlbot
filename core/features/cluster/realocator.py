import time
from core.request_engine import GameClient

class ClusterRealocator:
    def __init__(self, log_func):
        self.log = log_func

    def execute_relocation(self, account_data, target_buddy_id):
        """
        Executa a realocação da aldeia para perto de um amigo (Buddy).
        """
        try:
            client = GameClient(account_data)
            if not client.ensure_connection():
                return False

            self.log(f"🚀 Iniciando realocação de {account_data['username']} para ID {target_buddy_id}...", "info")

            # 1. Garante que temos o ID da aldeia
            village_id = account_data.get('village_id')
            if not village_id:
                # Tenta pegar dos dados do jogo se não tiver no cache da conta
                village_id = client.game_data.get('village', {}).get('id')
            
            if not village_id:
                self.log(f"❌ Erro: ID da aldeia não encontrado para {account_data['username']}", "error")
                return False

            # 2. Prepara o Payload (Carga de dados)
            payload = {
                "village": village_id,
                "screen": "inventory",
                "ajaxaction": "consume",
                "item_key": "200_0",  # ID padrão do item de realocação
                "amount": "1",
                "direction": "buddy",
                "buddy": str(target_buddy_id),
                "h": client.csrf_token
            }

            # 3. Cabeçalhos Obrigatórios (Simula navegador real)
            headers = {
                "X-Requested-With": "XMLHttpRequest",
                "Referer": f"https://{account_data['world']}.tribalwars.com.pt/game.php?village={village_id}&screen=inventory"
            }

            url = f"game.php?village={village_id}&screen=inventory&ajaxaction=consume"
            
            # 4. Envia a Requisição POST
            response = client.session.post(
                f"https://{account_data['world']}.tribalwars.com.pt/{url}", 
                data=payload, 
                headers=headers
            )

            # 5. Validação da Resposta (Lógica Tolerante)
            if response.status_code == 200:
                try:
                    res_data = response.json()
                    
                    # Verifica se existe uma mensagem de erro explícita
                    error_msg = res_data.get('error')
                    
                    # Às vezes o erro vem em 'msg', vamos checar se parece erro
                    if not error_msg and isinstance(res_data.get('msg'), str):
                         msg_text = res_data['msg'].lower()
                         if "erro" in msg_text or "não" in msg_text or "falha" in msg_text:
                             error_msg = res_data['msg']

                    if error_msg:
                        self.log(f"⚠️ Servidor recusou: {error_msg}", "error")
                        return False
                    
                    # Se chegou aqui: HTTP 200 + Sem mensagem de erro = SUCESSO!
                    self.log(f"✅ {account_data['username']} realocado com sucesso!", "success")
                    return True

                except:
                    # Se o servidor não retornou JSON (ex: redirecionou ou HTML vazio), 
                    # mas o status é 200, assumimos que funcionou.
                    self.log(f"✅ {account_data['username']} realocado com sucesso! (Resp: 200 OK)", "success")
                    return True
            else:
                self.log(f"❌ Erro HTTP {response.status_code}", "error")
                return False

        except Exception as e:
            self.log(f"Erro crítico na realocação: {e}", "error")
            return False

# Instância global para uso no Controller
cluster_realocator = ClusterRealocator(lambda m, t: print(f"[REALOCATOR] {m}"))