import time
import math
import json
import random

# Pesos para equalizar o tempo de retorno (15-6-3-2)
SCAVENGE_WEIGHTS = { 1: 15, 2: 6, 3: 3, 4: 2 }

# Capacidade de Carga
UNIT_CARRY = {
    "spear": 25, "sword": 15, "axe": 10, "archer": 10,
    "spy": 0, "light": 80, "marcher": 50, "heavy": 50, "knight": 100
}

class ScavengeManager:
    def __init__(self, client, log_func):
        self.client = client
        self.log = log_func

    def execute(self, acc, game_data):
        village_id = game_data.get('village_id')
        if not village_id: return

        # 1. Acessa a tela
        resp = self.client.safe_get("place", params={"mode": "scavenge", "village": village_id})
        if not resp: return

        from core.game_parser import GameParser
        parser = GameParser(resp.text)
        scavenge_data = parser.get_scavenge_data()
        
        # 2. Verifica erro de leitura
        if not scavenge_data:
            if "ScavengeScreen" not in resp.text:
                self.log("ℹ️ Mundo sem coleta disponível.", "info")
            else:
                self.log("⚠️ Erro ao ler dados de coleta.", "error")
            return

        # --- SALVAR ESTADO NA CONTA (CORRIGIDO) ---
        try:
            levels_info = {}
            active_end_times = [] # Lista de todos os horários de fim (retorno ou desbloqueio)

            for key, lvl in scavenge_data['levels'].items():
                status = "idle" 
                end_time = None
                
                if lvl.get('is_locked'):
                    if lvl.get('unlock_time'):
                        status = "unlocking"
                        end_time = lvl.get('unlock_time')
                    else:
                        status = "locked"
                elif lvl.get('scavenging_squad'):
                    status = "scavenging"
                    end_time = lvl['scavenging_squad'].get('return_time')
                
                # SE TEM TEMPO RODANDO, ADICIONA NA LISTA DE ATIVOS
                if end_time:
                    active_end_times.append(int(end_time))

                levels_info[key] = {
                    "id": key,
                    "status": status,
                    "end_time": end_time
                }
            
            # Salva na conta
            acc['scavenge_data'] = {
                "levels": levels_info,
                # Pega o maior tempo entre coletas E desbloqueios
                "max_return": max(active_end_times) if active_end_times else None,
                "updated_at": time.time()
            }
        except Exception as e:
            print(f"Erro ao salvar estado da coleta: {e}")

        # ... (O RESTANTE DA LÓGICA PERMANECE IGUAL AO ANTERIOR) ...
        # Copie o resto da função execute (passo 3 em diante) do código anterior ou mantenha o que você já tem.
        # A alteração crítica foi apenas no bloco try/except acima.
        
        # 3. Verifica Desbloqueios e Monta Lista de Disponíveis
        levels = scavenge_data['levels']
        unlocked_ids = [] 
        
        for key in sorted(levels.keys(), key=lambda x: int(x)):
            lvl = levels[key]
            if lvl['is_locked']:
                if lvl.get('unlock_time'): break 
                
                cost = lvl['unlock_cost']
                if (game_data['wood'] >= cost['wood'] and 
                    game_data['stone'] >= cost['stone'] and 
                    game_data['iron'] >= cost['iron']):
                    
                    self.log(f"🔓 Desbloqueando Nível {key}...", "warn")
                    if self._unlock_option(lvl['id'], village_id):
                        game_data['wood'] -= cost['wood']
                        game_data['stone'] -= cost['stone']
                        game_data['iron'] -= cost['iron']
                        time.sleep(1)
                    break 
                else:
                    break 
            else:
                unlocked_ids.append(lvl['id'])

        if not unlocked_ids: return

        busy_levels = [id for id in unlocked_ids if levels[str(id)]['scavenging_squad']]
        if len(busy_levels) > 0:
            if len(busy_levels) == len(unlocked_ids):
                self.log("✅ Coletas em andamento.", "success")
            else:
                self.log(f"⏳ Aguardando retorno ({len(busy_levels)}/{len(unlocked_ids)} ocupados).", "info")
            return

        home_units = scavenge_data.get('home_units', {})
        world_units = list(home_units.keys())
        
        available_troops = {}
        useful_units = ["spear", "sword", "axe", "archer", "light", "marcher", "heavy", "knight"]
        
        for u in useful_units:
            if u in home_units: 
                count = int(home_units.get(u, 0))
                if count > 0: available_troops[u] = count

        if not available_troops:
            self.log("ℹ️ Sem tropas para enviar.", "info")
            return

        final_distribution = {}
        active_options_pool = sorted(unlocked_ids)
        
        while active_options_pool:
            total_weight = sum(SCAVENGE_WEIGHTS[opt_id] for opt_id in active_options_pool)
            if total_weight == 0: break

            temp_distribution = {opt_id: {} for opt_id in active_options_pool}
            failed_min_check = False
            
            for unit, count in available_troops.items():
                remaining = count
                for i, opt_id in enumerate(active_options_pool[:-1]):
                    weight = SCAVENGE_WEIGHTS[opt_id]
                    amount = int(count * (weight / total_weight))
                    if amount > 0:
                        temp_distribution[opt_id][unit] = amount
                        remaining -= amount
                
                last_opt = active_options_pool[-1]
                if remaining > 0:
                    temp_distribution[last_opt][unit] = remaining

            for opt_id, squad in temp_distribution.items():
                if sum(squad.values()) < 10:
                    failed_min_check = True
                    break
            
            if failed_min_check:
                active_options_pool.pop() 
                continue
            else:
                final_distribution = temp_distribution
                break

        if not final_distribution:
            self.log("ℹ️ Tropas insuficientes para o mínimo.", "info")
            return

        for opt_id, troops in final_distribution.items():
            if not troops: continue
            
            post_data = {}
            if self.client.csrf_token:
                post_data['h'] = self.client.csrf_token

            carry_max = sum(troops[u] * UNIT_CARRY.get(u, 0) for u in troops)
            
            prefix = "squad_requests[0]"
            
            post_data[f"{prefix}[village_id]"] = str(village_id)
            post_data[f"{prefix}[option_id]"] = str(opt_id)
            post_data[f"{prefix}[use_premium]"] = "false"
            post_data[f"{prefix}[candidate_squad][carry_max]"] = str(carry_max)
            
            troop_log = []
            for u in world_units:
                qtd = troops.get(u, 0)
                post_data[f"{prefix}[candidate_squad][unit_counts][{u}]"] = str(qtd)
                if qtd > 0: troop_log.append(f"{u}:{qtd}")
            
            self.log(f"🪓 Nv{opt_id}: Enviando {','.join(troop_log)}...", "info")

            params = {
                "village": village_id,
                "screen": "scavenge_api",
                "ajaxaction": "send_squads"
            }
            extra_headers = {"X-Requested-With": "XMLHttpRequest", "TribalWars-Ajax": "1"}

            resp = self.client.safe_post("scavenge_api", post_data, params=params, extra_headers=extra_headers)
            
            success = False
            if resp and resp.status_code == 200:
                try:
                    rjson = resp.json()
                    if rjson.get('error'):
                         self.log(f"❌ Erro Nv{opt_id}: {rjson.get('error')}", "error")
                    else:
                        squad_res = rjson.get('squad_responses', [])
                        if squad_res and squad_res[0].get('success'):
                            success = True
                        elif '"success":true' in json.dumps(rjson) or '"success": true' in json.dumps(rjson):
                            success = True
                        
                        if success:
                            self.log(f"✅ Nv{opt_id} enviado com sucesso.", "success")
                        else:
                            self.log(f"⚠️ Nv{opt_id} resposta: {rjson}", "warn")
                except:
                    self.log(f"❌ Erro JSON Nv{opt_id}", "error")
            else:
                self.log(f"❌ Falha HTTP Nv{opt_id}", "error")

            time.sleep(random.uniform(0.8, 1.5))

    def _unlock_option(self, option_id, village_id):
        params = {
            "village": village_id, 
            "screen": "scavenge_api",
            "ajaxaction": "start_unlock"
        }
        data = {
            "village_id": village_id,
            "option_id": option_id
        }
        if self.client.csrf_token:
            data['h'] = self.client.csrf_token

        extra_headers = {"X-Requested-With": "XMLHttpRequest", "TribalWars-Ajax": "1"}
        
        resp = self.client.safe_post("scavenge_api", data, params=params, extra_headers=extra_headers)
        if resp and resp.status_code == 200:
            try:
                if not resp.json().get('error'): return True
            except: pass
        return False