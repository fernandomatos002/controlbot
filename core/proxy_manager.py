import re
import time
import uuid
import json
import os
import requests
import threading
from core.cloud_sync import cloud_sync
# Importa a segurança centralizada para usar a MESMA chave e caminho
from core.security import get_app_path, global_cipher

# Definição do caminho absoluto do arquivo de dados
DATA_FILE = os.path.join(get_app_path(), "proxies.encrypted")

class SecureStorage:
    def __init__(self):
        # Em vez de criar uma chave nova (o que causava o erro),
        # usa a chave global do sistema que já está carregada.
        self.cipher = global_cipher

    # A função _load_or_generate_key foi removida pois o core.security gerencia isso agora.

    def save(self, data):
        try:
            # Garante que não é None
            if data is None: data = []
            
            json_str = json.dumps(data)
            encrypted_data = self.cipher.encrypt(json_str.encode())
            
            with open(DATA_FILE, "wb") as df:
                df.write(encrypted_data)
        except Exception as e:
            print(f"Erro ao salvar proxies: {e}")

    def load(self):
        if not os.path.exists(DATA_FILE):
            return []
            
        try:
            with open(DATA_FILE, "rb") as df:
                encrypted_data = df.read()
            
            # Se arquivo vazio, retorna lista vazia
            if not encrypted_data: return []

            decrypted_data = self.cipher.decrypt(encrypted_data).decode()
            return json.loads(decrypted_data)
        except Exception as e:
            print(f"Erro ao ler proxies (resetando): {e}")
            return [] # Retorna vazio em caso de erro de criptografia


class ProxyManager:
    def __init__(self):
        self.storage = SecureStorage()

        # 1. Tentar carregar do servidor primeiro
        if cloud_sync.enabled:
            try:
                server_proxies = cloud_sync.load_proxies()
                if server_proxies is not None and len(server_proxies) > 0:
                    print("✅ Proxies carregados do SERVIDOR")
                    self.proxies = server_proxies
                    self._save_lock = threading.Lock()
                    return
            except Exception as e:
                print(f"Erro ao carregar proxies da nuvem: {e}")

        # 2. Fallback: carregar local
        self.proxies = self.storage.load()
        print("📁 Proxies carregados LOCALMENTE")
        self._save_lock = threading.Lock()

    def save_to_disk(self):
        with self._save_lock:    
            self.storage.save(self.proxies)

        # 2. Sincronizar com servidor (ASSÍNCRONO)
            if cloud_sync.enabled:
                proxies_copy = [p.copy() for p in self.proxies]
                threading.Thread(
                    target=cloud_sync.save_proxies,
                    args=(self.proxies,),
                    daemon=True
                ).start()

    def add_pending_proxies(self, raw_text):
        pattern = re.compile(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})[:\s](\d{2,5})(?:[:\s]([a-zA-Z0-9]+)[:\s]([a-zA-Z0-9]+))?')
        matches = pattern.findall(raw_text)

        new_entries = []
        for match in matches:
            ip, port, user, password = match
            if any(p['ip'] == ip and p['port'] == port for p in self.proxies):
                continue

            new_proxy = {
                "id": str(uuid.uuid4()),
                "ip": ip,
                "port": port,
                "user": user if user else None,
                "pass": password if password else None,
                "status": "testing", 
                "assigned_to": None,
                "latency": 0
            }
            self.proxies.append(new_proxy)
            new_entries.append(new_proxy)

        self.save_to_disk()
        return new_entries

    def test_proxy_connection(self, proxy, max_retries=3):
        """Testa conexão com tentativas antes de falhar"""
        
        # Monta a URL de teste
        if proxy.get('user') and proxy.get('pass'):
            url = f"http://{proxy['user']}:{proxy['pass']}@{proxy['ip']}:{proxy['port']}"
        else:
            url = f"http://{proxy['ip']}:{proxy['port']}"

        proxies_dict = {"http": url, "https": url}

        for attempt in range(1, max_retries + 1):
            try:
                print(f"📡 Testando proxy {proxy['ip']} (Tentativa {attempt}/{max_retries})...")
                start = time.time()
                
                # Timeout curto para não travar muito
                resp = requests.get("https://www.google.com", proxies=proxies_dict, timeout=8)
                end = time.time()

                if resp.status_code == 200:
                    proxy['status'] = "working"
                    proxy['latency'] = int((end - start) * 1000)
                    print(f"✅ Proxy {proxy['ip']} ONLINE ({proxy['latency']}ms)")
                    return # Sucesso, sai da função
                
            except Exception as e:
                print(f"⚠️ Falha na tentativa {attempt}: {e}")
                time.sleep(1.5) # Espera um pouco antes de tentar de novo

        # Se chegou aqui, falhou todas as vezes
        proxy['status'] = "error"
        print(f"❌ Proxy {proxy['ip']} marcado como ERROR após {max_retries} tentativas.")

    def assign_proxy(self, proxy_id, account_label):
        for p in self.proxies:
            if p['id'] == proxy_id:
                p['assigned_to'] = account_label
                break
        self.save_to_disk()

    def delete_proxy(self, proxy_id):
        self.proxies = [p for p in self.proxies if p['id'] != proxy_id]
        self.save_to_disk()


manager = ProxyManager()