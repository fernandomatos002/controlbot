from bs4 import BeautifulSoup
import re
import json

class GameParser:
    def __init__(self, html_content):
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.html = html_content

    def get_building_queue_count(self, building_name):
        """Conta ordens (Unidade ativa + Fila de espera) baseado no HTML fornecido."""
        count = 0
        try:
            # 1. Busca o Wrapper (O container geral da fila desse prédio)
            # Ex: id="trainqueue_wrap_barracks"
            wrapper = self.soup.find(id=f'trainqueue_wrap_{building_name}')
            
            if wrapper:
                # 2. Conta a unidade ATIVA (treinando agora)
                # Ela possui a classe "lit"
                active = wrapper.find_all('tr', class_='lit')
                count += len(active)
                
                # 3. Conta as unidades em ESPERA (na fila)
                # Elas possuem a classe "sortable_row"
                queued = wrapper.find_all('tr', class_='sortable_row')
                count += len(queued)
                
                # Debug (Opcional - aparecerá no terminal se quiser testar)
                # print(f"[DEBUG] {building_name}: Ativas={len(active)} + Fila={len(queued)} = Total {count}")
                
            return count

        except Exception as e:
            # print(f"Erro ao ler fila de {building_name}: {e}")
            return 0
    
    # --- SEGURANÇA E LOGIN ---
    def check_security(self):
        # 1. Detecção por Classes CSS do Bloqueio (O mais comum hoje)
        if self.soup.find(class_="bot-protection-row") or "bot-protection-row" in self.html:
            return 'captcha'
            
        if self.soup.find(class_="bot-protection-blur") or "bot-protection-blur" in self.html:
            return 'captcha'

        # 2. Detecção por Texto Visível (Caso mudem o CSS)
        if "Proteção contra Bots" in self.html or "Inicia a verificação" in self.html:
            return 'captcha'

        # 3. Detecção por Atributo no Body (Modo Forçado)
        # O jogo marca o body com data-bot-protect="forced" quando o captcha está ativo
        body = self.soup.find("body")
        if body and body.get("data-bot-protect") == "forced":
            return 'captcha'

        # 4. Detecção de Recaptcha Genérico ou Antigo (Mantido por segurança)
        if self.soup.find(id="bot_check") or "g-recaptcha" in self.html or "recaptcha-token" in self.html:
            return 'captcha'

        # 5. Verificação de Sessão Expirada
        if "sso/login" in str(self.soup) or self.soup.find("form", id="login_form"):
            return 'session_expired'
            
        return None

    # --- BÔNUS DIÁRIO ---
    def check_daily_bonus(self):
        if "DailyBonus.showDialog" in self.html: return True
        if "DailyBonus.init" in self.html: return True
        if "mode=daily_bonus" in self.html: return True
        return False

    def get_daily_bonus_day(self):
        try:
            pattern = r'"day"\s*:\s*(\d+)\s*,\s*"is_locked"\s*:\s*false\s*,\s*"is_collected"\s*:\s*false'
            match = re.search(pattern, self.html)
            if match: return match.group(1)
        except: pass
        return None

    # --- UTILITÁRIOS JSON ---
    def _extract_json_payload(self, start_marker, source=None):
        text_to_search = source if source else self.html
        start_idx = text_to_search.find(start_marker)
        if start_idx == -1: return None
        
        subset = text_to_search[start_idx:]
        match = re.search(r'[\[\{]', subset)
        if not match: return None
        
        json_start = start_idx + match.start()
        opening_char = text_to_search[json_start]
        closing_char = '}' if opening_char == '{' else ']'
        
        brace_count = 0
        json_str = ""
        started = False
        
        for i in range(json_start, len(text_to_search)):
            char = text_to_search[i]
            if char == opening_char:
                brace_count += 1
                started = True
            elif char == closing_char:
                brace_count -= 1
            
            json_str += char
            
            if started and brace_count == 0:
                break
        
        try: 
            return json.loads(json_str)
        except: 
            return None

    # --- DADOS PRINCIPAIS DO JOGO ---
    def get_game_data_from_json(self):
        data = {
            'wood': 0, 'stone': 0, 'iron': 0, 'storage': 0, 
            'pop_current': 0, 'pop_max': 0, 'village_id': None,
            'buildings': {}
        }
        
        game_data = None

        try:
            full_json = json.loads(self.html)
            if 'game_data' in full_json:
                game_data = full_json['game_data']
            elif 'response' in full_json and 'game_data' in full_json['response']:
                game_data = full_json['response']['game_data']
        except: pass

        if not game_data:
            game_data = self._extract_json_payload('TribalWars.updateGameData')

        if not game_data:
            try:
                pattern = r'TribalWars\.updateGameData\s*\(\s*(\{.*?\})\s*\)'
                match = re.search(pattern, self.html, re.DOTALL)
                if match: game_data = json.loads(match.group(1))
            except: pass

        if game_data:
            try:
                village = game_data.get('village', game_data) 
                
                data['wood'] = int(float(village.get('wood', 0)))
                data['stone'] = int(float(village.get('stone', 0)))
                data['iron'] = int(float(village.get('iron', 0)))
                data['storage'] = int(float(village.get('storage_max', 0)))
                data['pop_current'] = int(float(village.get('pop', 0)))
                data['pop_max'] = int(float(village.get('pop_max', 0)))
                data['village_id'] = int(village.get('id', 0))
                
                raw_buildings = village.get('buildings', {})
                for b_name, b_level in raw_buildings.items():
                    try: data['buildings'][b_name] = int(b_level)
                    except: data['buildings'][b_name] = 0
                
                return data
            except Exception as e:
                print(f"Erro parser game_data: {e}")
                pass

        return self.get_village_data()

    def get_village_data(self):
        data = {'buildings': {}} 
        try:
            wood = self.soup.find(id="wood")
            stone = self.soup.find(id="stone")
            iron = self.soup.find(id="iron")
            storage = self.soup.find(id="storage")
            
            data['wood'] = int(wood.text.replace('.', '')) if wood else 0
            data['stone'] = int(stone.text.replace('.', '')) if stone else 0
            data['iron'] = int(iron.text.replace('.', '')) if iron else 0
            data['storage'] = int(storage.text.replace('.', '')) if storage else 0

            pop_current = self.soup.find(id="pop_current_label")
            pop_max = self.soup.find(id="pop_max_label")
            
            data['pop_current'] = int(pop_current.text) if pop_current else 0
            data['pop_max'] = int(pop_max.text) if pop_max else 0
        except: pass 
        return data

    def get_points(self):
        try:
            rank_el = self.soup.find(id="rank_points")
            if rank_el: return int(rank_el.text.replace('.', ''))
        except: pass
        return 0

    def get_incoming_attacks(self):
        try:
            incoming_span = self.soup.find("span", id="incomings_amount")
            if incoming_span: return int(incoming_span.text.strip())
        except: pass
        return 0

    # --- MISSÕES PRINCIPAIS (Quests) ---
    def get_quests(self):
        """
        Retorna IDs das missões principais prontas para completar.
        Usa Regex para ser mais robusto na extração do JSON de Quests.setQuestData.
        """
        completable_quests = []
        quests_data = None

        # 1. Tenta extrair usando Regex (Mais seguro)
        try:
            # Procura por Quests.setQuestData({...});
            pattern = r'Quests\.setQuestData\s*\(\s*(\{.*?\})\s*\);'
            match = re.search(pattern, self.html, re.DOTALL)
            if match:
                quests_data = json.loads(match.group(1))
        except: 
            pass

        # 2. Fallback: Extrator antigo
        if not quests_data:
            quests_data = self._extract_json_payload('Quests.setQuestData')

        if quests_data:
            for qid, qdata in quests_data.items():
                if isinstance(qdata, dict):
                    # Critérios para Missão Completa
                    is_finished = (
                        qdata.get('finished') == True or 
                        qdata.get('finished') == 1 or
                        qdata.get('state') == 'finished'
                    )
                    
                    # Critérios para Missão NÃO Coletada (closed deve ser false/null)
                    # Se 'closed' não existe, assume false
                    is_closed = qdata.get('closed', False)
                    
                    if is_finished and not is_closed:
                        completable_quests.append(str(qid))
        
        return list(set(completable_quests))

    # --- RECOMPENSAS (RewardSystem) ---
    def get_new_quest_rewards(self):
        rewards_found = []
        candidates = []
        html_context = self.html
        
        try:
            json_response = json.loads(self.html)
            if isinstance(json_response, dict) and 'response' in json_response:
                response_obj = json_response['response']
                if 'dialog' in response_obj:
                    html_context = response_obj['dialog']
                elif isinstance(response_obj, str):
                    html_context = response_obj
        except: pass 

        rs_data = self._extract_json_payload('RewardSystem.setRewards', source=html_context)
        if isinstance(rs_data, list): candidates.append({"rewards": rs_data})

        json_rewards_list = self._extract_json_payload('"rewards"', source=html_context)
        if isinstance(json_rewards_list, list): candidates.append({"rewards": json_rewards_list})

        for data in candidates:
            rewards_list = data.get('rewards', [])
            if isinstance(rewards_list, list):
                for item in rewards_list:
                    reward_content = item.get('reward', {})
                    if item.get('status') == 'unlocked' or item.get('claimable'):
                        rewards_found.append({
                            'id': str(item.get('id')),
                            'status': 'unlocked',
                            'building': item.get('building', 'Missão'),
                            'wood': reward_content.get('wood', 0),
                            'stone': reward_content.get('stone', 0),
                            'iron': reward_content.get('iron', 0)
                        })

        if not rewards_found:
            matches = re.findall(r'RewardSystem\.claimReward\(\s*(\d+)', html_context)
            current_ids = [r['id'] for r in rewards_found]
            for rid in matches:
                if str(rid) not in current_ids:
                    rewards_found.append({
                        'id': str(rid),
                        'status': 'unlocked',
                        'building': 'Recompensa (Auto)',
                        'wood': 0, 'stone': 0, 'iron': 0
                    })
                    current_ids.append(str(rid))

        return rewards_found

    # --- RECRUTAMENTO ---
    def get_troop_data(self):
        data = {}
        known_units = [
            'spear', 'sword', 'axe', 'archer', 'spy', 
            'light', 'marcher', 'heavy', 'ram', 'catapult', 'snob'
        ]

        for u in known_units:
            data[u] = {'available': 0, 'training': 0, 'total': 0}

        recruit_inputs = self.soup.find_all('input', class_='recruit_unit')
        
        for inp in recruit_inputs:
            unit_id = inp.get('name')
            if unit_id in data:
                try:
                    row = inp.find_parent('tr')
                    if row:
                        cells = row.find_all('td')
                        if len(cells) > 2:
                            qty_text = cells[2].text.strip()
                            if '/' in qty_text:
                                avail = int(qty_text.split('/')[0])
                                data[unit_id]['available'] = avail
                except: pass

        queue_wraps = self.soup.find_all('div', class_='trainqueue_wrap')
        for wrap in queue_wraps:
            rows = wrap.find_all('tr')
            for row in rows:
                sprite = row.find('div', class_='unit_sprite_smaller')
                if sprite:
                    classes = sprite.get('class', [])
                    unit_id = classes[-1] if classes else None
                    
                    if unit_id in data:
                        try:
                            cell_text = row.find('td').text.strip()
                            match = re.search(r'^(\d+)\s', cell_text)
                            if match:
                                amount = int(match.group(1))
                                data[unit_id]['training'] += amount
                        except: pass

        for u in data:
            data[u]['total'] = data[u]['available'] + data[u]['training']

        return data

    def get_train_form_action(self):
        form = self.soup.find('form', id='train_form')
        if form and form.get('action'):
            return form.get('action')
        return None

    # --- COLETA (SCAVENGER) ---
    def get_scavenge_data(self):
        try:
            village_data = self._extract_json_payload('var village =')
            global_options = self._extract_json_payload('new ScavengeScreen(')

            if not village_data or not global_options:
                return None

            result = {
                'levels': {},
                'has_rally_point': village_data.get('has_rally_point', False),
                'home_units': village_data.get('unit_counts_home', {})
            }

            for key, opt_def in global_options.items():
                village_opt = village_data['options'].get(key, {})
                result['levels'][key] = {
                    'id': int(key),
                    'name': opt_def.get('name'),
                    'is_locked': village_opt.get('is_locked', True),
                    'unlock_cost': opt_def.get('unlock_cost', {'wood':0, 'stone':0, 'iron':0}),
                    'unlock_time': village_opt.get('unlock_time'), 
                    'scavenging_squad': village_opt.get('scavenging_squad', None) 
                }
            return result
        except: return None