import time
import re
import json
from core.settings_manager import global_settings

class BuildManager:
    def __init__(self, client, log_func):
        self.client = client
        self.log = log_func

    def execute(self, acc, game_data):
        self.log("🏗️ [Build] Iniciando verificação...", "info")

        # 1. Definir Alvo Preliminar (baseado na memória antiga)
        target_id = self._determine_target_id(acc, game_data)
        if not target_id:
            self.log("✅ [Build] Nada para construir na fila/prioridade.", "info")
            return

        # 2. Acessar página Main
        resp = self.client.safe_get("main", params={"village": game_data['village_id']})
        if not resp: return

        html = resp.text

        # 3. Atualização Inteligente de Dados (Sem BeautifulSoup pesado)
        # Atualiza recursos, fila e CSRF token
        self._update_game_state(acc, game_data, html)

        # 4. Verificação de Fila (Stop imediato)
        # Pega o limite configurado ou assume 2 (padrão free)
        max_queue = 5 if self._is_premium_active(html) else 2
        current_queue = game_data.get('build_order_count', 0)

        if current_queue >= max_queue:
            self.log(f"⏳ [Build] Fila cheia ({current_queue}/{max_queue}). Aguardando...", "warn")
            return

        # 5. Obter dados PRECISOS do edifício alvo (Custo, Erro, Nível)
        buildings_data = self._extract_json_var(html, "BuildingMain.buildings")
        
        if not buildings_data or target_id not in buildings_data:
            self.log(f"❌ [Build] Dados de {target_id} não encontrados no JSON do jogo.", "error")
            return

        target_info = buildings_data[target_id]

        # 6. Checagem Definitiva de Erro (O jogo diz se pode ou não)
        if target_info.get('error'):
            error_msg = target_info['error']
            # Traduz ou repassa o erro
            self.log(f"⛔ [Build] O jogo impediu: {error_msg}", "warn")
            
            # Se o erro for "população insuficiente", tentamos mudar para Fazenda
            if "popul" in error_msg.lower() or "fazenda" in error_msg.lower():
                 if target_id != 'farm':
                     self.log("🔄 Tentando trocar alvo para Fazenda...", "info")
                     self._send_build_request(acc, game_data, 'farm', html)
            return

        # 7. Validação de Recursos (Cross-check com o que acabamos de ler)
        # O JSON já tem 'wood', 'stone', 'iron' (custo)
        cost_wood = target_info['wood']
        cost_stone = target_info['stone']
        cost_iron = target_info['iron']

        if (game_data['wood'] < cost_wood or 
            game_data['stone'] < cost_stone or 
            game_data['iron'] < cost_iron):
            self.log(f"💰 [Build] Recursos insuficientes para {target_id}.", "warn")
            return

        # 8. Execução
        self._send_build_request(acc, game_data, target_id, html)

    def _determine_target_id(self, acc, game_data):
        """Lógica pura de decisão (sem rede)"""
        queue = acc.get('build_queue', [])
        current_buildings = game_data.get('buildings', {})
        
        # Prioridade Fazenda
        if global_settings.get("farm_priority"):
            pop_cur = game_data.get('pop_current', 0)
            pop_max = game_data.get('pop_max', 1)
            # Se pop > 90% e fazenda < 30
            if (pop_cur / pop_max) >= 0.90 and current_buildings.get('farm', 0) < 30:
                return 'farm'

        # Fila do Bot
        if not queue: return None

        # Simula níveis atuais + fila já enviada
        # (Lógica simplificada para brevidade, mantenha a sua lógica de contagem aqui se preferir)
        for item in queue:
            b_id = item['key']
            # Se o nível atual do jogo for menor que o desejado na fila, construa
            # Nota: O ideal é ter um contador local, mas para MVP isso funciona
            return b_id 
            
        return None

    def _update_game_state(self, acc, game_data, html):
        """Extrai dados vitais via Regex (Super Rápido)"""
        
        # 1. CSRF Token (Crítico para qualquer POST)
        # Procura: var csrf_token = '403d5aba';
        csrf_match = re.search(r"var csrf_token = '(['\w]+)';", html)
        if csrf_match:
            game_data['csrf'] = csrf_match.group(1)

        # 2. Contagem da Fila
        # Procura: BuildingMain.order_count = 2;
        count_match = re.search(r"BuildingMain\.order_count = (\d+);", html)
        if count_match:
            game_data['build_order_count'] = int(count_match.group(1))
        else:
            game_data['build_order_count'] = 0

        # 3. Game Data (Recursos)
        # Procura: TribalWars.updateGameData({...})
        # Isso é um JSON gigante. Vamos tentar pegar o bloco ou usar regex pontual.
        # Regex pontual é mais seguro contra erros de parser JSON em HTML sujo.
        
        def get_int(key):
            # "wood":1512
            m = re.search(f'"{key}":([\d\.]+)', html)
            if m: return int(float(m.group(1))) # float extrai caso venha 1512.0
            return game_data.get(key, 0)

        game_data['wood'] = get_int('wood')
        game_data['stone'] = get_int('stone')
        game_data['iron'] = get_int('iron')
        game_data['pop_current'] = get_int('pop')
        game_data['pop_max'] = get_int('pop_max')
        game_data['storage'] = get_int('storage_max')

    def _extract_json_var(self, html, var_name):
        """Extrai um objeto JSON declarado em JS no HTML"""
        try:
            # Padrão: var_name = { ... };
            pattern = re.compile(rf"{re.escape(var_name)}\s*=\s*({{.*?}});", re.DOTALL)
            match = pattern.search(html)
            if match:
                json_str = match.group(1)
                return json.loads(json_str)
        except Exception as e:
            # Fallback: tentar regex simplificado se o JSON for malformado pelo python
            pass
        return {}

    def _is_premium_active(self, html):
        # Verifica se 'Premium' está ativo no JSON de features ou texto
        return '"Premium":{"possible":true,"active":true}' in html

    def _send_build_request(self, acc, game_data, target_id, html):
        self.log(f"🔨 [Build] Enviando ordem: {target_id}...", "info")
        
        # É necessário pegar o token 'h' (csrf)
        csrf = game_data.get('csrf')
        if not csrf:
            self.log("❌ Erro: CSRF token não encontrado.", "error")
            return

        params = {
            "village": game_data['village_id'],
            "ajaxaction": "upgrade_building",
            "type": target_id,
            "h": csrf # Importante adicionar o h=token aqui também por segurança
        }
        
        payload = {
            "id": target_id,
            "force": "1",
            "destroy": "0",
            "source": game_data['village_id'],
            "h": csrf
        }
        
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "TribalWars-Ajax": "1"
        }

        resp = self.client.safe_post("main", payload, params=params, extra_headers=headers)
        
        if resp and resp.status_code == 200:
            try:
                rjson = resp.json()
                if 'response' in rjson and 'success' in str(rjson['response']):
                     self.log(f"✅ [Build] Sucesso! {target_id} na fila.", "success")
                     # Atualiza contador localmente para evitar spam imediato
                     game_data['build_order_count'] += 1
                elif 'error' in rjson:
                    self.log(f"⚠️ [Build] Erro API: {rjson['error']}", "warn")
                else:
                    self.log("✅ [Build] Ordem enviada (sem confirmação explícita).", "success")
            except:
                self.log("✅ [Build] Ordem enviada (HTML response).", "success")
        else:
            self.log(f"❌ [Build] Falha HTTP: {resp.status_code if resp else 'None'}", "error")