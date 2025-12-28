import flet as ft
import time
import ui.styles as st

class ScavengeModal(ft.AlertDialog):
    def __init__(self, close_callback):
        self.content_col = ft.Column(spacing=10, tight=True)
        self.current_acc = None
        
        super().__init__(
            bgcolor="#0f0f15",
            title=ft.Text("Detalhes da Coleta", size=18, weight="bold", font_family="Verdana"),
            content=ft.Container(
                width=350,
                padding=10,
                content=self.content_col
            ),
            actions=[ft.TextButton("Fechar", on_click=close_callback)]
        )

    def render(self, acc):
        self.current_acc = acc
        self.content_col.controls.clear()
        
        s_data = acc.get('scavenge_data', {})
        levels = s_data.get('levels', {})
        
        if not levels:
            self.content_col.controls.append(ft.Text("Sem dados de coleta recentes.", color="grey"))
            return

        now = time.time()

        for lvl_id in sorted(levels.keys(), key=lambda x: int(x)):
            info = levels[lvl_id]
            status = info['status']
            end_time = info.get('end_time')
            
            icon = ft.Icons.LOCK
            color = "grey"
            text_status = "BLOQUEADO"
            
            if status == "unlocking":
                icon = ft.Icons.LOCK_OPEN
                color = st.COLOR_WARNING
                remaining = int(end_time) - now if end_time else 0
                if remaining < 0: remaining = 0
                m, s = divmod(remaining, 60)
                h, m = divmod(m, 60)
                text_status = f"DESBLOQUEANDO: {int(h):02d}:{int(m):02d}:{int(s):02d}"

            elif status == "scavenging":
                icon = ft.Icons.TIMELAPSE
                color = st.COLOR_SUCCESS
                remaining = int(end_time) - now if end_time else 0
                if remaining < 0: remaining = 0
                m, s = divmod(remaining, 60)
                h, m = divmod(m, 60)
                text_status = f"RETORNA EM: {int(h):02d}:{int(m):02d}:{int(s):02d}"

            elif status == "idle":
                icon = ft.Icons.CHECK_CIRCLE_OUTLINE
                color = st.COLOR_ACCENT
                text_status = "DISPONÍVEL"

            card = ft.Container(
                bgcolor="#1a1a25",
                padding=10,
                border_radius=8,
                border=ft.border.all(1, color if status != 'locked' else "#333"),
                content=ft.Row([
                    ft.Container(
                        content=ft.Text(str(lvl_id), weight="bold", color="black"),
                        bgcolor=color, width=25, height=25, border_radius=12.5, alignment=ft.alignment.center
                    ),
                    ft.Column([
                        ft.Text(text_status, color=color, weight="bold", size=12),
                        ft.ProgressBar(value=None, color=color, bgcolor="#222", height=2) if status in ['scavenging', 'unlocking'] else ft.Container()
                    ], expand=True),
                    ft.Icon(icon, color=color, size=18)
                ], alignment="spaceBetween")
            )
            self.content_col.controls.append(card)