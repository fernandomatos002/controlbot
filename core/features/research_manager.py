import time
import random
import re
import json
from core.settings_manager import global_settings

class ResearchManager:
    def __init__(self, bot_controller, log_func=None):
        self.bot = bot_controller
        self.external_log = log_func
        self.running = False

        # Mapa para corrigir nomes caso o usuário coloque em PT-BR
        self.name_map = {
            "lanceiro": "spear", "espadachim": "sword", "barbaro": "axe", "bárbaro": "axe",
            "arqueiro": "archer", "explorador": "spy", "cavalaria leve": "light", "cav leve": "light",
            "arqueiro a cavalo": "marcher", "cavalaria pesada": "heavy", "cav pesada": "heavy",
            "ariete": "ram", "aríete": "ram", "catapulta": "catapult", "nobre": "snob"
        }

    def log(self, msg, level="info"):
        if self.external_log:
            self.external_log(f"[Pesquisa] {msg}", level)
        elif hasattr(self.bot, 'log'):
            self.bot.log(f"[Pesquisa] {msg}", level)
        else:
            print(f"[Pesquisa] {msg}")

    def execute(self, acc, game_data):
        # 1. Obter Lista de Prioridade Original
        raw_priority = global_settings.get("research_priority", [])
        if not raw_priority:
            raw_priority = acc.get('research_priority', [])
        
        if not raw_priority:
            self.log("Lista de prioridade vazia!", "warning")
            return

        # --- LÓGICA DE TRADUÇÃO INTERNA ---
        priority_list = []
        for item in raw_priority:
            # Procura qualquer coisa dentro de parênteses: (id)
            match = re.search(r'\((.*?)\)', item)
            if match:
                item_id = match.group(1).lower().strip()
                priority_list.append(item_id)
            else:
                # Fallback: se não tiver parêntese, usa o mapa de nomes PT-BR
                clean_item = item.lower().strip()
                priority_list.append(self.name_map.get(clean_item, clean_item))

        # Dados básicos da aldeia
        village_id = None
        
        if isinstance(game_data, dict):
            # Formato 1: {'village': {'id': ...}}
            if 'village' in game_data and isinstance(game_data['village'], dict):
                village_id = game_data['village'].get('id')
            # Formato 2: {'id': ...} (direto)
            elif 'id' in game_data:
                village_id = game_data.get('id')
            # Formato 3: procura em acc
            elif 'village_id' in game_data:
                village_id = game_data.get('village_id')
        
        # Último recurso: tenta pegar de acc
        if not village_id and isinstance(acc, dict):
            village_id = acc.get('village_id') or acc.get('id')
        
        if not village_id:
            self.log(f"Village ID não encontrado! game_data: {list(game_data.keys()) if isinstance(game_data, dict) else type(game_data)}", "error")
            self.log(f"acc: {list(acc.keys()) if isinstance(acc, dict) else type(acc)}", "error")
            return
        
        village_id = int(village_id)
        
        # 2. CORREÇÃO: Garantir que base_url termina com /
        base_url = self.bot.base_url
        if not base_url.endswith('/'):
            base_url += '/'
        
        # 3. Acessa a página (GET)
        url = f"{base_url}game.php?village={village_id}&screen=smith"
        
        try:
            response = self.bot.session.get(url, timeout=15)
            html = response.text
        except Exception as e:
            self.log(f"❌ Erro de conexão: {e}", "error")
            return

        # 4. Extração de CSRF Token
        csrf_token = None
        # Tenta pegar da variável JS direta
        match_csrf = re.search(r"var csrf_token = '([a-f0-9]+)';", html)
        if match_csrf:
            csrf_token = match_csrf.group(1)
        else:
            # Fallback: tenta TribalWars.updateGameData
            match_csrf_json = re.search(r'"csrf"\s*:\s*"([a-f0-9]+)"', html)
            if match_csrf_json:
                csrf_token = match_csrf_json.group(1)
        
        if not csrf_token:
            self.log("Token CSRF não encontrado!", "error")
            return

        # 5. Extração de Recursos
        current_wood, current_stone, current_iron = 0, 0, 0
        
        match_gd = re.search(r'TribalWars\.updateGameData\(({.*?})\);', html, re.DOTALL)
        if match_gd:
            try:
                gd_json = json.loads(match_gd.group(1))
                current_wood = int(gd_json.get('village', {}).get('wood', 0))
                current_stone = int(gd_json.get('village', {}).get('stone', 0))
                current_iron = int(gd_json.get('village', {}).get('iron', 0))
            except Exception as e:
                self.log(f"Erro ao ler recursos do JSON: {e}", "error")
                return
        else:
            self.log("Game data não encontrado", "error")
            return

        # 6. Extração de Tecnologias Disponíveis
        available_techs = {}
        match_tech = re.search(r'BuildingSmith\.techs\s*=\s*({.*?});', html, re.DOTALL)
        
        if match_tech:
            try:
                tech_data = json.loads(match_tech.group(1))
                available_techs = tech_data.get("available", {})
            except Exception as e:
                self.log(f"Erro ao ler JSON de tecnologias: {e}", "error")
                return
        else:
            self.log("Nenhuma tecnologia disponível ou Ferreiro não existe", "warning")
            return

        # 7. Loop de Tentativa de Pesquisa
        self.log(f"📋 Verificando {len(priority_list)} tecnologia(s) na lista", "info")
        
        for tech_id in priority_list:
            tech_info = available_techs.get(tech_id)
            
            if not tech_info:
                self.log(f"❌ {tech_id} não existe no jogo", "warn")
                continue

            # Verifica se já foi pesquisado (level atual >= 1)
            try:
                lvl = int(tech_info.get("level", 0))
                if lvl >= 1:
                    tech_name = tech_info.get('name', tech_id)
                    self.log(f"✅ {tech_name} já pesquisado (nível {lvl})", "info")
                    continue
            except:
                pass

            # Verifica se tem erro de requisito (ex: edifício faltando)
            if tech_info.get("error_level", False):
                tech_name = tech_info.get('name', tech_id)
                self.log(f"⚠️ {tech_name}: requisito faltando (ex: edifício não construído)", "warn")
                continue

            # Verifica se pode pesquisar
            can_research = tech_info.get("can_research", False)
            
            # Se não pode, identifica o motivo
            if not can_research:
                tech_name = tech_info.get('name', tech_id)
                
                # Verifica se falta edifício
                if tech_info.get("error_buildings", False):
                    # Tenta pegar o nome do edifício requerido
                    require = tech_info.get("require", {})
                    if require:
                        building_name = list(require.values())[0].get("name", "edifício")
                        building_level = list(require.values())[0].get("level", "?")
                        self.log(f"🏗️ {tech_name}: requer {building_name} nível {building_level}", "warn")
                    else:
                        self.log(f"🏗️ {tech_name}: requisito de edifício faltando", "warn")
                    continue
                
                # Se NÃO tem error_buildings, pode ser falta de recurso
                # Vamos verificar se aparece nos custos do HTML
                req_wood = tech_info.get("wood")
                req_stone = tech_info.get("stone")
                req_iron = tech_info.get("iron")
                
                if req_wood and req_stone and req_iron:
                    # Tem custos - provavelmente é falta de recurso
                    req_wood = int(req_wood)
                    req_stone = int(req_stone)
                    req_iron = int(req_iron)
                    
                    res_faltam = []
                    if current_wood < req_wood:
                        res_faltam.append(f"🌲 {req_wood - current_wood}")
                    if current_stone < req_stone:
                        res_faltam.append(f"🧱 {req_stone - current_stone}")
                    if current_iron < req_iron:
                        res_faltam.append(f"⛏️ {req_iron - current_iron}")
                    
                    if res_faltam:
                        self.log(f"⏳ {tech_name}: recursos insuficientes - faltam {' | '.join(res_faltam)}", "warn")
                        continue
                
                # Outro motivo desconhecido
                self.log(f"⏸️ {tech_name}: não disponível para pesquisa", "warn")
                continue

            # Verifica erro de fila ou recursos
            error_msg = tech_info.get("research_error")
            if error_msg:
                tech_name = tech_info.get('name', tech_id)
                
                if isinstance(error_msg, str):
                    # Verifica se é fila cheia
                    if "queue" in error_msg.lower() or "fila" in error_msg.lower():
                        self.log(f"⏸️ Fila de pesquisa cheia", "warning")
                        return
                    
                    # Verifica se é falta de recursos
                    if "recursos" in error_msg.lower() or "disponíveis" in error_msg.lower() or "available" in error_msg.lower():
                        # Calcula quanto falta
                        req_wood = int(tech_info.get("wood", 0))
                        req_stone = int(tech_info.get("stone", 0))
                        req_iron = int(tech_info.get("iron", 0))
                        
                        res_faltam = []
                        if current_wood < req_wood:
                            res_faltam.append(f"🌲 {req_wood - current_wood}")
                        if current_stone < req_stone:
                            res_faltam.append(f"🧱 {req_stone - current_stone}")
                        if current_iron < req_iron:
                            res_faltam.append(f"⛏️ {req_iron - current_iron}")
                        
                        if res_faltam:
                            self.log(f"⏳ {tech_name}: recursos insuficientes - faltam {' | '.join(res_faltam)}", "warn")
                        else:
                            self.log(f"⏳ {tech_name}: {error_msg}", "warn")
                        continue
                
                # Outro tipo de erro
                continue

            # ENCONTROU A PRÓXIMA DA LISTA (tem can_research = true)
            tech_name = tech_info.get('name', tech_id)
            self.log(f"🎯 Próxima prioridade: {tech_name}", "info")

            # PESQUISA!
            action_url = f"{base_url}game.php?village={village_id}&screen=smith&ajaxaction=research"
            
            payload = {
                "tech_id": tech_id,
                "source": str(village_id),
                "h": csrf_token
            }
            
            headers = {
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': url,
                'User-Agent': self.bot.session.headers.get('User-Agent', '')
            }

            try:
                r = self.bot.session.post(action_url, data=payload, headers=headers, timeout=10)
                
                if r.status_code == 200:
                    try:
                        resp_json = r.json()
                        
                        # Verifica se há erro explícito
                        if "error" in resp_json:
                            self.log(f"❌ Erro: {resp_json['error']}", "error")
                            return
                        
                        # Se tem game_data ou response, pesquisa foi aceita
                        if "game_data" in resp_json or "response" in resp_json:
                            self.log(f"✅ Pesquisa iniciada com sucesso", "success")
                            time.sleep(random.uniform(0.5, 1.5))
                            return
                        
                        # Fallback: se chegou aqui com 200, aceita como sucesso
                        self.log(f"✅ Pesquisa enviada", "success")
                        return
                        
                    except json.JSONDecodeError:
                        # Se não é JSON mas retornou 200, provavelmente funcionou
                        self.log(f"✅ Pesquisa iniciada", "success")
                        return
                else:
                    self.log(f"❌ Erro HTTP {r.status_code}", "error")
                    
            except Exception as e:
                self.log(f"❌ Erro na requisição: {e}", "error")
            
            return

        # Se chegou aqui, todas já foram pesquisadas
        self.log("✅ Todas as tecnologias da lista já foram Verificadas", "info")