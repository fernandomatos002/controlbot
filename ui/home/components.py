import flet as ft
import time
import ui.styles as st
from core.proxy_manager import manager as proxy_manager

# --- CONFIGURAÇÃO DO SPRITE (Link Oficial) ---
SPRITE_URL = "https://dszz.innogamescdn.com/graphic/icons/header.png"

# Coordenadas (X, Y) exatas para o header.png padrão
# Ordem: Madeira, Argila, Ferro, Armazém, População
ICON_COORDS = {
    "wood":    {"x": 18,   "y": 0},  # 1º Ícone: Madeira
    "stone":   {"x": 36,  "y": 0},  # 2º Ícone: Argila (Poço)
    "iron":    {"x": 54,  "y": 0},  # 3º Ícone: Ferro (Mina)
    "storage": {"x": 0,  "y": 0},  # 4º Ícone: Armazém
    "pop":     {"x": 72,  "y": 0}   # 5º Ícone: População (Fazenda)
}

def TribalSprite(icon_name):
    """
    Cria um componente que recorta o ícone exato da imagem header.png.
    """
    coords = ICON_COORDS.get(icon_name, {"x": 0, "y": 0})
    
    return ft.Container(
        width=18, 
        height=18,
        clip_behavior=ft.ClipBehavior.HARD_EDGE, # Corta o excesso
        content=ft.Stack([
            ft.Image(
                src=SPRITE_URL,
                # Desloca a imagem para esquerda para revelar o ícone certo
                left=-coords["x"], 
                top=-coords["y"],
                # Deixe width/height como None para usar o tamanho original da imagem
                fit=ft.ImageFit.NONE, 
                repeat=ft.ImageRepeat.NO_REPEAT,
            )
        ])
    )

def centered_cell(content, width=None):
    return ft.Container(content=content, alignment=ft.alignment.center, width=width, height=80, padding=0)

def header_txt(text, width=None):
    return ft.Container(content=ft.Text(text, weight="bold", size=11, color="grey", text_align="center"), alignment=ft.alignment.center, width=width)

