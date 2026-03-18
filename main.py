import flet as ft
import pg8000
from datetime import date

def get_connection():
    return pg8000.connect(
        database="system_factory",
        user="postgres",
        password="password",
        host="localhost",
        port=5432
    )

def check_materials_availability(product_id, quantity):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT m.id, m.name, m.unit, m.stock_balance, 
                   pm.quantity_per_unit, 
                   (pm.quantity_per_unit * %s) as required_quantity
            FROM materials m
            JOIN product_materials pm ON m.id = pm.material_id
            WHERE pm.product_id = %s
        """, (quantity, product_id))

        materials_needed = cursor.fetchall()
        conn.close()

        if not materials_needed:
            return [], "Для данного продукта не указаны нормы расхода материалов"

        missing_materials = []
        all_materials = []

        for m in materials_needed:
            material_info = {
                'id': m[0],
                'name': m[1],
                'unit': m[2],
                'available': float(m[3]),
                'required': float(m[5]),
                'per_unit': float(m[4])
            }
            all_materials.append(material_info)

            if m[3] < m[5]:
                material_info['shortage'] = float(m[5]) - float(m[3])
                missing_materials.append(material_info)

        if missing_materials:
            return missing_materials, None

        return all_materials, None

    except Exception as e:
        return None, str(e)


def reserve_materials(product_id, quantity):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT material_id, quantity_per_unit
            FROM product_materials
            WHERE product_id = %s
        """, (product_id,))

        materials = cursor.fetchall()

        for material_id, quantity_per_unit in materials:
            required = quantity_per_unit * quantity
            cursor.execute("""
                UPDATE materials 
                SET stock_balance = stock_balance - %s 
                WHERE id = %s AND stock_balance >= %s
                RETURNING stock_balance
            """, (required, material_id, required))

            result = cursor.fetchone()
            if not result:
                conn.rollback()
                conn.close()
                return False, f"Недостаточно материала ID {material_id} для резервирования"

        conn.commit()
        conn.close()
        return True, "Материалы успешно зарезервированы"

    except Exception as e:
        return False, str(e)


