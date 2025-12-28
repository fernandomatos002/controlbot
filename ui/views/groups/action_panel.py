import flet as ft
from ui.views.groups.constants import (
    COLOR_PANEL_BG, COLOR_BORDER, COLOR_PRIMARY, COLOR_SECONDARY,
    COLOR_TEXT_MAIN, COLOR_TEXT_SEC, COLOR_INPUT_BG, BORDER_RADIUS
)

class ActionPanel(ft.Container):
    def __init__(self, view_controller):
        super().__init__()
        self.view = view_controller
        
        self.width = 320
        self.bgcolor = COLOR_PANEL_BG
        self.border = ft.border.only(left=ft.BorderSide(1, COLOR_BORDER))
        self.padding = 25
        
        self.content = ft.Column([
            ft.Text("Ações em Massa", size=18, weight="bold", color=COLOR_TEXT_MAIN, font_family="Poppins"),
            ft.Text("Gerencie as contas selecionadas.", size=12, color=COLOR_TEXT_SEC, font_family="Inter"),
            ft.Divider(color="transparent", height=20),
            
            # Bloco Organização
            self._section_header("Organização", ft.Icons.DRIVE_FILE_MOVE_OUTLINE),
            self._card_container([
                ft.Text("Mover para:", size=11, color=COLOR_TEXT_SEC),
                self.view.dd_move,
                ft.Container(height=5),
                self.view.btn_move
            ]),

            ft.Divider(color="transparent", height=15),

            # Bloco Configurações
            self._section_header("Configurações do Bot", ft.Icons.TUNE_ROUNDED),
            self._card_container([
                ft.Text("Template de Construção:", size=11, color=COLOR_TEXT_SEC),
                self.view.dd_build,
                ft.Container(height=10),
                ft.Text("Template de Recrutamento:", size=11, color=COLOR_TEXT_SEC),
                self.view.dd_recruit,
                ft.Divider(height=15, color=COLOR_BORDER),
                self.view.btn_apply
            ]),
            
        ], scroll=ft.ScrollMode.AUTO)

    def _section_header(self, title, icon):
        return ft.Row([
            ft.Icon(icon, size=16, color=COLOR_PRIMARY),
            ft.Text(title, size=13, weight="w600", color=COLOR_TEXT_MAIN)
        ], spacing=8)

    def _card_container(self, controls):
        return ft.Container(
            padding=15,
            bgcolor="#131319", # Fundo levemente diferente do painel
            border=ft.border.all(1, COLOR_BORDER),
            border_radius=BORDER_RADIUS,
            content=ft.Column(controls, spacing=8)
        )

# --- HELPERS ESTÁTICOS DE DESIGN ---

def create_dropdown(label):
    return ft.Dropdown(
        hint_text=label,
        text_size=13,
        text_style=ft.TextStyle(color=COLOR_TEXT_MAIN, font_family="Inter"),
        bgcolor=COLOR_INPUT_BG,
        filled=True,
        border_color=COLOR_BORDER,
        border_radius=8,
        focused_border_color=COLOR_PRIMARY,
        focused_bgcolor="#1A1A22",
        content_padding=12,
        dense=True, # Deixa mais compacto visualmente
        # height=45  <-- REMOVIDO PARA CORRIGIR O ERRO
    )

def create_action_btn(text, icon, handler, outline=False):
    if outline:
        # Botão Secundário (Mover)
        return ft.OutlinedButton(
            text=text,
            icon=icon,
            style=ft.ButtonStyle(
                color=COLOR_TEXT_MAIN,
                shape=ft.RoundedRectangleBorder(radius=8),
                side={"": ft.BorderSide(1, COLOR_BORDER)},
                padding=18,
                overlay_color="#2A2A35"
            ),
            on_click=handler,
            width=280,
            disabled=True
        )
    else:
        # Botão Primário (Aplicar) - Com Gradiente
        content = ft.Container(
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=[COLOR_PRIMARY, COLOR_SECONDARY], # Roxo Neon -> Roxo Profundo
            ),
            border_radius=8,
            padding=ft.padding.symmetric(vertical=12),
            alignment=ft.alignment.center,
            content=ft.Row([
                ft.Icon(icon, color="white", size=18),
                ft.Text(text, color="white", weight="bold", size=13, font_family="Inter")
            ], alignment="center", spacing=8)
        )
        
        return ft.Container(
            content=content,
            on_click=handler,
            border_radius=8,
            shadow=ft.BoxShadow(blur_radius=15, color="#8B3DFF33", offset=ft.Offset(0,4)), # Sombra Neon
            width=280,
            opacity=0.5, # Começa desativado visualmente
            animate_opacity=200,
            ink=True
        )