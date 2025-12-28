import flet as ft

# --- PALETA ENTERPRISE (CYBERPUNK) ---
# Fundo
COLOR_BG = "#0B0B0F"           # Preto Absoluto (Fundo das telas)
COLOR_SURFACE = "#111115"      # Fundo do Header/Cards
COLOR_BORDER = "#2A2A35"       # Bordas sutis

# Cores de Ação
COLOR_PRIMARY = "#8B3DFF"      # Roxo Neon (Botões, Seleção, Destaques)
COLOR_SECONDARY = "#5B1DB8"    # Roxo Profundo (Gradientes)
COLOR_ACCENT = "#2EFF7A"       # Verde Neon (Status Online, Sucesso)

# Texto
COLOR_TEXT = "#F5F5F7"         # Branco Gelo
COLOR_TEXT_DIM = "#B5B5C0"     # Cinza Claro

# Status / Feedback
COLOR_ERROR = "#FF4D4D"        # Vermelho Suave
COLOR_WARNING = "#f39c12"      # Laranja

# --- COMPATIBILIDADE (FIX) ---
# Mapeia as cores antigas para as novas para não quebrar os outros arquivos
COLOR_SUCCESS = COLOR_ACCENT   # Agora COLOR_SUCCESS aponta para o Verde Neon

# --- ESTILOS PADRÃO ---

def get_input_style(label, hint="", height=None, width=None, multiline=False, prefix_icon=None, on_change=None):
    return ft.TextField(
        label=label,
        label_style=ft.TextStyle(color=COLOR_PRIMARY, size=12, weight="bold"),
        hint_text=hint,
        hint_style=ft.TextStyle(color="#555", size=12),
        text_style=ft.TextStyle(color="white", size=13),
        multiline=multiline,
        min_lines=10 if multiline else 1,
        max_lines=10 if multiline else 1,
        width=width,
        prefix_icon=prefix_icon,
        filled=True,
        fill_color="#16161C", # Input BG mais escuro
        border_color=COLOR_BORDER,
        focused_border_color=COLOR_PRIMARY,
        border_width=1,
        border_radius=10, 
        cursor_color=COLOR_PRIMARY,
        on_change=on_change
    )

def get_button_style(text, on_click, icon=None, is_primary=True, width=None):
    return ft.Container(
        content=ft.Row(
            [ft.Icon(icon, size=16, color="white" if is_primary else COLOR_TEXT_DIM), 
             ft.Text(text, weight="bold", color="white" if is_primary else COLOR_TEXT_DIM, size=13)],
            alignment=ft.MainAxisAlignment.CENTER, 
            spacing=8
        ),
        bgcolor=COLOR_PRIMARY if is_primary else "transparent",
        border=ft.border.all(1, COLOR_PRIMARY if is_primary else COLOR_BORDER),
        padding=ft.padding.symmetric(horizontal=20, vertical=12),
        border_radius=8,
        on_click=on_click,
        width=width,
        ink=True,
        
        # MUDE AQUI: Deixe shadow=None para tirar o brilho, 
        # ou use color="#000000" se quiser apenas uma sombra preta normal sem neon.
        shadow=None, 
        
        animate=ft.Animation(150, "easeOut")
    )