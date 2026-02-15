import flet as ft
import pg8000
from datetime import date
def get_connection():
    return pg8000.connect(
        database="system_factory",
        user="postgres",
        password="hunter1717",
        host="localhost",
        port=5432
    )
def main(page: ft.Page):
    page.title = "Система заказов машиностроительного завода"
    page.bgcolor = "#180C3B"
    page.padding = 20
    page.window_width = 800
    page.window_height = 650
    page.window_resizable = False
    page.add(
        ft.Row([
            ft.Text("Управление заказами", size=28, weight=ft.FontWeight.BOLD, color="white"),
        ]),
        ft.Divider(height=20, color="white24")
    )
    orders_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("ID", color="white")),
            ft.DataColumn(ft.Text("Изделие", color="white")),
            ft.DataColumn(ft.Text("Кол-во", color="white")),
            ft.DataColumn(ft.Text("Статус", color="white")),
            ft.DataColumn(ft.Text("Дата создания", color="white")),
            ft.DataColumn(ft.Text("Дата закрытия", color="white")),
        ],
        rows=[],
        width=750,
        bgcolor="#2A2A2A",
        heading_row_color="#5736EB",
    )
    def load_orders(e=None):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT o.id, p.name, o.quantity, o.status, 
                       o.date_of_creation, o.date_of_closing
                FROM orders o
                JOIN products p ON o.product_id = p.id
                ORDER BY o.id DESC
            """)
            rows = cursor.fetchall()
            conn.close()

            orders_table.rows.clear()
            for row in rows:
                if row[3] == 'Готов':
                    color = "green400"
                elif row[3] == 'В работе':
                    color = "orange400"
                else:
                    color = "blue400"
                closing = row[5] if row[5] else ""

                orders_table.rows.append(
                    ft.DataRow(cells=[
                        ft.DataCell(ft.Text(str(row[0]), color="white")),
                        ft.DataCell(ft.Text(row[1], color="white")),
                        ft.DataCell(ft.Text(str(row[2]), color="white")),
                        ft.DataCell(ft.Container(
                            content=ft.Text(row[3], color="white"),
                            bgcolor=color,
                            padding=5,
                            border_radius=5
                        )),
                        ft.DataCell(ft.Text(str(row[4]), color="white")),
                        ft.DataCell(ft.Text(str(closing), color="white")),
                    ])
                )
            page.update()
        except Exception:
            pass

    def change_status(order_id, new_status):
        try:
            conn = get_connection()
            cursor = conn.cursor()

            if new_status == "Готов":
                today = date.today()
                cursor.execute("""
                    UPDATE orders 
                    SET status = %s, date_of_closing = %s 
                    WHERE id = %s
                """, (new_status, today, order_id))
            else:
                cursor.execute("""
                    UPDATE orders 
                    SET status = %s, date_of_closing = NULL 
                    WHERE id = %s
                """, (new_status, order_id))
            conn.commit()
            conn.close()
            load_orders()
        except Exception:
            pass
    def delete_order(order_id):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM orders WHERE id = %s", (order_id,))
            conn.commit()
            conn.close()
            load_orders()
        except Exception:
            pass
    def show_change_status_dialog(e):
        order_id_field = ft.TextField(
            label="ID заказа",
            width=300,
            keyboard_type=ft.KeyboardType.NUMBER,
            color="white",
            label_style=ft.TextStyle(color="white")
        )

        status_dropdown = ft.Dropdown(
            label="Новый статус",
            options=[
                ft.dropdown.Option("В работе"),
                ft.dropdown.Option("Готов"),
            ],
            width=300,
            value="В работе",
            color="white",
            label_style=ft.TextStyle(color="white")
        )

        dialog = ft.AlertDialog(
            title=ft.Text("Смена статуса заказа", size=18, weight=ft.FontWeight.BOLD, color="white"),
            bgcolor="#2A2A2A",
            content=ft.Column([
                order_id_field,
                status_dropdown,
            ], height=160),
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: close_dialog(dialog), style=ft.ButtonStyle(color="white")),
                ft.FilledButton("Сохранить", on_click=lambda e: save_status(dialog),
                                style=ft.ButtonStyle(bgcolor="#5736EB", color="white")),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        def save_status(dlg):
            try:
                order_id = int(order_id_field.value)
                new_status = status_dropdown.value
                change_status(order_id, new_status)
                dlg.open = False
                page.update()
            except ValueError:
                pass
        def close_dialog(dlg):
            dlg.open = False
            page.update()

        page.show_dialog(dialog)
        page.update()
    def show_delete_order_dialog(e):
        order_id_field = ft.TextField(
            label="ID заказа для удаления",
            width=300,
            keyboard_type=ft.KeyboardType.NUMBER,
            color="white",
            label_style=ft.TextStyle(color="white")
        )
        dialog = ft.AlertDialog(
            title=ft.Text("Удаление заказа", size=18, weight=ft.FontWeight.BOLD, color="white"),
            bgcolor="#2A2A2A",
            content=ft.Column([
                order_id_field,
                ft.Text("Внимание! Это действие нельзя отменить.", color="red400"),
            ], height=120),
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: close_dialog(dialog), style=ft.ButtonStyle(color="white")),
                ft.FilledButton("Удалить", on_click=lambda e: delete_with_confirm(dialog),
                                style=ft.ButtonStyle(bgcolor="#5736EB", color="white")),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        def delete_with_confirm(dlg):
            try:
                order_id = int(order_id_field.value)
                delete_order(order_id)
                dlg.open = False
                page.update()
            except ValueError:
                pass
        def close_dialog(dlg):
            dlg.open = False
            page.update()
        page.show_dialog(dialog)
        page.update()

    def show_create_order_dialog(e):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM products ORDER BY name")
            products = cursor.fetchall()
            conn.close()
        except:
            products = []

        product_dropdown = ft.Dropdown(
            label="Продукт",
            options=[ft.dropdown.Option(str(p[0]), p[1]) for p in products],
            width=300,
            value=str(products[0][0]) if products else None,
            color="white",
            label_style=ft.TextStyle(color="white")
        )
        quantity_field = ft.TextField(
            label="Количество",
            value="1",
            width=300,
            keyboard_type=ft.KeyboardType.NUMBER,
            color="white",
            label_style=ft.TextStyle(color="white")
        )
        dialog = ft.AlertDialog(
            title=ft.Text("Заказ продукта", size=20, weight=ft.FontWeight.BOLD, color="white"),
            bgcolor="#2A2A2A",
            content=ft.Column([
                product_dropdown,
                quantity_field,
            ], height=150, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: close_dialog(dialog), style=ft.ButtonStyle(color="white")),
                ft.FilledButton("Создать", on_click=lambda e: save_order(dialog),
                                style=ft.ButtonStyle(bgcolor="#5736EB", color="white")),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        def save_order(dlg):
            try:
                product_id = int(product_dropdown.value)
                quantity = int(quantity_field.value)

                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO orders (product_id, quantity, status, date_of_creation)
                    VALUES (%s, %s, 'Новый', CURRENT_DATE)
                """, (product_id, quantity))
                conn.commit()
                conn.close()

                dlg.open = False
                page.update()
                load_orders()
            except Exception:
                pass
        def close_dialog(dlg):
            dlg.open = False
            page.update()
        page.show_dialog(dialog)
        page.update()
    def show_materials_dialog(e):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT p.name, m.name, m.unit, pm.quantity_per_unit
                FROM products p
                JOIN product_materials pm ON p.id = pm.product_id
                JOIN materials m ON pm.material_id = m.id
                ORDER BY p.name
            """)
            materials = cursor.fetchall()
            conn.close()
        except Exception:
            materials = []
        if not materials:
            return
        materials_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Продукт", color="white")),
                ft.DataColumn(ft.Text("Материал", color="white")),
                ft.DataColumn(ft.Text("Ед. изм.", color="white")),
                ft.DataColumn(ft.Text("Количество", color="white")),
            ],
            rows=[],
            bgcolor="#2A2A2A",
            heading_row_color="#5736EB",
        )
        for m in materials:
            materials_table.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(m[0], color="white")),
                    ft.DataCell(ft.Text(m[1], color="white")),
                    ft.DataCell(ft.Text(m[2], color="white")),
                    ft.DataCell(ft.Text(f"{float(m[3]):.2f}", color="white")),
                ])
            )

        dialog = ft.AlertDialog(
            title=ft.Text("Материалы", size=20, weight=ft.FontWeight.BOLD, color="white"),
            bgcolor="#2A2A2A",
            content=ft.Container(
                content=materials_table,
                width=600,
                height=300,
            ),
            actions=[
                ft.TextButton("Закрыть", on_click=lambda e: close_dialog(dialog), style=ft.ButtonStyle(color="white")),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        def close_dialog(dlg):
            dlg.open = False
            page.update()

        page.show_dialog(dialog)
        page.update()

    button_style = ft.ButtonStyle(
        bgcolor="#5736EB",
        color="white",
    )
    page.add(
        ft.Row([
            ft.FilledButton("Создать заказ", on_click=show_create_order_dialog, style=button_style),
            ft.FilledButton("Материалы", on_click=show_materials_dialog, style=button_style),
            ft.FilledButton("Смена статуса", on_click=show_change_status_dialog, style=button_style),
            ft.FilledButton("Удалить заказ", on_click=show_delete_order_dialog, style=button_style),
        ], wrap=True),
        ft.Divider(height=20, color="white24"),
        ft.Text("Производственные заказы", size=18, weight=ft.FontWeight.BOLD, color="white"),

        ft.Container(
            content=ft.Column([
                ft.Container(
                    content=orders_table,
                    padding=10,
                )
            ], scroll=ft.ScrollMode.ALWAYS, height=400),
            border=ft.Border.all(1, ft.Colors.GREY_800),
            border_radius=10,
            bgcolor="#2A2A2A",
        )
    )
    load_orders()

if __name__ == "__main__":
    ft.app(target=main)
