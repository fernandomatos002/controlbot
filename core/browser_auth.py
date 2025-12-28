import time
from playwright.sync_api import sync_playwright
from core.account_manager import account_manager

class BrowserAuthHandler:
    def __init__(self):
        pass

    def open_visual_mode(self, account_id):
        """
        Abre o navegador, bloqueia até fechar e REINICIA o bot no final.
        """
        print("📂 [Visual] Recarregando sessão...")
        account_manager.load()
        
        account_data = account_manager.get_account(account_id)
        if not account_data:
            print(f"❌ [Visual] Conta {account_id} não encontrada.")
            return

        self._run_browser_sync(account_data, account_id)

    def _run_browser_sync(self, account, account_id):
        user = account.get('username')
        print(f"👀 [Visual] Abrindo para: {user}")

        session = account.get('session', {})
        cookies = session.get('cookies', [])
        ua = session.get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        last_url = session.get('last_url')

        if not cookies:
            print("❌ [Visual] Sem cookies. Faça login automático primeiro.")
            return

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=False, 
                    channel="chrome",
                    args=["--disable-blink-features=AutomationControlled"]
                )
                
                context = browser.new_context(user_agent=ua, viewport=None)
                
                try:
                    context.add_cookies(cookies)
                except:
                    pass

                page = context.new_page()
                
                # Definição do alvo
                server_region = account.get('server', 'BR').lower()
                domain_ext = "com.br" if server_region == "br" else "com.pt"
                target_url = f"https://www.tribalwars.{domain_ext}"

                if last_url and "game.php" in last_url:
                    target_url = last_url
                else:
                    world = account.get('world', '')
                    if world:
                        target_url = f"https://{world}.tribalwars.{domain_ext}/game.php?screen=overview"

                print(f"🌍 [Visual] Navegando...")
                
                try:
                    page.goto(target_url, timeout=60000)
                except:
                    print("⚠️ Timeout no carregamento inicial, mas mantendo aberto...")

                print("✅ [Visual] Janela aberta. Pode navegar à vontade.")
                print("🔒 [Visual] Bot pausado. Feche a janela para retomar.")
                
                # --- LOOP COM TOLERÂNCIA A NAVEGAÇÃO ---
                consecutive_errors = 0 
                
                while True:
                    time.sleep(1) 
                    try:
                        # Verifica se o navegador ainda existe
                        if not browser.is_connected():
                            print("🔒 [Visual] Navegador desconectado.")
                            break
                            
                        if page.is_closed():
                            print("🔒 [Visual] Aba fechada.")
                            break

                        # Tenta pingar a página (gera erro se estiver carregando ou fechada)
                        _ = page.title()
                        
                        # Se sucesso, reseta contador
                        consecutive_errors = 0 

                    except Exception:
                        consecutive_errors += 1
                        
                        # Só encerra se falhar 3 vezes seguidas (aprox 3s)
                        # Isso evita fechar durante o loading de uma página
                        if consecutive_errors >= 3:
                            print(f"🔒 [Visual] Fechamento confirmado (Sem resposta por 3s).")
                            break
            
            # --- REINÍCIO DO BOT (CORRIGIDO) ---
            print("-" * 30)
            print(f"🔄 [Visual] Reiniciando automação para: {user}...")
            
            try:
                from core.bot_controller import bot_controller
                
                # [cite_start]CORREÇÃO AQUI: Mudado de start_bot para start_cycle [cite: 412]
                bot_controller.start_cycle(account_id)
                
                print(f"🚀 [Visual] Bot reiniciado com sucesso!")
            except Exception as e:
                print(f"❌ [Visual] Falha ao reiniciar bot: {e}")

        except Exception as e:
            print(f"⚠️ [Visual] Sessão visual encerrada: {e}")

# Instância
auth_handler = BrowserAuthHandler()