def create_scavenge_cell(acc, open_modal_callback):
    """Cria a célula de status da coleta com timer."""
    s_data = acc.get('scavenge_data', {})
    max_return = s_data.get('max_return')
    
    text = "INATIVO"
    color = st.COLOR_ERROR
    icon = ft.Icons.WARNING_AMBER_ROUNDED
    
    if max_return:
        now = time.time()
        remaining = int(max_return) - now
        
        if remaining > 0:
            m, s = divmod(remaining, 60)
            h, m = divmod(m, 60)
            text = f"{int(h):02d}:{int(m):02d}:{int(s):02d}"
            color = st.COLOR_SUCCESS
            icon = ft.Icons.TIMELAPSE
        else:
            text = "CONCLUÍDO" 
            color = st.COLOR_ACCENT
            icon = ft.Icons.CHECK_CIRCLE_OUTLINE

    content = ft.Container(
        content=ft.Row([
            ft.Icon(icon, size=14, color=color),
            ft.Text(text, size=11, weight="bold", color=color)
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=5),
        alignment=ft.alignment.center,
        width=100,
        height=80,
        on_click=lambda e: open_modal_callback(acc),
        ink=True,
        border_radius=5,
        tooltip="Ver detalhes da Coleta"
    )
    return content

def create_account_row(acc, logic_handler, open_logs_callback, open_scavenge_callback, ui_cache, open_edit_callback):
    
    # --- CRIAÇÃO DOS OBJETOS DE TEXTO ---
    txt_status_icon = ft.Icon(ft.Icons.SMART_TOY_ROUNDED, size=24, color="grey")
    txt_points = ft.Text("0", size=12, color="#f1c40f", weight="bold")
    
    txt_wood = ft.Text("0", size=11, color="white", weight="bold")
    txt_stone = ft.Text("0", size=11, color="white", weight="bold")
    txt_iron = ft.Text("0", size=11, color="white", weight="bold")
    txt_storage = ft.Text("0", size=11, color="white")
    txt_pop = ft.Text("0/0", size=11, color="white")
    
    txt_cycle_state = ft.Text("Parado", size=11, weight="bold", color="grey", text_align="center")
    txt_last_run = ft.Text("--:--:--", size=10, color="grey", text_align="center")
    
    icon_incomings = ft.Icon(ft.Icons.WARNING_ROUNDED, color="grey", size=20)
    txt_incomings = ft.Text("0", color="grey", weight="bold", size=13)

    # --- SALVAR NO CACHE ---
    ui_cache[acc['id']] = {
        "status_icon": txt_status_icon,
        "points": txt_points,
        "wood": txt_wood,
        "stone": txt_stone,
        "iron": txt_iron,
        "storage": txt_storage,
        "pop": txt_pop,
        "cycle_state": txt_cycle_state,
        "last_run": txt_last_run,
        "incomings": txt_incomings,
        "inc_icon": icon_incomings
    }

    # --- POPULAR DADOS INICIAIS ---
    res = acc.get('resources', {'wood': 0, 'stone': 0, 'iron': 0})
    storage = acc.get('storage', 0)
    pop = acc.get('population', {'current': 0, 'max': 0})
    points = acc.get('points', 0)
    incomings = acc.get('incomings', 0)
    
    txt_wood.value = str(res['wood'])
    txt_stone.value = str(res['stone'])
    txt_iron.value = str(res['iron'])
    txt_storage.value = str(storage)
    txt_pop.value = f"{pop['current']}/{pop['max']}"
    txt_points.value = f"{points:,}".replace(',', '.')
    
    if incomings > 0:
        txt_incomings.color = st.COLOR_ERROR
        icon_incomings.color = st.COLOR_ERROR
        txt_incomings.value = str(incomings)

    is_running = acc['status'] == 'running'
    txt_status_icon.color = st.COLOR_SUCCESS if is_running else st.COLOR_ERROR

    # --- MONTAGEM DA LINHA ---

    # Proxy
    pid = acc.get('proxy_id')
    proxy_color, proxy_text = "grey", "LOCAL"
    if pid and pid != 'none':
        p = next((x for x in proxy_manager.proxies if x['id'] == pid), None)
        if p:
            if p['status'] == 'working': proxy_color, proxy_text = st.COLOR_SUCCESS, "VALID"
            elif p['status'] == 'error': proxy_color, proxy_text = st.COLOR_ERROR, "ERRO"
            else: proxy_color, proxy_text = st.COLOR_WARNING, "TEST"
    cell_proxy = centered_cell(ft.Text(proxy_text, size=11, weight="bold", color=proxy_color), width=70)

    # Conta
    cell_conta = centered_cell(ft.Column([
        ft.Text(acc['username'], weight="bold", color="white", size=13, text_align="center"),
        ft.Text(acc['world'].upper(), size=10, color="grey", text_align="center")
    ], spacing=2, alignment=ft.MainAxisAlignment.CENTER), width=110)

    # Pontos
    cell_pontos = centered_cell(ft.Row([
        ft.Icon(ft.Icons.STAR, size=12, color="#f1c40f"),
        txt_points
    ], alignment=ft.MainAxisAlignment.CENTER, spacing=3), width=90)

    # Status
    cell_bot = centered_cell(txt_status_icon, width=70)

    # --- RECURSOS (ORDEM CORRIGIDA) ---
    def res_row(sprite_name, text_control):
        return ft.Row([
            TribalSprite(sprite_name), 
            text_control
        ], spacing=4, alignment=ft.MainAxisAlignment.CENTER)

    # AQUI ESTÁ A ORDEM SOLICITADA:
    # 1. Wood (Bosque)
    # 2. Stone (Argila)
    # 3. Iron (Ferro)
    # 4. Storage (Armazém)
    # 5. Pop (Fazenda)
    cell_dados = centered_cell(ft.Row([
        res_row("wood", txt_wood),
        res_row("stone", txt_stone),
        res_row("iron", txt_iron),
        res_row("storage", txt_storage),
        res_row("pop", txt_pop) 
    ], alignment=ft.MainAxisAlignment.SPACE_AROUND, spacing=10), width=280)

    # Coleta
    cell_scavenge = ft.DataCell(create_scavenge_cell(acc, open_scavenge_callback))

    # Ciclo
    cycle_state = acc.get('cycle_state', 'stopped')
    txt_cycle_state.value = cycle_state.upper()
    txt_last_run.value = f"Últ: {acc.get('last_cycle', '--:--')}"
    cell_ciclo = centered_cell(ft.Column([
        txt_cycle_state,
        txt_last_run
    ], alignment=ft.MainAxisAlignment.CENTER, spacing=2), width=110)

    # Ataques
    cell_ataque = centered_cell(ft.Row([
        icon_incomings,
        txt_incomings
    ], alignment=ft.MainAxisAlignment.CENTER, spacing=4), width=80)

    # --- AÇÕES (MODIFICADO) ---
    has_session = acc.get('session') is not None
    is_running = acc['status'] == 'running'
    
    play_icon = ft.Icons.STOP_CIRCLE_ROUNDED if is_running else ft.Icons.PLAY_CIRCLE_FILLED_ROUNDED
    play_color = st.COLOR_ERROR if is_running else (st.COLOR_SUCCESS if has_session else "grey")
    play_disabled = not has_session and not is_running

    # 1. Criamos o botão em uma variável separada
    btn_action = ft.IconButton(
        icon=play_icon, 
        icon_color=play_color, 
        icon_size=28, 
        disabled=play_disabled, 
        on_click=lambda e: logic_handler.toggle_bot(acc)
    )

    cell_acoes = centered_cell(ft.Row([
        ft.IconButton(ft.Icons.KEY, tooltip="Login Manual", icon_color="#3498db", icon_size=18, on_click=lambda e: logic_handler.perform_login(acc)),
        ft.IconButton(ft.Icons.EDIT, tooltip="Editar Conta", icon_color=st.COLOR_PRIMARY, icon_size=18, on_click=lambda e: open_edit_callback(acc)),
        ft.IconButton(ft.Icons.VISIBILITY, tooltip="Visualizar", icon_color=st.COLOR_ACCENT if has_session else "grey", icon_size=18, disabled=not has_session, on_click=lambda e: logic_handler.open_visual_village(acc)),
        
        btn_action, # <--- Usamos a variável aqui
        
        ft.IconButton(ft.Icons.HISTORY, tooltip="Logs", icon_color="grey", icon_size=18, on_click=lambda e: open_logs_callback(acc)),
        ft.IconButton(ft.Icons.DELETE_OUTLINE, tooltip="Excluir", icon_color=st.COLOR_ERROR, icon_size=18, on_click=lambda e, aid=acc['id']: logic_handler.delete_account(aid))
    ], alignment=ft.MainAxisAlignment.CENTER, spacing=0), width=230)

    # 2. ADICIONAMOS NO CACHE (IMPORTANTE!)
    # Localize onde o ui_cache é preenchido (no início da função) ou adicione esta linha logo antes do return:
    ui_cache[acc['id']] = {
        "status_icon": txt_status_icon,
        "points": txt_points,
        "wood": txt_wood,
        "stone": txt_stone,
        "iron": txt_iron,
        "storage": txt_storage,
        "pop": txt_pop,
        "cycle_state": txt_cycle_state,
        "last_run": txt_last_run,
        "incomings": txt_incomings,
        "inc_icon": icon_incomings,
        "btn_action": btn_action  # <--- NOVA LINHA: Adiciona o botão ao cache
    }

    return ft.DataRow(cells=[
        ft.DataCell(cell_proxy), 
        ft.DataCell(cell_conta), 
        ft.DataCell(cell_pontos), 
        ft.DataCell(cell_bot), 
        ft.DataCell(cell_dados), 
        cell_scavenge, 
        ft.DataCell(cell_ciclo),
        ft.DataCell(cell_ataque), 
        ft.DataCell(cell_acoes),
    ])