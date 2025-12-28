import flet as ft
import json
import os
import threading
import ui.styles as st
from core.cloud_sync import cloud_sync

# --- DADOS DAS TROPAS E IMAGENS ---
TROOPS_DATA = {
    "barracks": {
        "name": "Quartel", 
        "image": "quartel.webp",
        "units": [
            {"id": "spear", "name": "Lanceiro", "img": "lanceiro.png"},
            {"id": "sword", "name": "Espadachim", "img": "espada.png"},
            {"id": "axe", "name": "Bárbaro", "img": "barbaro.png"},
            {"id": "archer", "name": "Arqueiro", "img": "arqueiro.png"},
        ]
    },
    "stable": {
        "name": "Estábulo", 
        "image": "estabulo.webp",
        "units": [
            {"id": "spy", "name": "Explorador", "img": "spy.png"},
            {"id": "light", "name": "Cav. Leve", "img": "cl.png"},
            {"id": "marcher", "name": "Arq. Montado", "img": "clar.png"},
            {"id": "heavy", "name": "Cav. Pesada", "img": "cp.png"},
        ]
    },
    "workshop": {
        "name": "Oficina", 
        "image": "oficina.webp",
        "units": [
            {"id": "ram", "name": "Aríete", "img": "ram.png"},
            {"id": "catapult", "name": "Catapulta", "img": "catapulta.png"},
        ]
    }
}

TEMPLATE_FILE = "recruitment_templates.json"

