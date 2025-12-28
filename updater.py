import flet as ft
import requests
import zipfile
import os
import io
import sys
import subprocess
import time
import threading

# --- CONFIGURAÇÕES ---
SERVER_URL = "http://162.220.14.199:8080" 
VERSION_URL = f"{SERVER_URL}/version.txt"
ZIP_URL = f"{SERVER_URL}/app.zip"
MAIN_EXE = "main.exe" 
LOCAL_VERSION_FILE = "version.txt"

def main(page: ft.Page):
    page.title = "Updater"
    page.window_width = 280
    page.window_height = 200
    page.window_resizable = False
    page.window_maximizable = False
    page.bgcolor = "#0f0f1e"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.padding = 15

    # --- ELEMENTOS DA TELA ---
    logo = ft.Icon(ft.Icons.DIAMOND, size=35, color="#27ae60")
    lbl_title = ft.Text("TRIBALCORE", weight="bold", size=14, color="white", font_family="Verdana")
    lbl_status = ft.Text("Iniciando...", color="#888", size=10, text_align="center")
    
    pb = ft.ProgressBar(width=180, color="#27ae60", bgcolor="#222", visible=False, height=4)

    # Botões de Erro
    btn_retry = ft.ElevatedButton(
        "Tentar Novamente", 
        color="white",
        bgcolor="#27ae60",
        visible=False,
        height=25,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=4), text_style=ft.TextStyle(size=10)),
        on_click=lambda e: reiniciar_verificacao()
    )
    
    btn_skip = ft.TextButton(
        "Ignorar", 
        visible=False,
        height=25,
        style=ft.ButtonStyle(color="white", text_style=ft.TextStyle(size=10)),
        on_click=lambda e: launch_app()
    )

    actions_container = ft.Column([btn_retry, btn_skip], spacing=2, horizontal_alignment="center")

    def mostrar_erro(msg):
        lbl_status.value = f"Erro: {msg}"[:30] + "..." 
        lbl_status.color = "#e74c3c"
        lbl_status.tooltip = msg 
        pb.visible = False
        btn_retry.visible = True
        btn_skip.visible = True
        page.update()

    def reiniciar_verificacao():
        btn_retry.visible = False
        btn_skip.visible = False
        lbl_status.value = "Verificando..."
        lbl_status.color = "#888"
        page.update()
        threading.Thread(target=check_updates, daemon=True).start()

    def launch_app():
        lbl_status.value = "Abrindo..."
        lbl_status.color = "#27ae60"
        btn_retry.visible = False
        btn_skip.visible = False
        page.update()
        
        # 1. Inicia o Bot Principal
        if os.path.exists(MAIN_EXE):
            subprocess.Popen([MAIN_EXE])
        elif os.path.exists("main.py"):
            subprocess.Popen([sys.executable, "main.py"])
        else:
            mostrar_erro("Executável não encontrado!")
            return

        # 2. ESCONDE A JANELA VISUALMENTE (Correção da tela branca)
        try:
            page.window_visible = False # Versões antigas
            page.window.visible = False # Versões novas
            page.update()
            time.sleep(0.5) # Dá tempo da janela sumir antes de matar o processo
        except:
            pass

        # 3. Mata o processo do Updater
        os._exit(0)

    def install_update():
        try:
            lbl_status.value = "Baixando..."
            lbl_status.color = "#27ae60"
            pb.visible = True
            page.update()

            response = requests.get(ZIP_URL, stream=True, timeout=15)
            if response.status_code != 200: raise Exception(f"HTTP {response.status_code}")

            total_length = int(response.headers.get('content-length', 0))
            content = io.BytesIO()
            dl = 0
            
            for data in response.iter_content(chunk_size=4096):
                dl += len(data)
                content.write(data)
                if total_length: pb.value = dl / total_length
                page.update()

            lbl_status.value = "Extraindo..."
            page.update()

            with zipfile.ZipFile(content) as zf:
                zf.extractall(".") 

            try:
                r_ver = requests.get(VERSION_URL, timeout=5)
                with open(LOCAL_VERSION_FILE, "w") as f:
                    f.write(r_ver.text.strip())
            except: pass

            launch_app()

        except Exception as e:
            mostrar_erro("Falha no Download")
            print(e)

    def check_updates():
        try:
            lbl_status.value = "Verificando..."
            pb.visible = True
            pb.value = None
            page.update()

            if not os.path.exists(LOCAL_VERSION_FILE):
                with open(LOCAL_VERSION_FILE, "w") as f: f.write("0.0.0")

            with open(LOCAL_VERSION_FILE, "r") as f:
                local_ver = f.read().strip()

            try:
                resp = requests.get(VERSION_URL, timeout=5)
                if resp.status_code == 200:
                    server_ver = resp.text.strip()
                else:
                    launch_app(); return
            except:
                launch_app(); return

            if server_ver != local_ver:
                lbl_status.value = "Atualizando..."
                page.update()
                install_update()
            else:
                launch_app()

        except Exception:
            launch_app()

    page.add(
        ft.Column([
            logo,
            lbl_title,
            ft.Container(height=5),
            lbl_status,
            ft.Container(height=5),
            pb,
            actions_container
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0)
    )

    threading.Thread(target=check_updates, daemon=True).start()

if __name__ == "__main__":
    ft.app(target=main)