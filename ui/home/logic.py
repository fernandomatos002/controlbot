import threading
import time
import flet as ft
from core.account_manager import account_manager
from core.auto_login import auto_login  # ✅ NOVO IMPORT
from core.bot_controller import bot_controller
from core.proxy_manager import manager as proxy_manager
from core.settings_manager import global_settings
import ui.styles as st

class HomeLogic:
    def __init__(self, page: ft.Page, refresh_callback):
        self.page = page
        self.refresh_callback = refresh_callback

    def add_log(self, account_id, msg, type="info", log_modal=None, viewing_id=None):
        """Adiciona log na memória da conta e atualiza o modal se estiver aberto."""
        # Encontra a conta
        acc = next((a for a in account_manager.accounts if a['id'] == account_id), None)
        if not acc: return
        
        timestamp = time.strftime("%H:%M:%S")
        if 'logs' not in acc: acc['logs'] = []
        
        # MUDANÇA: Usa append para adicionar no final (Terminal Style)
        acc['logs'].append({"time": timestamp, "msg": msg, "type": type})
        
        # Se passar de 100 linhas, remove a primeira (a mais antiga)
        if len(acc['logs']) > 100: acc['logs'].pop(0) 

        # Se o modal de logs estiver aberto E vendo ESSA conta, atualiza em tempo real
        if log_modal and log_modal.open and viewing_id == account_id:
            try:
                log_modal.render_logs(acc)
            except: pass

    def perform_login(self, acc):
        """
        ✅ NOVO: Realiza login automático com credenciais
        Não requer mais navegador manual!
        """
        username = acc.get('username', 'Unknown')
        self.add_log(acc['id'], f"🔐 Iniciando login automático para {username}...", "process")
        
        def worker():
            try:
                # Chama o auto_login que faz tudo automaticamente
                success = auto_login.perform_auto_login(acc['id'])
                
                if success:
                    self.add_log(acc['id'], "✅ Login bem-sucedido! Sessão capturada.", "success")
                    acc['status'] = 'stopped'
                    account_manager.save()
                    self.add_log(acc['id'], "Agora você pode iniciar o bot!", "success")
                else:
                    self.add_log(acc['id'], "❌ Falha no login automático. Verifique as credenciais.", "error")
            
            except Exception as e:
                self.add_log(acc['id'], f"❌ Erro crítico: {str(e)}", "error")
            
            finally:
                self.refresh_callback()
        
        threading.Thread(target=worker, daemon=True).start()

    def open_visual_village(self, acc):
        """Abre o navegador apenas para visualizar (sem logar novamente)"""
        def worker():
            was_running = False
            if acc['status'] == 'running':
                was_running = True
                self.add_log(acc['id'], "⸸ Pausando para visualização...", "warn")
                bot_controller.stop_cycle(acc['id'])
                time.sleep(2)
                self.refresh_callback()

            self.add_log(acc['id'], "👁️ Visualização aberta.", "info")
            
            from core.browser_auth import auth_handler
            auth_handler.open_visual_mode(acc['id'])
            
            self.add_log(acc['id'], "👁️ Visualização fechada.", "info")
            
            if was_running:
                self.add_log(acc['id'], "▶️ Retomando automação...", "success")
                bot_controller.start_cycle(acc['id'], log_callback=self.add_log)
            
            self.refresh_callback()
        
        threading.Thread(target=worker, daemon=True).start()

    def toggle_bot(self, acc):
        """Liga/Desliga o bot usando o BotController"""
        if acc['status'] == 'running':
            # PARAR
            self.add_log(acc['id'], "Parando...", "warn")
            bot_controller.stop_cycle(acc['id'])
        else:
            # INICIAR
            
            # 1. Verifica Proxy
            pid = acc.get('proxy_id')
            if pid and pid != 'none':
                proxy = next((p for p in proxy_manager.proxies if p['id'] == pid), None)
                if not proxy or proxy['status'] != 'working':
                    self.page.snack_bar = ft.SnackBar(ft.Text("Erro: Proxy inválido ou offline!"), bgcolor=st.COLOR_ERROR)
                    self.page.snack_bar.open = True
                    self.page.update()
                    return

            # 2. Verifica Sessão
            if not acc.get('session'):
                self.page.snack_bar = ft.SnackBar(ft.Text("Erro: Faça login manual primeiro!"), bgcolor=st.COLOR_ERROR)
                self.page.snack_bar.open = True
                self.page.update()
                return

            # 3. Inicia
            acc['cycle_state'] = 'starting'
            self.add_log(acc['id'], "Iniciando ciclo...", "success")
            bot_controller.start_cycle(acc['id'], log_callback=self.add_log)
        
        self.refresh_callback()

    def delete_account(self, aid):
        """Remove conta e libera proxy"""
        acc = next((a for a in account_manager.accounts if a['id'] == aid), None)
        if acc:
            pid = acc.get('proxy_id')
            if pid and pid != 'none':
                # Libera o proxy (atribui None)
                proxy_manager.assign_proxy(pid, None)
            
            account_manager.delete_account(aid)
            self.refresh_callback()

    def edit_account(self, acc_id, new_data):
        """Edita dados da conta e gerencia troca de proxy"""
        for acc in account_manager.accounts:
            if acc['id'] == acc_id:
                # Atualiza dados básicos
                acc['username'] = new_data['username']
                
                # ✅ NOVO: Também permite editar a senha
                if new_data.get('password'):
                    acc['password'] = new_data['password']
                
                acc['world'] = new_data['world']
                
                # Gerencia Proxy
                old_proxy = acc.get('proxy_id')
                new_proxy = new_data['proxy_id']
                
                if old_proxy != new_proxy:
                    # Libera antigo
                    if old_proxy and old_proxy != 'none':
                        proxy_manager.assign_proxy(old_proxy, None)
                    
                    # Aloca novo
                    acc['proxy_id'] = new_proxy
                    if new_proxy and new_proxy != 'none':
                        label = f"[{acc.get('server', 'BR')}] {acc['username']} - {acc['world']}"
                        proxy_manager.assign_proxy(new_proxy, label)
                
                account_manager.save()
                self.add_log(acc_id, "Dados editados manualmente.", "info")
                break
    
    def start_all_bots(self, e):
        """Inicia todas as contas que possuem sessão e estão paradas."""
        count = 0
        
        for acc in account_manager.accounts:
            # Pula se já estiver rodando ou sem sessão
            if acc['status'] == 'running':
                continue
            if not acc.get('session'):
                continue

            # Verificação rápida de Proxy (similar ao toggle_bot)
            pid = acc.get('proxy_id')
            if pid and pid != 'none':
                proxy = next((p for p in proxy_manager.proxies if p['id'] == pid), None)
                if not proxy or proxy['status'] != 'working':
                    self.add_log(acc['id'], "Ignorado no 'Iniciar Tudo': Proxy inválido.", "error")
                    continue

            # Inicia o bot
            acc['cycle_state'] = 'starting'
            bot_controller.start_cycle(acc['id'], log_callback=self.add_log)
            count += 1
            
            # Pequeno delay para não congelar a UI se tiver muitas contas
            time.sleep(0.1)

        self.refresh_callback()
        
        # Feedback visual
        if count > 0:
            self.page.snack_bar = ft.SnackBar(
                ft.Text(f"🚀 {count} contas iniciadas com sucesso!"), 
                bgcolor=st.COLOR_SUCCESS
            )
        else:
            self.page.snack_bar = ft.SnackBar(
                ft.Text("Nenhuma conta apta para iniciar (verifique sessões/proxies)."), 
                bgcolor=st.COLOR_WARNING
            )
        self.page.snack_bar.open = True
        self.page.update()
        
        self.refresh_callback()