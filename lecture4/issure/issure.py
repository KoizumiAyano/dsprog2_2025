import math
import flet as ft


def main(page: ft.Page):
    page.title = "Calculator"
    page.window_width = 380
    page.window_height = 640
    page.padding = 16
    page.theme_mode = ft.ThemeMode.LIGHT

    display = ft.TextField(
        value="0",
        text_align=ft.TextAlign.RIGHT,
        read_only=True,
        height=70,
        text_size=28,
        border_radius=14,
    )

    mode = ft.SegmentedButton(
        selected={"basic"},
        segments=[
            ft.Segment(value="basic", label=ft.Text("基本")),
            ft.Segment(value="sci", label=ft.Text("科学")),
        ],
    )

    # 内部状態
    expr = "0"

    def set_display(v: str):
        nonlocal expr
        expr = v
        display.value = v
        display.update()

    def append(s: str):
        nonlocal expr
        if expr == "0" and s not in [".", "(", ")"]:
            expr = s
        else:
            expr += s
        set_display(expr)

    def clear(_=None):
        set_display("0")

    def backspace(_=None):
        nonlocal expr
        expr = expr[:-1] if len(expr) > 1 else "0"
        set_display(expr)

    def toggle_sign(_=None):
        nonlocal expr
        # 表示全体を数値として反転できるときだけ反転
        try:
            x = float(expr)
            set_display(str(-x))
        except:
            # 数式中なら末尾の数だけ反転するのは面倒なので、シンプルに先頭に - を付け外し
            if expr.startswith("-"):
                set_display(expr[1:])
            else:
                set_display("-" + expr)

    # 安全に評価（許可する文字を制限）
    def safe_eval(expression: str) -> float:
        allowed = set("0123456789+-*/(). ")
        # Sci用の記号は先に変換してから評価するのでここでは不要
        if any(c not in allowed for c in expression):
            raise ValueError("invalid characters")

        # math の関数/定数だけ許可
        env = {
            "__builtins__": None,
            "pi": math.pi,
            "e": math.e,
        }
        return eval(expression, env, {})

    def equals(_=None):
        nonlocal expr
        try:
            # x^y を ** に変換
            s = expr.replace("^", "**")
            v = safe_eval(s)
            # きれい表示
            if abs(v - int(v)) < 1e-12:
                set_display(str(int(v)))
            else:
                set_display(str(v))
        except Exception:
            set_display("Error")

    # 科学関数：表示をその場で数値に変換（ワンタップで計算）
    def apply_unary(fn):
        nonlocal expr
        try:
            s = expr.replace("^", "**")
            x = safe_eval(s)
            v = fn(x)
            if abs(v - int(v)) < 1e-12:
                set_display(str(int(v)))
            else:
                set_display(str(v))
        except Exception:
            set_display("Error")

    def insert_pi(_=None):
        append(str(math.pi))

    def sqrt(_=None):
        apply_unary(lambda x: math.sqrt(x))

    def sin(_=None):
        apply_unary(lambda x: math.sin(x))

    def cos(_=None):
        apply_unary(lambda x: math.cos(x))

    def tan(_=None):
        apply_unary(lambda x: math.tan(x))

    def log10(_=None):
        apply_unary(lambda x: math.log10(x))

    def ln(_=None):
        apply_unary(lambda x: math.log(x))

    # ボタン生成ヘルパ
    def btn(label, on_click, expand=1, bgcolor=None):
        return ft.ElevatedButton(
            text=label,
            on_click=on_click,
            expand=expand,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=14),
                bgcolor=bgcolor,
                padding=14,
            ),
        )

    # 科学パッド（最低5つ以上：sin cos tan log ln √ π ^）
    sci_pad = ft.Column(
        visible=False,
        spacing=10,
        controls=[
            ft.Row([btn("sin", sin), btn("cos", cos), btn("tan", tan), btn("π", insert_pi)]),
            ft.Row([btn("log", log10), btn("ln", ln), btn("√", sqrt), btn("^", lambda e: append("^"))]),
        ],
    )

    # 基本パッド
    basic_pad = ft.Column(
        spacing=10,
        controls=[
            ft.Row([btn("C", clear, bgcolor=ft.Colors.RED_50), btn("⌫", backspace), btn("±", toggle_sign), btn("÷", lambda e: append("/"))]),
            ft.Row([btn("7", lambda e: append("7")), btn("8", lambda e: append("8")), btn("9", lambda e: append("9")), btn("×", lambda e: append("*"))]),
            ft.Row([btn("4", lambda e: append("4")), btn("5", lambda e: append("5")), btn("6", lambda e: append("6")), btn("−", lambda e: append("-"))]),
            ft.Row([btn("1", lambda e: append("1")), btn("2", lambda e: append("2")), btn("3", lambda e: append("3")), btn("+", lambda e: append("+"))]),
            ft.Row([btn("0", lambda e: append("0"), expand=2), btn(".", lambda e: append(".")), btn("=", equals, bgcolor=ft.Colors.BLUE_50)]),
        ],
    )

    def on_mode_change(e):
        sci_pad.visible = "sci" in mode.selected
        sci_pad.update()

    mode.on_change = on_mode_change

    page.add(
        ft.Column(
            spacing=12,
            controls=[
                ft.Row([ft.Text("電卓", size=22, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                mode,
                display,
                sci_pad,
                basic_pad,
            ],
        )
    )


ft.app(target=main)
