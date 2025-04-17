import flet as ft
import pandas as pd
import os

KANBAN_PATH = "kanban_com_subtarefas.xlsx"

def build_checkboxes(subtarefas, update_status_and_save):
    checkboxes = []
    for i, (label, checked) in enumerate(subtarefas):
        def make_handler(idx):
            def handler(e):
                subtarefas[idx] = (subtarefas[idx][0], e.control.value)
                update_status_and_save()
            return handler
        checkbox = ft.Checkbox(label=label, value=checked, on_change=make_handler(i))
        checkboxes.append(checkbox)
    return checkboxes

def build_card(row, on_update, df_global, save_data, serialize_subtarefas, parse_subtarefas, page):
    subtarefas = parse_subtarefas(row.Subtarefas)

    def update_status_and_save():
        checked = sum(1 for _, checked in subtarefas if checked)
        total = len(subtarefas)
        new_status = row.Status

        if checked == 0:
            new_status = "A FAZER"
        elif checked < total:
            new_status = "EM ANDAMENTO"
        elif checked == total:
            new_status = "CONCLUÍDO"

        idx = df_global[df_global.Tarefa == row.Tarefa].index[0]
        df_global.at[idx, "Status"] = new_status
        df_global.at[idx, "Subtarefas"] = serialize_subtarefas(subtarefas)
        save_data(df_global)
        on_update()

    checkboxes = build_checkboxes(subtarefas, update_status_and_save)

    new_subtask_input = ft.TextField(label="Nova Subtarefa", expand=True)

    def add_subtask(e):
        new_sub = new_subtask_input.value.strip()
        if new_sub:
            subtarefas.append((new_sub, False))
            idx = df_global[df_global.Tarefa == row.Tarefa].index[0]
            df_global.at[idx, "Subtarefas"] = serialize_subtarefas(subtarefas)
            save_data(df_global)
            on_update()

    def remove_card(e):
        def confirm_delete(ev):
            df_global.drop(index=df_global[df_global.Tarefa == row.Tarefa].index, inplace=True)
            save_data(df_global)
            page.dialog.open = False
            page.update()
            on_update()

        def cancel_delete(ev):
            page.dialog.open = False
            page.update()

        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirmar exclusão"),
            content=ft.Text(f"Deseja remover a tarefa '{row.Tarefa}'?"),
            actions=[
                ft.TextButton("Cancelar", on_click=cancel_delete),
                ft.ElevatedButton("Confirmar", on_click=confirm_delete)
            ]
        )
        page.dialog = confirm_dialog
        confirm_dialog.open = True
        page.update()

    card_content = ft.Container(
        content=ft.Column([
            ft.Row(controls=[
                ft.Text(row.Tarefa, weight="bold", expand=True),
                ft.IconButton(icon=ft.icons.DELETE, tooltip="Remover tarefa", on_click=remove_card)
            ]),
            ft.Text(f"Prioridade: {row.Prioridade} | Categoria: {row.Categoria}", size=12, italic=True),
            *checkboxes,
            ft.Row([new_subtask_input, ft.IconButton(icon=ft.icons.ADD, tooltip="Adicionar Subtarefa", on_click=add_subtask)])
        ]),
        padding=10,
        margin=5,
        bgcolor=ft.colors.WHITE,
        border_radius=10,
        border=ft.border.all(1, ft.colors.GREY_300)
    )

    return ft.Container(
        content=ft.AnimatedSwitcher(
            content=ft.Draggable(           
                    group="cards",
                    data=str(row.Tarefa),
                    content=ft.Container(content=card_content, bgcolor=ft.colors.TRANSPARENT),
                    content_feedback=card_content,
                    content_when_dragging=ft.Container(
                        content=card_content.content,
                        opacity=0.5,  # semitransparente
                        animate_opacity=300,
                        border=ft.border.all(2, ft.colors.BLUE),
                        bgcolor=ft.colors.BLUE_100
                    ),  
                ),
    transition=ft.AnimatedSwitcherTransition.SCALE,
    duration=300
)
        
    )

