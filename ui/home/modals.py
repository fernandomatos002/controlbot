import flet as ft
import time
import ui.styles as st
from core.account_manager import account_manager
from core.proxy_manager import manager as proxy_manager

# --- MODAL DE LOGS ---
class LogsModal(ft.AlertDialog):
    def __init__(self, close_callback):
        self.lv_logs = ft.ListView(expand=True, spacing=2, auto_scroll=True, padding=10)
        super().__init__(
            bgcolor="#0f0f15", 
            title_padding=10, 
            content_padding=0,
            title=ft.Text("Logs do Sistema", font_family="Consolas", size=14, weight="bold"),
            content=ft.Container(
                width=600, 
                height=400, 
                content=self.lv_logs, 
                bgcolor="black", 
                border=ft.border.all(1, "#333"),
                border_radius=0
            ),
            actions=[
                ft.TextButton("Fechar", on_click=close_callback, style=ft.ButtonStyle(color="grey"))
            ]
        )

    def render_logs(self, acc):
        self.lv_logs.controls.clear()
        for log in acc.get('logs', []):
            c = "white"
            if log['type'] == 'error': c = st.COLOR_ERROR
            elif log['type'] == 'success': c = st.COLOR_SUCCESS
            elif log['type'] == 'warn': c = st.COLOR_WARNING
            
            self.lv_logs.controls.append(
                ft.Text(f"[{log['time']}] > {log['msg']}", color=c, size=12, font_family="Consolas")
            )

