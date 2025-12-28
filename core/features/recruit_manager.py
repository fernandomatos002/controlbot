import time
import re
import json
from core.settings_manager import global_settings

class RecruitManager:
    def __init__(self, client, log_func):
        self.client = client
        self.log = log_func

    def execute(self, acc, game_data):
        # 1. Verifica se tem metas configuradas
        targets = acc.get('recruit_targets', {})
        if not targets:
            return

        # 2. Acessa a tela de recrutamento
        self.log("⚔️ [Recruit] Verificando quartéis...", "info")
        resp = self.client.safe_get("train", params={"village": game_data['village_id']})
        if not resp: return

        html = resp.text
        
        # 3. Extração Cirúrgica de Dados (Regex/JSON)
        # Atualiza recursos, populaçao e pega o CSRF token
        self._update_game_data(acc, game_data, html)
        
        # Lê os custos exatos deste mundo (evita erros com arqueiros/paladinos)
        unit_costs = self._extract_unit_costs(html)
        if not unit_costs:
            self.log("❌ [Recruit] Não foi possível ler os custos das unidades.", "error")
            return

        # Lê quantas tropas já temos
        current_troops = self._extract_current_troops(html)
        
        # Lê o tamanho das filas (Quartel, Estábulo, Oficina)
        queues = self._extract_queue_counts(html)

        # 4. Planejamento do Recrutamento
        units_to_recruit = []
        active_buildings = set()

        # CLONE a fila atual para um contador local (simulação)
        # Isso garante que se adicionarmos uma ordem agora, o próximo loop já sabe
        virtual_queues = queues.copy() 

        UNIT_BUILDING_MAP = {
            'spear': 'barracks', 'sword': 'barracks', 'axe': 'barracks', 'archer': 'barracks',
            'spy': 'stable', 'light': 'stable', 'marcher': 'stable', 'heavy': 'stable',
            'ram': 'garage', 'catapult': 'garage'
        }

        for unit_id, target_data in targets.items():
            # (Leitura da config - igual ao anterior)
            if isinstance(target_data, int):
                target_total = target_data
                batch_size = 50
                queue_limit = 5
            else:
                target_total = int(target_data.get('total', 0))
                batch_size = int(target_data.get('batch', 50))
                queue_limit = int(target_data.get('limit_queue', 3))

            if target_total <= 0: continue

            have = current_troops.get(unit_id, 0)
            needed = target_total - have

            if needed > 0:
                building = UNIT_BUILDING_MAP.get(unit_id, 'barracks')
                
                # --- CORREÇÃO AQUI ---
                # Usamos 'virtual_queues' em vez de 'queues'
                curr_queue = virtual_queues.get(building, 0)
                
                if curr_queue >= queue_limit:
                    self.log(f"⏳ [Recruit] Fila do {building} cheia ({curr_queue}/{queue_limit}). Pulando {unit_id}.", "info")
                    continue

                active_buildings.add(building)
                
                amount = min(needed, batch_size)
                
                units_to_recruit.append({
                    'id': unit_id,
                    'amount': amount,
                    'building': building,
                    'cost': unit_costs.get(unit_id, {})
                })

                # --- INCREMENTO IMEDIATO ---
                # "Fingimos" que a fila aumentou para a próxima iteração
                virtual_queues[building] += 1 

        if not units_to_recruit:
            return

        # 5. Orçamento e Rateio
        # Divide os recursos disponíveis entre os prédios ativos
        avail_wood = game_data['wood']
        avail_stone = game_data['stone']
        avail_iron = game_data['iron']
        avail_pop = game_data['pop_max'] - game_data['pop_current']

        # Se houver construção pendente no Main, reserva 25% (Opcional)
        if global_settings.get("reserve_for_building", True) and acc.get('build_queue'):
            avail_wood *= 0.75
            avail_stone *= 0.75
            avail_iron *= 0.75

        num_active = len(active_buildings) if active_buildings else 1
        budget = {
            'wood': avail_wood / num_active,
            'stone': avail_stone / num_active,
            'iron': avail_iron / num_active
        }

        # 6. Cálculo Final e Preparação do Payload
        payload = {}
        log_msgs = []

        # Cache local para não estourar o orçamento se tiver várias unidades no mesmo prédio
        # Ex: Lança e Espada no Quartel. O orçamento é do Quartel.
        building_budgets = {b: budget.copy() for b in active_buildings}

        for task in units_to_recruit:
            u_id = task['id']
            b_name = task['building']
            cost = task['cost']
            
            # Se não temos dados de custo, ignora (segurança)
            if not cost: continue

            # Calcula máximo possível com o orçamento do prédio
            max_w = int(building_budgets[b_name]['wood'] // cost.get('wood', 99999))
            max_s = int(building_budgets[b_name]['stone'] // cost.get('stone', 99999))
            max_i = int(building_budgets[b_name]['iron'] // cost.get('iron', 99999))
            max_p = int(avail_pop // cost.get('pop', 1))

            final_amount = min(task['amount'], max_w, max_s, max_i, max_p)

            if final_amount > 0:
                payload[u_id] = final_amount
                log_msgs.append(f"{final_amount} {u_id}")
                
                # Deduz do orçamento local
                building_budgets[b_name]['wood'] -= final_amount * cost.get('wood', 0)
                building_budgets[b_name]['stone'] -= final_amount * cost.get('stone', 0)
                building_budgets[b_name]['iron'] -= final_amount * cost.get('iron', 0)
                avail_pop -= final_amount * cost.get('pop', 1)

        # 7. Envio (POST)
        if payload:
            self.log(f"⚔️ [Recruit] Treinando: {', '.join(log_msgs)}", "warn")
            self._send_recruit_request(game_data, payload)
        else:
            self.log("ℹ️ [Recruit] Sem recursos ou população suficiente.", "info")

    # =========================================================================
    # PARSERS (REGEX/JSON) - BLINDADOS
    # =========================================================================

    def _update_game_data(self, acc, game_data, html):
        """Lê recursos e CSRF token diretamente do HTML"""
        # CSRF Token
        csrf_match = re.search(r"var csrf_token = '(['\w]+)';", html)
        if csrf_match:
            game_data['csrf'] = csrf_match.group(1)

        # Resources (TribalWars.updateGameData)
        def get_val(key):
            m = re.search(f'"{key}":([\d\.]+)', html)
            return int(float(m.group(1))) if m else 0

        # Tentativa de ler do updateGameData que é mais seguro
        if "TribalWars.updateGameData" in html:
            game_data['wood'] = get_val('wood')
            game_data['stone'] = get_val('stone')
            game_data['iron'] = get_val('iron')
            game_data['pop_current'] = get_val('pop')
            game_data['pop_max'] = get_val('pop_max')

    def _extract_unit_costs(self, html):
        """Lê custos e verifica se a unidade está PESQUISADA/DISPONÍVEL"""
        costs = {}
        
        # Encontra o bloco JS das unidades
        block_match = re.search(r'unit_managers\.units\s*=\s*\{(.*?)\};', html, re.DOTALL)
        if not block_match:
            return None
        
        block = block_match.group(1)
        
        # Itera sobre cada unidade
        unit_pattern = re.compile(r'(?P<unit>\w+):\s*\{(.*?)\}', re.DOTALL)
        
        for match in unit_pattern.finditer(block):
            u_name = match.group('unit')
            props = match.group(2)
            
            # 1. VERIFICAÇÃO DE REQUISITOS (NOVO)
            # Procura por "requirements_met": true ou false
            req_match = re.search(r'requirements_met:\s*(true|false)', props)
            if req_match and req_match.group(1) == 'false':
                # Se não estiver pesquisada ou faltar edifício, ignora essa unidade
                # self.log(f"Unidade {u_name} ignorada (não pesquisada).", "debug")
                continue

            # 2. Extração de Custos
            def get_prop(p_name):
                m = re.search(rf"{p_name}:\s*(\d+)", props)
                return int(m.group(1)) if m else 0
            
            costs[u_name] = {
                'wood': get_prop('wood'),
                'stone': get_prop('stone'),
                'iron': get_prop('iron'),
                'pop': get_prop('pop')
            }
        
        return costs

    def _extract_current_troops(self, html):
        """Lê a quantidade atual de tropas dos links 'set_max'"""
        # Padrão: <a id="spear_0_a" ...>(123)</a>
        troops = {}
        pattern = re.compile(r'id="(\w+)_0_a"[^>]*>\((\d+)\)<')
        
        for match in pattern.finditer(html):
            unit = match.group(1)
            count = int(match.group(2))
            troops[unit] = count
            
        return troops

    def _extract_queue_counts(self, html):
        """Conta ordens TOTAIS (Ativa + Fila de Espera) para cada edifício"""
        queues = {'barracks': 0, 'stable': 0, 'garage': 0}
        
        for building in queues.keys():
            # Procura o container da fila deste edifício
            # Ex: id="trainqueue_wrap_barracks"
            start_marker = f'id="trainqueue_wrap_{building}"'
            start_idx = html.find(start_marker)
            
            if start_idx != -1:
                # Pega o conteúdo até o fim da tabela
                end_idx = html.find('</table>', start_idx)
                if end_idx != -1:
                    block = html[start_idx:end_idx]
                    
                    # 1. Conta as ordens em ESPERA (IDs trainorder_X)
                    queued = block.count('id="trainorder_')
                    
                    # 2. Conta a ordem ATIVA (classe "lit")
                    # O jogo usa <tr class="lit"> para a unidade treinando agora
                    # Verificamos class="lit" com aspas para não confundir com lit-item
                    active = 1 if 'class="lit"' in block or "class='lit'" in block else 0
                    
                    queues[building] = queued + active

        return queues

    def _send_recruit_request(self, game_data, payload):
        csrf = game_data.get('csrf')
        if not csrf: return

        # URL correta de recrutamento (action=train)
        url = f"game.php?village={game_data['village_id']}&screen=train&action=train&mode=train"
        
        # Adiciona o token ao payload e query params
        payload['h'] = csrf
        
        # Ajuste de URL completa
        full_url = f"{self.client.base_url}/{url}"
        
        # Headers essenciais
        headers = self.client.headers.copy()
        headers["Referer"] = f"{self.client.base_url}/game.php?village={game_data['village_id']}&screen=train"

        try:
            self.client.session.post(full_url, data=payload, headers=headers)
            self.log("✅ [Recruit] Requisição enviada com sucesso.", "success")
            time.sleep(1) # Delay leve
        except Exception as e:
            self.log(f"❌ [Recruit] Falha de conexão: {e}", "error")