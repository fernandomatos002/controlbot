import flet as ft
import threading
from core.account_manager import account_manager
from core.features.cluster.controller import cluster_controller
from core.features.cluster.calculator import cluster_calculator
from core.bot_controller import bot_controller  # <--- ADICIONE ESTE IMPORT
import ui.styles as st

class ClusterView(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__(expand=True, padding=20)
        self.page_ref = page
        
        # --- ESTADO ---
        self.selected_master_id = None
        self.manual_master_name = None
        self.pool_ids = set()
        self.calculated_tree = None 
        
        # --- COMPONENTES ---
        
        # 1. Seletor de Tipo de Master
        self.radio_type = ft.RadioGroup(
            content=ft.Row([
                ft.Radio(value="internal", label="Usar Conta do Bot", active_color=st.COLOR_PRIMARY),
                ft.Radio(value="external", label="Jogador Externo", active_color=st.COLOR_ACCENT)
            ]),
            value="internal",
            on_change=self._toggle_master_input
        )

        # 2. Input: Dropdown (Para conta Interna)
        self.dd_master = ft.Dropdown(
            hint_text="Selecione a conta Rei...",
            text_size=13,
            text_style=ft.TextStyle(color="white"),
            bgcolor="#16161C",
            border_color=st.COLOR_BORDER,
            focused_border_color=st.COLOR_PRIMARY,
            filled=True,
            border_radius=10,
            content_padding=15,
            on_change=self._on_master_change
        )

        # 3. Input: Texto (Para conta Externa)
        self.txt_manual_master = ft.TextField(
            label="Nome do Jogador Master",
            hint_text="Ex: General_Zod",
            text_style=ft.TextStyle(color="white"),
            bgcolor="#16161C",
            border_color=st.COLOR_ACCENT,
            border_radius=10,
            visible=False,
            on_change=self._validate_calc_button 
        )

        # Lista de Pool
        self.lv_pool = ft.ListView(expand=True, spacing=2, padding=5)
        
        # --- Visualização da Árvore ---
        self.txt_tree = ft.Text(
            value="Configure o Master e o Pool, depois clique em 'Calcular'.",
            font_family="Consolas", 
            size=11, 
            color="grey",
            selectable=True
        )
        self.tree_container = ft.Container(
            content=ft.Column([self.txt_tree], scroll=ft.ScrollMode.AUTO),
            bgcolor="#0F0F12",
            border=ft.border.all(1, "#333"),
            border_radius=8,
            padding=10,
            expand=2 
        )

        # Console
        self.lv_console = ft.ListView(expand=True, spacing=2, padding=10, auto_scroll=True)
        self.console_container = ft.Container(
            content=self.lv_console,
            bgcolor="black",
            border=ft.border.all(1, "#333"),
            border_radius=8,
            expand=1
        )

        # --- BOTÕES ---
        
        # Botão Calcular (CORRIGIDO: Usando string hex em vez de ft.colors)
        self.btn_calc = ft.ElevatedButton(
            "1. CALCULAR ESTRUTURA",
            icon=ft.Icons.SCHEMA,
            style=ft.ButtonStyle(
                color="white",
                bgcolor="#37474F",  # Equivalente ao BLUE_GREY_800
                shape=ft.RoundedRectangleBorder(radius=8),
            ),
            on_click=self._on_click_calculate
        )

        # Botão Iniciar
        self.btn_start = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.ROCKET_LAUNCH, color="white"),
                ft.Text("2. INICIAR OPERAÇÃO", weight="bold", color="white")
            ], alignment="center"),
            bgcolor=st.COLOR_PRIMARY,
            padding=15,
            border_radius=10,
            
            # AQUI ESTÁ A MUDANÇA IMPORTANTE:
            # Antes era: on_click=self._start_cluster_process
            # Agora é:
            on_click=self._ask_confirmation, 
            
            opacity=0.5, 
            animate_opacity=300,
            ignore_interactions=True # Começa desativado até calcular
        )
        # ---------------- ATÉ ESTA LINHA ----------------

        # --- LAYOUT ---
        col_config = ft.Container(
            expand=1,
            bgcolor=st.COLOR_SURFACE,
            padding=20,
            border_radius=10,
            border=ft.border.all(1, st.COLOR_BORDER),
            content=ft.Column([
                ft.Text("Configuração do Cluster (Base 5)", size=16, weight="bold", color="white"),
                ft.Container(height=5),
                
                self.radio_type,
                ft.Container(height=10),
                self.dd_master,       
                self.txt_manual_master,
                
                ft.Divider(height=20, color="#333"),
                
                ft.Row([
                    ft.Text("Pool de Contas", size=14, weight="bold", color="white"),
                    ft.TextButton("Selecionar Tudo", on_click=self._select_all_pool)
                ], alignment="spaceBetween"),
                
                ft.Container(
                    content=self.lv_pool,
                    expand=True,
                    bgcolor="#121218",
                    border_radius=8,
                    padding=5,
                    border=ft.border.all(1, "#222")
                ),
                
                ft.Divider(height=10, color="transparent"),
                self.btn_calc, 
                ft.Container(height=5),
                self.btn_start 
            ])
        )

        col_terminal = ft.Container(
            expand=1,
            bgcolor="#121218",
            padding=15,
            border_radius=10,
            border=ft.border.all(1, st.COLOR_BORDER),
            content=ft.Column([
                ft.Text("Pré-visualização da Pirâmide", size=14, weight="bold", color="white"),
                self.tree_container, 
                ft.Divider(height=10, color="#333"),
                ft.Text("Console de Operação", size=14, weight="bold", color="white"),
                self.console_container
            ])
        )

        self.content = ft.Row([col_config, col_terminal], spacing=20, expand=True)

        # Config Inicial
        cluster_controller.set_logger(self._log)
        self._load_accounts()

    # --- LÓGICA DE UI ---

    def _toggle_master_input(self, e):
        mode = self.radio_type.value
        if mode == "internal":
            self.dd_master.visible = True
            self.txt_manual_master.visible = False
            self.selected_master_id = self.dd_master.value
        else:
            self.dd_master.visible = False
            self.txt_manual_master.visible = True
            self.selected_master_id = "EXTERNAL"
        
        self.update()
        self._render_pool_list()
        self._validate_calc_button()

    def _load_accounts(self):
        options = []
        for acc in account_manager.accounts:
            label = f"{acc['username']} ({acc.get('world', '?')})"
            options.append(ft.dropdown.Option(acc['id'], label))
        self.dd_master.options = options
        self._render_pool_list()

    def _render_pool_list(self):
        self.lv_pool.controls.clear()
        
        for acc in account_manager.accounts:
            if self.radio_type.value == "internal" and acc['id'] == self.dd_master.value:
                continue

            is_selected = acc['id'] in self.pool_ids
            
            item = ft.Container(
                bgcolor="#1A1A22" if not is_selected else "#2A2A35",
                border=ft.border.all(1, st.COLOR_PRIMARY if is_selected else "transparent"),
                border_radius=6,
                padding=8,
                on_click=lambda e, aid=acc['id']: self._toggle_pool_id(aid),
                content=ft.Row([
                    ft.Checkbox(value=is_selected, disabled=True, active_color=st.COLOR_PRIMARY),
                    ft.Text(acc['username'], weight="bold", color="white" if is_selected else "grey"),
                    ft.Text(f"[{acc.get('world','?')}]", size=10, color="grey")
                ])
            )
            self.lv_pool.controls.append(item)
        
        if self.page: self.update()

    def _on_master_change(self, e):
        self.selected_master_id = self.dd_master.value
        if self.selected_master_id in self.pool_ids:
            self.pool_ids.remove(self.selected_master_id)
        self._render_pool_list()
        self._validate_calc_button()

    def _toggle_pool_id(self, aid):
        if aid in self.pool_ids: self.pool_ids.remove(aid)
        else: self.pool_ids.add(aid)
        self._render_pool_list()
        self.calculated_tree = None
        self._validate_calc_button()
        self._disable_start_button()

    def _select_all_pool(self, e):
        for acc in account_manager.accounts:
            if self.radio_type.value == "internal" and acc['id'] == self.dd_master.value:
                continue
            self.pool_ids.add(acc['id'])
        self._render_pool_list()
        self._validate_calc_button()

    def _validate_calc_button(self, e=None):
        has_pool = len(self.pool_ids) > 0
        has_master = False
        if self.radio_type.value == "internal":
            has_master = self.dd_master.value is not None
        else:
            has_master = len(self.txt_manual_master.value or "") > 2

        is_valid = has_master and has_pool
        self.btn_calc.disabled = not is_valid
        self.update()

    def _disable_start_button(self):
        self.btn_start.opacity = 0.5
        self.btn_start.ignore_interactions = True
        self.btn_start.content.controls[1].value = "2. INICIAR OPERAÇÃO"
        self.update()

    def _enable_start_button(self):
        self.btn_start.opacity = 1
        self.btn_start.ignore_interactions = False
        self.update()

    # --- AÇÃO: CALCULAR ---
    def _on_click_calculate(self, e):
        master_name = ""
        if self.radio_type.value == "internal":
            acc = account_manager.get_account(self.dd_master.value)
            master_name = acc['username'] if acc else "Desconhecido"
        else:
            master_name = self.txt_manual_master.value.strip()

        pool_names = []
        for aid in self.pool_ids:
            acc = account_manager.get_account(aid)
            if acc: pool_names.append(acc['username'])
        
        result = cluster_calculator.calculate(len(pool_names)+1, master_name, pool_names)
        
        if result['is_valid']:
            visual_tree = cluster_calculator.visualize(result['structure'])
            self.txt_tree.value = visual_tree
            self.txt_tree.color = st.COLOR_SUCCESS
            self.calculated_tree = result['structure']
            self._enable_start_button() 
            self._log(f"✅ Cálculo OK: {result['message']}", "success")
        else:
            self.txt_tree.value = f"❌ {result['message']}"
            self.txt_tree.color = st.COLOR_ERROR
            self.calculated_tree = None
            self._disable_start_button()
            self._log(result['message'], "error")
        
        self.update()

    # --- AÇÃO: INICIAR ---
    # --- NOVO: LÓGICA DE CONFIRMAÇÃO E PARADA ---

    def _ask_confirmation(self, e):
        """1. Primeiro passo ao clicar em INICIAR: Pede confirmação"""
        if not self.calculated_tree:
            self._log("Calcule a estrutura antes de iniciar!", "error")
            return

        # Cria o modal de confirmação
        dlg_confirm = ft.AlertDialog(
            title=ft.Text("⚠️ Atenção: Conflito de Processos", color=st.COLOR_WARNING, weight="bold"),
            content=ft.Column([
                ft.Text("Para executar o Cluster com segurança, o bot de farm/construção NÃO pode estar rodando nas contas envolvidas.", size=13),
                ft.Container(height=10),
                ft.Text("Ao confirmar, o sistema irá:", size=13, weight="bold"),
                ft.Text("1. PAUSAR automaticamente todas as contas do Pool.", size=12, color="grey"),
                ft.Text("2. Iniciar o processo de convites e realocação.", size=12, color="grey"),
            ], tight=True, spacing=5),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self.page_ref.close(dlg_confirm)),
                ft.ElevatedButton(
                    "Entendido, Parar Bots e Iniciar", 
                    bgcolor=st.COLOR_ERROR, 
                    color="white",
                    on_click=lambda e: self._execute_force_stop_and_start(dlg_confirm)
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            bgcolor="#1A1A22",
            shape=ft.RoundedRectangleBorder(radius=10)
        )
        
        self.page_ref.open(dlg_confirm)

    def _execute_force_stop_and_start(self, dlg):
        """2. Segundo passo: Para os bots e inicia a thread"""
        self.page_ref.close(dlg)
        
        # Identifica quem está envolvido
        master_target = None
        is_manual = False
        pool_ids_list = list(self.pool_ids)

        if self.radio_type.value == "internal":
            master_target = self.dd_master.value
            # Se o master é interno, também precisa ser pausado
            if master_target:
                self._stop_bot_if_running(master_target)
        else:
            master_target = self.txt_manual_master.value.strip()
            is_manual = True

        # Pausa todos do pool
        self._log("🛑 Verificando e pausando bots ativos...", "process")
        for aid in pool_ids_list:
            self._stop_bot_if_running(aid)
            
        # UI Feedback
        self._disable_start_button()
        self.btn_start.content.controls[1].value = "OPERANDO..."
        self.update()

        # Inicia Thread do Cluster
        threading.Thread(
            target=self._run_thread, 
            args=(master_target, pool_ids_list, is_manual),
            daemon=True
        ).start()

    def _stop_bot_if_running(self, account_id):
        """Helper para parar bot individualmente"""
        acc = account_manager.get_account(account_id)
        if acc and acc.get('status') == 'running':
            bot_controller.stop_cycle(account_id)
            self._log(f"⏸️ Bot pausado na conta: {acc['username']}", "warn")
    
    def _start_cluster_process(self, e):
        if not self.calculated_tree:
            self._log("Calcule a estrutura antes de iniciar!", "error")
            return

        self._disable_start_button()
        self.btn_start.content.controls[1].value = "OPERANDO..."
        self.update()
        
        master_target = None
        is_manual = False

        if self.radio_type.value == "internal":
            master_target = self.dd_master.value
        else:
            master_target = self.txt_manual_master.value.strip()
            is_manual = True

        threading.Thread(
            target=self._run_thread, 
            args=(master_target, list(self.pool_ids), is_manual),
            daemon=True
        ).start()

    def _run_thread(self, master, pool, manual):
        try:
            cluster_controller.execute_operation(master, pool, manual)
        except Exception as e:
            self._log(f"Erro Crítico: {e}", "error")
        finally:
            self.page_ref.update()

    # --- LOGGING ---
    def _log(self, msg, type="info"):
        color = "white"
        if type == "success": color = st.COLOR_SUCCESS
        elif type == "error": color = st.COLOR_ERROR
        elif type == "warn": color = st.COLOR_WARNING
        elif type == "process": color = st.COLOR_ACCENT

        self.lv_console.controls.append(
            ft.Text(f"> {msg}", color=color, font_family="Consolas", size=11, selectable=True)
        )
        self.page_ref.update()