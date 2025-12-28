import time
from playwright.sync_api import sync_playwright
from core.account_manager import account_manager
from core.proxy_manager import manager as proxy_manager

class AutoLogin:
    def __init__(self, log_callback=None):
        self.log = log_callback or print
        self.page = None
        self.context = None
        self.browser = None

    def _log(self, msg, type="info"):
        """Log padronizado"""
        prefix = {
            "info": "ℹ️",
            "success": "✅",
            "error": "❌",
            "warn": "⚠️",
            "process": "🔄"
        }.get(type, "→")
        
        full_msg = f"{prefix} {msg}"
        if callable(self.log):
            self.log(full_msg, type)
        else:
            print(full_msg)

    def _setup_proxy_config(self, account_data):
        """
        Configura o objeto de proxy para o Playwright.
        CORREÇÃO: Passa username e password em campos separados.
        """
        pid = account_data.get('proxy_id')
        
        if pid and pid != 'none':
            try:
                # Busca o objeto proxy pelo ID na lista do manager
                proxy = next((p for p in proxy_manager.proxies if p['id'] == pid), None)
                
                if proxy and proxy.get('status') != 'error':
                    # Configuração base (Server)
                    proxy_config = {
                        "server": f"http://{proxy['ip']}:{proxy['port']}"
                    }
                    
                    # Se tiver autenticação, insere nos campos específicos do Playwright
                    if proxy.get('user') and proxy.get('pass'):
                        proxy_config["username"] = proxy['user']
                        proxy_config["password"] = proxy['pass']
                    
                    return proxy_config
            except Exception as e:
                self._log(f"Erro na config do proxy: {e}", "warn")
        
        return None

    def perform_auto_login(self, account_id):
        """
        Fluxo de Login Semiautomático:
        1. Abre navegador.
        2. Preenche usuário e senha e clica login.
        3. ESPERA 60 SEGUNDOS para o usuário resolver Captcha e selecionar Mundo.
        4. Detecta URL 'game.php', salva os cookies e fecha.
        """
        
        acc = account_manager.get_account(account_id)
        if not acc:
            self._log(f"Conta {account_id} não encontrada", "error")
            return False
        
        username = acc.get('username')
        password = acc.get('password')
        
        if not username or not password:
            self._log(f"Credenciais incompletas.", "error")
            return False
        
        # Prepara proxy com a correção
        proxy_config = self._setup_proxy_config(acc)
        if proxy_config:
            self._log(f"Usando Proxy: {proxy_config['server']}", "info")

        self._log(f"🔐 Iniciando login para {username}...", "process")
        
        try:
            with sync_playwright() as p:
                # 1. Abre o navegador visível (headless=False)
                self.browser = p.chromium.launch(
                    headless=False,
                    channel="chrome", 
                    args=["--disable-blink-features=AutomationControlled"]
                )
                
                # Cria contexto
                self.context = self.browser.new_context(
                    proxy=proxy_config,
                    viewport={'width': 1280, 'height': 720},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                
                self.page = self.context.new_page()
                
                # 2. Acessa home
                server_region = acc.get('server', 'BR').lower()
                domain_ext = "com.br" if server_region == "br" else "com.pt"
                target_url = f"https://www.tribalwars.{domain_ext}/"

                self._log(f"Navegando para {target_url}...", "info")
                try:
                    self.page.goto(target_url, timeout=60000)
                except Exception as e:
                    self._log(f"Erro de conexão/proxy: {e}", "error")
                    return False

                # 3. Preenche Login
                try:
                    self.page.locator('#user').fill(username)
                    self.page.locator('#password').fill(password)
                    
                    # Tenta clicar no botão ou submeter form
                    try:
                        self.page.locator('a.btn-login').click()
                    except:
                        self.page.locator('form#login_form').evaluate('form => form.submit()')

                    self._log("✓ Credenciais enviadas.", "success")
                except Exception as e:
                    self._log(f"Erro ao preencher login: {e}", "error")
                    return False

                # 4. PAUSA PARA O USUÁRIO (60s)
                self._log("⏳ AGUARDANDO VOCÊ: Resolva o Captcha e ENTRE NO MUNDO!", "warn")
                self._log("⏰ Você tem 60 segundos...", "warn")

                try:
                    # Espera a URL mudar para conter 'game.php' (sinal de sucesso)
                    self.page.wait_for_url(lambda u: "game.php" in u, timeout=60000)
                    
                    self._log("✅ Entrada no mundo detectada!", "success")
                    time.sleep(1) # Garante carregamento dos cookies

                    # 5. Salva Sessão
                    cookies = self.context.cookies()
                    ua = self.page.evaluate("navigator.userAgent")
                    current_url = self.page.url
                    
                    acc['session'] = {
                        'cookies': cookies,
                        'user_agent': ua,
                        'last_url': current_url,
                        'cookies_date': time.time()
                    }
                    account_manager.save()
                    
                    self._log("✅ Sessão salva no disco.", "success")
                    self.browser.close()
                    return True

                except Exception:
                    self._log("❌ Tempo esgotado! Você não entrou no mundo em 60s.", "error")
                    self.browser.close()
                    return False
        
        except Exception as e:
            self._log(f"Erro crítico: {e}", "error")
            return False
        finally:
            if self.browser:
                try: self.browser.close()
                except: pass

# Instância global
auto_login = AutoLogin()