# --- MODAL ADICIONAR CONTA (MELHORADO) ---
class AddAccountModal(ft.AlertDialog):
    def __init__(self, page, close_callback, on_save_callback):
        self.page_ref = page
        self.on_save = on_save_callback
        
        # --- ESTADO ---
        self.selected_server = "BR"
        self.selected_server_mass = "BR"
        
        # --- ABA 1: CONTA ÚNICA ---
        self.txt_user = st.get_input_style("Usuário", height=45)
        self.txt_pass = st.get_input_style("Senha", height=45)
        self.txt_world = st.get_input_style("Mundo", hint="Ex: 120", height=45)
        
        self.dd_proxy = ft.Dropdown(
            label="Proxy",
            text_size=13,
            filled=True,
            bgcolor="#1a1a25",
            border_color=st.COLOR_PRIMARY,
            label_style=ft.TextStyle(color="grey", size=12),
            focused_border_color=st.COLOR_PRIMARY,
            border_radius=10,
            content_padding=15
        )
        
        self.btn_br = self._create_server_btn("🇧🇷 BR", "BR", True)
        self.btn_pt = self._create_server_btn("🇵🇹 PT", "PT", False)
        
        # --- ABA 2: CONTA EM MASSA ---
        self.txt_import = ft.TextField(
            multiline=True,
            min_lines=10,
            max_lines=10,
            text_size=12,
            hint_text="login1:senha1\nlogin2:senha2\nlogin3:senha3",
            hint_style=ft.TextStyle(color="#444", font_family="Consolas"),
            text_style=ft.TextStyle(font_family="Consolas", color=st.COLOR_PRIMARY),
            bgcolor="#0B0B0F",
            border_color=st.COLOR_BORDER,
            cursor_color=st.COLOR_PRIMARY,
            filled=True,
            border_radius=8,
            content_padding=15
        )
        
        self.txt_world_mass = st.get_input_style("Mundo", hint="Ex: 120", height=45)
        
        self.btn_br_mass = self._create_server_btn("🇧🇷 BR", "BR", True, is_mass=True)
        self.btn_pt_mass = self._create_server_btn("🇵🇹 PT", "PT", False, is_mass=True)
        
        self.chk_auto_proxy = ft.Checkbox(
            label="Auto-atribuir proxies livres",
            label_style=ft.TextStyle(color="white", size=13),
            active_color=st.COLOR_PRIMARY,
            value=True
        )
        
        # --- ABAS ---
        self.tabs = ft.Tabs(
            selected_index=0,
            tabs=[
                ft.Tab(
                    text="CONTA ÚNICA",
                    content=ft.Container(
                        padding=20,
                        content=ft.Column([
                            ft.Text("Adicionar Uma Conta", size=16, weight="bold", color="white"),
                            ft.Divider(height=15, color="transparent"),
                            self.txt_user,
                            ft.Container(height=5),
                            self.txt_pass,
                            ft.Container(height=5),
                            self.txt_world,
                            ft.Container(height=10),
                            ft.Text("Servidor:", size=12, weight="bold", color="white"),
                            ft.Row([self.btn_br, self.btn_pt], alignment=ft.MainAxisAlignment.CENTER, spacing=15),
                            ft.Container(height=10),
                            ft.Text("Proxy:", size=12, weight="bold", color="white"),
                            self.dd_proxy
                        ], spacing=0, tight=True)
                    )
                ),
                ft.Tab(
                    text="EM MASSA",
                    content=ft.Container(
                        padding=20,
                        content=ft.Column([
                            ft.Text("Adicionar Múltiplas Contas", size=16, weight="bold", color="white"),
                            ft.Divider(height=10, color="transparent"),
                            ft.Text("Formato: login:senha (uma por linha)", size=11, color="grey", italic=True),
                            ft.Container(height=5),
                            self.txt_import,
                            ft.Container(height=10),
                            self.txt_world_mass,
                            ft.Container(height=10),
                            ft.Text("Servidor:", size=12, weight="bold", color="white"),
                            ft.Row([self.btn_br_mass, self.btn_pt_mass], alignment=ft.MainAxisAlignment.CENTER, spacing=15),
                            ft.Container(height=10),
                            self.chk_auto_proxy
                        ], spacing=0, tight=True)
                    )
                )
            ],
            expand=True
        )
        
        super().__init__(
            bgcolor=st.COLOR_SURFACE,
            shape=ft.RoundedRectangleBorder(radius=15),
            modal=True,
            title=ft.Row([
                ft.Icon(ft.Icons.PERSON_ADD, color=st.COLOR_PRIMARY, size=24),
                ft.Text("Adicionar Contas", size=20, weight="bold", color="white"),
                ft.IconButton(ft.Icons.CLOSE, icon_color="grey", on_click=lambda e: self._close())
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            content=ft.Container(
                width=500,
                height=550,
                bgcolor=st.COLOR_SURFACE,
                content=self.tabs
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self._close(), style=ft.ButtonStyle(color="#888")),
                ft.ElevatedButton(
                    "PROCESSAR",
                    on_click=lambda e: self._on_save(e),
                    bgcolor=st.COLOR_PRIMARY,
                    color="black",
                    style=ft.ButtonStyle(padding=15, text_style=ft.TextStyle(weight="bold"))
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
    
    def _create_server_btn(self, label, code, is_default, is_mass=False):
        """Cria botão de servidor estilizado"""
        btn = ft.Container(
            content=ft.Text(label, size=16, weight="bold", color="black" if is_default else "grey"),
            bgcolor=st.COLOR_PRIMARY if is_default else "#1a1a25",
            border=ft.border.all(2, st.COLOR_PRIMARY if is_default else "#333"),
            border_radius=8,
            padding=ft.padding.symmetric(vertical=12, horizontal=24),
            alignment=ft.alignment.center,
            width=90,
            height=45,
            ink=True,
            on_click=lambda e: self._set_server(code, is_mass)
        )
        return btn
    
    def _set_server(self, code, is_mass=False):
        """Muda servidor selecionado"""
        if is_mass:
            self.selected_server_mass = code
            self._update_server_ui_mass()
        else:
            self.selected_server = code
            self._update_server_ui()
    
    def _update_server_ui(self):
        """Atualiza visual dos botões de servidor (Aba 1)"""
        is_br = self.selected_server == "BR"
        
        self.btn_br.bgcolor = st.COLOR_PRIMARY if is_br else "#1a1a25"
        self.btn_br.border = ft.border.all(2, st.COLOR_PRIMARY if is_br else "#333")
        self.btn_br.content.color = "black" if is_br else "grey"
        
        self.btn_pt.bgcolor = st.COLOR_PRIMARY if not is_br else "#1a1a25"
        self.btn_pt.border = ft.border.all(2, st.COLOR_PRIMARY if not is_br else "#333")
        self.btn_pt.content.color = "black" if not is_br else "grey"
        
        if self.page_ref: self.page_ref.update()
    
    def _update_server_ui_mass(self):
        """Atualiza visual dos botões de servidor (Aba 2)"""
        is_br = self.selected_server_mass == "BR"
        
        self.btn_br_mass.bgcolor = st.COLOR_PRIMARY if is_br else "#1a1a25"
        self.btn_br_mass.border = ft.border.all(2, st.COLOR_PRIMARY if is_br else "#333")
        self.btn_br_mass.content.color = "black" if is_br else "grey"
        
        self.btn_pt_mass.bgcolor = st.COLOR_PRIMARY if not is_br else "#1a1a25"
        self.btn_pt_mass.border = ft.border.all(2, st.COLOR_PRIMARY if not is_br else "#333")
        self.btn_pt_mass.content.color = "black" if not is_br else "grey"
        
        if self.page_ref: self.page_ref.update()
    
    def _close(self):
        """Fecha o modal"""
        self.open = False
        if self.page_ref: self.page_ref.update()
    
    def prepare_and_open(self):
        """Prepara dados e abre o modal"""
        self._refresh_proxy_list()
        self.txt_user.value = ""
        self.txt_pass.value = ""
        self.txt_world.value = ""
        self.txt_import.value = ""
        self.txt_world_mass.value = ""
        self.selected_server = "BR"
        self.selected_server_mass = "BR"
        self.chk_auto_proxy.value = True
        self._update_server_ui()
        self._update_server_ui_mass()
        self.open = True
        if self.page_ref: self.page_ref.update()
    
    def _refresh_proxy_list(self):
        """Atualiza lista de proxies disponíveis (livres)"""
        free_proxies = [
            ft.dropdown.Option(p['id'], f"{p['ip']}:{p['port']}")
            for p in proxy_manager.proxies
            if p['status'] == 'working' and (not p.get('assigned_to') or p['assigned_to'] is None)
        ]
        self.dd_proxy.options = [ft.dropdown.Option("none", "Sem Proxy (IP Local)")] + free_proxies
        self.dd_proxy.value = "none"
    
    def _on_save(self, e):
        try:
            print("[DEBUG] _on_save() iniciado - Tab index:", self.tabs.selected_index)
            if self.tabs.selected_index == 0:
                self._save_single()
            else:
                self._save_mass()
        except Exception as ex:
            print(f"❌ ERRO CRÍTICO: {ex}")
            import traceback
            traceback.print_exc()
            self._show_error(f"Erro: {str(ex)}")
    
    def _save_single(self):
        """Salva uma conta única (CORRIGIDO)"""
        if not self.txt_user.value or not self.txt_pass.value or not self.txt_world.value:
            self._show_error("Preencha todos os campos!")
            return
        
        world = self.txt_world.value.lower()
        if not world.startswith(self.selected_server.lower()):
            world = self.selected_server.lower() + world
        
        account_manager.add_account(
            world=world,
            username=self.txt_user.value,
            proxy_id=self.dd_proxy.value,
            server_region=self.selected_server,
            password=self.txt_pass.value
        )
        
        if self.dd_proxy.value and self.dd_proxy.value != "none":
            new_acc = next((a for a in account_manager.accounts if a['username'] == self.txt_user.value), None)
            if new_acc:
                for p in proxy_manager.proxies:
                    if p['id'] == self.dd_proxy.value:
                        p['assigned_to'] = new_acc['id']
                proxy_manager.save_to_disk()
        
        self._close()
        self.on_save()
        self._show_success(f"✅ Conta {self.txt_user.value} adicionada!")


    def _show_modal_proxy_warning(self, needed, available):
        """Mostra aviso de proxies insuficientes com opção para continuar"""
        
        # Cria o conteúdo do snackbar
        self.page_ref.snack_bar = ft.SnackBar(
            content=ft.Container(
                padding=15,
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, size=24, color=st.COLOR_WARNING),
                        ft.Column([
                            ft.Text("⚠️ Proxies Insuficientes!", weight="bold", size=14, color="white"),
                            ft.Text(f"Precisa de {needed}, tem apenas {available} disponíveis", 
                                   size=11, color="grey")
                        ], spacing=2, expand=True)
                    ], spacing=10)
                ], spacing=10)
            ),
            bgcolor="#1a1a25",
            duration=5000,  # 5 segundos
            action="Continuar SEM Proxies",
            action_color=st.COLOR_PRIMARY,
            on_action=lambda e: self._save_mass_without_proxy(None)
        )
        
        self.page_ref.snack_bar.open = True
        self.page_ref.update()
        
        print(f"[DEBUG] SnackBar de aviso exibido: {needed} contas vs {available} proxies")

    def _save_mass_without_proxy(self, dlg):
        """Salva contas sem atribuir proxies automaticamente"""
        print("[DEBUG] _save_mass_without_proxy() chamado")
        
        auto_proxy_backup = self.chk_auto_proxy.value
        self.chk_auto_proxy.value = False
        
        print(f"[DEBUG] Auto-proxy desativado temporariamente: {self.chk_auto_proxy.value}")
        
        try:
            self._save_mass()
        finally:
            self.chk_auto_proxy.value = auto_proxy_backup
            self.chk_auto_proxy.update()
            print(f"[DEBUG] Auto-proxy restaurado: {self.chk_auto_proxy.value}")

    def _save_mass(self):
        """Salva múltiplas contas em massa (CORRIGIDO)"""
        print("[DEBUG] _save_mass() INICIADO")  # ✅ PRINT 1
        
        import_text = self.txt_import.value.strip()
        world = self.txt_world_mass.value.strip()
        
        print(f"[DEBUG] Import length: {len(import_text)}, World: {world}")  # ✅ PRINT 2
        
        if not import_text:
            print("[DEBUG] Import vazio - RETORNANDO")  # ✅ PRINT 3
            self._show_error("Cole a lista de contas!")
            return
        
        if not world:
            print("[DEBUG] World vazio - RETORNANDO")  # ✅ PRINT 4
            self._show_error("Digite o mundo!")
            return
        
        lines = [l.strip() for l in import_text.split('\n') if l.strip()]
        accounts_to_add = []
        
        print(f"[DEBUG] Total de linhas: {len(lines)}")  # ✅ PRINT 5
        
        i = 0
        while i < len(lines):
            line = lines[i]
            username = None
            password = None
            
            if ':' in line and not line.lower().startswith('nickname') and not line.lower().startswith('senha'):
                parts = line.split(':', 1)
                if len(parts) == 2:
                    username, password = parts[0].strip(), parts[1].strip()
                    i += 1
            
            elif line.lower().startswith('nickname'):
                if ':' in line:
                    username = line.split(':', 1)[1].strip()
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    if next_line.lower().startswith('senha'):
                        if ':' in next_line:
                            password = next_line.split(':', 1)[1].strip()
                        i += 2
                    else:
                        i += 1
                else:
                    i += 1
            
            else:
                username = line
                if i + 1 < len(lines):
                    password = lines[i + 1].strip()
                    i += 2
                else:
                    i += 1
            
            if username and password:
                accounts_to_add.append((username, password))
                print(f"[DEBUG] Conta parseada: {username}")  # ✅ PRINT 6
            
        print(f"[DEBUG] Total de contas parseadas: {len(accounts_to_add)}")  # ✅ PRINT 7
        
        if not accounts_to_add:
            print("[DEBUG] Nenhuma conta válida - RETORNANDO")  # ✅ PRINT 8
            self._show_error("Nenhuma conta válida encontrada!")
            return
        
        print(f"[DEBUG] Auto-proxy ativado? {self.chk_auto_proxy.value}")  # ✅ PRINT 9
        
        if self.chk_auto_proxy.value:
            free_proxies = [
                p for p in proxy_manager.proxies
                if p['status'] == 'working' and (not p.get('assigned_to') or p['assigned_to'] is None)
            ]
            print(f"[DEBUG] Proxies livres: {len(free_proxies)}, Contas: {len(accounts_to_add)}")
            
            if len(free_proxies) < len(accounts_to_add):
                print(f"[DEBUG] MOSTRANDO AVISO - Faltam {len(accounts_to_add) - len(free_proxies)} proxies")
                self._show_modal_proxy_warning(len(accounts_to_add), len(free_proxies))
                return
        
        print("[DEBUG] Iniciando loop de adição de contas")  # ✅ PRINT 14
        
        world = world.lower()
        if not world.startswith(self.selected_server_mass.lower()):
            world = self.selected_server_mass.lower() + world
        
        proxy_idx = 0
        free_proxies = [
            p for p in proxy_manager.proxies
            if p['status'] == 'working' and (not p.get('assigned_to') or p['assigned_to'] is None)
        ] if self.chk_auto_proxy.value else []
        
        for username, password in accounts_to_add:
            print(f"[DEBUG] Adicionando: {username}")  # ✅ PRINT 15
            
            proxy_id = "none"
            
            if self.chk_auto_proxy.value and proxy_idx < len(free_proxies):
                proxy_id = free_proxies[proxy_idx]['id']
                proxy_idx += 1
            
            new_acc = account_manager.add_account(
                world=world, 
                username=username, 
                proxy_id=proxy_id, 
                server_region=self.selected_server_mass,
                password=password
            )
            
            if proxy_id != "none":
                for p in proxy_manager.proxies:
                    if p['id'] == proxy_id:
                        p['assigned_to'] = new_acc['id']
        
        print("[DEBUG] Salvando dados em disco")  # ✅ PRINT 16
        
        account_manager.save()
        proxy_manager.save_to_disk()
        
        print("[DEBUG] Fechando modal e recarregando")  # ✅ PRINT 17
        
        self._close()
        self.on_save()
        
        print("[DEBUG] Mostrando mensagem de sucesso")  # ✅ PRINT 18
        
        self._show_success(f"✅ {len(accounts_to_add)} contas adicionadas com sucesso!")
        
        print("[DEBUG] _save_mass() FINALIZADO COM SUCESSO")  # ✅ PRINT 19

    def _show_error(self, msg):
        """Mostra erro em snackbar"""
        if self.page_ref:
            self.page_ref.snack_bar = ft.SnackBar(
                ft.Text(msg, color="white", weight="bold"),
                bgcolor=st.COLOR_ERROR
            )
            self.page_ref.snack_bar.open = True
            self.page_ref.update()
    
    def _show_success(self, msg):
        """Mostra sucesso em snackbar"""
        if self.page_ref:
            self.page_ref.snack_bar = ft.SnackBar(
                ft.Text(msg, color="black", weight="bold"),
                bgcolor=st.COLOR_SUCCESS
            )
            self.page_ref.snack_bar.open = True
            self.page_ref.update()