def order_materials(material_id, quantity):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE materials 
            SET stock_balance = stock_balance + %s 
            WHERE id = %s
            RETURNING name, stock_balance
        """, (quantity, material_id))

        result = cursor.fetchone()
        if not result:
            conn.rollback()
            conn.close()
            return False, "Материал не найден"

        material_name, new_balance = result

        conn.commit()
        conn.close()
        return True, f"Заказ материалов '{material_name}' на {quantity} ед. выполнен. Новый остаток: {new_balance}"

    except Exception as e:
        return False, str(e)


def main(page: ft.Page):
    page.title = "Система заказов машиностроительного завода"
    page.bgcolor = "#180C3B"
    page.padding = 20
    page.window_width = 950
    page.window_height = 800
    page.window_resizable = False

    snack_bar = ft.SnackBar(content=ft.Text(""))
    page.overlay.append(snack_bar)

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
        width=900,
        bgcolor="#2A2A2A",
        heading_row_color="#5736EB",
    )

    def show_snack_bar(message, color="green400"):
        snack_bar.content = ft.Text(message)
        snack_bar.bgcolor = color
        snack_bar.open = True
        page.update()

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
        except Exception as e:
            print(f"Error loading orders: {e}")

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
        except Exception as e:
            print(f"Error changing status: {e}")

    def delete_order(order_id):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM orders WHERE id = %s", (order_id,))
            conn.commit()
            conn.close()
            load_orders()
        except Exception as e:
            print(f"Error deleting order: {e}")

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

        def save_status(dlg):
            try:
                order_id = int(order_id_field.value)
                new_status = status_dropdown.value
                change_status(order_id, new_status)
                dlg.open = False
                page.update()
                show_snack_bar("Статус успешно изменен", "green400")
            except ValueError:
                show_snack_bar("Введите корректный ID", "red400")

        def close_dialog(dlg):
            dlg.open = False
            page.update()

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

        def delete_with_confirm(dlg):
            try:
                order_id = int(order_id_field.value)
                delete_order(order_id)
                dlg.open = False
                page.update()
                show_snack_bar(f"Заказ №{order_id} успешно удален", "green400")
            except ValueError:
                show_snack_bar("Введите корректный ID", "red400")

        def close_dialog(dlg):
            dlg.open = False
            page.update()

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

        page.show_dialog(dialog)
        page.update()

    def show_create_order_dialog(e):
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM products ORDER BY name")
            products = cursor.fetchall()
            conn.close()
        except Exception as ex:
            print(f"Error loading products: {ex}")
            products = []

        if not products:
            show_snack_bar("Нет доступных продуктов", "red400")
            return

        product_dropdown = ft.Dropdown(
            label="Продукт",
            options=[ft.dropdown.Option(str(p[0]), p[1]) for p in products],
            width=300,
            value=str(products[0][0]),
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

        materials_info = ft.Column([], scroll=ft.ScrollMode.ALWAYS, height=200)

        def update_materials_info(e):
            try:
                product_id = int(product_dropdown.value)
                quantity = int(quantity_field.value) if quantity_field.value and quantity_field.value.isdigit() else 1

                missing_materials, error = check_materials_availability(product_id, quantity)

                materials_info.controls.clear()

                if error:
                    materials_info.controls.append(
                        ft.Text(f"Ошибка: {error}", color="red400", size=12)
                    )
                elif missing_materials and len(missing_materials) > 0 and 'shortage' in missing_materials[0]:
                    materials_info.controls.append(
                        ft.Text("⚠️ Недостаточно материалов:", color="red400", size=14, weight=ft.FontWeight.BOLD)
                    )
                    for m in missing_materials:
                        materials_info.controls.append(
                            ft.Container(
                                content=ft.Column([
                                    ft.Text(f"{m['name']}:", color="white", size=12, weight=ft.FontWeight.BOLD),
                                    ft.Text(f"  Требуется: {m['required']:.2f} {m['unit']}", color="orange400",
                                            size=12),
                                    ft.Text(f"  В наличии: {m['available']:.2f} {m['unit']}", color="yellow400",
                                            size=12),
                                    ft.Text(f"  Не хватает: {m['shortage']:.2f} {m['unit']}", color="red400", size=12),
                                ]),
                                padding=5,
                                bgcolor="#3A3A3A",
                                border_radius=5,
                                margin=5
                            )
                        )
                else:
                    materials_info.controls.append(
                        ft.Text("✅ Материалов достаточно для производства", color="green400", size=14)
                    )
                    if missing_materials and len(missing_materials) > 0:
                        materials_info.controls.append(
                            ft.Text("Потребуется материалов:", color="white", size=14, weight=ft.FontWeight.BOLD)
                        )
                        for m in missing_materials:
                            materials_info.controls.append(
                                ft.Text(
                                    f"  {m['name']}: {m['required']:.2f} {m['unit']} (в наличии: {m['available']:.2f})",
                                    color="lightblue", size=12)
                            )

                page.update()
            except Exception as ex:
                print(f"Error updating materials info: {ex}")

        product_dropdown.on_change = update_materials_info
        quantity_field.on_change = update_materials_info

        def save_order(dlg):
            try:
                product_id = int(product_dropdown.value)
                quantity = int(quantity_field.value) if quantity_field.value and quantity_field.value.isdigit() else 1

                missing_materials, error = check_materials_availability(product_id, quantity)

                if error:
                    show_snack_bar(f"Ошибка: {error}", "red400")
                    return

                if missing_materials and len(missing_materials) > 0 and 'shortage' in missing_materials[0]:
                    show_snack_bar("Недостаточно материалов для создания заказа!", "red400")
                    return

                conn = get_connection()
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO orders (product_id, quantity, status, date_of_creation)
                    VALUES (%s, %s, 'Новый', CURRENT_DATE)
                    RETURNING id
                """, (product_id, quantity))

                order_id = cursor.fetchone()[0]

                success, message = reserve_materials(product_id, quantity)

                if success:
                    conn.commit()
                    dlg.open = False
                    page.update()
                    load_orders()

                    show_snack_bar(f"Заказ №{order_id} успешно создан! Материалы зарезервированы.", "green400")
                else:
                    conn.rollback()
                    show_snack_bar(f"Ошибка при резервировании материалов: {message}", "red400")

                conn.close()

            except Exception as ex:
                show_snack_bar(f"Ошибка при создании заказа: {str(ex)}", "red400")

        def close_dialog(dlg):
            dlg.open = False
            page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Заказ продукта", size=20, weight=ft.FontWeight.BOLD, color="white"),
            bgcolor="#2A2A2A",
            content=ft.Container(
                content=ft.Column([
                    product_dropdown,
                    quantity_field,
                    ft.Divider(height=10, color="white24"),
                    ft.Text("Расчет материалов:", size=14, weight=ft.FontWeight.BOLD, color="white"),
                    ft.Container(
                        content=materials_info,
                        height=200,
                        border=ft.Border.all(1, ft.Colors.GREY_700),
                        border_radius=5,
                        padding=10,
                    )
                ], height=400, scroll=ft.ScrollMode.AUTO),
                width=400,
            ),
            actions=[
                ft.TextButton("Отмена", on_click=lambda e: close_dialog(dialog), style=ft.ButtonStyle(color="white")),
                ft.FilledButton("Создать заказ", on_click=lambda e: save_order(dialog),
                                style=ft.ButtonStyle(bgcolor="#5736EB", color="white")),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.show_dialog(dialog)
        update_materials_info(None)
        page.update()

    def show_order_materials_dialog(e, pre_selected_materials=None):
        try:
            conn = get_connection()
            cursor = conn.cursor()

            if pre_selected_materials:
                material_ids = [m['id'] for m in pre_selected_materials]
                cursor.execute("""
                    SELECT id, name, unit, stock_balance 
                    FROM materials 
                    WHERE id = ANY(%s)
                    ORDER BY name
                """, (material_ids,))
            else:
                cursor.execute("""
                    SELECT id, name, unit, stock_balance 
                    FROM materials 
                    ORDER BY name
                """)

            materials = cursor.fetchall()
            conn.close()
        except Exception as ex:
            print(f"Error loading materials: {ex}")
            materials = []

        if not materials:
            show_snack_bar("Нет доступных материалов", "red400")
            return

        material_widgets = []
        material_fields = []

        def create_order_button(material_id, material_name, unit, quantity_field, dialog):
            def order_handler(ev):
                try:
                    quantity = float(quantity_field.value) if quantity_field.value and quantity_field.value.replace('.',
                                                                                                                    '').isdigit() else 0

                    if quantity <= 0:
                        show_snack_bar("Введите положительное количество", "orange400")
                        return

                    success, message = order_materials(material_id, quantity)

                    if success:
                        dialog.open = False
                        page.update()
                        show_snack_bar(f"✓ {material_name}: заказано {quantity} {unit}", "green400")
                    else:
                        show_snack_bar(message, "red400")

                except ValueError:
                    show_snack_bar("Введите корректное число", "red400")
                except Exception as ex:
                    show_snack_bar(f"Ошибка: {str(ex)}", "red400")

            return ft.FilledButton(
                "Заказать",
                style=ft.ButtonStyle(
                    bgcolor="#5736EB",
                    color="white",
                ),
                width=80,
                height=40,
                on_click=order_handler
            )

        def create_order_all_button(dialog):
            def order_all_handler(ev):
                try:
                    conn = get_connection()
                    cursor = conn.cursor()

                    success_count = 0
                    total_count = 0
                    ordered_materials = []

                    for mf in material_fields:
                        try:
                            quantity = float(mf['field'].value) if mf['field'].value and mf['field'].value.replace('.',
                                                                                                                   '').isdigit() else 0
                            if quantity > 0:
                                total_count += 1
                                cursor.execute("""
                                    UPDATE materials 
                                    SET stock_balance = stock_balance + %s 
                                    WHERE id = %s
                                    RETURNING name, stock_balance
                                """, (quantity, mf['id']))
                                result = cursor.fetchone()
                                if result:
                                    success_count += 1
                                    ordered_materials.append(f"{result[0]}: +{quantity} {mf['unit']}")
                        except ValueError:
                            pass

                    if total_count > 0:
                        conn.commit()
                        dialog.open = False
                        page.update()

                        if ordered_materials:
                            message = "Заказаны материалы:\n" + "\n".join(ordered_materials[:3])
                            if len(ordered_materials) > 3:
                                message += f"\nи еще {len(ordered_materials) - 3} материалов"
                        else:
                            message = f"Заказано {success_count} из {total_count} материалов"

                        show_snack_bar(message, "green400" if success_count == total_count else "orange400")
                    else:
                        show_snack_bar("Нет материалов для заказа", "orange400")

                    conn.close()

                except Exception as ex:
                    show_snack_bar(f"Ошибка: {str(ex)}", "red400")

            return ft.FilledButton(
                "Заказать все",
                on_click=order_all_handler,
                style=ft.ButtonStyle(bgcolor="#5736EB", color="white")
            )

        for i, m in enumerate(materials):
            material_id, material_name, unit, current_balance = m

            if current_balance < 100:
                balance_color = "red400"
            elif current_balance < 300:
                balance_color = "orange400"
            else:
                balance_color = "green400"

            quantity_field = ft.TextField(
                label="Количество",
                value="0",
                width=120,
                keyboard_type=ft.KeyboardType.NUMBER,
                color="white",
                label_style=ft.TextStyle(color="white"),
                text_size=12
            )

            if pre_selected_materials:
                for m_missing in pre_selected_materials:
                    if m_missing['id'] == material_id:
                        quantity_field.value = str(round(m_missing.get('shortage', 0), 2))
                        break

            material_fields.append({
                'id': material_id,
                'name': material_name,
                'field': quantity_field,
                'unit': unit
            })

        dialog = ft.AlertDialog(
            title=ft.Text("Заказ материалов на склад", size=20, weight=ft.FontWeight.BOLD, color="white"),
            bgcolor="#2A2A2A",
            content=None,
            actions=None,
            actions_alignment=ft.MainAxisAlignment.END,
        )

        order_buttons = []
        for i, m in enumerate(materials):
            material_id, material_name, unit, current_balance = m

            if current_balance < 100:
                balance_color = "red400"
            elif current_balance < 300:
                balance_color = "orange400"
            else:
                balance_color = "green400"

            quantity_field = None
            for mf in material_fields:
                if mf['id'] == material_id:
                    quantity_field = mf['field']
                    break

            if quantity_field:
                order_button = create_order_button(material_id, material_name, unit, quantity_field, dialog)

                order_buttons.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text(f"{material_name} ({unit})", color="white", width=150, size=14),
                            ft.Row([
                                ft.Text(f"Остаток: ", color="gray", size=12),
                                ft.Text(f"{current_balance:.2f}", color=balance_color, size=12,
                                        weight=ft.FontWeight.BOLD),
                            ], spacing=5),
                            quantity_field,
                            order_button
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=5,
                        bgcolor="#3A3A3A" if i % 2 == 0 else "#2A2A2A",
                        border_radius=5
                    )
                )

        def close_dialog(dlg):
            dlg.open = False
            page.update()

        dialog.content = ft.Container(
            content=ft.Column([
                ft.Text("Введите количество для заказа:", color="white", size=14),
                ft.Container(
                    content=ft.Column(order_buttons, scroll=ft.ScrollMode.ALWAYS, height=350),
                    border=ft.Border.all(1, ft.Colors.GREY_700),
                    border_radius=5,
                    padding=10,
                ),
                ft.Container(
                    content=ft.Row([
                        ft.Text("•", color="blue400", size=16),
                        ft.Text("Для заказа нажмите кнопку 'Заказать' рядом с материалом", color="gray", size=12),
                    ]),
                    padding=5,
                )
            ]),
            width=700,
            height=500,
        )

        dialog.actions = [
            ft.TextButton("Отмена", on_click=lambda e: close_dialog(dialog), style=ft.ButtonStyle(color="white")),
            create_order_all_button(dialog),
        ]

        page.show_dialog(dialog)
        page.update()

    def show_materials_dialog(e):
        try:
            conn = get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT m.id, m.name, m.unit, m.stock_balance,
                       (SELECT COUNT(*) FROM product_materials pm WHERE pm.material_id = m.id) as products_count
                FROM materials m
                ORDER BY m.name
            """)
            materials = cursor.fetchall()
            conn.close()
        except Exception as ex:
            print(f"Error loading materials: {ex}")
            materials = []

        if not materials:
            show_snack_bar("Нет материалов для отображения", "red400")
            return

        materials_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID", color="white")),
                ft.DataColumn(ft.Text("Материал", color="white")),
                ft.DataColumn(ft.Text("Ед. изм.", color="white")),
                ft.DataColumn(ft.Text("Остаток", color="white")),
                ft.DataColumn(ft.Text("Исп. в изделиях", color="white")),
            ],
            rows=[],
            bgcolor="#2A2A2A",
            heading_row_color="#5736EB",
        )

        for m in materials:
            balance = float(m[3])
            if balance < 100:
                balance_color = "red400"
            elif balance < 300:
                balance_color = "orange400"
            else:
                balance_color = "green400"

            materials_table.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(str(m[0]), color="white")),
                    ft.DataCell(ft.Text(m[1], color="white")),
                    ft.DataCell(ft.Text(m[2], color="white")),
                    ft.DataCell(ft.Text(f"{balance:.2f}", color=balance_color)),
                    ft.DataCell(ft.Text(str(m[4]), color="white")),
                ])
            )

        def close_and_order_materials(dlg):
            dlg.open = False
            page.update()
            show_order_materials_dialog(None)

        def close_dialog(dlg):
            dlg.open = False
            page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Склад материалов", size=20, weight=ft.FontWeight.BOLD, color="white"),
            bgcolor="#2A2A2A",
            content=ft.Container(
                content=ft.Column([
                    materials_table,
                    ft.Divider(height=10, color="white24"),
                    ft.Row([
                        ft.Container(width=20, height=20, bgcolor="red400"),
                        ft.Text("< 100 - критический остаток", color="white", size=12),
                        ft.Container(width=20, height=20, bgcolor="orange400"),
                        ft.Text("100-300 - недостаточно", color="white", size=12),
                        ft.Container(width=20, height=20, bgcolor="green400"),
                        ft.Text("> 300 - достаточно", color="white", size=12),
                    ], wrap=True),
                    ft.Row([
                        ft.FilledButton("Заказать материалы", on_click=lambda e: close_and_order_materials(dialog),
                                        style=ft.ButtonStyle(bgcolor="green", color="white")),
                    ], alignment=ft.MainAxisAlignment.CENTER)
                ]),
                width=700,
                height=450,
            ),
            actions=[
                ft.TextButton("Закрыть", on_click=lambda e: close_dialog(dialog), style=ft.ButtonStyle(color="white")),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        page.show_dialog(dialog)
        page.update()

    button_style = ft.ButtonStyle(
        bgcolor="#5736EB",
        color="white",
    )

    page.add(
        ft.Row([
            ft.FilledButton("Создать заказ", on_click=show_create_order_dialog, style=button_style),
            ft.FilledButton("Склад материалов", on_click=show_materials_dialog, style=button_style),
            ft.FilledButton("Заказать материалы", on_click=show_order_materials_dialog,
                            style=ft.ButtonStyle(bgcolor="green", color="white")),
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
