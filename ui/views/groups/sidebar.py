import flet as ft
from core.account_manager import account_manager
from ui.views.groups.constants import (
    COLOR_BG, COLOR_BORDER, COLOR_PRIMARY, COLOR_TEXT_MAIN, 
    COLOR_TEXT_SEC, COLOR_PANEL_BG, get_all_known_groups, 
    LOCAL_KNOWN_GROUPS, COLOR_ERROR
)

class GroupSidebar(ft.Container):
    def __init__(self, view_controller):
        super().__init__()
        self.view = view_controller
        self.lv_groups = ft.Column(spacing=5)
        
        self.width = 260
        self.bgcolor = COLOR_BG
        self.border = ft.border.only(right=ft.BorderSide(1, COLOR_BORDER))
        self.padding = 20
        
        self.content = ft.Column([
            ft.Row([
                ft.Text("GRUPOS", color=COLOR_TEXT_SEC, weight="bold", size=11, font_family="Inter"),
                ft.IconButton(
                    ft.Icons.ADD_CIRCLE_OUTLINE, 
                    icon_color=COLOR_PRIMARY, 
                    icon_size=20, 
                    tooltip="Criar Novo Grupo", 
                    on_click=self.view._dialog_create_group
                )
            ], alignment="spaceBetween"),
            ft.Divider(height=10, color="transparent"),
            self.lv_groups
        ])

    def render(self):
        self.lv_groups.controls.clear()
        
        def _item(id, icon, label, count, is_removable=False):
            active = self.view.current_filter == id
            
            icon_color = COLOR_PRIMARY if active else COLOR_TEXT_SEC
            text_color = COLOR_TEXT_MAIN if active else COLOR_TEXT_SEC
            bg_color = "#1A1A22" if active else "transparent"
            border_side = ft.border.only(left=ft.BorderSide(3, COLOR_PRIMARY)) if active else ft.border.only(left=ft.BorderSide(3, "transparent"))

            row_content = [
                ft.Icon(icon, size=16, color=icon_color),
                ft.Text(label, size=13, color=text_color, weight="w600" if active else "normal", font_family="Inter", expand=True),
                ft.Container(
                    content=ft.Text(str(count), size=10, color="white", weight="bold"),
                    bgcolor=COLOR_PRIMARY if active else "#2A2A35",
                    padding=ft.padding.symmetric(horizontal=6, vertical=2), 
                    border_radius=6
                )
            ]

            if is_removable:
                # Botão de deletar com prevenção de clique duplo e lógica encapsulada
                btn_delete = ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE, 
                    icon_color=COLOR_ERROR, 
                    icon_size=16, 
                    tooltip="Excluir Grupo",
                    opacity=1 if active else 0.5, # Sempre visível mas mais fraco se inativo
                    on_click=lambda e: self._delete_group_click(e, id)
                )
                row_content.insert(2, btn_delete)

            return ft.Container(
                content=ft.Row(row_content, spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.padding.symmetric(horizontal=12, vertical=10),
                bgcolor=bg_color,
                border=border_side,
                border_radius=ft.border_radius.only(top_right=8, bottom_right=8),
                ink=True,
                # Ao clicar no container, define o filtro
                on_click=lambda e: self.view._set_filter(id)
            )

        # Itens Fixos
        total = len(account_manager.accounts)
        ungrouped = len([a for a in account_manager.accounts if not a.get('group') or a.get('group') == 'ungrouped'])
        
        self.lv_groups.controls.extend([
            _item("all", ft.Icons.GRID_VIEW_ROUNDED, "Todas as Contas", total),
            _item("ungrouped", ft.Icons.FOLDER_OFF_OUTLINED, "Sem Grupo", ungrouped),
            ft.Divider(color=COLOR_BORDER, thickness=1),
            ft.Text("SEUS GRUPOS", size=10, color=COLOR_TEXT_SEC, weight="bold")
        ])

        # Grupos Dinâmicos
        for g in get_all_known_groups(account_manager):
            c = len([a for a in account_manager.accounts if a.get('group') == g])
            self.lv_groups.controls.append(_item(g, ft.Icons.FOLDER_OPEN_ROUNDED, g, c, is_removable=True))

    def _delete_group_click(self, e, group_name):
        """Wrapper para impedir que o clique propague para o container pai (seleção)"""
        e.control.disabled = True # Evita duplo clique
        e.control.update()
        self._delete_group(group_name)
        # Não precisamos reativar o botão pois a UI será recriada

    def _delete_group(self, group_name):
        # 1. Remove das contas
        changed = 0
        for acc in account_manager.accounts:
            if acc.get('group') == group_name:
                acc['group'] = 'ungrouped'
                changed += 1
        
        # 2. Remove do cache local
        if group_name in LOCAL_KNOWN_GROUPS:
            LOCAL_KNOWN_GROUPS.remove(group_name)

        # 3. Salva
        account_manager.save()
        
        # Se estava visualizando o grupo excluído, volta para 'all'
        if self.view.current_filter == group_name:
            self.view.current_filter = "all"
        
        # 4. Atualiza dropdowns na view pai e recarrega tudo
        self.view._refresh_move_dropdown()
        self.view._refresh_ui()
        
        # 5. Notificação (Correção da Sintaxe do SnackBar)
        if self.view.page_ref:
            self.view.page_ref.snack_bar = ft.SnackBar(
                content=ft.Text(f"Grupo '{group_name}' excluído. {changed} contas movidas para 'Sem Grupo'.", color="white"), 
                bgcolor=COLOR_ERROR
            )
            self.view.page_ref.snack_bar.open = True
            self.view.page_ref.update()