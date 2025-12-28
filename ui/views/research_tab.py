import flet as ft
from core.settings_manager import global_settings

# --- MAPEAMENTO DE TECNOLOGIAS ---
TECH_TRANSLATIONS = {
    "spear": "Lanceiro (Spear)",
    "sword": "Espadachim (Sword)",
    "axe": "Bárbaro (Axe)",
    "archer": "Arqueiro",
    "spy": "Espião (Spy)",
    "light": "Cavalaria Leve",
    "marcher": "Arqueiro a Cavalo",
    "heavy": "Cavalaria Pesada",
    "ram": "Aríete",
    "catapult": "Catapulta"
}

NAME_TO_ID = {v: k for k, v in TECH_TRANSLATIONS.items()}

class ResearchTab(ft.Container):
    def __init__(self, page_ref, account_id=None):
        super().__init__(padding=15, expand=True)
        self.page_ref = page_ref
        
        # Carrega as configurações GLOBAIS
        current_settings = global_settings.load_settings()
        self.priority_list = current_settings.get('research_priority', [])

        self._setup_ui()

    def _setup_ui(self):
        # --- Dropdown ---
        self.dd_techs = ft.Dropdown(
            label="Selecionar Tecnologia",
            width=250,
            options=[
                ft.dropdown.Option(text=name) 
                for name in TECH_TRANSLATIONS.values()
            ],
            text_size=14,
            content_padding=10,
            bgcolor="#2d2d2d",
            border_color="white24",
        )
        
        # --- Botão Adicionar ---
        btn_add = ft.IconButton(
            icon=ft.Icons.ADD_CIRCLE,
            icon_color="green",
            icon_size=30,
            on_click=self._add_tech,
            tooltip="Adicionar à fila GLOBAL de prioridade"
        )

        # --- Container da Lista ---
        self.list_container = ft.Column(
            spacing=4, 
            scroll=ft.ScrollMode.AUTO
        )
        
        list_wrapper = ft.Container(
            content=self.list_container,
            border=ft.border.all(1, "white12"),
            border_radius=8,
            padding=8,
            bgcolor="#1a1a1a",
            expand=True 
        )

        # --- Layout Principal ---
        self.content = ft.Column([
            ft.Row([
                ft.Column([
                    ft.Text("Ordem de Pesquisa (GLOBAL)", weight="bold", size=16, color="white"),
                    ft.Text("Esta ordem será aplicada a TODAS as contas.", size=11, color="grey")
                ], spacing=2),
                
                ft.Icon(
                    ft.Icons.INFO_OUTLINE, 
                    size=18, 
                    color="grey",
                    tooltip="O bot tentará pesquisar o primeiro item disponível desta lista em qualquer conta."
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            
            ft.Divider(height=10, color="transparent"),
            
            ft.Row([self.dd_techs, btn_add], alignment=ft.MainAxisAlignment.START),
            
            ft.Divider(height=10, color="transparent"),
            
            list_wrapper,
            
            ft.Divider(height=10, color="transparent"),
            
            ft.Row(
                [
                    ft.ElevatedButton(
                        "Salvar Configuração Global", 
                        icon=ft.Icons.SAVE, 
                        on_click=self._save, 
                        style=ft.ButtonStyle(
                            bgcolor="blue800",
                            color="white",
                            padding=15,
                            shape=ft.RoundedRectangleBorder(radius=8)
                        ),
                        width=250
                    )
                ], 
                alignment=ft.MainAxisAlignment.END
            )
        ], expand=True)

        # CORREÇÃO PRINCIPAL: Passamos update_ui=False na inicialização
        # para evitar o erro "Control must be added to the page first"
        self._render_list(update_ui=False)

    def _render_list(self, update_ui=True):
        self.list_container.controls.clear()
        
        if not self.priority_list:
            self.list_container.controls.append(
                ft.Container(
                    content=ft.Text("Nenhuma prioridade definida.", italic=True, color="grey"),
                    padding=20,
                    alignment=ft.alignment.center
                )
            )
        else:
            for i, tech_id in enumerate(self.priority_list):
                display_name = TECH_TRANSLATIONS.get(tech_id, tech_id)
                
                actions = ft.Row([
                    ft.IconButton(
                        icon=ft.Icons.ARROW_UPWARD, 
                        icon_size=18, 
                        tooltip="Subir prioridade",
                        on_click=lambda e, idx=i: self._move_item(idx, -1),
                        disabled=(i == 0)
                    ),
                    ft.IconButton(
                        icon=ft.Icons.ARROW_DOWNWARD, 
                        icon_size=18, 
                        tooltip="Descer prioridade",
                        on_click=lambda e, idx=i: self._move_item(idx, 1),
                        disabled=(i == len(self.priority_list) - 1)
                    ),
                    ft.IconButton(
                        icon=ft.Icons.CLOSE, 
                        icon_size=18, 
                        icon_color="red400", 
                        tooltip="Remover",
                        on_click=lambda e, idx=i: self._remove_item(idx)
                    )
                ], spacing=0)

                row = ft.Container(
                    bgcolor="#2d2d2d",
                    padding=ft.padding.symmetric(horizontal=10, vertical=5),
                    border_radius=5,
                    content=ft.Row([
                        ft.Row([
                            ft.Text(f"{i+1}.", width=25, weight="bold", color="white54"),
                            ft.Text(display_name, size=14, weight="w500"),
                        ]),
                        actions
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                )
                self.list_container.controls.append(row)
        
        # Só atualiza visualmente se a flag for True (cliques de botão)
        if update_ui:
            self.list_container.update()

    def _add_tech(self, e):
        selected_name = self.dd_techs.value
        if not selected_name: 
            self._show_snack("Selecione uma tecnologia primeiro.", color="orange")
            return
            
        tech_id = NAME_TO_ID.get(selected_name)
        
        if tech_id in self.priority_list:
            self._show_snack("Esta tecnologia já está na lista!", color="red")
            return

        self.priority_list.append(tech_id)
        self._render_list(update_ui=True)
        self.dd_techs.value = None
        self.dd_techs.update()

    def _remove_item(self, index):
        if 0 <= index < len(self.priority_list):
            self.priority_list.pop(index)
            self._render_list(update_ui=True)

    def _move_item(self, index, direction):
        new_index = index + direction
        if 0 <= new_index < len(self.priority_list):
            self.priority_list[index], self.priority_list[new_index] = \
            self.priority_list[new_index], self.priority_list[index]
            self._render_list(update_ui=True)

    def _save(self, e):
        # Carrega settings atuais e atualiza APENAS a priority_list
        current = global_settings.load_settings()
        current['research_priority'] = self.priority_list
        global_settings.save_settings(current)
        
        self._show_snack("Prioridades GLOBAIS salvas com sucesso!", color="green")

    def _show_snack(self, msg, color="green"):
        snack = ft.SnackBar(
            content=ft.Text(msg, color="white", weight="bold"),
            bgcolor=color,
            duration=2000
        )
        self.page_ref.overlay.append(snack)
        snack.open = True
        self.page_ref.update()