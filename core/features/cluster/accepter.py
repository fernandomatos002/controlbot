import time
import re
from bs4 import BeautifulSoup
from core.request_engine import GameClient

class ClusterAccepter:
    def __init__(self, log_func):
        self.log = log_func

    def accept_all(self, account_data, target_players=None):
        """
        Aceita convites de amizade pendentes na conta Master ou General.
        """
        try:
            client = GameClient(account_data)
            if not client.ensure_connection():
                self.log(f"Falha ao conectar na conta {account_data['username']}", "error")
                return {"success": False, "accepted": 0, "failed": 0}

            # 1. Acessa tela de amigos
            resp = client.safe_get("buddies")
            if not resp:
                self.log(f"Falha ao acessar tela de amigos", "error")
                return {"success": False, "accepted": 0, "failed": 0}

            # 2. Extrai os convites pendentes
            pending_invites = self._extract_pending_invites(resp.text)
            
            if not pending_invites:
                self.log(f"✅ Nenhum convite pendente para {account_data['username']}", "success")
                return {"success": True, "accepted": 0, "failed": 0}

            # 3. Filtra se o usuário especificou nomes (ex: apenas os 7 generais)
            if target_players:
                target_players_lower = [p.lower() for p in target_players]
                pending_invites = [
                    inv for inv in pending_invites 
                    if inv['name'].lower() in target_players_lower
                ]
                self.log(f"🔍 Filtrando: {len(pending_invites)} convites correspondem à lista de alvos.", "info")

            if not pending_invites:
                return {"success": True, "accepted": 0, "failed": 0}

            self.log(f"📋 Processando {len(pending_invites)} aceites para {account_data['username']}...", "info")
            
            stats = {
                "success": True,
                "accepted": 0,
                "failed": 0
            }

            # 4. Loop para aceitar cada um
            for idx, invite in enumerate(pending_invites, 1):
                try:
                    self.log(f"[{idx}/{len(pending_invites)}] Aceitando {invite['name']}...", "info")
                    
                    # Constrói a URL de aceitar (usando o href extraído ou montando um novo)
                    # O href extraído já contém o buddy_id e o token h
                    approve_url = invite['href'].replace('&amp;', '&')
                    
                    # Faz o GET para aceitar
                    resp_accept = client.safe_get_absolute(approve_url)
                    
                    if not resp_accept:
                        self.log(f"❌ [{idx}] Falha na requisição para {invite['name']}", "error")
                        stats["failed"] += 1
                        continue
                    
                    # 5. Validação Robusta: Verifica se sumiu da lista de pendentes
                    time.sleep(2) # Pausa para o servidor processar a mudança
                    resp_check = client.safe_get("buddies")
                    
                    if resp_check:
                        # Extrai a lista de novo e vê se o ID ainda está lá
                        check_list = self._extract_pending_invites(resp_check.text)
                        is_still_pending = any(inv['buddy_id'] == invite['buddy_id'] for inv in check_list)
                        
                        if not is_still_pending:
                            self.log(f"✅ [{idx}] {invite['name']} aceito com sucesso!", "success")
                            stats["accepted"] += 1
                        else:
                            self.log(f"⚠️ [{idx}] {invite['name']} ainda aparece como pendente.", "warn")
                            stats["failed"] += 1
                    
                    # Pausa entre aceites para evitar detecção
                    if idx < len(pending_invites):
                        time.sleep(1.5)

                except Exception as e:
                    self.log(f"❌ [{idx}] Erro ao aceitar {invite['name']}: {e}", "error")
                    stats["failed"] += 1
                    continue

            return stats

        except Exception as e:
            self.log(f"Erro crítico no Accepter ({account_data['username']}): {e}", "error")
            return {"success": False, "accepted": 0, "failed": 0}

    def _extract_pending_invites(self, html):
        """
        Extrai os convites pendentes da página de amigos usando BeautifulSoup.
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            invites = []
            
            # Encontra o cabeçalho "Convites em aberto"
            h3_tag = soup.find('h3', string=lambda t: t and 'Convites em aberto' in t)
            if not h3_tag:
                return []
            
            table = h3_tag.find_next('table', class_='vis')
            if not table:
                return []
            
            rows = table.find_all('tr')[1:] # Pula o cabeçalho da tabela
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 2: continue
                
                # Nome do Player
                name_link = cells[0].find('a')
                if not name_link: continue
                player_name = name_link.text.strip()
                
                # Link de Aceitar
                accept_link = cells[1].find('a', class_='btn-confirm-yes')
                if not accept_link:
                    # Tenta achar qualquer link que tenha approve_buddy
                    accept_link = cells[1].find('a', href=re.compile(r'action=approve_buddy'))
                
                if accept_link:
                    href = accept_link.get('href', '')
                    buddy_id_match = re.search(r'buddy_id=(\d+)', href)
                    
                    if buddy_id_match:
                        invites.append({
                            "name": player_name,
                            "buddy_id": buddy_id_match.group(1),
                            "href": href
                        })
            
            return invites
        except Exception as e:
            print(f"Erro ao extrair convites: {e}")
            return []

# Exemplo de inicialização (ajuste conforme seu sistema de log)
# accepter = ClusterAccepter(lambda msg, typ: print(f"[{typ.upper()}] {msg}"))