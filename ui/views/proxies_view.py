import flet as ft
import threading
from core.proxy_manager import manager
from core.account_manager import account_manager
import ui.styles as st 

def ProxiesView(page: ft.Page):

    # --- HELPER: OPACIDADE ---
    def get_transparent_color(hex_color, opacity):
        try:
            hex_color = hex_color.lstrip('#')
            if len(hex_color) == 6:
                alpha = int(opacity * 255)
                return f"#{alpha:02x}{hex_color}"
            return hex_color
        except:
            return hex_color

    # --- ESTADO ---
    txt_stat_total = ft.Text("0", size=24, weight="bold", color="white")
    txt_stat_online = ft.Text("0", size=24, weight="bold", color="white")
    txt_stat_offline = ft.Text("0", size=24, weight="bold", color="white")
    
    txt_import_ref = ft.Ref[ft.TextField]()

    # --- COMPONENTES VISUAIS ---

    def _status_text(text, color, icon):
        """Retorna Status limpo (Row centralizada)"""
        return ft.Row([
            ft.Icon(icon, size=14, color=color),
            ft.Text(text, size=11, weight="bold", color=color)
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=6)

    def _latency_badge(ms):
        if ms == 0: return ft.Text("-", size=11, color="grey", text_align="center")
        
        c = st.COLOR_SUCCESS 
        if ms > 1000: c = st.COLOR_ERROR 
        elif ms > 300: c = st.COLOR_WARNING 
        
        return ft.Row([
            ft.Icon(ft.Icons.SIGNAL_CELLULAR_ALT, size=12, color=c),
            ft.Text(f"{ms}ms", size=11, color=c, weight="bold")
        ], alignment=ft.MainAxisAlignment.CENTER, spacing=2)

    # Helper para centralizar Títulos das Colunas (Usando Container com largura fixa para forçar alinhamento)
    def header_centered(text, width):
        return ft.DataColumn(
            ft.Container(
                content=ft.Text(text, weight="bold", size=11, color=st.COLOR_TEXT_DIM),
                alignment=ft.alignment.center,
                width=width
            )
        )

    # Definição de Larguras das Colunas (Para ficar alinhado perfeitamente)
    W_STATUS = 120
    W_ADDR = 180
    W_USER = 120
    W_LAT = 100
    W_ACTION = 60

    # Tabela principal
    proxy_table = ft.DataTable(
        width=float("inf"),
        heading_row_color=st.COLOR_SURFACE, 
        heading_row_height=45,
        data_row_min_height=55,
        data_row_max_height=55,
        data_row_color={"hover": "#1AFFFFFF"},
        divider_thickness=0,
        column_spacing=10,
        horizontal_margin=10,
        columns=[
            header_centered("STATUS", W_STATUS),
            header_centered("ENDEREÇO", W_ADDR),
            header_centered("ATRIBUÍDO A", W_USER),
            header_centered("LATÊNCIA", W_LAT),
            header_centered("AÇÃO", W_ACTION),
        ],
        rows=[]
    )

    # --- LÓGICA DE DADOS ---

    def get_account_name_by_id(account_id):
        acc = next((a for a in account_manager.accounts if a['id'] == account_id), None)
        return acc['username'] if acc else "Desconhecido"

    def refresh_ui():
        # 1. Atualiza Stats
        total = len(manager.proxies)
        working = len([p for p in manager.proxies if p['status'] == 'working'])
        errors = len([p for p in manager.proxies if p['status'] == 'error'])
        
        txt_stat_total.value = str(total)
        txt_stat_online.value = str(working)
        txt_stat_offline.value = str(errors)
        
        try:
            txt_stat_total.update()
            txt_stat_online.update()
            txt_stat_offline.update()
        except: pass

        # 2. Atualiza Tabela
        proxy_table.rows.clear()
        
        for p in manager.proxies:
            # Lógica de Status
            if p['status'] == 'testing':
                status_view = ft.Row([
                    ft.ProgressRing(width=12, height=12, stroke_width=2, color=st.COLOR_PRIMARY), 
                    ft.Text("TESTANDO", size=10, color="grey")
                ], alignment="center", spacing=5)
            elif p['status'] == 'error':
                status_view = _status_text("OFFLINE", st.COLOR_ERROR, ft.Icons.WIFI_OFF)
            elif p['assigned_to'] and p['assigned_to'] != 'none':
                status_view = _status_text("EM USO", st.COLOR_WARNING, ft.Icons.LOCK_CLOCK)
            else:
                status_view = _status_text("DISPONÍVEL", st.COLOR_SUCCESS, ft.Icons.CHECK_CIRCLE)

            # Atribuição
            if p['assigned_to'] and p['assigned_to'] != 'none':
                user = get_account_name_by_id(p['assigned_to'])
                assign_view = ft.Row([
                    ft.Icon(ft.Icons.PERSON, size=12, color="grey"), 
                    ft.Text(user, size=11, color="white")
                ], alignment="center", spacing=3)
            else:
                assign_view = ft.Text("-", color="grey", text_align="center")

            # Endereço
            addr_text = f"{p['ip']}:{p['port']}"
            if p['user']: addr_text += " (Auth)"

            # Adiciona linha (Containers com largura FIXA e alinhamento CENTER)
            proxy_table.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Container(content=status_view, width=W_STATUS, alignment=ft.alignment.center)),
                    ft.DataCell(ft.Container(content=ft.Text(addr_text, font_family="Consolas", size=12, color="white", text_align="center"), width=W_ADDR, alignment=ft.alignment.center)),
                    ft.DataCell(ft.Container(content=assign_view, width=W_USER, alignment=ft.alignment.center)),
                    ft.DataCell(ft.Container(content=_latency_badge(p.get('latency', 0)), width=W_LAT, alignment=ft.alignment.center)),
                    ft.DataCell(
                        ft.Container(
                            content=ft.IconButton(
                                ft.Icons.DELETE_OUTLINE, 
                                icon_color=st.COLOR_ERROR, 
                                icon_size=20,
                                tooltip="Remover",
                                on_click=lambda e, pid=p['id']: delete_proxy(pid)
                            ),
                            width=W_ACTION,
                            alignment=ft.alignment.center
                        )
                    ),
                ])
            )
        
        try: proxy_table.update()
        except: pass

    def delete_proxy(pid):
        for p in manager.proxies:
            if p['id'] == pid:
                p['assigned_to'] = None
                break
        manager.delete_proxy(pid)
        refresh_ui()

    def processar_import(e):
        content = txt_import_ref.current.value
        if not content: return
        
        novos = manager.add_pending_proxies(content)
        txt_import_ref.current.value = ""
        refresh_ui()
        
        def background_work():
            for p in novos:
                manager.test_proxy_connection(p)
                manager.save_to_disk()
                refresh_ui()
        
        threading.Thread(target=background_work, daemon=True).start()
        
        page.snack_bar = ft.SnackBar(
            content=ft.Text(f"{len(novos)} Proxies adicionados à fila!", color="black", weight="bold"),
            bgcolor=st.COLOR_SUCCESS
        )
        page.snack_bar.open = True
        page.update()

    # --- LAYOUT ---

    # Cards de Estatística
    def _stat_card(label, txt_control, icon, color):
        return ft.Container(
            expand=1,
            bgcolor=st.COLOR_SURFACE,
            border=ft.border.all(1, st.COLOR_BORDER),
            border_radius=10,
            padding=15,
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(icon, color=color, size=24),
                    bgcolor=get_transparent_color(color, 0.1), padding=12, border_radius=8
                ),
                ft.Column([
                    ft.Text(label, size=11, color="grey", weight="bold"),
                    txt_control
                ], spacing=0)
            ], alignment="start")
        )

    stats_row = ft.Row([
        _stat_card("TOTAL", txt_stat_total, ft.Icons.LIST, st.COLOR_PRIMARY),
        _stat_card("ONLINE", txt_stat_online, ft.Icons.CHECK_CIRCLE, st.COLOR_SUCCESS),
        _stat_card("OFFLINE", txt_stat_offline, ft.Icons.ERROR_OUTLINE, st.COLOR_ERROR),
    ], spacing=15)

    # Painel de Importação
    import_panel = ft.Container(
        width=300,
        bgcolor=st.COLOR_SURFACE,
        border=ft.border.only(right=ft.BorderSide(1, st.COLOR_BORDER)),
        padding=20,
        content=ft.Column([
            ft.Text("ADICIONAR PROXIES", size=14, weight="bold", color="white"),
            ft.Text("Formato: ip:porta:user:pass", size=11, color="grey"),
            ft.Divider(height=10, color="transparent"),
            
            ft.TextField(
                ref=txt_import_ref,
                multiline=True,
                min_lines=15,
                max_lines=15,
                text_size=12,
                hint_text="192.168.0.1:8000\n10.0.0.1:8080:user:123",
                hint_style=ft.TextStyle(color="#444", font_family="Consolas"),
                text_style=ft.TextStyle(font_family="Consolas", color=st.COLOR_PRIMARY),
                bgcolor="#0B0B0F",
                border_color=st.COLOR_BORDER,
                cursor_color=st.COLOR_PRIMARY,
                filled=True,
                border_radius=8,
                content_padding=15
            ),
            
            ft.Divider(height=10, color="transparent"),
            
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.BOLT, color="black", size=18),
                    ft.Text("PROCESSAR LISTA", color="black", weight="bold", size=12)
                ], alignment="center"),
                bgcolor=st.COLOR_PRIMARY,
                border_radius=8,
                padding=12,
                on_click=processar_import,
                shadow=ft.BoxShadow(blur_radius=10, color=get_transparent_color(st.COLOR_PRIMARY, 0.3), offset=ft.Offset(0,4)),
                ink=True
            )
        ])
    )

    # Painel da Tabela
    table_panel = ft.Container(
        expand=True,
        padding=20,
        content=ft.Column([
            stats_row,
            ft.Divider(height=20, color="transparent"),
            ft.Container(
                content=ft.Column([proxy_table], scroll="auto"),
                bgcolor=st.COLOR_SURFACE,
                border_radius=10,
                border=ft.border.all(1, st.COLOR_BORDER),
                padding=0,
                expand=True
            )
        ])
    )

    # Inicialização
    refresh_ui()

    return ft.Row([import_panel, table_panel], spacing=0, expand=True)