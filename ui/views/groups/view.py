import flet as ft
import json
import os
from core.account_manager import account_manager
import ui.styles as st

# Imports dos Módulos Refatorados
from ui.views.groups.constants import (
    BUILD_TEMPLATE_FILE, RECRUIT_TEMPLATE_FILE, 
    COLOR_PRIMARY, LOCAL_KNOWN_GROUPS, get_all_known_groups, COLOR_SUCCESS
)
from ui.views.groups.sidebar import GroupSidebar
from ui.views.groups.account_list import AccountList
from ui.views.groups.action_panel import ActionPanel, create_dropdown, create_action_btn

class GroupsView(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True)
        self.page_ref = page 
        
        # --- ESTADO ---
        self.current_filter = "all"
        self.selected_ids = set()
        
        # --- CONTROLES DE AÇÃO ---
        self.dd_build = create_dropdown("Template Construção")
        self.dd_recruit = create_dropdown("Template Recrutamento")
        self.dd_move = create_dropdown("Mover para Grupo")
        
        self.btn_move = create_action_btn("Mover Contas", ft.Icons.DRIVE_FILE_MOVE_OUTLINE, self._action_move, outline=True)
        self.btn_apply = create_action_btn("APLICAR", ft.Icons.BOLT, self._action_apply)

        # --- COMPONENTES VISUAIS ---
        self.sidebar = GroupSidebar(self)
        self.account_list = AccountList(self)
        self.action_panel = ActionPanel(self)

        # --- LAYOUT ---
        self.content = ft.Row([
            self.sidebar,
            self.account_list,
            self.action_panel
        ], expand=True, spacing=0)

        # --- INICIALIZAÇÃO ---
        self._load_initial_data()
        self._refresh_ui()

    # =========================================================================
    # LOGIC & DATA
    # =========================================================================

    def _load_initial_data(self):
        self._load_json_options(BUILD_TEMPLATE_FILE, self.dd_build)
        self._load_json_options(RECRUIT_TEMPLATE_FILE, self.dd_recruit)
        self._refresh_move_dropdown()

    def _load_json_options(self, filepath, dropdown):
        options = [ft.dropdown.Option("none", "--- Manter Atual ---"), ft.dropdown.Option("remove", "❌ Remover Template")]
        if os.path.exists(filepath):
            try:
                with open(filepath, "r") as f:
                    for t in json.load(f): options.append(ft.dropdown.Option(t['name'], t['name']))
            except: pass
        dropdown.options = options
        dropdown.value = "none"

    def _get_filtered_accounts(self):
        accs = []
        for acc in account_manager.accounts:
            g = acc.get('group', 'ungrouped') or 'ungrouped'
            if self.current_filter == 'all': accs.append(acc)
            elif self.current_filter == 'ungrouped' and g == 'ungrouped': accs.append(acc)
            elif g == self.current_filter: accs.append(acc)
        return accs

    # =========================================================================
    # UI UPDATES (Orquestrador)
    # =========================================================================

    def _refresh_ui(self):
        # Chama o render de cada sub-componente
        self.sidebar.render()
        self.account_list.render()
        
        # Atualiza título e botões
        self._update_title()
        self._update_buttons()
        
        if self.page: self.update()

    def _update_title(self):
        map_names = {"all": "Todas as Contas", "ungrouped": "Sem Grupo"}
        self.account_list.txt_title.value = map_names.get(self.current_filter, f"Grupo: {self.current_filter}")

    def _update_buttons(self):
        count = len(self.selected_ids)
        active = count > 0
        
        # Botão Mover
        self.btn_move.disabled = not active
        
        # Botão Aplicar (Custom Container)
        self.btn_apply.opacity = 1 if active else 0.5
        
        # Atualiza Texto do Botão Aplicar
        try:
            # Estrutura: Container -> Container(Gradient) -> Row -> [Icon, Text]
            text_control = self.btn_apply.content.content.controls[1]
            text_control.value = f"APLICAR ({count})" if active else "APLICAR"
        except: pass
        
        # Define evento
        self.btn_apply.disabled = not active 
        self.btn_apply.on_click = self._action_apply if active else None

    def _refresh_move_dropdown(self):
        self.dd_move.options = [ft.dropdown.Option("ungrouped", "Sem Grupo")] + [ft.dropdown.Option(g, g) for g in get_all_known_groups(account_manager)]
        if self.dd_move.page: self.dd_move.update()

    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================

    def _set_filter(self, filter_id):
        self.current_filter = filter_id
        self.selected_ids.clear()
        self._refresh_ui()

    def _toggle_one(self, acc_id, value):
        if value: self.selected_ids.add(acc_id)
        else: self.selected_ids.discard(acc_id)
        self._refresh_ui()

    def _toggle_all(self, e):
        value = e.control.value
        visible = self._get_filtered_accounts()
        for acc in visible:
            if value: self.selected_ids.add(acc['id'])
            else: self.selected_ids.discard(acc['id'])
        self._refresh_ui()

    # =========================================================================
    # BUSINESS ACTIONS
    # =========================================================================

    def _action_move(self, e):
        target = self.dd_move.value
        if not target: return
        
        count = 0
        for acc in account_manager.accounts:
            if acc['id'] in self.selected_ids:
                acc['group'] = target
                count += 1
        
        self._save_and_notify(f"{count} contas movidas para '{target}'")
        self.selected_ids.clear()
        self._refresh_move_dropdown()
        self._refresh_ui()

    def _action_apply(self, e):
        b_name, r_name = self.dd_build.value, self.dd_recruit.value
        
        b_queue = self._fetch_template_data(BUILD_TEMPLATE_FILE, b_name, 'queue')
        r_targets = self._fetch_template_data(RECRUIT_TEMPLATE_FILE, r_name, 'targets')

        for acc in account_manager.accounts:
            if acc['id'] in self.selected_ids:
                if b_name == "remove":
                    acc['build_template_name'] = None
                    acc['build_queue'] = []
                elif b_name != "none":
                    acc['build_template_name'] = b_name
                    acc['build_queue'] = b_queue
                
                if r_name == "remove":
                    acc['recruit_template_name'] = None
                    acc['recruit_targets'] = {}
                elif r_name != "none":
                    acc['recruit_template_name'] = r_name
                    acc['recruit_targets'] = r_targets
        
        self._save_and_notify("Configurações atualizadas!")
        self._refresh_ui()

    def _fetch_template_data(self, file, name, key):
        if name and name not in ["none", "remove"] and os.path.exists(file):
            with open(file, "r") as f:
                ts = json.load(f)
                t = next((x for x in ts if x['name'] == name), None)
                return t[key] if t else [] if key == 'queue' else {}
        return [] if key == 'queue' else {}

    def _save_and_notify(self, msg):
        account_manager.save()
        if self.page_ref:
            # --- CORREÇÃO AQUI ---
            # Removemos o primeiro argumento posicional e usamos apenas keyword args
            self.page_ref.snack_bar = ft.SnackBar(
                content=ft.Text(msg, color="black", weight="bold"),
                bgcolor=COLOR_SUCCESS
            )
            self.page_ref.snack_bar.open = True
            self.page_ref.update()

    def _dialog_create_group(self, e):
        txt_name = st.get_input_style("Nome do Grupo")
        
        def _confirm(e):
            if name := txt_name.value.strip():
                LOCAL_KNOWN_GROUPS.add(name)
                self._refresh_move_dropdown()
                self._refresh_ui()
                self.page_ref.close(dlg)
                self._save_and_notify(f"Grupo '{name}' criado!")

        dlg = ft.AlertDialog(
            title=ft.Text("Novo Grupo", color="white"), 
            content=ft.Container(txt_name, height=60, padding=10),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.page_ref.close(dlg)), 
                ft.ElevatedButton("Criar", on_click=_confirm, bgcolor=COLOR_PRIMARY, color="white")
            ],
            bgcolor="#1A1A22",
            shape=ft.RoundedRectangleBorder(radius=12)
        )
        self.page_ref.open(dlg)