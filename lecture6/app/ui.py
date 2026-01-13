import flet as ft

from .db import (
    init_db,
    upsert_forecast,
    load_latest_forecasts,
    list_available_target_dates,
    load_forecast_for_date_latest,
    get_latest_published_at,
)
from .jma_api import fetch_areas_json, fetch_forecast_json
from .parser import parse_jma_forecast


def run_app(page: ft.Page):
    conn = init_db()

    page.title = "天気予報アプリ（DB版）"
    page.window_width = 1200
    page.window_height = 700
    page.bgcolor = "#b0bec5"

    page.appbar = ft.AppBar(
        leading=ft.Icon(ft.Icons.WB_SUNNY, color="white"),
        title=ft.Text("天気予報アプリ（DB版）", color="white"),
        center_title=True,
        bgcolor="#3f2aa5",
        actions=[ft.IconButton(icon=ft.Icons.MORE_VERT)],
    )

    status_text = ft.Text("地域リストを取得中...", size=11, color="#eeeeee")

    area_dropdown = ft.Dropdown(label="地域を選択", width=260)

    area_list_view = ft.ListView(expand=True, spacing=2, padding=0, auto_scroll=False)

    left_panel = ft.Container(
        bgcolor="#78909c",
        width=280,
        padding=15,
        content=ft.Column(
            [
                status_text,
                ft.Divider(height=10, color="transparent"),
                area_dropdown,
                ft.Divider(),
                ft.Container(content=area_list_view, expand=True),
            ],
            expand=True,
        ),
    )

    area_title = ft.Text("", size=22, weight=ft.FontWeight.BOLD)
    area_subtitle = ft.Text("", size=12, color="#455a64")
    error_text = ft.Text("", color="red")

    date_dropdown = ft.Dropdown(label="日付で表示（保存済み）", width=240, visible=False)

    forecast_column = ft.Column(spacing=20, expand=True, scroll="auto")

    right_panel = ft.Container(
        bgcolor="#b0bec5",
        expand=True,
        padding=20,
        content=ft.Column(
            [
                ft.Row(
                    [area_title, ft.Container(expand=True), date_dropdown],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                area_subtitle,
                ft.Divider(),
                forecast_column,
                error_text,
            ],
            expand=True,
        ),
    )

    page.add(ft.Row([left_panel, right_panel], expand=True))

    areas_data: list[tuple[str, str]] = []
    current_area_code: str | None = None
    current_area_name: str | None = None

    def weather_icon(weather: str | None):
        w = weather or ""
        if "雪" in w:
            return ft.Icons.AC_UNIT
        if "雨" in w:
            return ft.Icons.UMBRELLA
        if "曇" in w or "くもり" in w:
            if "晴" in w:
                return ft.Icons.WB_CLOUDY
            return ft.Icons.CLOUD
        if "晴" in w:
            return ft.Icons.WB_SUNNY
        return ft.Icons.WB_CLOUDY

    def fmt_temp(x):
        if x is None or x == "":
            return ""
        try:
            fx = float(x)
            return str(int(fx)) if fx.is_integer() else str(fx)
        except Exception:
            return str(x)

    def render_cards(rows, subtitle: str):
        forecast_column.controls.clear()
        area_subtitle.value = subtitle

        if not rows:
            forecast_column.controls.append(
                ft.Text("保存済みデータがありません。まず地域を選択して取得してください。")
            )
            page.update()
            return

        row_cards = []
        for i, r in enumerate(rows):
            date_iso = r["target_date"]
            weather_str = r["weather"] or ""
            tmin_s = fmt_temp(r["temp_min"])
            tmax_s = fmt_temp(r["temp_max"])

            card = ft.Card(
                elevation=3,
                color="white",
                content=ft.Container(
                    padding=15,
                    width=210,
                    content=ft.Column(
                        [
                            ft.Text(date_iso, weight=ft.FontWeight.BOLD, size=16),
                            ft.Row(
                                [
                                    ft.Icon(weather_icon(weather_str), size=40, color="#ff9800"),
                                    ft.Icon(ft.Icons.CLOUD, size=26, color="#90a4ae"),
                                ],
                                alignment=ft.MainAxisAlignment.START,
                            ),
                            ft.Text(weather_str, size=14),
                            ft.Divider(),
                            ft.Row(
                                [
                                    ft.Text(f"{tmin_s}°C" if tmin_s else "°C", color="#1976d2", size=14),
                                    ft.Text(" / "),
                                    ft.Text(f"{tmax_s}°C" if tmax_s else "°C", color="#e53935", size=14),
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                            ),
                        ],
                        spacing=5,
                    ),
                ),
            )

            row_cards.append(card)
            if len(row_cards) == 3 or i == len(rows) - 1:
                forecast_column.controls.append(ft.Row(row_cards, spacing=20))
                row_cards = []

        page.update()

    def refresh_date_dropdown(area_code: str):
        dates = list_available_target_dates(conn, area_code)
        date_dropdown.options = [ft.dropdown.Option(d) for d in dates]
        date_dropdown.visible = len(dates) > 0
        if dates:
            date_dropdown.value = dates[-1]
        page.update()

    def on_date_changed(e):
        nonlocal current_area_code
        if not current_area_code:
            return
        d = e.control.value
        if not d:
            return

        r = load_forecast_for_date_latest(conn, current_area_code, d)
        if not r:
            render_cards([], "該当日付のデータがありません。")
            return

        subtitle = f"{r['detail_area_name'] or ''} / 発表: {r['publishing_office'] or ''} {r['published_at'] or ''} / 表示日: {d}"
        render_cards([r], subtitle)

    date_dropdown.on_change = on_date_changed

    def load_areas():
        nonlocal areas_data
        try:
            data = fetch_areas_json()
            offices = data.get("offices", {})
            areas_data = sorted(
                [(code, info.get("name", "")) for code, info in offices.items()],
                key=lambda x: int(x[0]),
            )

            area_dropdown.options = [ft.dropdown.Option(f"{name} ({code})") for code, name in areas_data]

            area_list_view.controls.clear()
            for code, name in areas_data:
                tile = ft.ListTile(
                    title=ft.Text(name, color="white"),
                    subtitle=ft.Text(code, color="#cfd8dc"),
                    on_click=lambda e, c=code: select_area(c),
                )
                area_list_view.controls.append(tile)

            status_text.value = "地域を選択してください。"
        except Exception as ex:
            status_text.value = "地域リストの取得に失敗しました。"
            error_text.value = f"[ERROR] {ex}"
        finally:
            page.update()

    def select_area(value: str):
        nonlocal current_area_code, current_area_name
        if not value:
            return

        if "(" in value and ")" in value:
            code = value.split("(")[-1].rstrip(")")
        else:
            code = value

        name = code
        for c, n in areas_data:
            if c == code:
                name = n
                break

        current_area_code = code
        current_area_name = name
        fetch_store_show(code, name)

    def on_dropdown_changed(e):
        select_area(e.control.value)

    area_dropdown.on_change = on_dropdown_changed

    def fetch_store_show(area_code: str, area_name: str):
        area_title.value = f"{area_name} の天気予報"
        area_subtitle.value = ""
        error_text.value = ""
        forecast_column.controls.clear()
        date_dropdown.visible = False
        page.update()

        status_text.value = f"{area_name}（{area_code}）の天気を取得中..."
        page.update()

        try:
            data = fetch_forecast_json(area_code)
            rows, meta = parse_jma_forecast(area_code, area_name, data)
            if not rows:
                raise ValueError("予報データのパースに失敗しました。")

            for row in rows:
                upsert_forecast(conn, row)

            latest_rows = load_latest_forecasts(conn, area_code)
            subtitle = f"{meta.get('detail_area_name','')} / 発表: {meta.get('publishing_office','')} {meta.get('published_at','')}"
            render_cards(latest_rows, subtitle)

            refresh_date_dropdown(area_code)
            status_text.value = "天気の取得が完了しました（DBに保存済み）。"

        except Exception as ex:
            status_text.value = "天気予報の取得に失敗しました。"
            error_text.value = f"[ERROR] {ex}"

            # 通信失敗でもDBがあれば表示
            latest_rows = load_latest_forecasts(conn, area_code)
            if latest_rows:
                subtitle = f"（通信失敗のため保存済みを表示）/ 最新発表: {get_latest_published_at(conn, area_code) or ''}"
                render_cards(latest_rows, subtitle)
                refresh_date_dropdown(area_code)

        page.update()

    load_areas()
