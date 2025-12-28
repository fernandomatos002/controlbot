import time
import random

class RewardManager:
    def __init__(self, client, log_func):
        self.client = client
        self.log = log_func

    def handle_daily_bonus(self, parser):
        self.log("🕵️ Verificando Bônus Diário...", "info")
        if parser.check_daily_bonus():
            self.log("🎁 Janela de Bônus detectada! Tentando coletar...", "warn")
            try:
                resp = self.client.safe_get("daily_bonus")
                from core.game_parser import GameParser 
                parser_bonus = GameParser(resp.text)
                
                day = parser_bonus.get_daily_bonus_day()
                if day:
                    self.log(f"📅 Coletando recompensa do Dia {day}...", "success")
                    payload = {
                        "day": day, "from_screen": "login", "client_time": int(time.time())
                    }
                    self.client.safe_post("daily_bonus", payload, params={"ajaxaction": "open"})
                    time.sleep(1)
                    self.log("✅ Bônus Diário coletado com sucesso!", "success")
                    return True 
            except Exception as e:
                self.log(f"⚠️ Erro ao coletar bônus: {e}", "error")
        else:
            self.log("✅ Bônus Diário já coletado hoje.", "info")
        return False

    def handle_new_quests(self, parser, game_data):
        """
        parser: Parser da página OVERVIEW (contém as Missões Principais/Quests)
        game_data: Dados da aldeia atual
        """
        self.log("🏅 Verificando Missões e Recompensas...", "info")
        
        village_id = game_data.get('village_id')
        storage_cap = game_data.get('storage', 0)
        res = {'wood': game_data['wood'], 'stone': game_data['stone'], 'iron': game_data['iron']}

        if village_id and self.client.csrf_token:
            headers = {
                "X-Requested-With": "XMLHttpRequest", "TribalWars-Ajax": "1",
                "Referer": f"{self.client.base_url}/game.php?village={village_id}&screen=overview",
                "Accept": "application/json, text/javascript, */*; q=0.01"
            }
            
            try:
                found_any = False

                # 1. MISSÕES PRINCIPAIS (Lê do parser da Overview passado como argumento)
                quests_to_complete = parser.get_quests()
                
                if quests_to_complete:
                    found_any = True
                    for qid in quests_to_complete:
                        self.log(f"🎯 Completando Missão Principal {qid}...", "warn")
                        
                        # --- CORREÇÃO BASEADA NO LOG DE REDE ---
                        # Endpoint: screen=api
                        # Params: ajaxaction=quest_complete, quest=ID, skip=false
                        # Body: h=TOKEN (injetado automaticamente pelo safe_post)
                        
                        self.client.safe_post(
                            "api", # Mudado de 'quests' para 'api'
                            {},    # Corpo vazio (o token 'h' entra aqui automaticamente)
                            params={
                                "ajaxaction": "quest_complete", 
                                "village": village_id,
                                "quest": qid,   # ID vai na URL agora
                                "skip": "false" # Obrigatório segundo o log
                            }, 
                            extra_headers=headers
                        )
                        time.sleep(random.uniform(0.5, 1.0))
                        self.log(f"✅ Missão {qid} completada!", "success")

                # 2. RECOMPENSAS / ITENS (Lê do Popup AJAX)
                resp = self.client.safe_get("new_quests", 
                    params={"village": village_id, "ajax": "quest_popup", "tab": "main-tab", "quest": "0", "h": self.client.csrf_token},
                    extra_headers=headers
                )
                
                if resp:
                    from core.game_parser import GameParser
                    p_popup = GameParser(resp.text)
                    
                    rewards = p_popup.get_new_quest_rewards()
                    
                    if rewards:
                        found_any = True
                        for r in rewards:
                            if r['status'] == 'locked': continue
                            
                            # Verifica estouro de armazém
                            if (res['wood'] + r['wood'] > storage_cap or 
                                res['stone'] + r['stone'] > storage_cap or 
                                res['iron'] + r['iron'] > storage_cap):
                                self.log(f"⚠️ {r['building']}: Armazém ficaria cheio. Pulando.", "warn")
                                continue
                            
                            self.log(f"📥 Coletando Recompensa: {r['building']}", "success")
                            self.client.safe_post("new_quests", {"reward_id": r['id']}, 
                                params={"ajax": "claim_reward", "village": village_id}, extra_headers=headers)
                            
                            res['wood'] += r['wood']; res['stone'] += r['stone']; res['iron'] += r['iron']
                            time.sleep(random.uniform(0.8, 1.5))
                            
                if not found_any:
                    self.log("ℹ️ Nenhuma missão ou recompensa pendente.", "info")

            except Exception as e:
                self.log(f"⚠️ Erro no sistema de missões: {e}", "error")