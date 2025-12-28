import flet as ft
from core.session_manager import session
from core.proxy_manager import manager
from core.account_manager import account_manager
from ui.home.view import HomeView
from ui.views.proxies_view import ProxiesView
from ui.views.construction_view import ConstructionView
from ui.views.recruitment_view import RecruitmentView
from ui.views.groups.view import GroupsView
from ui.views.settings_view import SettingsView
from ui.views.research_tab import ResearchTab

import ui.styles as st
from ui.views.cluster_view import ClusterView

def DashboardScreen(page: ft.Page, user_data=None):
    if not user_data:
        user_data = session.load_session()
        if not user_data: return

    # --- Extração de Dados do Usuário ---
    username = user_data.get('username', 'Admin')
    days_remaining = user_data.get('days_remaining', 0)

    content_area = ft.Container(expand=True, padding=0)

    # --- CACHE DE VIEWS ---
    views_cache = {}

    # --- ESTILOS DO MENU ---
    style_active = ft.ButtonStyle(
        color="white", 
        bgcolor=st.COLOR_PRIMARY, 
        shape=ft.RoundedRectangleBorder(radius=8),
        elevation=0,
        padding=ft.padding.symmetric(horizontal=20, vertical=18)
    )
    
    style_inactive = ft.ButtonStyle(
        color=st.COLOR_TEXT_DIM, 
        bgcolor="transparent", 
        overlay_color="#ffffff08",
        shape=ft.RoundedRectangleBorder(radius=8),
        padding=ft.padding.symmetric(horizontal=20, vertical=18)
    )

    # Definição dos botões
    btn_home = ft.TextButton("Contas", icon=ft.Icons.GRID_VIEW_ROUNDED, data="home", style=style_active)
    btn_proxies = ft.TextButton("Proxies", icon=ft.Icons.SHIELD_OUTLINED, data="proxies", style=style_inactive)
    btn_build = ft.TextButton("Construção", icon=ft.Icons.CONSTRUCTION_ROUNDED, data="construction", style=style_inactive)
    btn_recruit = ft.TextButton("Recrutamento", icon=ft.Icons.GROUP_ADD_ROUNDED, data="recruitment", style=style_inactive)
    btn_research = ft.TextButton("Pesquisa", icon=ft.Icons.SCIENCE_ROUNDED, data="research", style=style_inactive)
    btn_groups = ft.TextButton("Grupos", icon=ft.Icons.FOLDER_OPEN_ROUNDED, data="groups", style=style_inactive)
    btn_cluster = ft.TextButton("Cluster", icon=ft.Icons.HUB_ROUNDED, data="cluster", style=style_inactive)

    btn_settings = ft.IconButton(
        icon=ft.Icons.TUNE_ROUNDED, 
        tooltip="Configurações Globais", 
        data="settings", 
        icon_color=st.COLOR_TEXT_DIM,
        on_click=lambda e: mudar_aba(e)
    )

    def mudar_aba(e):
        aba = e.control.data
        
        # Reset visual dos botões
        for btn in [btn_home, btn_proxies, btn_build, btn_recruit, btn_groups, btn_cluster, btn_research]:
            btn.style = style_inactive
            if btn.data == aba: 
                btn.style = style_active
        
        btn_settings.icon_color = st.COLOR_PRIMARY if aba == "settings" else st.COLOR_TEXT_DIM
        btn_settings.update()

        # --- ROTEAMENTO ---
        
        # 1. FORÇAR RECARREGAMENTO para Proxies e Grupos
        if aba == "proxies":
            views_cache[aba] = ProxiesView(page)
        elif aba == "groups":
            views_cache[aba] = GroupsView(page)

        # 2. USAR CACHE para o resto
        if aba not in views_cache:
            if aba == "home": views_cache[aba] = HomeView(page, user_data)
            elif aba == "construction": views_cache[aba] = ConstructionView(page)
            elif aba == "recruitment": views_cache[aba] = RecruitmentView(page)
            elif aba == "settings": views_cache[aba] = SettingsView(page)
            elif aba == "research": views_cache[aba] = ResearchTab(page, account_id=None)
            elif aba == "cluster": 
                # Em vez de carregar ClusterView, criamos uma tela de aviso na hora
                views_cache[aba] = ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.ENGINEERING, size=80, color=st.COLOR_PRIMARY),
                        ft.Text("Em Construção", size=24, weight="bold", color="white"),
                        ft.Text("Este módulo estará disponível na próxima atualização.", color="grey", size=14),
                    ], 
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER, 
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=10
                    ),
                    alignment=ft.alignment.center,
                    expand=True
                )
        
        content_area.content = views_cache[aba]
        page.update()

    btn_home.on_click = mudar_aba
    btn_proxies.on_click = mudar_aba
    btn_build.on_click = mudar_aba
    btn_recruit.on_click = mudar_aba
    btn_research.on_click = mudar_aba
    btn_groups.on_click = mudar_aba
    btn_cluster.on_click = mudar_aba
    
    # --- LOGOUT CORRIGIDO ---
    def logout(e):
        session.logout()
        try:
            page.window_destroy() # Fecha a janela (Correto no Desktop)
        except:
            page.window.destroy() # Alternativa para versões mais novas

    # --- HEADER ---
    header = ft.Container(
        height=70, 
        padding=ft.padding.symmetric(horizontal=30), 
        bgcolor=st.COLOR_SURFACE,
        border=ft.border.only(bottom=ft.BorderSide(1, st.COLOR_BORDER)),
        content=ft.Row([
            
            # 1. LOGOTIPO (Texto Estilizado Limpo)
            ft.Container(
                 on_click=lambda e: mudar_aba(e), data="home",
                 content=ft.Row([
                    ft.Container(
                        content=ft.Icon(ft.Icons.DIAMOND_OUTLINED, color=st.COLOR_PRIMARY, size=22),
                    ),
                    ft.Row([
                        ft.Text("TRIBAL", weight="900", size=20, color="white", font_family="Verdana", 
                                style=ft.TextStyle(letter_spacing=1)),
                        ft.Text("CORE", weight="900", size=20, color=st.COLOR_PRIMARY, font_family="Verdana", 
                                style=ft.TextStyle(letter_spacing=1)),
                    ], spacing=0)
                ], spacing=10, alignment=ft.MainAxisAlignment.CENTER)
            ),
            
            # 2. MENU CENTRAL
            ft.Row(
                [btn_home, btn_proxies, btn_build, btn_recruit, btn_research, btn_groups, btn_cluster], 
                spacing=5
            ),
            
            # 3. PERFIL E AÇÕES
            ft.Row([
                ft.Column([
                    ft.Text(username.upper(), weight="bold", size=13, color="white", text_align="right"),
                    ft.Container(
                        content=ft.Text(f"{days_remaining} DIAS", size=9, color="black", weight="bold"),
                        bgcolor=st.COLOR_ACCENT,
                        padding=ft.padding.symmetric(horizontal=6, vertical=2),
                        border_radius=4,
                        alignment=ft.alignment.center
                    )
                ], spacing=3, alignment="center", horizontal_alignment="end"),

                ft.VerticalDivider(width=20, color=st.COLOR_BORDER, thickness=1),
                
                btn_settings,
                ft.IconButton(icon=ft.Icons.LOGOUT_ROUNDED, tooltip="Sair", icon_color=st.COLOR_ERROR, icon_size=20, on_click=logout)
            ], spacing=5, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        ], alignment="spaceBetween")
    )

    page.bgcolor = st.COLOR_BG
    page.add(ft.Column([header, content_area], expand=True, spacing=0))
    
    # Inicia na Home
    views_cache["home"] = HomeView(page, user_data)
    content_area.content = views_cache["home"]