def main(page: ft.Page):
    page.title = "Kanban com Subtarefas"
    page.scroll = "auto"
    page.window_maximized = True
    page.window_resizable = True

    if not os.path.exists(KANBAN_PATH):
        df_init = pd.DataFrame([{
            "Tarefa": "Tarefa Exemplo",
            "Status": "A FAZER",
            "Categoria": "Geral",
            "Prioridade": "Média",
            "Subtarefas": "Sub1:False;Sub2:False"
        }])
        df_init.to_excel(KANBAN_PATH, index=False)

    df_global = pd.read_excel(KANBAN_PATH)

    def save_data(df):
        df.to_excel(KANBAN_PATH, index=False)

    def serialize_subtarefas(subtarefas):
        return ";".join([f"{label}:{str(checked)}" for label, checked in subtarefas])

    def parse_subtarefas(text):
        subtarefas = []
        if text:
            for item in text.split(";"):
                if ":" in item:
                    label, state = item.rsplit(":", 1)
                    subtarefas.append((label.strip(), state.strip() == "True"))
                else:
                    subtarefas.append((item.strip(), False))
        return subtarefas

    def render_app():
        def build_column(status, color):
            tasks_in_column = df_global[df_global["Status"] == status].copy()

            cards = [
                build_card(row, render_app, df_global, save_data, serialize_subtarefas, parse_subtarefas, page)
                for _, row in tasks_in_column.iterrows()
            ]

            add_button = ft.IconButton(icon=ft.icons.ADD_CIRCLE_OUTLINE, tooltip="Nova tarefa", on_click=open_add_task_dialog)
            dummy_button = ft.IconButton(
                icon=ft.icons.ADD_CIRCLE_OUTLINE,
                icon_color=ft.colors.TRANSPARENT,  # ícone invisível
                disabled=True,
                tooltip="",  # nada ao passar o mouse
            )
            
            def on_accept_card(e):
                src = page.get_control(eval(e.data)['src_id'])
                task_name = f"{src.content.content.content.controls[0].controls[0].value}"
                if task_name in df_global.Tarefa.values:
                    idx = df_global[df_global.Tarefa == task_name].index[0]
                    df_global.at[idx, "Status"] = status
                    save_data(df_global)
                    page.update()
                    render_app()  # <- chama render após salvar

            def on_will_accept(e):
                e.control.content.bgcolor = ft.colors.BLUE_50
                page.update()
                return True

            def on_leave(e):
                e.control.content.bgcolor = color
                page.update()

            return ft.Container(
                expand=True,
                key=f'{status}',
                content=ft.Column(
                    controls=[
                        # Cabeçalho fixo
                        ft.Row(
                            controls=[
                                ft.Text(status, size=16, weight="bold"),
                                add_button if status == "A FAZER" else dummy_button
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        # Cards scrolláveis
                        ft.Container(
                            height=page.height - 120,  # altura da área de cards — ajustável
                            content=ft.DragTarget(
                                group="cards",
                                on_accept=on_accept_card,
                                on_will_accept=on_will_accept,
                                on_leave=on_leave,
                                content=ft.Container(
                                    bgcolor=color,
                                    border_radius=10,
                                    padding=10,
                                    content=ft.Column(
                                        scroll="auto",
                                        spacing=10,
                                        controls=cards if cards else [ft.Container(height=100, opacity=0)]
                                    )
                                )
                            )
                        )
                    ]
                )
            )


        page.controls.clear()
        page.add(
            ft.Row([
                build_column("A FAZER", ft.colors.RED_100),
                build_column("EM ANDAMENTO", ft.colors.YELLOW_100),
                build_column("CONCLUÍDO", ft.colors.GREEN_100)
            ], expand=True)
        )
        page.update()

    def open_add_task_dialog(e):
        input_task = ft.TextField(label="Nova tarefa")
        input_category = ft.TextField(label="Categoria")
        input_priority = ft.Dropdown(
            label="Prioridade",
            options=[
                ft.dropdown.Option("Alta"),
                ft.dropdown.Option("Média"),
                ft.dropdown.Option("Baixa")
            ]
        )
        input_subtasks = ft.TextField(label="Subtarefas (separadas por ;)")

        def confirm_add(e):
            if not input_task.value.strip() or not input_category.value.strip() or not input_priority.value or not input_subtasks.value.strip():
                page.snack_bar = ft.SnackBar(ft.Text("Preencha todos os campos antes de adicionar a tarefa."))
                page.snack_bar.open = True
                page.update()
                return

            subtarefas_formatadas = serialize_subtarefas([(st.strip(), False) for st in input_subtasks.value.split(";")])

            new_task = {
                "Tarefa": input_task.value,
                "Status": "A FAZER",
                "Categoria": input_category.value,
                "Prioridade": input_priority.value,
                "Subtarefas": subtarefas_formatadas
            }
            df_global.loc[len(df_global)] = new_task
            save_data(df_global)
            page.dialog.open = False
            page.update()
            render_app()

        def cancel_add(e):
            page.dialog.open = False
            page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Adicionar nova tarefa"),
            content=ft.Column([
                input_task,
                input_category,
                input_priority,
                input_subtasks
            ], tight=True),
            actions=[
                ft.TextButton("Cancelar", on_click=cancel_add),
                ft.ElevatedButton("Adicionar", on_click=confirm_add)
            ]
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    page.on_resize = lambda e: render_app()
    render_app()

ft.app(target=main)