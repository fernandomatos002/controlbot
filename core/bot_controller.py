import time
import random
import threading
from datetime import datetime, timedelta
from core.account_manager import account_manager
from core.request_engine import GameClient
from core.game_parser import GameParser
from core.settings_manager import global_settings

# --- MANAGERS ---
from core.features.reward_manager import RewardManager
from core.features.build_manager import BuildManager
from core.features.recruit_manager import RecruitManager
from core.features.scavenge_manager import ScavengeManager 
from core.features.research_manager import ResearchManager

class BotController:
    def __init__(self):
        self.active_threads = {}
        self.ui_callbacks = {}

    def start_cycle(self, account_id, log_callback=None):
        # --- ADICIONE ESTE BLOCO AQUI ---
        # 1. Se veio da interface, salva na memória
        if log_callback:
            self.ui_callbacks[account_id] = log_callback
        # 2. Se veio do reinício automático (sem callback), recupera da memória
        elif account_id in self.ui_callbacks:
            log_callback = self.ui_callbacks[account_id]
        if account_id in self.active_threads and self.active_threads[account_id].is_alive(): 
            return 
        
        acc = self._get_account(account_id)
        if not acc: return
        
        acc['logs'] = [] 
        acc['status'] = 'running'
        acc['cycle_state'] = 'starting'
        account_manager.save()
        
        t = threading.Thread(target=self._worker, args=(account_id, log_callback), daemon=True)
        self.active_threads[account_id] = t
        t.start()

    def stop_cycle(self, account_id):
        acc = self._get_account(account_id)
        if acc:
            acc['status'] = 'stopped'
            acc['cycle_state'] = 'stopped'
            account_manager.save()

    def _worker(self, account_id, log_callback):
        def log(msg, type="info"):
            if log_callback: log_callback(account_id, msg, type)
            acc = self._get_account(account_id)
            if acc: 
                acc['last_activity'] = msg
                acc['last_activity_type'] = type
        
        def fmt(num): return f"{num:,}".replace(",", ".")

        acc = self._get_account(account_id)
        log("🚀 === INICIANDO CICLO ===", "info")
        
        try:
            log("🌐 Conectando ao servidor...", "warn")
            client = GameClient(acc)
            
            # Inicializa Managers
            rewards_mgr = RewardManager(client, log)
            build_mgr = BuildManager(client, log)
            recruit_mgr = RecruitManager(client, log)
            scavenge_mgr = ScavengeManager(client, log) 
            research_mgr = ResearchManager(client, log) 

            acc['cycle_state'] = 'checking'
            
            if not client.ensure_connection():
                log("❌ Falha crítica: Não foi possível conectar.", "error")
                acc['status'] = 'stopped'
                acc['cycle_state'] = 'error'
                account_manager.save()
                return
            
            # Sincroniza cookies
            client.update_account_session()
            account_manager.save()
            
            log("✅ Conectado com sucesso.", "success")

            while acc['status'] == 'running':
                acc = self._get_account(account_id)
                if acc['status'] != 'running': break

                acc['cycle_state'] = 'checking'
                log("🔄 -----------------------------------------", "info")
                log("🔄 Iniciando análise da aldeia...", "info")
                
                # 1. Overview
                t_start = time.time()
                resp = client.safe_get("overview")
                if not resp:
                    log("❌ Erro de rede ao carregar Overview.", "error")
                    time.sleep(10)
                    continue
                log(f"📡 Overview carregado em {time.time()-t_start:.2f}s", "info")

                parser = GameParser(resp.text)
                
                # 2. Segurança
                sec = parser.check_security()
                if sec == 'captcha':
                    log("⛔ CAPTCHA DETECTADO! Parando bot.", "error")
                    acc['status'] = 'stopped'
                    acc['cycle_state'] = 'captcha'
                    account_manager.save()
                    break
                elif sec == 'session_expired':
                    log("⚠️ Sessão expirou. Tentando renovar...", "warn")
                    if client.ensure_connection(): 
                        client.update_account_session()
                        account_manager.save()
                        log("✅ Sessão renovada com sucesso.", "success")
                        continue
                    else: 
                        log("❌ Falha ao renovar sessão. Parando.", "error")
                        acc['status'] = 'stopped'
                        break

                game_data = parser.get_game_data_from_json()
                if not game_data:
                    log("⚠️ Erro ao ler dados do jogo (JSON não encontrado).", "warn")
                    time.sleep(5)
                    continue

                # Log de Recursos Inicial
                log(f"💰 Recursos Atuais: 🌲{fmt(game_data['wood'])} 🧱{fmt(game_data['stone'])} ⛏️{fmt(game_data['iron'])}", "info")
                
                # --- 1. RECOMPENSAS (PRIORIDADE) ---
                log("🎁 [FASE 1] Verificando Recompensas...", "info")
                
                if rewards_mgr.handle_daily_bonus(parser):
                    log("✅ Bônus diário processado.", "success")
                else:
                    log("ℹ️ Sem bônus diário pendente.", "info")
                
                time.sleep(random.uniform(0.8, 1.5)) 

                if game_data:
                    rewards_mgr.handle_new_quests(parser, game_data)
                    time.sleep(random.uniform(1.2, 2.0))

                # --- 2. AÇÕES DE GASTO (ORDEM ALEATÓRIA) ---
                if game_data:
                    log("🎲 [FASE 2] Sorteando ordem das tarefas...", "info")
                    
                    tasks = [
                        {"name": "Construção",   "func": build_mgr.execute},
                        {"name": "Recrutamento", "func": recruit_mgr.execute},
                        {"name": "Coleta",       "func": scavenge_mgr.execute},
                        {"name": "Pesquisa",     "func": research_mgr.execute}
                    ]
                    
                    random.shuffle(tasks)
                    
                    # Log da ordem sorteada para você saber o que ele vai fazer
                    order_names = [t['name'] for t in tasks]
                    log(f"📋 Ordem do Ciclo: {' -> '.join(order_names)}", "warn")

                    for i, task in enumerate(tasks):
                        if acc['status'] != 'running': break
                        
                        # Log antes de começar
                        log(f"▶️ [{i+1}/3] Iniciando módulo: {task['name']}", "info")
                        
                        try:
                            task['func'](acc, game_data)
                        except Exception as e_task:
                            log(f"❌ Erro no módulo {task['name']}: {e_task}", "error")
                        
                        # Pausa humana com log
                        if i < len(tasks) - 1: # Não pausa no último
                            pause = random.uniform(2.5, 5.5)
                            log(f"⏳ Pausa humana de {pause:.1f}s antes da próxima tarefa...", "info")
                            time.sleep(pause)

                # 5. FINALIZAÇÃO E RELATÓRIO
                log("🏁 [FASE 3] Finalizando ciclo e atualizando dados...", "info")
                time.sleep(1) 
                
                resp = client.safe_get("overview") # Atualiza dados finais
                if resp:
                    parser = GameParser(resp.text)
                    game_data = parser.get_game_data_from_json()
                                          
                    if game_data:
                        acc['resources'] = {
                            'wood': game_data['wood'], 
                            'stone': game_data['stone'], 
                            'iron': game_data['iron']
                        }
                        acc['storage'] = game_data['storage']
                        acc['population'] = {
                            'current': game_data['pop_current'], 
                            'max': game_data['pop_max']
                        }
                        acc['points'] = parser.get_points()
                        acc['incomings'] = parser.get_incoming_attacks()
                        
                        log(f"📊 Status Final: População {game_data['pop_current']}/{game_data['pop_max']} | Armazém: {game_data['storage']}", "info")
                        
                        if acc['incomings'] > 0: 
                             log(f"⚔️ PERIGO: {acc['incomings']} ATAQUES A CAMINHO!", "error")
                        else:
                             log("🛡️ Nenhum ataque detectado.", "success")
                        
                        account_manager.save()

                # 6. SLEEP (DORMIR)
                acc['last_cycle'] = time.strftime("%H:%M:%S")
                acc['cycle_state'] = 'verified'
                
                min_min = global_settings.get("min_interval")
                max_min = global_settings.get("max_interval")
                
                total_sleep = random.randint(min_min*60, max_min*60) + random.randint(15, 59)
                wake_time = (datetime.now() + timedelta(seconds=total_sleep)).strftime("%H:%M:%S")

                log(f"💤 Ciclo concluído com sucesso.", "success")
                log(f"⏲️ Dormindo {total_sleep}s (Próxima execução: {wake_time})", "warn")
            
                # Loop de espera visual
                for _ in range(total_sleep):
                    if acc['status'] != 'running': break
                    time.sleep(1)

        except Exception as e:
            log(f"🔥 Crash Crítico no Controller: {e}", "error")
            acc['status'] = 'stopped'
            acc['cycle_state'] = 'error'
            import traceback
            traceback.print_exc() 
        finally:
            log("🛑 Bot parou.", "error")
            account_manager.save()

    def _get_account(self, aid):
        return next((a for a in account_manager.accounts if a['id'] == aid), None)

bot_controller = BotController()