# --- MODAL COLETA ---
class ScavengeModal(ft.AlertDialog):
    def __init__(self, close_callback):
        self.content_col = ft.Column(spacing=10, tight=True)
        self.current_acc = None
        
        super().__init__(
            bgcolor="#0f0f15",
            title=ft.Text("Detalhes da Coleta", size=18, weight="bold", font_family="Verdana"),
            content=ft.Container(
                width=350,
                padding=10,
                content=self.content_col
            ),
            actions=[ft.TextButton("Fechar", on_click=close_callback)]
        )

    def render(self, acc):
        self.current_acc = acc
        self.content_col.controls.clear()
        
        s_data = acc.get('scavenge_data', {})
        levels = s_data.get('levels', {})
        
        if not levels:
            self.content_col.controls.append(ft.Text("Sem dados de coleta recentes.", color="grey"))
            return

        now = time.time()

        for lvl_id in sorted(levels.keys(), key=lambda x: int(x)):
            info = levels[lvl_id]
            status = info['status']
            end_time = info.get('end_time')
            
            icon = ft.Icons.LOCK
            color = "grey"
            text_status = "BLOQUEADO"
            
            if status == "unlocking":
                icon = ft.Icons.LOCK_OPEN
                color = st.COLOR_WARNING
                remaining = int(end_time) - now if end_time else 0
                if remaining < 0: remaining = 0
                m, s = divmod(remaining, 60)
                h, m = divmod(m, 60)
                text_status = f"DESBLOQUEANDO: {int(h):02d}:{int(m):02d}:{int(s):02d}"

            elif status == "scavenging":
                icon = ft.Icons.TIMELAPSE
                color = st.COLOR_SUCCESS
                remaining = int(end_time) - now if end_time else 0
                if remaining < 0: remaining = 0
                m, s = divmod(remaining, 60)
                h, m = divmod(m, 60)
                text_status = f"RETORNA EM: {int(h):02d}:{int(m):02d}:{int(s):02d}"

            elif status == "idle":
                icon = ft.Icons.CHECK_CIRCLE_OUTLINE
                color = st.COLOR_ACCENT
                text_status = "DISPONÍVEL"

            card = ft.Container(
                bgcolor="#1a1a25",
                padding=10,
                border_radius=8,
                border=ft.border.all(1, color if status != 'locked' else "#333"),
                content=ft.Row([
                    ft.Container(
                        content=ft.Text(str(lvl_id), weight="bold", color="black"),
                        bgcolor=color, width=25, height=25, border_radius=12.5, alignment=ft.alignment.center
                    ),
                    ft.Column([
                        ft.Text(text_status, color=color, weight="bold", size=12),
                        ft.ProgressBar(value=None, color=color, bgcolor="#222", height=2) if status in ['scavenging', 'unlocking'] else ft.Container()
                    ], expand=True),
                    ft.Icon(icon, color=color, size=18)
                ], alignment="spaceBetween")
            )
            self.content_col.controls.append(card)

