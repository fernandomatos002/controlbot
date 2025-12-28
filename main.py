import flet as ft
import threading
import time
import requests
import os
import subprocess
import sys
import ui.styles as st
from ui.screens.login_panel import LoginScreen
from ui.screens.dashboard import DashboardScreen
from core.cloud_sync import cloud_sync
from core.session_manager import session
from core.account_manager import account_manager
from core.proxy_manager import manager as proxy_manager
from core.settings_manager import global_settings
from core.bot_controller import bot_controller
from core.version import CURRENT_VERSION, UPDATE_URL, LAUNCHER_NAME


def start_version_watchdog(page: ft.Page):
    """
    Verifica atualizações em segundo plano a cada 5 minutos 
    e abre um DIÁLOGO perguntando se o usuário quer atualizar.
    """
    
    # 1. Definição da Ação de Atualizar
    def confirmar_atualizacao(e):
        print("Usuário aceitou atualização. Iniciando Launcher...")
        dlg_update.open = False
        page.update()
        
        # Verifica se o launcher existe
        if os.path.exists(LAUNCHER_NAME):
            subprocess.Popen([LAUNCHER_NAME])
            page.window_destroy()
            os._exit(0)
        else:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Erro: {LAUNCHER_NAME} não encontrado!"),
                bgcolor="red"
            )
            page.snack_bar.open = True
            page.update()

    # 2. Definição da Ação de Ignorar (Fechar Janela)
    def ignorar_atualizacao(e):
        dlg_update.open = False
        page.update()

    # 3. Criação do Componente de Diálogo (Criado uma vez, reutilizado depois)
    dlg_update = ft.AlertDialog(
        modal=True,
        title=ft.Text("Nova Versão Disponível 🚀"),
        content=ft.Column(
            [
                ft.Text("Uma atualização importante foi detectada."),
                ft.Text("Deseja fechar o bot e atualizar agora?", weight="bold"),
                ft.Text("Recomendamos atualizar para evitar erros.", size=12, color="grey"),
            ],
            tight=True,
            spacing=10
        ),
        actions=[
            ft.TextButton("Não, lembrar depois", on_click=ignorar_atualizacao),
            ft.ElevatedButton(
                "Sim, Atualizar",
                on_click=confirmar_atualizacao,
                bgcolor="#27ae60",
                color="white"
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    # 4. Loop de Verificação (Watchdog)
    def watchdog():
        # Associa o diálogo à página (sem abrir ainda)
        page.dialog = dlg_update
        
        while True:
            try:
                # Se o diálogo já estiver aberto, espera e não faz nada
                if dlg_update.open:
                    time.sleep(300)
                    continue

                # Verifica versão no servidor
                resp = requests.get(UPDATE_URL, timeout=10)
                if resp.status_code == 200:
                    server_ver = resp.text.strip()

                    # Compara com a versão definida no código
                    if CURRENT_VERSION != server_ver:
                        print(f"⚠️ Update encontrado: {CURRENT_VERSION} -> {server_ver}")
                        
                        # Atualiza o texto do título
                        dlg_update.title.value = f"Nova Versão {server_ver} 🚀"
                        dlg_update.open = True
                        page.update()
            
            except Exception as e:
                print(f"Erro no watchdog de versão: {e}")
            
            # Aguarda 5 minutos antes de tentar de novo
            time.sleep(300) 

    # Inicia a thread
    threading.Thread(target=watchdog, daemon=True).start()

# --- ADICIONE ESTA FUNÇÃO NO main.py (FORA da função main) ---

def start_license_watchdog(page: ft.Page, user_data: dict):
    """
    Thread que roda em segundo plano.
    Verifica a cada 10 minutos se a licença ainda é válida na API.
    """
    user_id = user_data.get('id') or user_data.get('user_id')
    
    # SEU IP DA VPS (Confirme se é este mesmo)
    API_URL = "http://162.220.14.199" 

    def watchdog_loop():
        print(f"🕵️ [Watchdog] Iniciado para User ID: {user_id}")
        
        while True:
            # 1. Aguarda 10 minutos (600 segundos) entre verificações
            # Para testes rápidos, mude para 60 segundos
            time.sleep(600) 

            try:
                # 2. Consulta a API (Nova rota que criamos)
                response = requests.get(f"{API_URL}/api/users/{user_id}/status", timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    is_active = data.get("active", False)
                    days = data.get("days_remaining", 0)

                    # Se a licença NÃO estiver ativa
                    if not is_active:
                        print("⛔ [Watchdog] LICENÇA EXPIROU! Bloqueando acesso...")
                        
                        # A. Para todos os bots que estão rodando
                        running_accounts = [acc for acc in account_manager.accounts if acc.get('status') == 'running']
                        for acc in running_accounts:
                            print(f"   -> Parando bot da conta: {acc.get('username')}")
                            bot_controller.stop_cycle(acc.get('id'))
                            # Atualiza status visualmente no manager para 'stopped'
                            account_manager.update_status(acc.get('id'), "stopped")

                        # B. Ação na Interface (UI) - Precisa ser thread-safe
                        def bloquear_ui():
                            # Feedback visual
                            page.snack_bar = ft.SnackBar(
                                content=ft.Text("Sua licença expirou! Sessão encerrada.", weight="bold"),
                                bgcolor="red",
                                duration=10000 # 10 segundos
                            )
                            page.snack_bar.open = True
                            
                            # Limpa sessão local
                            session.logout() 
                            
                            # Limpa a tela e volta para o Login
                            page.clean()
                            
                            # Importação tardia para evitar ciclo de importação
                            from ui.screens.login_panel import LoginScreen
                            
                            # Função auxiliar para re-logar (igual a usada no main)
                            def reload_dash(new_data):
                                page.clean()
                                from ui.screens.dashboard import DashboardScreen
                                DashboardScreen(page, user_data=new_data)
                                start_license_watchdog(page, new_data) # Reinicia watchdog no novo login
                                page.update()

                            LoginScreen(page, on_login_success=reload_dash)
                            page.update()

                        # Executa a ação de bloqueio na thread principal da UI (Flet não gosta de updates de outras threads)
                        # Se sua versão do Flet for antiga e não tiver run_task, use apenas bloquear_ui()
                        # Mas o ideal é agendar na thread principal se possível, ou chamar direto:
                        try:
                            bloquear_ui()
                        except Exception as ui_err:
                            print(f"Erro ao atualizar UI: {ui_err}")
                        
                        # Sai do loop infinito pois o usuário foi deslogado
                        break 
                    
                    else:
                        print(f"✅ [Watchdog] Licença OK. Dias restantes: {days}")

            except Exception as e:
                print(f"⚠️ [Watchdog] Erro de conexão ao verificar licença: {e}")
                # Não faz nada, tenta novamente daqui 10 min (pode ser só oscilação de internet)

    # Inicia a thread como Daemon (morre se fechar o app)
    threading.Thread(target=watchdog_loop, daemon=True, name="LicenseWatchdog").start()

def main(page: ft.Page):
    # --- Configurações da Janela ---
    page.title = "TribalCore - Enterprise Bot"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = st.COLOR_BG
    page.padding = 0
    page.window_maximized = True
    page.window_min_width = 1100
    page.window_min_height = 700

    # --- INICIA O VIGILANTE DE VERSÃO ---
    start_version_watchdog(page)

    # --- Funções de Navegação ---
    def ir_para_dashboard(data=None):
        page.clean()
        DashboardScreen(page, user_data=data)
        start_license_watchdog(page, data)
        page.update()

    def ir_para_login():
        page.clean()
        LoginScreen(page, on_login_success=ir_para_dashboard)
        page.update()

    # --- LÓGICA DE AUTO-LOGIN ---
    def carregar_sessao_async():
        """Carrega a sessão e sincroniza dados em thread separada"""
        # Pequeno delay para garantir que a UI carregou
        time.sleep(1) 
        
        saved_user = session.load_session()
        
        if saved_user:
            print("Sessão encontrada! Entrando direto...")
            user_id = saved_user.get('user_id')
            
            if user_id:
                cloud_sync.set_user(user_id)
                print("🚀 Auto-Login: Sincronizando dados da nuvem...")
                
                try:
                    all_configs = cloud_sync.load_all()
                    
                    if all_configs:
                        if 'accounts' in all_configs:
                            account_manager.accounts = all_configs['accounts']
                            account_manager.save()
                            
                        if 'proxies' in all_configs:
                            proxy_manager.proxies = all_configs['proxies']
                            
                        if 'settings' in all_configs:
                            global_settings.settings = all_configs['settings']
                            
                        print("✅ Dados sincronizados com sucesso.")
                    else:
                        print("⚠️ Nenhuma configuração encontrada na nuvem. Usando dados locais.")
                        
                except Exception as e:
                    print(f"⚠️ Erro na sincronização cloud: {e}")
                    print("📁 Continuando com dados locais...")
                
                # Volta para a thread principal e abre o dashboard
                page.clean()
                ir_para_dashboard(saved_user)
        else:
            print("Nenhuma sessão salva. Indo para login...")
            page.clean()
            ir_para_login()

    # Inicia sincronização em thread separada
    threading.Thread(target=carregar_sessao_async, daemon=True).start()
    
    # Mostra uma tela de carregamento enquanto sincroniza
    page.add(
        ft.Column(
            [
                ft.ProgressRing(color=st.COLOR_PRIMARY),
                ft.Text("Carregando...", size=16, weight="bold"),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )
    )

if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")