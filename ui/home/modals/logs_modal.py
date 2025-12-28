import flet as ft
import ui.styles as st

class LogsModal(ft.AlertDialog):
    def __init__(self, close_callback):
        self.lv_logs = ft.ListView(expand=True, spacing=2, auto_scroll=True, padding=10)
        super().__init__(
            bgcolor="#0f0f15", 
            title_padding=10, 
            content_padding=0,
            title=ft.Text("Logs do Sistema", font_family="Consolas", size=14, weight="bold"),
            content=ft.Container(
                width=600, 
                height=400, 
                content=self.lv_logs, 
                bgcolor="black", 
                border=ft.border.all(1, "#333"),
                border_radius=0
            ),
            actions=[
                ft.TextButton("Fechar", on_click=close_callback, style=ft.ButtonStyle(color="grey"))
            ]
        )

    def render_logs(self, acc):
        self.lv_logs.controls.clear()
        for log in acc.get('logs', []):
            c = "white"
            if log['type'] == 'error': c = st.COLOR_ERROR
            elif log['type'] == 'success': c = st.COLOR_SUCCESS
            elif log['type'] == 'warn': c = st.COLOR_WARNING
            
            self.lv_logs.controls.append(
                ft.Text(f"[{log['time']}] > {log['msg']}", color=c, size=12, font_family="Consolas")
            )