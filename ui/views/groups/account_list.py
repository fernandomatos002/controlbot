import flet as ft
from ui.views.groups.constants import (
    COLOR_BG, COLOR_BORDER, COLOR_PRIMARY, COLOR_SECONDARY,
    COLOR_TEXT_MAIN, COLOR_TEXT_SEC, COLOR_PANEL_BG
)

class AccountList(ft.Container):
    def __init__(self, view_controller):
        super().__init__()
        self.view = view_controller
        self.lv_accounts = ft.ListView(expand=True, spacing=5)
        self.txt_title = ft.Text("Todas as Contas", size=20, weight="bold", font_family="Poppins", color=COLOR_TEXT_MAIN)
        
        self.expand = True
        self.bgcolor = COLOR_BG # Fundo Preto Absoluto
        self.padding = ft.padding.only(left=30, right=30, top=25, bottom=10)
        
        self.content = ft.Column([
            ft.Row([
                self.txt_title,
                ft.Container(
                    content=ft.Row([
                        ft.Checkbox(
                            label="Selecionar Tudo", 
                            label_style=ft.TextStyle(color=COLOR_TEXT_SEC, size=12),
                            active_color=COLOR_PRIMARY, 
                            check_color="black",
                            on_change=self.view._toggle_all
                        )
                    ]),
                    opacity=0.9
                )
            ], alignment="spaceBetween"),
            ft.Divider(color=COLOR_BORDER, height=20),
            self.lv_accounts
        ])

    def render(self):
        self.lv_accounts.controls.clear()
        accounts = self.view._get_filtered_accounts()
        
        if not accounts:
            self.lv_accounts.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.SEARCH_OFF, size=40, color="#333"),
                        ft.Text("Nenhuma conta encontrada neste grupo.", color=COLOR_TEXT_SEC)
                    ], horizontal_alignment="center"),
                    alignment=ft.alignment.center,
                    padding=50
                )
            )
            return

        for acc in accounts:
            is_sel = acc['id'] in self.view.selected_ids
            
            # Badges Logic (Chips coloridos)
            badges = []
            if (b := acc.get('build_template_name')) and b != 'none':
                badges.append(self._create_badge(ft.Icons.CONSTRUCTION, b, "#9C27B0"))
            if (r := acc.get('recruit_template_name')) and r != 'none':
                badges.append(self._create_badge(ft.Icons.GROUP_ADD, r, "#3F51B5"))

            card = ft.Container(
                content=ft.Row([
                    ft.Checkbox(
                        value=is_sel, 
                        active_color=COLOR_PRIMARY, 
                        check_color="black",
                        on_change=lambda e, aid=acc['id']: self.view._toggle_one(aid, e.control.value)
                    ),
                    ft.Container(
                        content=ft.Text(acc['username'][0].upper(), size=14, weight="bold", color="white"),
                        bgcolor=COLOR_SECONDARY, 
                        width=32, height=32, border_radius=16, alignment=ft.alignment.center
                    ),
                    ft.Column([
                        ft.Text(acc['username'], color=COLOR_TEXT_MAIN, weight="w600", size=14, font_family="Inter"),
                        ft.Text(f"Mundo: {acc['world'].upper()}", color=COLOR_TEXT_SEC, size=11, font_family="JetBrains Mono")
                    ], spacing=1, expand=True),
                    ft.Row(badges, spacing=8)
                ], alignment="center"),
                bgcolor=COLOR_PANEL_BG, 
                border=ft.border.all(1, COLOR_PRIMARY if is_sel else "transparent"),
                border_radius=10, 
                padding=ft.padding.symmetric(horizontal=15, vertical=12),
                animate=ft.Animation(150, "easeOut"),
                on_click=lambda e, aid=acc['id']: self.view._toggle_one(aid, not (aid in self.view.selected_ids))
            )
            self.lv_accounts.controls.append(card)

    def _create_badge(self, icon, text, color):
        return ft.Container(
            content=ft.Row([
                ft.Icon(icon, size=10, color=color), 
                ft.Text(text, size=10, color=COLOR_TEXT_MAIN, weight="bold")
            ], spacing=4),
            bgcolor=f"{color}22", # Hex com transparência
            border=ft.border.all(1, f"{color}44"),
            padding=ft.padding.symmetric(horizontal=8, vertical=4), 
            border_radius=6
        )