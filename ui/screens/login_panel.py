import flet as ft
import time
import re
import requests
import uuid
import threading
from core.session_manager import session
from core.cloud_sync import cloud_sync

# --- IMPORTAÇÃO DOS GERENCIADORES ---
from core.account_manager import account_manager
from core.proxy_manager import manager as proxy_manager
from core.settings_manager import global_settings
import ui.styles as st

# --- CONFIGURAÇÃO ---
API_URL = "http://162.220.14.199" 
ICONS = ft.Icons

def get_hwid():
    return str(uuid.getnode())

def LoginScreen(page: ft.Page, on_login_success):
    page.title = "TribalCore - Autenticação"
    page.bgcolor = st.COLOR_BG
    # Removemos o alinhamento central forçado da página para controlar melhor no scroll
    page.vertical_alignment = ft.MainAxisAlignment.START 
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    # --- HELPER: INPUT PERSONALIZADO ---
    def criar_input_custom(label, icon_name, password=False, can_reveal=False, on_change=None):
        txt_field = ft.TextField(
            label=label,
            label_style=ft.TextStyle(color="grey", size=12),
            text_style=ft.TextStyle(color="white", size=13),
            cursor_color=st.COLOR_PRIMARY,
            bgcolor="#16161C",
            border_color=st.COLOR_BORDER,
            focused_border_color=st.COLOR_PRIMARY,
            border_radius=10,
            height=50,
            password=password,
            can_reveal_password=can_reveal,
            prefix_icon=icon_name,
            on_change=on_change,
            filled=True
        )
        return ft.Container(), txt_field

    # --- LOGO SECTION (GIGANTE) ---
    logo_section = ft.Container(
        content=ft.Column([
            # MUDANÇA: Tamanho aumentado de 80 para 160 (O Dobro)
            ft.Image(src="logo.png", width=160, height=160, fit=ft.ImageFit.CONTAIN, 
                     error_content=ft.Icon(ICONS.DIAMOND_OUTLINED, size=120, color=st.COLOR_PRIMARY)),
            ft.Row([
                ft.Text("TRIBAL", weight="900", size=32, color="white", font_family="Verdana", 
                        style=ft.TextStyle(letter_spacing=2)),
                ft.Text("CORE", weight="900", size=32, color=st.COLOR_PRIMARY, font_family="Verdana", 
                        style=ft.TextStyle(letter_spacing=2)),
            ], alignment="center", spacing=0),
            ft.Text("Enterprise Automation", size=14, color="grey", weight="bold", 
                    style=ft.TextStyle(letter_spacing=3))
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5),
        margin=ft.margin.only(bottom=10) # Margem reduzida
    )

    # ---------------------------------------------------------
    # TELA 1: LOGIN
    # ---------------------------------------------------------
    def show_login(e=None):
        page.clean()
        
        _, input_user = criar_input_custom("Usuário", ICONS.PERSON)
        _, input_pass = criar_input_custom("Senha", ICONS.LOCK, password=True, can_reveal=True)
        
        txt_error = ft.Text("", color=st.COLOR_ERROR, size=12, visible=False, text_align=ft.TextAlign.CENTER)
        loading_indicator = ft.ProgressRing(width=20, height=20, stroke_width=2, color="white", visible=False)
        btn_text = ft.Text("ENTRAR", size=14, weight="bold", color="white")

        def logar_backend(usuario, senha):
            try:
                hwid = get_hwid()
                payload = {"username": usuario, "password": senha, "hwid": hwid}
                response = requests.post(f"{API_URL}/auth/login", json=payload, timeout=8)
                
                if response.status_code == 200:
                    data = response.json()
                    if 'user_id' not in data: data['user_id'] = 1 
                    session.save_session(data)
                    sucesso_login(data)

                elif response.status_code == 403:
                    msg = response.json().get('detail', '')
                    if "outro computador" in msg: mostrar_erro("⛔ CONTA VINCULADA A OUTRO PC!")
                    elif "expirou" in msg: mostrar_erro("⛔ SUA LICENÇA EXPIROU!")
                    else: mostrar_erro(f"Acesso Negado: {msg}")
                else:
                    mostrar_erro("Usuário ou senha incorretos")
            except Exception as e:
                print(e)
                mostrar_erro("Erro de conexão com o servidor")
            
            resetar_botao()

        def sucesso_login(data):
            dias = data.get('days_remaining', 0)
            btn_text.value = f"✓ SUCESSO ({dias} dias)"
            login_btn.bgcolor = st.COLOR_SUCCESS
            loading_indicator.visible = False
            page.update()

            user_id = data.get('user_id')
            if user_id:
                cloud_sync.set_user(user_id)
                print(f"☁️ Sincronização ativada para user_id: {user_id}")
                print("🚀 Turbo Sync: Baixando todos os dados...")
                all_configs = cloud_sync.load_all()
                
                if all_configs:
                    if 'accounts' in all_configs: account_manager.accounts = all_configs['accounts']
                    if 'proxies' in all_configs: proxy_manager.proxies = all_configs['proxies']
                    if 'settings' in all_configs: global_settings.settings = all_configs['settings']
                    print("✅ Dados sincronizados.")
                else:
                    print("⚠️ Nenhum dado na nuvem.")

            time.sleep(0.5)
            on_login_success(data)

        def mostrar_erro(msg):
            txt_error.value = msg
            txt_error.visible = True
            page.update()

        def resetar_botao():
            login_btn.disabled = False
            loading_indicator.visible = False
            btn_text.opacity = 1
            if "SUCESSO" not in btn_text.value: btn_text.value = "ENTRAR"
            try: page.update()
            except: pass

        def on_click_login(e):
            if not input_user.value or not input_pass.value:
                mostrar_erro("Preencha todos os campos")
                return
            
            txt_error.visible = False
            login_btn.disabled = True
            loading_indicator.visible = True
            btn_text.opacity = 0.5
            page.update()
            threading.Thread(target=logar_backend, args=(input_user.value, input_pass.value)).start()

        login_btn = ft.Container(
            content=ft.Row([loading_indicator, btn_text], alignment=ft.MainAxisAlignment.CENTER, spacing=10),
            bgcolor=st.COLOR_PRIMARY, 
            border_radius=10, 
            height=50,
            on_click=on_click_login,
            ink=True
        )

        form_container = ft.Container(
            content=ft.Column([
                input_user, ft.Container(height=5), input_pass, txt_error,
                ft.Container(height=10), login_btn, ft.Container(height=20),
                ft.Row([
                    ft.TextButton("Recuperar Senha", style=ft.ButtonStyle(color=st.COLOR_PRIMARY), on_click=show_reset),
                    ft.Text("|", color="#333"),
                    ft.TextButton("Registrar", style=ft.ButtonStyle(color=st.COLOR_PRIMARY), on_click=show_register),
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(height=10),
                ft.Text(f"Device ID: {get_hwid()}", size=10, color="#333", text_align=ft.TextAlign.CENTER)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=40, bgcolor=st.COLOR_SURFACE, border_radius=20,
            border=ft.border.all(1, st.COLOR_BORDER), width=400
        )
        renderizar_tela(form_container)

    # ---------------------------------------------------------
    # TELA 2: REGISTRO
    # ---------------------------------------------------------
    def show_register(e=None):
        page.clean()
        
        txt_val_email = ft.Text("• Email válido", size=11, color="grey")
        txt_val_user = ft.Text("• Sem espaços", size=11, color="grey")
        txt_val_len = ft.Text("• Mínimo 8 caracteres", size=11, color="grey")
        txt_val_upper = ft.Text("• 1 Letra Maiúscula", size=11, color="grey")
        txt_val_match = ft.Text("• Senhas conferem", size=11, color="grey")
        txt_status = ft.Text("", size=12, text_align=ft.TextAlign.CENTER)

        def validar(e=None):
            val_email = inp_email.value
            val_user = inp_user.value
            val_pass = inp_pass.value
            val_conf = inp_conf.value
            valid_ok = True

            if re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", val_email):
                txt_val_email.color = st.COLOR_SUCCESS; txt_val_email.value = "✓ Email válido"
            else:
                txt_val_email.color = "grey"; txt_val_email.value = "• Email válido"; valid_ok = False

            if val_user and " " not in val_user and len(val_user) > 2:
                txt_val_user.color = st.COLOR_SUCCESS; txt_val_user.value = "✓ Sem espaços"
            else:
                txt_val_user.color = "grey"; txt_val_user.value = "• Sem espaços"; valid_ok = False

            if len(val_pass) >= 8:
                txt_val_len.color = st.COLOR_SUCCESS; txt_val_len.value = "✓ Mínimo 8 caracteres"
            else:
                txt_val_len.color = "grey"; txt_val_len.value = "• Mínimo 8 caracteres"; valid_ok = False
            
            if re.search(r"[A-Z]", val_pass):
                txt_val_upper.color = st.COLOR_SUCCESS; txt_val_upper.value = "✓ 1 Letra Maiúscula"
            else:
                txt_val_upper.color = "grey"; txt_val_upper.value = "• 1 Letra Maiúscula"; valid_ok = False

            if val_pass and val_conf and val_pass == val_conf:
                txt_val_match.color = st.COLOR_SUCCESS; txt_val_match.value = "✓ Senhas conferem"
            else:
                txt_val_match.color = "grey"; txt_val_match.value = "• Senhas conferem"; valid_ok = False

            if valid_ok:
                btn_reg.disabled = False
                btn_reg.bgcolor = st.COLOR_PRIMARY
                btn_reg.opacity = 1
            else:
                btn_reg.disabled = True
                btn_reg.bgcolor = "#333"
                btn_reg.opacity = 0.5
            page.update()

        _, inp_email = criar_input_custom("Email", ICONS.EMAIL, on_change=validar)
        _, inp_user = criar_input_custom("Usuário", ICONS.PERSON, on_change=validar)
        _, inp_pass = criar_input_custom("Senha", ICONS.LOCK, password=True, on_change=validar)
        _, inp_conf = criar_input_custom("Confirmar Senha", ICONS.LOCK_CLOCK, password=True, on_change=validar)

        def registrar_thread():
            try:
                payload = {"username": inp_user.value, "password": inp_pass.value, "email": inp_email.value}
                resp = requests.post(f"{API_URL}/admin/create-user", json=payload, timeout=5)
                if resp.status_code == 200:
                    set_status("Conta Criada! Redirecionando...", st.COLOR_SUCCESS)
                    time.sleep(2); show_login()
                elif resp.status_code == 500:
                    set_status("Erro: Usuário ou Email já existem", st.COLOR_ERROR)
                else:
                    set_status(f"Erro: {resp.text}", st.COLOR_ERROR)
            except:
                set_status("Erro de Conexão", st.COLOR_ERROR)
            reset_btn()

        def set_status(msg, color):
            txt_status.value = msg; txt_status.color = color; page.update()

        def reset_btn():
            btn_text.value = "CRIAR CONTA"; validar(); page.update()

        btn_text = ft.Text("CRIAR CONTA", size=14, weight="bold", color="white")
        btn_reg = ft.Container(
            content=ft.Row([btn_text], alignment=ft.MainAxisAlignment.CENTER),
            bgcolor="#333", border_radius=12, height=50, disabled=True, opacity=0.5,
            on_click=lambda e: threading.Thread(target=registrar_thread).start()
        )

        form_container = ft.Container(
            content=ft.Column([
                ft.Text("Nova Conta", size=24, weight="bold", color="white"),
                ft.Container(height=10),
                inp_email, ft.Container(content=txt_val_email, margin=ft.margin.only(top=-10, bottom=5)),
                inp_user, ft.Container(content=txt_val_user, margin=ft.margin.only(top=-10, bottom=5)),
                inp_pass, ft.Container(content=ft.Row([txt_val_len, txt_val_upper], spacing=10), margin=ft.margin.only(top=-10, bottom=5)),
                inp_conf, ft.Container(content=txt_val_match, margin=ft.margin.only(top=-10, bottom=5)),
                txt_status, ft.Container(height=10),
                btn_reg, ft.Container(height=10),
                ft.TextButton("Voltar", style=ft.ButtonStyle(color="grey"), on_click=show_login)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=40, bgcolor=st.COLOR_SURFACE, border_radius=20, border=ft.border.all(1, st.COLOR_BORDER), width=400
        )
        renderizar_tela(form_container)

    # ---------------------------------------------------------
    # TELA 3: RECUPERAR SENHA
    # ---------------------------------------------------------
    def show_reset(e=None):
        page.clean()
        email_digitado = ""
        txt_status = ft.Text("", size=12, text_align=ft.TextAlign.CENTER)
        area_dinamica = ft.Column()

        def enviar_codigo_thread(email):
            nonlocal email_digitado
            email_digitado = email
            try:
                resp = requests.post(f"{API_URL}/auth/forgot-password", json={"email": email}, timeout=5)
                if resp.status_code == 200: montar_estagio_2()
                elif resp.status_code == 404: set_status("⛔ E-mail não encontrado", st.COLOR_ERROR)
                else: set_status("Erro ao enviar código", st.COLOR_ERROR)
            except: set_status("Erro de conexão", st.COLOR_ERROR)
            reset_btn_env()

        def confirmar_thread(code, new_pass):
            try:
                payload = {"email": email_digitado, "code": code, "new_password": new_pass}
                resp = requests.post(f"{API_URL}/auth/reset-password", json=payload, timeout=5)
                if resp.status_code == 200:
                    set_status("Senha Alterada! Login...", st.COLOR_SUCCESS)
                    time.sleep(2); show_login()
                else: set_status("Código inválido", st.COLOR_ERROR)
            except: set_status("Erro de conexão", st.COLOR_ERROR)

        def set_status(msg, color):
            txt_status.value = msg; txt_status.color = color; page.update()

        txt_val_email = ft.Text("• Formato válido", size=11, color="grey")

        def validar_email(e):
            val = inp_email.value
            if re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", val):
                txt_val_email.value = "✓ Formato válido"; txt_val_email.color = st.COLOR_SUCCESS
                btn_env.disabled = False; btn_env.bgcolor = st.COLOR_PRIMARY; btn_env.opacity = 1
            else:
                txt_val_email.value = "• Formato válido"; txt_val_email.color = "grey"
                btn_env.disabled = True; btn_env.bgcolor = "#333"; btn_env.opacity = 0.5
            page.update()

        _, inp_email = criar_input_custom("Seu Email", ICONS.EMAIL, on_change=validar_email)
        btn_text_env = ft.Text("ENVIAR CÓDIGO", size=14, weight="bold", color="white")
        
        def reset_btn_env():
             btn_text_env.value = "ENVIAR CÓDIGO"; validar_email(None); page.update()

        btn_env = ft.Container(
            content=ft.Row([btn_text_env], alignment=ft.MainAxisAlignment.CENTER),
            bgcolor="#333", border_radius=12, height=50, disabled=True, opacity=0.5,
            on_click=lambda e: threading.Thread(target=enviar_codigo_thread, args=(inp_email.value,)).start()
        )
        area_dinamica.controls = [
            inp_email, ft.Container(content=txt_val_email, margin=ft.margin.only(top=-10, bottom=5)),
            ft.Container(height=10), btn_env
        ]

        def montar_estagio_2():
            txt_val_len = ft.Text("• Mínimo 8 caracteres", size=11, color="grey")
            
            def validar_reset(e=None):
                if len(inp_new.value) >= 8: btn_alt.disabled = False; btn_alt.bgcolor = st.COLOR_PRIMARY; btn_alt.opacity = 1
                else: btn_alt.disabled = True; btn_alt.bgcolor = "#333"; btn_alt.opacity = 0.5
                page.update()

            _, inp_code = criar_input_custom("Código (6 dígitos)", ICONS.KEY)
            _, inp_new = criar_input_custom("Nova Senha", ICONS.LOCK_RESET, password=True, on_change=validar_reset)
            
            btn_alt = ft.Container(
                content=ft.Row([ft.Text("ALTERAR SENHA", size=14, weight="bold", color="white")], alignment=ft.MainAxisAlignment.CENTER),
                bgcolor="#333", border_radius=12, height=50, disabled=True, opacity=0.5,
                on_click=lambda e: threading.Thread(target=confirmar_thread, args=(inp_code.value, inp_new.value)).start()
            )
            
            area_dinamica.controls = [
                ft.Text(f"Código enviado para: {email_digitado}", size=12, color="grey"),
                ft.Container(height=10), inp_code, inp_new, ft.Container(height=10), btn_alt
            ]
            txt_status.value = ""; page.update()

        form_container = ft.Container(
            content=ft.Column([
                ft.Text("Recuperar Acesso", size=24, weight="bold", color="white"),
                ft.Container(height=20), area_dinamica, ft.Container(height=10), txt_status,
                ft.Container(height=10),
                ft.TextButton("Voltar", style=ft.ButtonStyle(color="grey"), on_click=show_login)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=40, bgcolor=st.COLOR_SURFACE, border_radius=20, border=ft.border.all(1, st.COLOR_BORDER), width=400
        )
        renderizar_tela(form_container)

    # --- UTILITÁRIOS (MUDANÇA AQUI: REMOVIDO ESPAÇADOR SUPERIOR) ---
    def renderizar_tela(card):
        coluna_principal = ft.Column(
            controls=[
                logo_section, # Logo vem primeiro, sem espaçador em cima
                ft.Container(height=10), 
                card
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER # Centraliza tudo verticalmente
        )
        scroll_container = ft.Column(
            controls=[coluna_principal], scroll=ft.ScrollMode.AUTO, expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER # Garante centro mesmo com scroll
        )
        page.add(scroll_container)

    show_login()