def RecruitmentView(page: ft.Page):
    
    # --- ESTADO LOCAL ---
    inputs_refs = {} 
    
    saved_templates_ref = ft.Ref[list]()
    saved_templates_ref.current = []

    # Input Nome do Modelo
    txt_template_name = st.get_input_style("Nome do Modelo", hint="Ex: Full Ataque")

    # --- FUNÇÃO DE MENSAGEM (CORRIGIDA - FORÇA BRUTA) ---
    def show_message(text, color):
        print(f"ALERTA: {text}") # Log para debug
        
        # Cria um NOVO snackbar toda vez. Isso garante que ele apareça.
        snack = ft.SnackBar(
            content=ft.Text(text, color="white", weight="bold"),
            bgcolor=color,
            duration=3000,
            action="OK",
            action_color="white"
        )
        
        # Atribui à página e abre
        page.snack_bar = snack
        snack.open = True
        page.update()

    # --- LÓGICA DE SALVAR/CARREGAR ---
    
    def load_templates_from_disk():
        if cloud_sync.enabled:
            server_tpl = cloud_sync.load_templates("templates_recruit")
            if server_tpl is not None:
                saved_templates_ref.current = server_tpl
                render_templates_list()
                return

        if os.path.exists(TEMPLATE_FILE):
            try:
                with open(TEMPLATE_FILE, "r") as f:
                    saved_templates_ref.current = json.load(f)
            except:
                saved_templates_ref.current = []
        else:
            saved_templates_ref.current = []
        render_templates_list()

    def save_current_template(e):
        name = txt_template_name.value.strip() if txt_template_name.value else ""
        
        # 1. VALIDAÇÃO: NOME VAZIO
        if not name:
            show_message("Erro: O modelo precisa de um nome!", st.COLOR_ERROR)
            return

        # 2. VALIDAÇÃO: NOME DUPLICADO
        current_list = saved_templates_ref.current or []
        for t in current_list:
            if t['name'].lower() == name.lower():
                show_message(f"Erro: Já existe um modelo chamado '{name}'!", st.COLOR_ERROR)
                return

        # Coleta dados dos inputs
        data = {}
        has_value = False
        for unit_id, fields in inputs_refs.items():
            # Extrai valores
            total_val = fields["total"].value.strip()
            batch_val = fields["batch"].value.strip()
            queue_val = fields["queue"].value.strip()
            
            if total_val and total_val.isdigit() and int(total_val) > 0:
                data[unit_id] = {
                    "total": int(total_val),
                    "batch": int(batch_val) if batch_val.isdigit() else 50, # Default 50
                    "limit_queue": int(queue_val) if queue_val.isdigit() else 3 # Default 3
                }
                has_value = True
            else:
                data[unit_id] = 0
        
        # 3. VALIDAÇÃO: MODELO VAZIO
        if not has_value:
            show_message("Erro: Defina a quantidade de pelo menos uma tropa!", st.COLOR_ERROR)
            return

        # Tudo certo, salva
        new_template = {"name": name, "targets": data}
        saved_templates_ref.current.append(new_template)
        
        try:
            with open(TEMPLATE_FILE, "w") as f:
                json.dump(saved_templates_ref.current, f)
                
            if cloud_sync.enabled:
                cloud_sync.save_templates("templates_recruit", saved_templates_ref.current)

            txt_template_name.value = ""
            show_message(f"Modelo '{name}' salvo com sucesso!", st.COLOR_SUCCESS)
            render_templates_list()
        except Exception as ex:
            show_message(f"Erro ao salvar arquivo: {ex}", st.COLOR_ERROR)

    def load_template_to_ui(template):
        targets = template['targets']
        for unit_id, fields in inputs_refs.items():
            if unit_id in targets:
                t_data = targets[unit_id]
                
                # Suporte a legado (se o JSON antigo tiver apenas inteiros)
                if isinstance(t_data, int):
                    fields["total"].value = str(t_data)
                    fields["batch"].value = "50"
                    fields["queue"].value = "3"
                else:
                    # Novo formato (Dicionário)
                    fields["total"].value = str(t_data.get("total", 0))
                    fields["batch"].value = str(t_data.get("batch", 50))
                    fields["queue"].value = str(t_data.get("limit_queue", 3))
            else:
                fields["total"].value = ""
        
        show_message(f"Modelo '{template['name']}' carregado nos campos!", st.COLOR_PRIMARY)

    def delete_template(index):
        if 0 <= index < len(saved_templates_ref.current):
            del saved_templates_ref.current[index]
            with open(TEMPLATE_FILE, "w") as f:
                json.dump(saved_templates_ref.current, f)
            if cloud_sync.enabled:
                cloud_sync.save_templates("templates_recruit", saved_templates_ref.current)
            render_templates_list()

    # --- COMPONENTES VISUAIS ---

    def create_building_card(building_key, building_data):
        rows = []
        for unit in building_data['units']:
            # 1. Campo META TOTAL (Igual antes)
            txt_total = ft.TextField(text_size=12, width=70, height=30, content_padding=5, 
                                     filled=True, fill_color="#0b0b0f", border_color="#333", 
                                     hint_text="Meta", text_align="center", keyboard_type="number")
            
            # 2. Campo LOTE (Novo)
            txt_batch = ft.TextField(text_size=12, width=60, height=30, content_padding=5, 
                                     filled=True, fill_color="#1a1a25", border_color="#444", 
                                     hint_text="Lote", text_align="center", keyboard_type="number",
                                     value="50") # Valor padrão sugerido

            # 3. Campo FILA (Novo)
            txt_queue = ft.TextField(text_size=12, width=50, height=30, content_padding=5, 
                                     filled=True, fill_color="#1a1a25", border_color="#444", 
                                     hint_text="Fila", text_align="center", keyboard_type="number",
                                     value="3") # Valor padrão sugerido

            # Guarda referências
            inputs_refs[unit['id']] = {"total": txt_total, "batch": txt_batch, "queue": txt_queue}

            # Layout da Linha
            row = ft.Container(
                bgcolor="#15151b", padding=5, border_radius=6, border=ft.border.all(1, "#222"),
                content=ft.Row([
                    # Ícone + Nome
                    ft.Row([
                        ft.Image(src=unit['img'], width=22, height=22, fit=ft.ImageFit.CONTAIN),
                        ft.Text(unit['name'], size=12, weight="bold", width=70, no_wrap=True),
                    ], spacing=5),
                    
                    # Inputs lado a lado
                    ft.Row([
                        ft.Column([ft.Text("Meta", size=9, color="grey"), txt_total], spacing=0),
                        ft.Column([ft.Text("Lote", size=9, color="grey"), txt_batch], spacing=0),
                        ft.Column([ft.Text("Fila", size=9, color="grey"), txt_queue], spacing=0),
                    ], spacing=5)
                ], alignment="spaceBetween")
            )
            rows.append(row)

        return ft.Container(
            expand=True, 
            bgcolor=st.COLOR_SURFACE, 
            padding=0, 
            border_radius=10, 
            border=ft.border.all(1, st.COLOR_BORDER),
            content=ft.Column([
                # Cabeçalho do Edifício
                ft.Container(
                    height=50,
                    bgcolor="#121215",
                    padding=ft.padding.symmetric(horizontal=15),
                    border=ft.border.only(bottom=ft.BorderSide(1, st.COLOR_BORDER)),
                    border_radius=ft.border_radius.only(top_left=10, top_right=10),
                    content=ft.Row([
                        ft.Image(src=building_data['image'], width=35, height=35, fit=ft.ImageFit.CONTAIN),
                        ft.Text(
                            building_data['name'].upper(), 
                            size=14, 
                            weight="bold", 
                            color="white", 
                            style=ft.TextStyle(letter_spacing=1)
                        )
                    ], spacing=10, alignment="start")
                ),
                # Lista de Tropas
                ft.Container(
                    padding=15,
                    content=ft.Column(rows, spacing=8)
                )
            ], spacing=0)
        )

    list_templates_container = ft.ListView(expand=True, spacing=5, padding=10)

    def render_templates_list():
        list_templates_container.controls.clear()
        
        # Se a lista estiver vazia
        if not saved_templates_ref.current:
            list_templates_container.controls.append(
                ft.Container(
                    content=ft.Column([
                        # CORREÇÃO AQUI: Trocamos SAVE_OFF por FOLDER_OPEN
                        ft.Icon(ft.Icons.FOLDER_OPEN, color="grey", size=30),
                        ft.Text("Sem modelos salvos", color="grey", size=12)
                    ], horizontal_alignment="center"),
                    alignment=ft.alignment.center,
                    padding=20
                )
            )
        else:
            # Se tiver itens, renderiza a lista
            for i, t in enumerate(saved_templates_ref.current):
                
                # LÓGICA DE SOMA SEGURA (Mantivemos a correção anterior aqui)
                total_troops = 0
                for val in t['targets'].values():
                    # Se for dicionário (novo formato), pega o 'total'
                    if isinstance(val, dict):
                        total_troops += int(val.get('total', 0))
                    # Se for número (formato legado), soma direto
                    elif isinstance(val, (int, float, str)) and str(val).isdigit():
                        total_troops += int(val)
                
                list_templates_container.controls.append(
                    ft.Container(
                        bgcolor="#15151b", 
                        padding=12, 
                        border_radius=8, 
                        border=ft.border.all(1, "#333"),
                        on_click=lambda e, tm=t: load_template_to_ui(tm),
                        ink=True,
                        content=ft.Row([
                            ft.Column([
                                ft.Row([
                                    ft.Icon(ft.Icons.DATA_OBJECT, size=14, color=st.COLOR_PRIMARY),
                                    ft.Text(t['name'], weight="bold", color="white", size=13)
                                ], spacing=5),
                                ft.Text(f"Total: {total_troops} un.", size=11, color="grey"),
                            ], spacing=2),
                            
                            ft.IconButton(
                                ft.Icons.DELETE_OUTLINE, 
                                tooltip="Excluir", 
                                icon_color=st.COLOR_ERROR, 
                                icon_size=18, 
                                on_click=lambda e, idx=i: delete_template(idx)
                            )
                        ], alignment="spaceBetween")
                    )
                )
        
        try:
            if page: page.update()
        except: pass

    # Criação dos Cards
    card_barracks = create_building_card("barracks", TROOPS_DATA["barracks"])
    card_stable = create_building_card("stable", TROOPS_DATA["stable"])
    card_workshop = create_building_card("workshop", TROOPS_DATA["workshop"])

    btn_save = st.get_button_style("Salvar Modelo", save_current_template, icon=ft.Icons.SAVE, is_primary=True, width=float("inf"))

    # Async Load
    def run_initial_recruit_load():
        load_templates_from_disk()
        try:
            if page: page.update()
        except: pass

    threading.Thread(target=run_initial_recruit_load, daemon=True).start()

    # --- LAYOUT PRINCIPAL ---
    return ft.Container(
        padding=ft.padding.symmetric(horizontal=10),
        expand=True,
        content=ft.Column([
            # Header da Página
            ft.Container(
                padding=ft.padding.symmetric(vertical=10),
                content=ft.Row([
                    ft.Icon(ft.Icons.GROUP_ADD, size=24, color=st.COLOR_PRIMARY),
                    ft.Text("Gerenciador de Recrutamento", size=20, weight="bold", color="white")
                ], spacing=10)
            ),
            
            # Área Principal dividida
            ft.Row([
                # COLUNA ESQUERDA (Maior): Edifícios + Painel de Salvar
                ft.Container(
                    expand=3,
                    content=ft.Column([
                        # Linha 1: Quartel e Estábulo
                        ft.Row([card_barracks, card_stable], spacing=15, vertical_alignment=ft.CrossAxisAlignment.START),
                        
                        # Linha 2: Oficina e Painel de Salvar (Lado a Lado)
                        ft.Row([
                            card_workshop, # Esquerda
                            
                            # Direita: Painel de Salvar (Abaixo do Estábulo)
                            ft.Container(
                                expand=True,
                                bgcolor=st.COLOR_SURFACE, 
                                padding=20, 
                                border_radius=10, 
                                border=ft.border.all(1, st.COLOR_BORDER),
                                content=ft.Column([
                                    ft.Text("SALVAR CONFIGURAÇÃO", weight="bold", size=12, color="grey"),
                                    ft.Divider(height=10, color="transparent"),
                                    txt_template_name,
                                    ft.Container(height=10),
                                    btn_save
                                ], alignment=ft.MainAxisAlignment.CENTER)
                            )
                        ], spacing=15, vertical_alignment=ft.CrossAxisAlignment.START)
                    ], scroll="auto", spacing=15)
                ),

                # COLUNA DIREITA (Lateral Fixa): Lista de Salvos
                ft.Container(
                    width=300,
                    bgcolor=st.COLOR_SURFACE, 
                    padding=10, 
                    border_radius=10, 
                    border=ft.border.all(1, st.COLOR_BORDER),
                    content=ft.Column([
                        ft.Container(
                            padding=10,
                            content=ft.Row([
                                ft.Icon(ft.Icons.CLOUD, size=16, color="grey"),
                                ft.Text("MODELOS SALVOS", weight="bold", size=12, color="grey")
                            ], spacing=5)
                        ),
                        ft.Divider(height=1, color="#222"),
                        list_templates_container
                    ])
                )
            ], expand=True, spacing=20)
        ], expand=True)
    )