"""Original Tam canvas design; explicit CLI only, no import-time writes."""
from pathlib import Path
import argparse

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output', default=str(__import__('pathlib').Path(__file__).resolve().parent/'design_assets'/'canvas_background_page1.png'))
    args=parser.parse_args()

    from pathlib import Path
    from PIL import Image, ImageDraw, ImageFont

    # Kích thước chuẩn HD của Power BI: 1920 x 1080
    WIDTH, HEIGHT = 1920, 1080
    bg = Image.new("RGBA", (WIDTH, HEIGHT), "#EFF6FF")
    draw = ImageDraw.Draw(bg)

    # ==========================================
    # 1. SIDEBAR BÊN TRÁI (NAVBAR)
    # ==========================================
    SIDEBAR_WIDTH = 250
    draw.rectangle([0, 0, SIDEBAR_WIDTH, HEIGHT], fill="#0B1F46")

    # Thử nạp font hệ thống Segoe UI hoặc Arial
    def get_font(size, bold=False):
        font_names = ["segoeui.ttf", "segoeuib.ttf", "arial.ttf", "arialbd.ttf"]
        if bold:
            font_names = ["segoeuib.ttf", "arialbd.ttf", "segoeui.ttf"]
        for name in font_names:
            try:
                return ImageFont.truetype(f"C:/Windows/Fonts/{name}", size)
            except Exception:
                continue
        return ImageFont.load_default()

    font_logo = get_font(24, bold=True)
    font_menu_active = get_font(15, bold=True)
    font_menu = get_font(15, bold=False)
    font_header = get_font(26, bold=True)
    font_sub = get_font(13, bold=False)
    font_card_title = get_font(14, bold=True)

    # Logo Olist Analytics
    draw.text((35, 35), "Olist", fill="#FFFFFF", font=font_logo)
    draw.text((35, 65), "Analytics", fill="#93C5FD", font=font_sub)

    # Menu Items
    menus = [
        ("01. Tổng quan\n    kinh doanh", True),
        ("02. Phân tích\n    khách hàng", False),
        ("03. Sản phẩm\n    và thanh toán", False),
        ("04. Giao hàng\n    và đánh giá", False),
        ("05. Phân khúc và\n    nguy cơ rời bỏ", False),
    ]

    y_pos = 130
    for text, is_active in menus:
        if is_active:
            # Active Pill màu xanh #2563EB
            draw.rounded_rectangle([15, y_pos, SIDEBAR_WIDTH - 15, y_pos + 60], radius=8, fill="#2563EB")
            draw.text((30, y_pos + 12), text, fill="#FFFFFF", font=font_menu_active)
        else:
            draw.text((30, y_pos + 12), text, fill="#94A3B8", font=font_menu)
        y_pos += 80

    # Footer Sidebar
    draw.text((25, 960), "• Dữ liệu: Olist E-commerce", fill="#64748B", font=font_sub)
    draw.text((25, 985), "• Thời gian: 2017-01 – 2018-08", fill="#64748B", font=font_sub)
    draw.text((25, 1010), "• Cập nhật: 22/10/2026", fill="#64748B", font=font_sub)

    # ==========================================
    # 2. HEADER KHU VỰC NỘI DUNG (MAIN CONTENT HEADER)
    # ==========================================
    CONTENT_LEFT = SIDEBAR_WIDTH + 30
    CONTENT_RIGHT = WIDTH - 30

    # Icon tròn xanh
    draw.ellipse([CONTENT_LEFT, 28, CONTENT_LEFT + 46, 74], fill="#2563EB")
    draw.rectangle([CONTENT_LEFT + 12, 45, CONTENT_LEFT + 18, 62], fill="#FFFFFF")
    draw.rectangle([CONTENT_LEFT + 20, 38, CONTENT_LEFT + 26, 62], fill="#FFFFFF")
    draw.rectangle([CONTENT_LEFT + 28, 48, CONTENT_LEFT + 34, 62], fill="#FFFFFF")

    # Tiêu đề trang
    draw.text((CONTENT_LEFT + 60, 26), "01. TỔNG QUAN KINH DOANH", fill="#0B1F46", font=font_header)
    draw.text((CONTENT_LEFT + 60, 62), "Kinh doanh đang tăng hay chững? Nhìn tổng quan doanh thu, số đơn, khách hàng và hiệu quả hoạt động của Olist.", fill="#64748B", font=font_sub)

    # Khung cho 2 Slicers góc trên bên phải
    SLICER_Y = 28
    SLICER_H = 50
    # Slicer 1: Khoảng thời gian
    draw.rounded_rectangle([1320, SLICER_Y, 1680, SLICER_Y + SLICER_H], radius=8, fill="#FFFFFF", outline="#CBD5E1", width=1)
    draw.text((1335, SLICER_Y + 6), "Khoảng thời gian", fill="#64748B", font=get_font(11, bold=True))
    # Slicer 2: Bang
    draw.rounded_rectangle([1700, SLICER_Y, 1890, SLICER_Y + SLICER_H], radius=8, fill="#FFFFFF", outline="#CBD5E1", width=1)
    draw.text((1715, SLICER_Y + 6), "Bang", fill="#64748B", font=get_font(11, bold=True))

    # ==========================================
    # 3. HÀNG 4 THẺ KPI CARDS
    # ==========================================
    CARD_Y = 100
    CARD_H = 145
    TOTAL_CARD_WIDTH = CONTENT_RIGHT - CONTENT_LEFT
    GAP = 20
    CARD_W = (TOTAL_CARD_WIDTH - 3 * GAP) / 4

    kpi_configs = [
        ("Doanh thu sản phẩm", "#10B981", "#E6F4EA"),  # Green icon
        ("Số đơn hàng", "#3B82F6", "#EFF6FF"),          # Blue icon
        ("Giá trị đơn trung bình (AOV)", "#8B5CF6", "#F5F3FF"), # Purple icon
        ("Tỷ lệ đơn bị hủy", "#EF4444", "#FEF2F2")      # Red icon
    ]

    for i, (title, icon_color, icon_bg) in enumerate(kpi_configs):
        x0 = CONTENT_LEFT + i * (CARD_W + GAP)
        x1 = x0 + CARD_W
        # Khung thẻ trắng bo góc viền nhẹ
        draw.rounded_rectangle([x0, CARD_Y, x1, CARD_Y + CARD_H], radius=10, fill="#FFFFFF", outline="#E2E8F0", width=1)
        # Icon tròn nhỏ
        draw.ellipse([x0 + 15, CARD_Y + 15, x0 + 55, CARD_Y + 55], fill=icon_bg)
        draw.ellipse([x0 + 23, CARD_Y + 23, x0 + 47, CARD_Y + 47], fill=icon_color)
        # Tiêu đề thẻ
        draw.text((x0 + 65, CARD_Y + 16), title, fill="#64748B", font=font_sub)

    # ==========================================
    # 4. HÀNG GIỮA: 2 CONTAINER (HERO CHART & TOP 10 BANG)
    # ==========================================
    MID_Y = 265
    MID_H = 390
    HERO_W = (TOTAL_CARD_WIDTH - GAP) * 0.58
    SUB_W = TOTAL_CARD_WIDTH - HERO_W - GAP

    # Khung Hero Chart
    hero_x0 = CONTENT_LEFT
    hero_x1 = hero_x0 + HERO_W
    draw.rounded_rectangle([hero_x0, MID_Y, hero_x1, MID_Y + MID_H], radius=10, fill="#FFFFFF", outline="#E2E8F0", width=1)
    draw.text((hero_x0 + 20, MID_Y + 15), "Doanh thu sản phẩm theo tháng và tăng trưởng MoM", fill="#0B1F46", font=font_card_title)

    # Khung Top 10 Bang
    sub_x0 = hero_x1 + GAP
    sub_x1 = CONTENT_RIGHT
    draw.rounded_rectangle([sub_x0, MID_Y, sub_x1, MID_Y + MID_H], radius=10, fill="#FFFFFF", outline="#E2E8F0", width=1)
    draw.text((sub_x0 + 20, MID_Y + 15), "Top 10 bang theo doanh thu", fill="#0B1F46", font=font_card_title)

    # ==========================================
    # 5. HÀNG DƯỚI: 3 CONTAINER
    # ==========================================
    BOT_Y = 675
    BOT_H = 375
    BOT_W = (TOTAL_CARD_WIDTH - 2 * GAP) / 3

    bot_titles = [
        "Top 5 ngành hàng theo doanh thu",
        "Tỷ lệ đơn hủy và tỷ lệ giao hàng trễ theo tháng",
        "Trạng thái đơn hàng"
    ]

    for i, title in enumerate(bot_titles):
        bx0 = CONTENT_LEFT + i * (BOT_W + GAP)
        bx1 = bx0 + BOT_W
        draw.rounded_rectangle([bx0, BOT_Y, bx1, BOT_Y + BOT_H], radius=10, fill="#FFFFFF", outline="#E2E8F0", width=1)
        draw.text((bx0 + 20, BOT_Y + 15), title, fill="#0B1F46", font=font_card_title)

    # Lưu ảnh nền
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    bg.save(output_path, "PNG")
    print(f"Đã tạo thành công ảnh nền: {output_path}")

if __name__=='__main__': main()
