# ARQUIVO: core/request_engine.py
from curl_cffi import requests
import time
import random
import re
from bs4 import BeautifulSoup

class GameClient:
    def __init__(self, account_data):
        self.account = account_data
        # Impersonate Chrome 120 para bypass de fingerprint
        self.session = requests.Session(impersonate="chrome120")
        
        session_data = account_data.get('session', {})
        if not session_data:
            raise Exception("Sessão não encontrada. Faça login manual primeiro.")

        # Configurações do Mundo e Servidor
        self.server_code = account_data.get('server', 'BR').lower()
        self.world_id = account_data['world']
        
        self.base_url = f"https://{self.world_id}.tribalwars.com.{self.server_code}"
        self.lobby_url = f"https://www.tribalwars.com.{self.server_code}".rstrip('/')
        
        # Domínio base para cookies (ex: .tribalwars.com.pt)
        self.base_domain = f".tribalwars.com.{self.server_code}"

        # 🟢 NOVO: Configura Proxy se disponível
        self._setup_proxy(account_data)

        # 1. Carregamento e Correção de Escopo de Cookies
        cookies_list = session_data.get('cookies', [])
        for cookie in cookies_list:
            domain_to_use = cookie.get('domain', '')
            
            # Libera cookies do 'www' para o domínio raiz
            if 'www.' in domain_to_use:
                domain_to_use = self.base_domain
            elif not domain_to_use.startswith('.'):
                domain_to_use = self.base_domain

            self.session.cookies.set(
                cookie['name'], 
                cookie['value'], 
                domain=domain_to_use
            )

        # 2. Headers Base
        user_agent = session_data.get('user_agent', "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        self.headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Ch-Ua": '"Chromium";v="120", "Google Chrome";v="120", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-site",
            "Sec-Fetch-User": "?1",
        }

        self.csrf_token = None

    def _setup_proxy(self, account_data):
        """Configura proxy com segurança máxima (Fail-Safe)"""
        pid = account_data.get('proxy_id')
        
        if pid and pid != "none":
            try:
                from core.proxy_manager import manager as proxy_manager
                
                # Busca proxy atualizado
                proxy = next((p for p in proxy_manager.proxies if p['id'] == pid), None)
                
                # SE O PROXY ESTIVER COM ERRO, LANÇA EXCEÇÃO PARA PARAR O BOT
                if not proxy or proxy.get('status') == 'error':
                    raise Exception(f"⛔ SEGURANÇA: Proxy {pid} offline/erro. Conexão abortada para proteger IP Real.")

                if proxy.get('user') and proxy.get('pass'):
                    proxy_url = f"http://{proxy['user']}:{proxy['pass']}@{proxy['ip']}:{proxy['port']}"
                else:
                    proxy_url = f"http://{proxy['ip']}:{proxy['port']}"
                
                self.session.proxies = {
                    "http": proxy_url,
                    "https": proxy_url
                }
                print(f"[ENGINE] 🛡️ Proxy blindado configurado: {proxy['ip']}")
                    
            except Exception as e:
                # Relança o erro para impedir que o __init__ continue
                raise Exception(f"Falha crítica no Proxy: {e}")

    def update_account_session(self):
        """
        Sincroniza os cookies da sessão atual (RAM) de volta para o dicionário da conta.
        CORRIGIDO: Lida com strings ou objetos ao iterar cookies do curl_cffi.
        """
        cookies_list = []
        
        try:
            # Itera sobre os cookies. No curl_cffi, isso pode retornar chaves (strings) ou objetos dependendo da versão.
            for cookie_or_name in self.session.cookies:
                
                # Caso 1: É um objeto Cookie completo (com .name, .value, .domain)
                if hasattr(cookie_or_name, 'name'):
                    c_domain = getattr(cookie_or_name, 'domain', self.base_domain)
                    if not c_domain: c_domain = self.base_domain
                    
                    cookies_list.append({
                        'name': cookie_or_name.name,
                        'value': cookie_or_name.value,
                        'domain': c_domain,
                        'path': getattr(cookie_or_name, 'path', '/')
                    })
                    
                # Caso 2: É apenas uma string (nome do cookie) - Comportamento comum do curl_cffi
                else:
                    name = str(cookie_or_name)
                    try:
                        value = self.session.cookies[name]
                    except:
                        continue # Se não conseguir pegar o valor, pula
                        
                    # Forçamos o domínio base para garantir que funcione no navegador (visual)
                    cookies_list.append({
                        'name': name,
                        'value': value,
                        'domain': self.base_domain,
                        'path': '/'
                    })

            # Atualiza a referência da conta
            if 'session' not in self.account:
                self.account['session'] = {}

            self.account['session']['cookies'] = cookies_list
            self.account['session']['cookies_date'] = time.time()
            
            # print(f"[ENGINE] Sessão atualizada: {len(cookies_list)} cookies sincronizados.")
            
        except Exception as e:
            print(f"[ENGINE ERROR] Falha ao atualizar sessão no disco: {e}")

    def ensure_connection(self):
        """Verifica conexão com 3 tentativas antes de desistir."""
        check_url = f"{self.base_url}/game.php?screen=overview"
        
        headers_game = self.headers.copy()
        headers_game["Sec-Fetch-Site"] = "same-origin"
        headers_game["Referer"] = f"{self.base_url}/game.php"
        
        max_retries = 3
        
        for attempt in range(1, max_retries + 1):
            try:
                # Timeout aumentado um pouco para tolerar lags do proxy
                response = self.session.get(check_url, headers=headers_game, timeout=20)
                
                # Verificações de falha de sessão
                if self.world_id not in response.url:
                    print(f"[ENGINE] ⚠️ Redirecionado incorretamente. Tentativa {attempt}/{max_retries}...")
                    if self._reenter_world(): return True
                    time.sleep(2)
                    continue 
                
                if "session_expired" in response.url or "login.php" in response.url:
                     print(f"[ENGINE] ⚠️ Sessão expirada. Tentando recuperar ({attempt}/{max_retries})...")
                     if self._reenter_world(): return True
                     time.sleep(2)
                     continue

                # Sucesso
                if "game.php" in response.url:
                    self._extract_csrf(response.text)
                    return True
                
                # Se chegou aqui mas não é game.php, tenta reentrar
                if self._reenter_world(): return True

            except Exception as e:
                print(f"[ENGINE] ❌ Erro de conexão na tentativa {attempt}: {e}")
                time.sleep(3) # Espera 3 segundos antes de tentar de novo

        # Se falhou 3 vezes
        return False

    def _reenter_world(self):
        """Reconexão via Lobby com simulação de clique humano."""
        print(f"[ENGINE] Tentando recuperar sessão via Lobby...")
        
        try:
            # 1. Acessa Lobby
            headers_lobby = self.headers.copy()
            headers_lobby["Referer"] = "https://www.google.com/"
            headers_lobby["Sec-Fetch-Site"] = "none"
            
            resp_lobby = self.session.get(self.lobby_url, headers=headers_lobby)
            
            if "login.php" in resp_lobby.url:
                print(f"[ENGINE] ❌ SESSÃO INVÁLIDA. Necessário login manual.")
                return False

            self._extract_csrf(resp_lobby.text)

            # 2. Busca Link do Mundo
            soup = BeautifulSoup(resp_lobby.text, 'html.parser')
            target_href = None
            
            links = soup.find_all('a', href=True)
            for link in links:
                if f"play/{self.world_id}" in link['href']:
                    target_href = link['href']
                    break
            
            if target_href:
                final_url = f"{self.lobby_url}{target_href}" if target_href.startswith('/') else target_href

                time.sleep(random.uniform(1.2, 2.5))
                
                # 3. Clique com Referer do Lobby (Crucial)
                headers_enter = self.headers.copy()
                headers_enter["Referer"] = resp_lobby.url 
                headers_enter["Sec-Fetch-Site"] = "same-site"
                
                resp_enter = self.session.get(final_url, headers=headers_enter)
                
                if "game.php" in resp_enter.url:
                    print(f"[ENGINE] ✅ Sessão recuperada com sucesso!")
                    self._extract_csrf(resp_enter.text)
                    return True
                else:
                    print(f"[ENGINE] ❌ Falha na recuperação automática.")
            else:
                print(f"[ENGINE] ❌ Mundo {self.world_id} não encontrado no Lobby.")
                
            return False

        except Exception as e:
            print(f"[ENGINE ERROR] Erro no re-login: {e}")
            return False

    def safe_get(self, screen, params=None, extra_headers=None):
        url = f"{self.base_url}/game.php?screen={screen}"
        if params:
            for k, v in params.items():
                url += f"&{k}={v}"
        
        headers_req = self.headers.copy()
        headers_req["Referer"] = f"{self.base_url}/game.php"
        headers_req["Sec-Fetch-Site"] = "same-origin"
        
        # Injeta headers customizados (para o AJAX funcionar)
        if extra_headers:
            headers_req.update(extra_headers)

        try:
            time.sleep(random.uniform(0.6, 1.8))
            response = self.session.get(url, headers=headers_req, timeout=20)
            
            if "session_expired" in response.url or "login.php" in response.url:
                print("[ENGINE] Sessão caiu durante GET. Recuperando...")
                if self._reenter_world():
                     self.update_account_session() # Importante atualizar se recuperou
                     return self.session.get(url, headers=headers_req, timeout=20)
                return None

            self._extract_csrf(response.text)
            return response
        except Exception as e:
            print(f"[ENGINE ERROR] GET {screen}: {e}")
            return None

    def safe_get_absolute(self, full_url):
        """
        NOVO MÉTODO (CORRIGIDO): Acessa uma URL completa extraída do HTML.
        Trata URLs relativas forçando a adição do domínio base.
        """
        # 1. Se começar com /, adiciona o domínio base (ex: .tribalwars.com.br)
        if full_url.startswith("/"):
            # Remove a barra inicial para não duplicar se base_url tiver
            path = full_url.lstrip("/")
            full_url = f"{self.base_url}/{path}"
        
        # 2. Se NÃO começar com http (e não começou com /), assume que é relativo à pasta atual (game.php?...)
        elif not full_url.startswith("http"):
             full_url = f"{self.base_url}/{full_url}"

        headers_req = self.headers.copy()
        headers_req["Referer"] = f"{self.base_url}/game.php?screen=main"
        headers_req["Sec-Fetch-Site"] = "same-origin"
        
        try:
            time.sleep(random.uniform(0.8, 1.5))
            response = self.session.get(full_url, headers=headers_req, timeout=20)
            
            if "session_expired" in response.url or "login.php" in response.url:
                print("[ENGINE] Sessão caiu durante GET Absoluto. Recuperando...")
                if self._reenter_world():
                     self.update_account_session()
                     return self.session.get(full_url, headers=headers_req, timeout=20)
                return None

            self._extract_csrf(response.text)
            return response
        except Exception as e:
            print(f"[ENGINE ERROR] Absolute GET Crash: {e}")
            return None

    def safe_post(self, screen, data, params=None, extra_headers=None):
        url = f"{self.base_url}/game.php?screen={screen}"
        if params:
            for k, v in params.items():
                url += f"&{k}={v}"
        
        if self.csrf_token:
            data['h'] = self.csrf_token
            
        headers_req = self.headers.copy()
        headers_req["Referer"] = f"{self.base_url}/game.php"
        headers_req["Sec-Fetch-Site"] = "same-origin"
        
        if extra_headers:
            headers_req.update(extra_headers)

        try:
            time.sleep(random.uniform(1.0, 2.5))
            response = self.session.post(url, data=data, headers=headers_req)
            self._extract_csrf(response.text)
            return response
        except Exception as e:
            print(f"[ENGINE ERROR] POST {screen}: {e}")
            return None

    def _extract_csrf(self, html):
        try:
            # Token META (Lobby)
            match_meta = re.search(r'name="csrf-token" content="([a-f0-9]+)"', html)
            if match_meta:
                self.csrf_token = match_meta.group(1)
                return

            # Token JS (Jogo)
            match_js = re.search(r'csrf_token\s*=\s*[\'"]([a-f0-9]+)[\'"]', html)
            if match_js:
                self.csrf_token = match_js.group(1)
                return
            
            # Token JSON
            if '"csrf":"' in html:
                start = html.find('"csrf":"') + 8
                end = html.find('"', start)
                token = html[start:end]
                if token: self.csrf_token = token
        except:
            pass