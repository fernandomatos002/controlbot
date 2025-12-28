import time
import re
from core.account_manager import account_manager
from core.features.cluster.inviter import ClusterInviter 
from core.features.cluster.accepter import ClusterAccepter
from core.features.cluster.calculator import cluster_calculator
from core.features.cluster.realocator import cluster_realocator
from core.request_engine import GameClient

class ClusterController:
    def __init__(self):
        self.stop_flag = False
        self.log_callback = None

    def set_logger(self, callback):
        self.log_callback = callback

    def log(self, msg, type="info"):
        if self.log_callback: self.log_callback(msg, type)
        print(f"[CLUSTER] {msg}")

    def execute_operation(self, master_target, pool_ids, is_manual_master=False):
        """
        Fluxo Cluster Seguro:
        1. Cálculo
        2. Convites
        3. Aceites (Cascata)
        4. TRAVA DE SEGURANÇA (Aguarda Master aceitar)
        5. Realocação
        """
        self.stop_flag = False
        
        # --- 1. SETUP ---
        master_acc = account_manager.get_account(master_target)
        if not master_acc and not is_manual_master:
            self.log("Erro: Conta Master interna não encontrada.", "error")
            return
        
        master_username = master_acc['username'] if master_acc else master_target
        pool_accounts = [account_manager.get_account(aid) for aid in pool_ids if account_manager.get_account(aid)]
        pool_names = [acc['username'] for acc in pool_accounts]

        # --- 2. CÁLCULO BASE 5 ---
        calc_result = cluster_calculator.calculate(len(pool_names) + 1, master_username, pool_names)
        if not calc_result["is_valid"]:
            self.log(f"Erro no cálculo: {calc_result['message']}", "error")
            return
        
        tree = calc_result["structure"]
        relations = tree["relations"]
        
        self.log(f"🚀 Iniciando Cluster (Base 5) com {tree['total_used']} contas.", "process")
        self.log(cluster_calculator.visualize(tree))

        # --- FASE 1: CONVITES ---
        inviter = ClusterInviter(self.log)
        for acc in pool_accounts:
            if self.stop_flag: break
            target_parent = relations.get(acc['username'])
            if target_parent:
                self.log(f"📧 {acc['username']} enviando convite para {target_parent}...", "info")
                inviter.invite_player(acc, target_parent)
                time.sleep(1.5)

        # --- FASE 2: ACEITES (Internos) ---
        accepter = ClusterAccepter(self.log)
        
        # Se Master é interno, ele aceita. Se não, pulamos.
        if not is_manual_master:
            self.log(f"📥 Master {master_username} aceitando generais...", "process")
            targets = [gen['name'] for gen in tree['generals']]
            accepter.accept_all(master_acc, target_players=targets)
        
        # Generais e Soldados aceitam seus subordinados
        for acc in pool_accounts:
            if self.stop_flag: break
            children = [child for child, parent in relations.items() if parent == acc['username']]
            if children:
                accepter.accept_all(acc, target_players=children)
                time.sleep(1)

        # --- FASE 2.5: TRAVA DE SEGURANÇA (SAFETY LOCK) ---
        # Antes de realocar, temos que garantir que o Master aceitou os 5 Generais.
        if is_manual_master:
            self.log(f"🔒 ATENÇÃO: Master é Externo. Iniciando verificação de segurança...", "warn")
            self.log(f"⏳ Por favor, ACEITE os pedidos de amizade na conta {master_username} AGORA!", "warn")
            
            generals_l1_names = [g['name'] for g in tree['generals']]
            
            if not self._wait_for_master_confirmation(generals_l1_names, master_username):
                self.log("❌ Operação cancelada pelo usuário ou falha na verificação.", "error")
                return
        
        # --- FASE 3: REALOCAÇÃO ---
        self.log("🏘️ Todos os convites confirmados! Iniciando Realocação...", "process")
        
        for acc in pool_accounts:
            if self.stop_flag: break
            
            parent_name = relations.get(acc['username'])
            if not parent_name: continue

            # Busca ID e Realoca
            parent_id = self._get_buddy_id(acc, parent_name)
            
            if parent_id:
                success = cluster_realocator.execute_relocation(acc, parent_id)
                if success: time.sleep(3)
            else:
                self.log(f"❌ ERRO GRAVE: {acc['username']} não é amigo de {parent_name}. Pulando.", "error")

        self.log("🏁 OPERAÇÃO CLUSTER FINALIZADA!", "success")

    def _wait_for_master_confirmation(self, generals_names, master_name):
        """
        Loop infinito (até parar) que verifica se os Generais já veem o Master como amigo.
        """
        while not self.stop_flag:
            pending_generals = []
            
            self.log(f"🔍 Verificando se {master_name} aceitou os {len(generals_names)} Generais...", "info")
            
            all_confirmed = True
            for gen_name in generals_names:
                gen_acc = account_manager.get_account(gen_name)
                if not gen_acc: continue

                # Checa se são amigos DE VERDADE (tem ID e não tá pendente)
                buddy_id = self._get_buddy_id(gen_acc, master_name)
                
                if not buddy_id:
                    all_confirmed = False
                    pending_generals.append(gen_name)
                    self.log(f"⏳ {gen_name}: Aguardando aceite do Master...", "warn")
                else:
                    self.log(f"✅ {gen_name}: Confirmado! É amigo do Master.", "success")
                
                time.sleep(1) # Pausa leve pra não bloquear proxies
            
            if all_confirmed:
                self.log("🔓 Trava liberada! Todos os Generais foram aceitos.", "success")
                return True
            
            self.log(f"⚠️ Faltam {len(pending_generals)} aceites. Verificando novamente em 10s...", "process")
            self.log("👉 DICA: Vá na conta Master e aceite os pedidos!", "process")
            
            # Espera 10 segundos antes de tentar de novo
            for _ in range(10):
                if self.stop_flag: return False
                time.sleep(1)
        
        return False

    def _get_buddy_id(self, account, buddy_name):
        """
        Busca o ID numérico do amigo.
        Versão corrigida para lidar com quebras de linha e link de info_player.
        """
        try:
            from core.request_engine import GameClient
            client = GameClient(account)
            resp = client.safe_get("buddies")
            if not resp: return None
            
            # O HTML do jogo coloca o nome assim:
            # <a href="...screen=info_player&id=849038049">
            #     DomRodrigues
            # </a>
            
            # 1. Tenta pegar pelo link do Perfil (onde o nome aparece)
            # Usamos re.DOTALL para que o ponto (.) pegue quebras de linha
            # Usamos \s* para ignorar espaços antes e depois do nome
            pattern_profile = (
                r'screen=info_player(?:&amp;|&)id=(\d+)[^>]*?>'  # Captura o ID na URL
                r'\s*' + re.escape(buddy_name) + r'\s*'          # Encontra o nome com possíveis espaços
                r'</a>'
            )
            
            match = re.search(pattern_profile, resp.text, re.DOTALL | re.IGNORECASE)
            
            if match:
                return match.group(1)

            # 2. Tenta busca alternativa (caso o layout mude)
            # Procura pelo ID genérico se o nome estiver na mesma linha de tabela
            if buddy_name in resp.text:
                # Procura qualquer ID próximo do nome
                # (Menos preciso, mas serve de backup)
                backup_match = re.search(rf'id=(\d+)[^>]*?>\s*{re.escape(buddy_name)}', resp.text, re.DOTALL)
                if backup_match:
                    return backup_match.group(1)

            return None

        except Exception as e:
            self.log(f"Erro ao buscar ID de amigo: {e}", "error")
            return None

cluster_controller = ClusterController()