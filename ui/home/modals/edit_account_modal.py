import flet as ft
import ui.styles as st
from core.proxy_manager import manager as proxy_manager 

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