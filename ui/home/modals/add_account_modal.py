import flet as ft
import ui.styles as st
from core.account_manager import account_manager
from core.proxy_manager import manager as proxy_manager

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
        if is_mass:
            self.selected_server_mass = code
            self._update_server_ui_mass()
        else:
            self.selected_server = code
            self._update_server_ui()
    
    def _update_server_ui(self):
        is_br = self.selected_server == "BR"
        
        self.btn_br.bgcolor = st.COLOR_PRIMARY if is_br else "#1a1a25"
        self.btn_br.border = ft.border.all(2, st.COLOR_PRIMARY if is_br else "#333")
        self.btn_br.content.color = "black" if is_br else "grey"
        
        self.btn_pt.bgcolor = st.COLOR_PRIMARY if not is_br else "#1a1a25"
        self.btn_pt.border = ft.border.all(2, st.COLOR_PRIMARY if not is_br else "#333")
        self.btn_pt.content.color = "black" if not is_br else "grey"
        
        if self.page_ref: self.page_ref.update()
    
    def _update_server_ui_mass(self):
        is_br = self.selected_server_mass == "BR"
        
        self.btn_br_mass.bgcolor = st.COLOR_PRIMARY if is_br else "#1a1a25"
        self.btn_br_mass.border = ft.border.all(2, st.COLOR_PRIMARY if is_br else "#333")
        self.btn_br_mass.content.color = "black" if is_br else "grey"
        
        self.btn_pt_mass.bgcolor = st.COLOR_PRIMARY if not is_br else "#1a1a25"
        self.btn_pt_mass.border = ft.border.all(2, st.COLOR_PRIMARY if not is_br else "#333")
        self.btn_pt_mass.content.color = "black" if not is_br else "grey"
        
        if self.page_ref: self.page_ref.update()
    
    def _close(self):
        self.open = False
        if self.page_ref: self.page_ref.update()
    
    def prepare_and_open(self):
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
        free_proxies = [
            ft.dropdown.Option(p['id'], f"{p['ip']}:{p['port']}")
            for p in proxy_manager.proxies
            if p['status'] == 'working' and (not p.get('assigned_to') or p['assigned_to'] is None)
        ]
        self.dd_proxy.options = [ft.dropdown.Option("none", "Sem Proxy (IP Local)")] + free_proxies
        self.dd_proxy.value = "none"
    
    def _on_save(self, e):
        if self.tabs.selected_index == 0:
            self._save_single()
        else:
            self._save_mass()
    
    def _save_single(self):
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
    
    def _save_mass(self):
        import_text = self.txt_import.value.strip()
        world = self.txt_world_mass.value.strip()
        
        if not import_text:
            self._show_error("Cole a lista de contas!")
            return
        
        if not world:
            self._show_error("Digite o mundo!")
            return
        
        lines = [l.strip() for l in import_text.split('\n') if l.strip()]
        accounts_to_add = []
        
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
            
        if not accounts_to_add:
            self._show_error("Nenhuma conta válida encontrada!")
            return
        
        if self.chk_auto_proxy.value:
            free_proxies = [
                p for p in proxy_manager.proxies
                if p['status'] == 'working' and (not p.get('assigned_to') or p['assigned_to'] is None)
            ]
            if len(free_proxies) < len(accounts_to_add):
                self._show_error(f"Faltam proxies! Precisa de {len(accounts_to_add)}, tem {len(free_proxies)} livres.")
                return
        
        world = world.lower()
        if not world.startswith(self.selected_server_mass.lower()):
            world = self.selected_server_mass.lower() + world
        
        proxy_idx = 0
        free_proxies = [
            p for p in proxy_manager.proxies
            if p['status'] == 'working' and (not p.get('assigned_to') or p['assigned_to'] is None)
        ] if self.chk_auto_proxy.value else []
        
        for username, password in accounts_to_add:
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
        
        proxy_manager.save_to_disk()
        
        self._close()
        self.on_save()
        self._show_success(f"✅ {len(accounts_to_add)} contas adicionadas com sucesso!")
    
    def _show_error(self, msg):
        if self.page_ref:
            self.page_ref.snack_bar = ft.SnackBar(
                ft.Text(msg, color="white", weight="bold"),
                bgcolor=st.COLOR_ERROR
            )
            self.page_ref.snack_bar.open = True
            self.page_ref.update()
    
    def _show_success(self, msg):
        if self.page_ref:
            self.page_ref.snack_bar = ft.SnackBar(
                ft.Text(msg, color="black", weight="bold"),
                bgcolor=st.COLOR_SUCCESS
            )
            self.page_ref.snack_bar.open = True
            self.page_ref.update()