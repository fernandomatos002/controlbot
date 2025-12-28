import flet as ft
import time
import threading
from core.account_manager import account_manager
import ui.styles as st
from ui.home.logic import HomeLogic
from ui.home.components import create_account_row, header_txt, create_scavenge_cell
from ui.home.modals import LogsModal, AddAccountModal, ScavengeModal, EditAccountModal
from core.version import CURRENT_VERSION # Importando a versão

def HomeView(page: ft.Page, user_data):
    username = user_data.get('username', 'Admin')
    viewing_log_account_id = ft.Ref[str]()
    
    stop_timer = threading.Event()
    
    # 1. CACHE DE REFERÊNCIAS (Performance)
    ui_cache = {}

    # 2. Definição da Tabela
    table_contas = ft.DataTable(
        width=float("inf"), heading_row_color=st.COLOR_SURFACE, data_row_max_height=80,
        heading_row_height=50, data_row_min_height=80, divider_thickness=0, column_spacing=0, horizontal_margin=0,
        data_row_color={"hover": "#1AFFFFFF"},
        columns=[
            ft.DataColumn(header_txt("PROXY", 70)), 
            ft.DataColumn(header_txt("CONTA", 110)),
            ft.DataColumn(header_txt("PONTOS", 90)), 
            ft.DataColumn(header_txt("STATUS", 70)),
            ft.DataColumn(header_txt("RECURSOS", 280)), 
            ft.DataColumn(header_txt("COLETA", 100)),
            ft.DataColumn(header_txt("CICLO", 110)),
            ft.DataColumn(header_txt("ATAQUES", 80)), 
            ft.DataColumn(header_txt("AÇÕES", 230)),
        ], rows=[]
    )

    # 3. Funções de Callback
    def close_overlays(e):
        modal_logs.open = False
        modal_add.open = False
        modal_scavenge.open = False
        modal_edit.open = False
        page.update()

    def open_logs_window(acc):
        viewing_log_account_id.current = acc['id']
        modal_logs.title = ft.Text(f"Terminal: {acc['username']}", font_family="Consolas", size=14)
        modal_logs.render_logs(acc)
        if modal_logs not in page.overlay: page.overlay.append(modal_logs)
        modal_logs.open = True
        page.update()

    def open_add_modal(e):
        if modal_add not in page.overlay: page.overlay.append(modal_add)
        modal_add.prepare_and_open()
    
    def open_scavenge_modal(acc):
        modal_scavenge.render(acc)
        if modal_scavenge not in page.overlay: page.overlay.append(modal_scavenge)
        modal_scavenge.open = True
        page.update()

    def open_edit_modal(acc):
        if modal_edit not in page.overlay: page.overlay.append(modal_edit)
        modal_edit.open_for_edit(acc)

    # 4. Funções de Atualização da UI
    def reset_all_ui_states():
        """Reseta dados visuais na inicialização"""
        for acc in account_manager.accounts:
            aid = acc['id']
            if aid not in ui_cache: continue
            refs = ui_cache[aid]
            
            # Reset visual basics
            refs['status_icon'].color = st.COLOR_ERROR
            refs['status_icon'].name = ft.Icons.SMART_TOY_ROUNDED
            refs['cycle_state'].value = "PARADO"
            refs['cycle_state'].color = "grey"
            refs['last_run'].value = "Ult: --:--"
            
            if "btn_action" in refs:
                btn = refs["btn_action"]
                btn.icon = ft.Icons.PLAY_CIRCLE_FILLED_ROUNDED
                has_session = acc.get('session') is not None
                btn.icon_color = st.COLOR_SUCCESS if has_session else "grey"
                btn.disabled = not has_session

        try:
            if page: page.update()
        except: pass

    def refresh_ui():
        """Recria TODA a tabela."""
        table_contas.rows.clear()
        ui_cache.clear() 
        
        for acc in account_manager.accounts:
            row = create_account_row(acc, logic, open_logs_window, open_scavenge_modal, ui_cache, open_edit_modal)
            table_contas.rows.append(row)
        
        try:
            page.update()
        except: pass
        fast_update()

    def fast_update():
        """Atualiza APENAS valores (Zero Lag)."""
        has_updates = False
        for acc in account_manager.accounts:
            aid = acc['id']
            if aid not in ui_cache: continue
            
            refs = ui_cache[aid]
            has_updates = True
            
            # 1. Recursos
            res = acc.get('resources', {})
            refs['wood'].value = str(res.get('wood', 0))
            refs['stone'].value = str(res.get('stone', 0))
            refs['iron'].value = str(res.get('iron', 0))
            refs['storage'].value = str(acc.get('storage', 0))
            
            pop = acc.get('population', {})
            refs['pop'].value = f"{pop.get('current',0)}/{pop.get('max',0)}"
            refs['points'].value = f"{acc.get('points', 0):,}".replace(",", ".")

            # 2. Botão Start/Stop
            if "btn_action" in refs:
                btn = refs["btn_action"]
                is_running = acc['status'] == 'running'
                has_session = acc.get('session') is not None
                
                btn.icon = ft.Icons.STOP_CIRCLE_ROUNDED if is_running else ft.Icons.PLAY_CIRCLE_FILLED_ROUNDED
                if is_running:
                    btn.icon_color = st.COLOR_ERROR
                else:
                    btn.icon_color = st.COLOR_SUCCESS if has_session else "grey"
                btn.disabled = not has_session and not is_running

            # 3. Status
            state = acc.get('cycle_state', 'stopped')
            cyc_texts = {'checking': "Verificando...", 'verified': "VERIFICADO", 'captcha': "⛔ CAPTCHA!", 
                         'starting': "Iniciando...", 'stopped': "Parado", 'error': "ERRO"}
            refs['cycle_state'].value = cyc_texts.get(state, state.upper())
            refs['last_run'].value = f"Ult: {acc.get('last_cycle', '--:--')}"

            # Cores do Status
            if state == 'captcha':
                refs['cycle_state'].color = st.COLOR_ERROR
                refs['status_icon'].name = ft.Icons.GPP_BAD_ROUNDED
                refs['status_icon'].color = st.COLOR_ERROR
            elif state == 'running' or state == 'verified':
                refs['cycle_state'].color = st.COLOR_SUCCESS
                refs['status_icon'].name = ft.Icons.SMART_TOY_ROUNDED
                refs['status_icon'].color = st.COLOR_SUCCESS
            elif state in ['checking', 'starting']:
                refs['cycle_state'].color = st.COLOR_WARNING
                refs['status_icon'].color = st.COLOR_WARNING
            else:
                refs['cycle_state'].color = "grey"
                refs['status_icon'].color = st.COLOR_ERROR

            # 4. Ataques
            inc = acc.get('incomings', 0)
            refs['incomings'].value = str(inc)
            color_inc = st.COLOR_ERROR if inc > 0 else "grey"
            refs['incomings'].color = color_inc
            refs['inc_icon'].color = color_inc

        if has_updates:
            try: page.update()
            except: pass

    # 5. Instancia Logic e Modais
    logic = HomeLogic(page, refresh_ui) 
    
    modal_logs = LogsModal(close_overlays)
    modal_add = AddAccountModal(page, close_overlays, refresh_ui)
    modal_scavenge = ScavengeModal(close_overlays)
    modal_edit = EditAccountModal(page, close_overlays, logic.edit_account)

    original_add_log = logic.add_log
    logic.add_log = lambda aid, msg, t="info": original_add_log(aid, msg, t, modal_logs, viewing_log_account_id.current)

    # 6. Loop do Timer
    def timer_loop():
        counter = 0
        while not stop_timer.is_set():
            try:
                if not table_contas.page:
                    time.sleep(1); continue

                # Atualiza Modal Scavenge
                if modal_scavenge.open and modal_scavenge.current_acc:
                    modal_scavenge.render(modal_scavenge.current_acc)

                # Atualiza Timers da Tabela
                if len(table_contas.rows) == len(account_manager.accounts):
                    idx_coleta = 5 
                    needs_table_update = False
                    for i, row in enumerate(table_contas.rows):
                        acc = account_manager.accounts[i]
                        new_cell_content = create_scavenge_cell(acc, open_scavenge_modal)
                        if row.cells[idx_coleta].content != new_cell_content: # Otimização básica
                            row.cells[idx_coleta].content = new_cell_content
                            needs_table_update = True
                    if needs_table_update: table_contas.update()

                if counter >= 2:
                    fast_update()
                    counter = 0
                
                counter += 1
                time.sleep(1)
            except Exception as e:
                print(f"Erro Timer: {e}")
                time.sleep(1)

    # 7. Inicialização
    print("[HOME] Carregando painel - Sincronizando estados reais...")
    for acc in account_manager.accounts:
        if acc.get('status') == 'running':
            acc['status'] = 'stopped'
            acc['cycle_state'] = 'stopped'
        
        # Limpa dados visuais antigos
        acc['resources'] = {'wood': 0, 'stone': 0, 'iron': 0}
        acc['storage'] = 0
        acc['population'] = {'current': 0, 'max': 0}
        acc['points'] = 0
        acc['incomings'] = 0
    
    account_manager.save()
    refresh_ui()
    
    timer_thread = threading.Thread(target=timer_loop, daemon=True)
    timer_thread.start()

    # --- 8. DEFINIÇÃO DA UI E BOTÕES ---

    # Botões de Ação
    btn_start_all = st.get_button_style(
        "Iniciar Todas", 
        logic.start_all_bots, 
        icon=ft.Icons.ROCKET_LAUNCH_ROUNDED,
        is_primary=True 
    )

    btn_add = st.get_button_style("Adicionar", open_add_modal, icon=ft.Icons.ADD)

    # Texto da Versão (no canto superior)
    txt_version = ft.Text(f"v{CURRENT_VERSION}", size=12, color="grey", weight="bold")

    # Layout Final
    container = ft.Container(
        padding=30, 
        content=ft.Column([
            # Cabeçalho
            ft.Row([
                ft.Column([
                    ft.Text(f"Painel de Controle - {username}", size=20, weight="bold", color="white"),
                    txt_version # Colocamos a versão logo abaixo do título
                ], spacing=2),
                
                # Botões
                ft.Row([
                    btn_start_all,
                    btn_add
                ], spacing=10)
                
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            
            ft.Divider(color="transparent", height=10),
            
            # Tabela
            ft.Container(
                content=ft.Column([table_contas], scroll=ft.ScrollMode.AUTO), 
                expand=True, bgcolor=st.COLOR_SURFACE, border_radius=10, 
                border=ft.border.all(1, st.COLOR_BORDER)
            )
        ], scroll=ft.ScrollMode.AUTO)
    )

    return container