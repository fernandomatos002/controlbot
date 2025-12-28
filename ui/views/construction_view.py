import flet as ft
import json
import os
import threading
import ui.styles as st
from core.cloud_sync import cloud_sync

# --- DADOS DO JOGO (COM IMAGENS) ---
# Mapeado conforme sua lista de arquivos
BUILDINGS_DATA = {
    "main":     {"name": "Edifício Principal", "req": {}, "img": "main.webp"},
    "wood":     {"name": "Bosque", "req": {}, "img": "wood3.webp"},
    "stone":    {"name": "Poço de Argila", "req": {}, "img": "stone3.webp"},
    "iron":     {"name": "Mina de Ferro", "req": {}, "img": "iron3.webp"},
    "farm":     {"name": "Fazenda", "req": {}, "img": "farm3.webp"},
    "storage":  {"name": "Armazém", "req": {}, "img": "storage.webp"},
    "hide":     {"name": "Esconderijo", "req": {}, "img": "hide1.webp"},
    "place":    {"name": "Praça de Reunião", "req": {"main": 1}, "img": "place1.webp"},
    "barracks": {"name": "Quartel", "req": {"main": 3}, "img": "quartel.webp"},
    "smithy":   {"name": "Ferreiro", "req": {"main": 5, "barracks": 1}, "img": "smith3.webp"},
    "market":   {"name": "Mercado", "req": {"main": 3, "storage": 2}, "img": "market3.webp"},
    "wall":     {"name": "Muralha", "req": {"barracks": 1}, "img": "wall3.webp"},
    "stable":   {"name": "Estábulo", "req": {"main": 10, "barracks": 5, "smithy": 5}, "img": "estabulo.webp"},
    "garage":   {"name": "Oficina", "req": {"main": 10, "smithy": 10}, "img": "oficina.webp"},
    "church":   {"name": "Igreja", "req": {}, "img": "church3.webp"}, 
    "statue":   {"name": "Estátua", "req": {}, "img": "statue1.webp"},
    # Fallback para ícone se não tiver imagem (Academia)
    "snob":     {"name": "Academia", "req": {"main": 20, "smithy": 20, "market": 10}, "img": "snob1.webp"},}

TEMPLATE_FILE = "templates.json"

