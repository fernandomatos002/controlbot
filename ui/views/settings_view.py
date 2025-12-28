import flet as ft
from core.settings_manager import global_settings
import ui.styles as st

def SettingsView(page: ft.Page):
    
    current_settings = global_settings.load_settings()

    # --- INPUTS DE TEMPO ---
    txt_min = st.get_input_style("Mínimo (minutos)", hint="3", width=150)
    txt_min.value = str(current_settings.get('min_interval', 3))
    
    txt_max = st.get_input_style("Máximo (minutos)", hint="5", width=150)
    txt_max.value = str(current_settings.get('max_interval', 5))
    
    # --- CHECKBOXES ---
    chk_farm = ft.Checkbox(
        label="Priorizar Fazenda (se População > 80%)", 
        value=current_settings.get('farm_priority', False),
        label_style=ft.TextStyle(color="white", size=14),
        active_color=st.COLOR_PRIMARY
    )
    
    chk_storage = ft.Checkbox(
        label="Priorizar Armazém (se Custo > Capacidade)", 
        value=current_settings.get('storage_priority', False),
        label_style=ft.TextStyle(color="white", size=14),
        active_color=st.COLOR_PRIMARY
    )

    # NOVO CHECKBOX
    chk_reserve = ft.Checkbox(
        label="Reservar Recursos para Construção (Recrutamento Inteligente)", 
        value=current_settings.get('reserve_for_building', True),
        label_style=ft.TextStyle(color="white", size=14),
        active_color=st.COLOR_PRIMARY,
        tooltip="Se ativado, o recrutamento não gastará recursos necessários para o próximo item da fila de construção."
    )

    # --- SALVAR ---
    def save_action(e):
        try:
            val_min = int(txt_min.value)
            val_max = int(txt_max.value)
            
            if val_min < 1:
                page.snack_bar = ft.SnackBar(ft.Text("Mínimo deve ser >= 1 min!"), bgcolor=st.COLOR_ERROR); page.snack_bar.open=True; page.update(); return
            if val_max <= val_min:
                page.snack_bar = ft.SnackBar(ft.Text("Máximo deve ser maior que o mínimo!"), bgcolor=st.COLOR_ERROR); page.snack_bar.open=True; page.update(); return

            new_data = {
                "min_interval": val_min,
                "max_interval": val_max,
                "farm_priority": chk_farm.value,
                "storage_priority": chk_storage.value,
                "reserve_for_building": chk_reserve.value # Salva a nova config
            }
            
            global_settings.save_settings(new_data)
            
            page.snack_bar = ft.SnackBar(ft.Text("Configurações Salvas!"), bgcolor=st.COLOR_SUCCESS)
            page.snack_bar.open = True
            page.update()
            
        except ValueError:
            page.snack_bar = ft.SnackBar(ft.Text("Use apenas números inteiros."), bgcolor=st.COLOR_ERROR); page.snack_bar.open=True; page.update()

    btn_save = st.get_button_style("Salvar Configurações", save_action, icon=ft.Icons.SAVE)

    # --- LAYOUT ---
    return ft.Container(
        padding=30,
        content=ft.Column([
            ft.Row([ft.Icon(ft.Icons.SETTINGS, size=28, color=st.COLOR_ACCENT), ft.Text("Configurações Globais", size=22, weight="bold", color="white")], spacing=10),
            ft.Divider(color="transparent", height=20),
            ft.Container(
                bgcolor=st.COLOR_SURFACE, padding=20, border_radius=10, border=ft.border.all(1, st.COLOR_BORDER),
                content=ft.Column([
                    ft.Text("Intervalo de Verificação", weight="bold", size=16, color=st.COLOR_ACCENT),
                    ft.Text("Tempo aleatório entre os ciclos.", size=12, color="grey"),
                    ft.Divider(height=10, color="transparent"),
                    ft.Row([ft.Column([ft.Text("Mínimo", size=12), txt_min]), ft.Column([ft.Text("Máximo", size=12), txt_max])], spacing=20),
                    
                    ft.Divider(height=30, color="#222"),
                    
                    ft.Text("Lógica Inteligente", weight="bold", size=16, color=st.COLOR_ACCENT),
                    ft.Divider(height=10, color="transparent"),
                    chk_farm,
                    ft.Container(height=5),
                    chk_storage,
                    ft.Container(height=5),
                    chk_reserve, # <--- Adicionado na tela
                    
                    ft.Divider(height=30, color="transparent"),
                    ft.Row([btn_save], alignment="start")
                ])
            )
        ], expand=True, scroll="auto")
    )