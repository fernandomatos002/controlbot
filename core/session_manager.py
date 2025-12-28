import json
import os
from core.security import get_app_path, global_cipher # <--- IMPORTAÇÃO NOVA

SESSION_FILE = os.path.join(get_app_path(), "session.encrypted")

class SessionManager:
    def __init__(self):
        self.cipher = global_cipher # Usa a chave centralizada

    def save_session(self, user_data):
        try:
            if user_data is None: user_data = {}
            json_str = json.dumps(user_data)
            encrypted_data = self.cipher.encrypt(json_str.encode())
            
            with open(SESSION_FILE, "wb") as f:
                f.write(encrypted_data)
        except Exception as e:
            print(f"Erro ao salvar sessão: {e}")

    def load_session(self):
        if not os.path.exists(SESSION_FILE):
            return {} # Retorna vazio, não None

        try:
            with open(SESSION_FILE, "rb") as f:
                encrypted_data = f.read()
            
            if not encrypted_data: return {}

            decrypted_data = self.cipher.decrypt(encrypted_data).decode()
            return json.loads(decrypted_data)
        except Exception as e:
            print(f"Erro ao ler sessão: {e}")
            return {} # Se der erro de chave, reseta para vazio

    def logout(self):
        if os.path.exists(SESSION_FILE):
            try:
                os.remove(SESSION_FILE)
            except:
                pass

session = SessionManager()