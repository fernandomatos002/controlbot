import os
import flet as ft

# --- ARQUIVOS ---
BUILD_TEMPLATE_FILE = "templates.json"
RECRUIT_TEMPLATE_FILE = "recruitment_templates.json"

# --- PALETA OFICIAL (BRAND CORE) ---
COLOR_BG = "#0B0B0F"           # Preto Absoluto (Fundo Principal)
COLOR_PANEL_BG = "#111115"     # Fundo de Painéis/Cards (Ligeiramente mais claro)
COLOR_BORDER = "#2A2A35"       # Bordas Sutis
COLOR_PRIMARY = "#8B3DFF"      # Roxo Neon (Ações Principais)
COLOR_SECONDARY = "#5B1DB8"    # Roxo Profundo (Gradientes)

# --- CORES DE APOIO ---
COLOR_TEXT_MAIN = "#F5F5F7"    # Branco Gelo
COLOR_TEXT_SEC = "#B5B5C0"     # Cinza Claro
COLOR_ERROR = "#FF4D4D"        # Vermelho Suave
COLOR_SUCCESS = "#2EFF7A"      # Verde Neon
COLOR_INPUT_BG = "#16161C"     # Fundo de Inputs

# --- ESTILOS GERAIS ---
BORDER_RADIUS = 12

# --- CACHE GLOBAL ---
# Mantém grupos criados na sessão
LOCAL_KNOWN_GROUPS = set()

def get_all_known_groups(account_manager):
    """Retorna união de grupos das contas + grupos criados na sessão"""
    groups = {acc.get('group', 'ungrouped') for acc in account_manager.accounts if acc.get('group') != 'ungrouped'}
    return sorted(list(groups.union(LOCAL_KNOWN_GROUPS)))