# --- MODAL EDITAR CONTA (CORRIGIDO) ---
class EditAccountModal(ft.AlertDialog):
    def __init__(self, page, close_callback, on_save_callback):
        super().__init__()
        self.page_ref = page
        self.close_callback = close_callback
        self.on_save_callback = on_save_callback
        self.current_acc_id = None

        # Inputs
        self.txt_user = st.get_input_style("Usuário")
        
        # Campo de Senha (DESABILITADO VISUALMENTE)
        self.txt_pass = st.get_input_style("Senha", height=45)
        self.txt_pass.password = True
        self.txt_pass.can_reveal_password = True
        self.txt_pass.disabled = True
        self.txt_pass.label = "Senha (Bloqueado)"
        self.txt_pass.value = "******" 
        
        self.txt_world = st.get_input_style("Mundo (Ex: br130)")
        
        # Dropdown de Proxy
        self.dd_proxy = ft.Dropdown(
            label="Proxy",
            label_style=ft.TextStyle(color=st.COLOR_PRIMARY, size=12),
            bgcolor="#16161C",
            border_color=st.COLOR_BORDER,
            text_size=13,
            filled=True,
            border_radius=10,
            options=[]
        )

        self.title = ft.Text("Editar Conta", color="white", weight="bold")
        self.modal = True
        self.bgcolor = st.COLOR_SURFACE
        
        self.content = ft.Container(
            width=400,
            height=320,
            content=ft.Column([
                self.txt_user,
                self.txt_pass,
                self.txt_world,
                self.dd_proxy,
                ft.Text("Nota: A senha não pode ser alterada aqui.", size=11, color="grey", italic=True)
            ], spacing=15)
        )
        
        self.actions = [
            ft.OutlinedButton(
                "Cancelar", 
                icon=ft.Icons.CANCEL, 
                style=ft.ButtonStyle(
                    color=st.COLOR_ERROR, 
                    side={"": ft.BorderSide(1, st.COLOR_ERROR)},
                    shape=ft.RoundedRectangleBorder(radius=8)
                ),
                on_click=lambda e: self.close_callback(e)
            ),
            st.get_button_style("Salvar Alterações", self._save, icon=ft.Icons.SAVE)
        ]
        self.actions_alignment = ft.MainAxisAlignment.END

    def open_for_edit(self, acc):
        from core.proxy_manager import manager as proxy_manager 
        
        self.current_acc_id = acc['id']
        
        self.txt_user.value = acc.get('username', '')
        self.txt_pass.value = acc.get('password', '') 
        self.txt_world.value = acc.get('world', '')
        
        options = [ft.dropdown.Option("none", "Sem Proxy (Local)")]
        for p in proxy_manager.proxies:
            label = f"{p['ip']}:{p['port']}"
            options.append(ft.dropdown.Option(p['id'], label))
        self.dd_proxy.options = options
        
        current_proxy = acc.get('proxy_id', 'none')
        valid_ids = [o.key for o in options]
        self.dd_proxy.value = current_proxy if current_proxy in valid_ids else 'none'

        self.open = True
        self.page_ref.update()

    def _save(self, e):
        if not self.txt_user.value or not self.txt_world.value:
            self.page_ref.snack_bar = ft.SnackBar(ft.Text("Preencha Usuário e Mundo!"), bgcolor=st.COLOR_ERROR)
            self.page_ref.snack_bar.open = True
            self.page_ref.update()
            return

        new_data = {
            "username": self.txt_user.value.strip(),
            "password": self.txt_pass.value,
            "world": self.txt_world.value.strip(),
            "proxy_id": self.dd_proxy.value
        }
        
        self.on_save_callback(self.current_acc_id, new_data)
        self.open = False
        self.page_ref.update()