import flet as ft
import requests

AREA_URL = "https://www.jma.go.jp/bosai/common/const/area.json"
FORECAST_BASE_URL = "https://www.jma.go.jp/bosai/forecast/data/forecast"


def main(page: ft.Page):
    page.title = "天気予報アプリ"
    page.window_width = 1200
    page.window_height = 700
    page.bgcolor = "#b0bec5"

    # -------- AppBar --------
    page.appbar = ft.AppBar(
        leading=ft.Icon(ft.Icons.WB_SUNNY, color="white"),
        title=ft.Text("天気予報アプリ", color="white"),
        center_title=True,
        bgcolor="#3f2aa5",
        actions=[
            ft.IconButton(icon=ft.Icons.MORE_VERT)
        ],
    )

    # -------- 左ペイン（地域選択） --------
    status_text = ft.Text("地域リストを取得中...", size=11, color="#eeeeee")

    area_dropdown = ft.Dropdown(
        label="地域を選択",
        width=260,
    )

    area_list_view = ft.ListView(
        expand=True,
        spacing=2,
        padding=0,
        auto_scroll=False,
    )

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

    # -------- 右ペイン（天気カード） --------
    area_title = ft.Text("", size=22, weight=ft.FontWeight.BOLD)
    area_subtitle = ft.Text("", size=12, color="#455a64")
    error_text = ft.Text("", color="red")

    # Wrap が無いバージョン用 → Column + Row でグリッド風にする
    forecast_column = ft.Column(spacing=20, expand=True, scroll="auto")

    right_panel = ft.Container(
        bgcolor="#b0bec5",
        expand=True,
        padding=20,
        content=ft.Column(
            [area_title, area_subtitle, ft.Divider(), forecast_column, error_text],
            expand=True,
        ),
    )

    layout = ft.Row([left_panel, right_panel], expand=True)
    page.add(layout)

    # 取得した (code, name) を保存
    areas_data = []

    # -------- 天気→アイコン変換 --------
    def weather_icon(weather: str):
        if "雪" in weather:
            return ft.Icons.AC_UNIT
        if "雨" in weather:
            return ft.Icons.UMBRELLA
        if "曇" in weather or "くもり" in weather:
            if "晴" in weather:
                return ft.Icons.WB_CLOUDY
            return ft.Icons.CLOUD
        if "晴" in weather:
            return ft.Icons.WB_SUNNY
        return ft.Icons.WB_CLOUDY

    # -------- 地域リスト取得 --------
    def load_areas():
        nonlocal areas_data
        try:
            res = requests.get(AREA_URL, timeout=10)
            res.raise_for_status()
            data = res.json()

            offices = data.get("offices", {})
            areas_data = sorted(
                [(code, info.get("name", "")) for code, info in offices.items()],
                key=lambda x: int(x[0]),
            )

            # Dropdown
            area_dropdown.options = [
                ft.dropdown.Option(f"{name} ({code})") for code, name in areas_data
            ]

            # 左側リスト
            for code, name in areas_data:
                tile = ft.ListTile(
                    title=ft.Text(name, color="white"),
                    subtitle=ft.Text(code, color="#cfd8dc"),
                    on_click=lambda e, c=code: select_area(c),
                )
                area_list_view.controls.append(tile)

            status_text.value = "地域を選択してください。"
        except Exception as e:
            status_text.value = "地域リストの取得に失敗しました。"
            error_text.value = f"[ERROR] {e}"
        finally:
            page.update()

    # -------- 地域選択 --------
    def select_area(value: str):
        if not value:
            return

        # Dropdown の場合 "東京都 (130000)" → "130000"
        if "(" in value and ")" in value:
            code = value.split("(")[-1].rstrip(")")
        else:
            code = value

        name = code
        for c, n in areas_data:
            if c == code:
                name = n
                break

        fetch_forecast(code, name)

    def dropdown_changed(e):
        select_area(e.control.value)

    area_dropdown.on_change = dropdown_changed

    # -------- 天気取得＆カード作成 --------
    def fetch_forecast(area_code: str, area_name: str):
        area_title.value = f"{area_name} の天気予報"
        area_subtitle.value = ""
        error_text.value = ""
        forecast_column.controls.clear()
        status_text.value = f"{area_name}（{area_code}）の天気を取得中..."
        page.update()

        url = f"{FORECAST_BASE_URL}/{area_code}.json"

        try:
            res = requests.get(url, timeout=10)
            res.raise_for_status()
            data = res.json()

            first = data[0]
            time_series_list = first["timeSeries"]
            weather_ts = time_series_list[0]

            time_defines = weather_ts["timeDefines"]
            areas = weather_ts["areas"]
            target_area = areas[0]
            weathers = target_area["weathers"]

            temps_min = []
            temps_max = []
            for ts in time_series_list:
                area0 = ts["areas"][0]
                if "tempsMin" in area0 and not temps_min:
                    temps_min = area0["tempsMin"]
                if "tempsMax" in area0 and not temps_max:
                    temps_max = area0["tempsMax"]

            office = first.get("publishingOffice", "")
            report_time = first.get("reportDatetime", "")
            detail_name = target_area["area"]["name"]

            area_subtitle.value = f"{detail_name} / 発表: {office} {report_time}"

            days = min(len(time_defines), len(weathers))

            # 3列×複数行くらいのグリッド風に並べる
            row_cards = []
            for i in range(days):
                date_iso = time_defines[i][:10]
                weather_str = weathers[i]
                tmin = temps_min[i] if i < len(temps_min) and temps_min[i] != "" else ""
                tmax = temps_max[i] if i < len(temps_max) and temps_max[i] != "" else ""

                card = ft.Card(
                    elevation=3,
                    color="white",
                    content=ft.Container(
                        padding=15,
                        width=210,
                        content=ft.Column(
                            [
                                ft.Text(
                                    date_iso,
                                    weight=ft.FontWeight.BOLD,
                                    size=16,
                                ),
                                ft.Row(
                                    [
                                        ft.Icon(
                                            weather_icon(weather_str),
                                            size=40,
                                            color="#ff9800",
                                        ),
                                        ft.Icon(
                                            ft.Icons.CLOUD,
                                            size=26,
                                            color="#90a4ae",
                                        ),
                                    ],
                                    alignment=ft.MainAxisAlignment.START,
                                ),
                                ft.Text(weather_str, size=14),
                                ft.Divider(),
                                ft.Row(
                                    [
                                        ft.Text(
                                            f"{tmin}°C" if tmin else "°C",
                                            color="#1976d2",
                                            size=14,
                                        ),
                                        ft.Text(" / "),
                                        ft.Text(
                                            f"{tmax}°C" if tmax else "°C",
                                            color="#e53935",
                                            size=14),
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                ),
                            ],
                            spacing=5,
                        ),
                    ),
                )

                row_cards.append(card)

                # 3枚ごとに Row にして追加
                if len(row_cards) == 3 or i == days - 1:
                    forecast_column.controls.append(
                        ft.Row(row_cards, spacing=20)
                    )
                    row_cards = []

            status_text.value = "天気の取得が完了しました。"

        except Exception as e:
            status_text.value = "天気予報の取得に失敗しました。"
            error_text.value = f"[ERROR] {e}"

        page.update()

    # 起動時に地域リストを読み込み
    load_areas()


if __name__ == "__main__":
    ft.app(target=main)