def ConstructionView(page: ft.Page):
    
    # Estado Local
    queue_ref = ft.Ref[list]()
    queue_ref.current = []
    
    saved_templates_ref = ft.Ref[list]()
    saved_templates_ref.current = []

    # Inputs
    txt_template_name = st.get_input_style("Nome do Modelo", hint="Ex: Rushar Cavalaria")

    # --- HELPER FUNCTIONS ---
    def get_base_levels():
        levels = {k: 0 for k in BUILDINGS_DATA.keys()}
        levels['main'] = 1 
        return levels

    def get_current_levels(queue_list):
        levels = get_base_levels()
        for item in queue_list:
            key = item['key']
            if key in levels:
                levels[key] += 1
        return levels

    def check_missing_reqs(key, current_levels):
        reqs = BUILDINGS_DATA[key]['req']
        missing = []
        for r_key, r_val in reqs.items():
            if current_levels.get(r_key, 0) < r_val:
                r_name = BUILDINGS_DATA[r_key]['name']
                missing.append(f"{r_name} nv.{r_val}")
        return missing
    
    def is_sequence_valid(queue_list):
        levels = get_base_levels()
        for item in queue_list:
            key = item['key']
            reqs = BUILDINGS_DATA[key]['req']
            for r_key, r_val in reqs.items():
                if levels.get(r_key, 0) < r_val:
                    return False
            levels[key] += 1
        return True

    # --- AÇÕES ---
    def handle_add_click(key):
        current_levels = get_current_levels(queue_ref.current)
        missing = check_missing_reqs(key, current_levels)
        
        if not missing:
            queue_ref.current.append({"key": key, "name": BUILDINGS_DATA[key]['name']})
            update_ui()
        else:
            msg = f"Bloqueado! Requer: {', '.join(missing)}"
            page.snack_bar = ft.SnackBar(ft.Text(msg, weight="bold"), bgcolor=st.COLOR_ERROR)
            page.snack_bar.open = True
            page.update()

    def remove_item(index):
        if 0 <= index < len(queue_ref.current):
            simulated = queue_ref.current.copy()
            simulated.pop(index)
            if is_sequence_valid(simulated):
                queue_ref.current.pop(index)
                update_ui()
            else:
                page.snack_bar = ft.SnackBar(ft.Text("Não pode remover! Quebra a sequência de requisitos."), bgcolor=st.COLOR_ERROR)
                page.snack_bar.open = True
            page.update()

    def move_item(index, direction):
        new_index = index + direction
        if 0 <= new_index < len(queue_ref.current):
            simulated = queue_ref.current.copy()
            simulated[index], simulated[new_index] = simulated[new_index], simulated[index]
            if is_sequence_valid(simulated):
                queue_ref.current = simulated
                update_ui()
            else:
                page.snack_bar = ft.SnackBar(ft.Text("Movimento inválido! Quebra a ordem de requisitos."), bgcolor=st.COLOR_ERROR)
                page.snack_bar.open = True
                page.update()

    def clear_queue(e):
        queue_ref.current.clear()
        update_ui()

    # --- PERSISTÊNCIA ---
    def load_templates():
        if cloud_sync.enabled:
            server_tpl = cloud_sync.load_templates("templates_build")
            if server_tpl is not None:
                saved_templates_ref.current = server_tpl
                return

        if os.path.exists(TEMPLATE_FILE):
            try:
                with open(TEMPLATE_FILE, "r") as f:
                    saved_templates_ref.current = json.load(f)
            except:
                saved_templates_ref.current = []
        else:
            saved_templates_ref.current = []

    def save_template(e):
        if not txt_template_name.value:
            page.snack_bar = ft.SnackBar(ft.Text("Digite um nome para o modelo!"), bgcolor=st.COLOR_ERROR)
            page.snack_bar.open=True; page.update(); return
        if not queue_ref.current:
            page.snack_bar = ft.SnackBar(ft.Text("A fila está vazia!"), bgcolor=st.COLOR_ERROR)
            page.snack_bar.open=True; page.update(); return

        new_t = {"name": txt_template_name.value, "queue": queue_ref.current}
        saved_templates_ref.current.append(new_t)
        
        with open(TEMPLATE_FILE, "w") as f:
            json.dump(saved_templates_ref.current, f)

        if cloud_sync.enabled:
            cloud_sync.save_templates("templates_build", saved_templates_ref.current)
        
        txt_template_name.value = ""
        page.snack_bar = ft.SnackBar(ft.Text("Modelo salvo e sincronizado!"), bgcolor=st.COLOR_SUCCESS)
        page.snack_bar.open=True
        update_ui()

    def load_selected_template(template):
        queue_ref.current = template['queue'].copy()
        update_ui()
        page.snack_bar = ft.SnackBar(ft.Text(f"Modelo '{template['name']}' carregado!"), bgcolor=st.COLOR_PRIMARY)
        page.snack_bar.open=True; page.update()

    def delete_template(index):
        if 0 <= index < len(saved_templates_ref.current):
            del saved_templates_ref.current[index]
            with open(TEMPLATE_FILE, "w") as f:
                json.dump(saved_templates_ref.current, f)
            if cloud_sync.enabled:
                cloud_sync.save_templates("templates_build", saved_templates_ref.current)
            update_ui()

    # --- UI CONTAINERS ---
    grid_container = ft.Container()
    list_queue_container = ft.ListView(expand=True, spacing=5, padding=10)
    list_templates_container = ft.ListView(expand=True, spacing=5, padding=10)

    def update_ui():
        # Calcular níveis atuais para a Grade
        current_levels_for_grid = get_current_levels(queue_ref.current)

        # 1. ATUALIZA GRADE (GRID) COM IMAGENS
        btns = []
        for key, data in BUILDINGS_DATA.items():
            missing = check_missing_reqs(key, current_levels_for_grid)
            enabled = len(missing) == 0
            
            lvl = current_levels_for_grid.get(key, 0)
            btn_text = f"{data['name']} ({lvl})"
            
            opacity = 1 if enabled else 0.4
            border_color = st.COLOR_BORDER if enabled else "#222"
            
            # Conteúdo Visual do Card (Imagem ou Ícone)
            if data.get('img'):
                visual_content = ft.Image(
                    src=data['img'], 
                    width=40, height=40, 
                    fit=ft.ImageFit.CONTAIN,
                    opacity=1 if enabled else 0.5
                )
            else:
                visual_content = ft.Icon(
                    data.get('icon', ft.Icons.BUILD), 
                    size=30, 
                    color=st.COLOR_ACCENT if enabled else "grey"
                )

            btn = ft.Container(
                content=ft.Column([
                    visual_content,
                    ft.Text(btn_text, size=10, color="white" if enabled else "grey", text_align="center", weight="bold", no_wrap=False)
                ], alignment="center", spacing=5),
                bgcolor="#151525",
                border=ft.border.all(1, border_color),
                border_radius=10, 
                padding=5, 
                width=100, # Um pouco mais largo para caber nomes
                height=90,
                opacity=opacity,
                ink=True,
                on_click=lambda e, k=key: handle_add_click(k),
                tooltip=f"Req: {data['req']}" if not enabled else None
            )
            btns.append(btn)
        
        grid_container.content = ft.Row(controls=btns, wrap=True, spacing=10, run_spacing=10, alignment="center")

        # 2. ATUALIZA FILA (LISTA CENTRAL)
        list_queue_container.controls.clear()
        sim_levels = get_base_levels()
        
        if not queue_ref.current:
            list_queue_container.controls.append(ft.Text("Fila vazia.", color="grey", italic=True, size=12, text_align="center"))
        else:
            for i, item in enumerate(queue_ref.current):
                key = item['key']
                next_lvl = sim_levels[key] + 1
                sim_levels[key] = next_lvl
                display_name = f"{item['name']} (Lv {next_lvl})"
                
                # Imagem Pequena para a Fila
                b_data = BUILDINGS_DATA.get(key, {})
                if b_data.get('img'):
                    tiny_img = ft.Image(src=b_data['img'], width=20, height=20, fit=ft.ImageFit.CONTAIN)
                else:
                    tiny_img = ft.Icon(b_data.get('icon', ft.Icons.BUILD), size=16, color="grey")

                list_queue_container.controls.append(
                    ft.Container(
                        bgcolor="#1a1a25", padding=ft.padding.symmetric(horizontal=10, vertical=8), border_radius=6,
                        content=ft.Row([
                            ft.Row([
                                ft.Container(
                                    content=ft.Text(str(i+1), size=10, weight="bold", color="black"),
                                    bgcolor=st.COLOR_PRIMARY, width=20, height=20, border_radius=10, alignment=ft.alignment.center
                                ),
                                tiny_img, # <--- Imagem aqui
                                ft.Text(display_name, color="white", weight="bold", size=13),
                            ], spacing=10),
                            
                            ft.Row([
                                ft.IconButton(ft.Icons.ARROW_UPWARD, icon_color="grey", icon_size=16, tooltip="Subir", on_click=lambda e, idx=i: move_item(idx, -1)),
                                ft.IconButton(ft.Icons.ARROW_DOWNWARD, icon_color="grey", icon_size=16, tooltip="Descer", on_click=lambda e, idx=i: move_item(idx, 1)),
                                ft.IconButton(ft.Icons.CLOSE, icon_color=st.COLOR_ERROR, icon_size=16, tooltip="Remover", on_click=lambda e, idx=i: remove_item(idx))
                            ], spacing=0)
                        ], alignment="spaceBetween")
                    )
                )

        # 3. ATUALIZA LISTA DE MODELOS
        list_templates_container.controls.clear()
        if not saved_templates_ref.current:
            list_templates_container.controls.append(ft.Text("Nenhum modelo salvo.", color="grey", italic=True, size=12, text_align="center"))
        else:
            for i, t in enumerate(saved_templates_ref.current):
                list_templates_container.controls.append(
                    ft.Container(
                        bgcolor="#1a1a25", padding=10, border_radius=6, border=ft.border.all(1, "#333"),
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.DATA_OBJECT, size=16, color=st.COLOR_ACCENT),
                                ft.Text(t['name'], weight="bold", color="white", size=13)
                            ]),
                            ft.Row([
                                ft.Text(f"{len(t['queue'])} passos", size=11, color="grey"),
                                ft.Row([
                                    ft.IconButton(ft.Icons.FILE_UPLOAD, tooltip="Carregar", icon_color=st.COLOR_SUCCESS, icon_size=18, on_click=lambda e, tm=t: load_selected_template(tm)),
                                    ft.IconButton(ft.Icons.DELETE, tooltip="Excluir", icon_color=st.COLOR_ERROR, icon_size=18, on_click=lambda e, idx=i: delete_template(idx))
                                ], spacing=0)
                            ], alignment="spaceBetween")
                        ])
                    )
                )
        try:
            if page: page.update()
        except: pass

    # Async Load
    def run_initial_load():
        load_templates()
        update_ui()

    update_ui()
    threading.Thread(target=run_initial_load, daemon=True).start()
    
    btn_clear = st.get_button_style("Limpar", clear_queue, icon=ft.Icons.DELETE_SWEEP, is_primary=False)
    btn_save = st.get_button_style("Salvar", save_template, icon=ft.Icons.SAVE, is_primary=True)

    # --- LAYOUT FINAL ---
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=10),
        expand=True,
        content=ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.CONSTRUCTION, size=28, color=st.COLOR_ACCENT),
                ft.Text("Criador de Templates", size=22, weight="bold", color="white")
            ], spacing=10),
            
            ft.Divider(color="transparent", height=10),
            
            ft.Row([
                # COLUNA 1: Grade de Edifícios (Visual Melhorado)
                ft.Container(
                    expand=2, bgcolor="#12121a", padding=15, border_radius=10, border=ft.border.all(1, st.COLOR_BORDER),
                    content=ft.Column([
                        ft.Text("1. Selecione o Edifício", weight="bold", size=14, color="grey"),
                        ft.Divider(color="transparent", height=5),
                        ft.Column([grid_container], scroll="auto", expand=True)
                    ])
                ),
                
                # COLUNA 2: Fila de Construção
                ft.Container(
                    expand=2, bgcolor=st.COLOR_SURFACE, padding=15, border_radius=10, border=ft.border.all(1, st.COLOR_BORDER),
                    content=ft.Column([
                        ft.Row([ft.Text("2. Organize a Ordem", weight="bold", size=14, color="grey"), btn_clear], alignment="spaceBetween"),
                        ft.Divider(color="transparent", height=5),
                        ft.Container(content=list_queue_container, bgcolor="#0f0f15", border_radius=8, border=ft.border.all(1, st.COLOR_BORDER), expand=True),
                        ft.Divider(color="transparent", height=5),
                        ft.Row([txt_template_name, btn_save], alignment="spaceBetween")
                    ])
                ),
                
                # COLUNA 3: Salvos
                ft.Container(
                    expand=1, bgcolor="#12121a", padding=15, border_radius=10, border=ft.border.all(1, st.COLOR_BORDER),
                    content=ft.Column([
                        ft.Text("3. Salvos (Cloud)", weight="bold", size=14, color="grey"),
                        ft.Divider(color="transparent", height=5),
                        list_templates_container
                    ])
                )
            ], expand=True, spacing=15, vertical_alignment=ft.CrossAxisAlignment.START)
        ], expand=True)
    )