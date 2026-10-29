"""Original Tam canvas design; explicit CLI only, no import-time writes."""
from pathlib import Path
import argparse

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output', default=str(__import__('pathlib').Path(__file__).resolve().parent/'design_assets'/'canvas_background_page5.png'))
    args=parser.parse_args()
    import sys
    if hasattr(sys.stdout, 'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    from pathlib import Path
    from PIL import Image, ImageDraw, ImageFont

    WIDTH, HEIGHT = 1920, 1080
    bg = Image.new("RGBA", (WIDTH, HEIGHT), "#EFF6FF")
    draw = ImageDraw.Draw(bg)

    # 1. SIDEBAR BÊN TRÁI (NAVBAR)
    SIDEBAR_WIDTH = 250
    draw.rectangle([0, 0, SIDEBAR_WIDTH, HEIGHT], fill="#0B1F46")

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
    font_header = get_font(24, bold=True)
    font_sub = get_font(12, bold=False)
    font_card_title = get_font(13, bold=True)
    font_card_sub = get_font(11, bold=False)

    # Logo
    draw.text((35, 30), "Olist", fill="#FFFFFF", font=font_logo)
    draw.text((35, 60), "Analytics", fill="#93C5FD", font=font_sub)

    # Menu items (Page 5 active)
    menus = [
        ("01. Tổng quan\n    kinh doanh", False),
        ("02. Phân tích\n    khách hàng", False),
        ("03. Sản phẩm\n    và thanh toán", False),
        ("04. Giao hàng\n    và đánh giá", False),
        ("05. Phân khúc và\n    nguy cơ rời bỏ", True),
    ]

    y_pos = 120
    for text, is_active in menus:
        if is_active:
            draw.rounded_rectangle([15, y_pos, SIDEBAR_WIDTH - 15, y_pos + 56], radius=8, fill="#2563EB")
            draw.text((30, y_pos + 10), text, fill="#FFFFFF", font=font_menu_active)
        else:
            draw.text((30, y_pos + 10), text, fill="#94A3B8", font=font_menu)
        y_pos += 76

    # Footer Sidebar
    draw.text((25, 960), "• Dữ liệu: Olist E-commerce", fill="#64748B", font=font_sub)
    draw.text((25, 985), "• Giai đoạn: 2016-09 – 2018-09", fill="#64748B", font=font_sub)
    draw.text((25, 1010), "• Phiên bản: Temporal v4", fill="#64748B", font=font_sub)

    # 2. MAIN HEADER
    CONTENT_LEFT = SIDEBAR_WIDTH + 30 # 280
    CONTENT_RIGHT = WIDTH - 30        # 1890

    draw.ellipse([CONTENT_LEFT, 24, CONTENT_LEFT + 44, 68], fill="#2563EB")
    draw.rectangle([CONTENT_LEFT + 11, 40, CONTENT_LEFT + 17, 56], fill="#FFFFFF")
    draw.rectangle([CONTENT_LEFT + 19, 34, CONTENT_LEFT + 25, 56], fill="#FFFFFF")
    draw.rectangle([CONTENT_LEFT + 27, 43, CONTENT_LEFT + 33, 56], fill="#FFFFFF")

    draw.text((CONTENT_LEFT + 56, 22), "05. PHÂN KHÚC KHÁCH HÀNG & THỬ NGHIỆM MACHINE LEARNING", fill="#0B1F46", font=font_header)
    draw.text((CONTENT_LEFT + 56, 54), "Đối chiếu phân khúc RFM truyền thống và thử nghiệm mô hình ML dự báo nguy cơ không mua lại (Temporal v4).", fill="#64748B", font=font_sub)

    # Slicer Box góc trên bên phải
    SLICER_X0 = 1530
    SLICER_X1 = CONTENT_RIGHT
    SLICER_Y0 = 20
    SLICER_Y1 = 70
    draw.rounded_rectangle([SLICER_X0, SLICER_Y0, SLICER_X1, SLICER_Y1], radius=8, fill="#FFFFFF", outline="#CBD5E1", width=1)
    draw.text((SLICER_X0 + 15, SLICER_Y0 + 6), "Khoảng thời gian & Bộ lọc", fill="#64748B", font=get_font(11, bold=True))

    # 3. HÀNG 1: 4 THẺ KPI CARDS (y=86 đến y=180, h=94)
    CARD_Y = 86
    CARD_H = 94
    GAP = 16
    TOTAL_W = CONTENT_RIGHT - CONTENT_LEFT
    CARD_W = (TOTAL_W - 3 * GAP) / 4

    kpi_cards = [
        ("Tập khách hàng RFM", "Phạm vi: Đơn delivered", "#2563EB", "#EFF6FF"),
        ("Khách hàng mua lại (Loyal)", "Tập khách mua >= 2 lần", "#0D9488", "#F0FDF4"),
        ("Khách chấm điểm ML Churn", "Tập thử nghiệm (ml_scored=True)", "#6366F1", "#EEF2FF"),
        ("Độ chính xác Test (Accuracy)", "Lệch lớp mạnh (Threshold 0.5)", "#F59E0B", "#FFFBEB")
    ]

    for i, (title, sub, icon_c, bg_c) in enumerate(kpi_cards):
        x0 = CONTENT_LEFT + i * (CARD_W + GAP)
        x1 = x0 + CARD_W
        draw.rounded_rectangle([x0, CARD_Y, x1, CARD_Y + CARD_H], radius=8, fill="#FFFFFF", outline="#E2E8F0", width=1)
        # Icon tròn
        draw.ellipse([x0 + 12, CARD_Y + 12, x0 + 44, CARD_Y + 44], fill=bg_c)
        draw.ellipse([x0 + 18, CARD_Y + 18, x0 + 38, CARD_Y + 38], fill=icon_c)
        # Title & Sub
        draw.text((x0 + 52, CARD_Y + 12), title, fill="#64748B", font=get_font(12, bold=True))
        draw.text((x0 + 52, CARD_Y + 30), sub, fill="#94A3B8", font=get_font(10, bold=False))

    # 4. HÀNG 2: 4 CONTAINER BIỂU ĐỒ PHÂN TÍCH (y=194 đến y=580, h=386)
    ROW2_Y = 194
    ROW2_H = 386

    w_col1 = 410
    w_col2 = 360
    w_col3 = 390
    w_col4 = TOTAL_W - (w_col1 + w_col2 + w_col3 + 3 * GAP) # ~414px

    cols_r2 = [
        (CONTENT_LEFT, w_col1, "Phân khúc RFM: Khách hàng vs Doanh thu", "6 nhóm phân khúc RFM luật truyền thống"),
        (CONTENT_LEFT + w_col1 + GAP, w_col2, "Cảnh báo RFM theo recency", "Quy tắc Recency 180/365 ngày (Không phải ML)"),
        (CONTENT_LEFT + w_col1 + w_col2 + 2 * GAP, w_col3, "Phân bố nguy cơ ML – thử nghiệm temporal v4", "Trục ml_risk_level | Distinct customer_unique_id"),
        (CONTENT_LEFT + w_col1 + w_col2 + w_col3 + 3 * GAP, w_col4, "Xác suất không mua lại trong 180 ngày – thử nghiệm", "Theo ml_score_decile | Avg of ml_churn_probability")
    ]

    for x0, w, title, desc in cols_r2:
        x1 = x0 + w
        draw.rounded_rectangle([x0, ROW2_Y, x1, ROW2_Y + ROW2_H], radius=8, fill="#FFFFFF", outline="#E2E8F0", width=1)
        draw.text((x0 + 16, ROW2_Y + 14), title, fill="#0B1F46", font=font_card_title)
        draw.text((x0 + 16, ROW2_Y + 34), desc, fill="#64748B", font=font_card_sub)

    # 5. HÀNG 3: ĐÁNH GIÁ MÔ HÌNH VÀ GHI CHÚ CHUYÊN GIA (y=594 đến y=1055, h=461)
    ROW3_Y = 594
    ROW3_H = 461

    w3_col1 = 370
    w3_col2 = 340
    w3_col3 = 410
    w3_col4 = TOTAL_W - (w3_col1 + w3_col2 + w3_col3 + 3 * GAP) # ~454px

    # Khung 3A: Báo cáo phân loại (Classification Report)
    x3a = CONTENT_LEFT
    draw.rounded_rectangle([x3a, ROW3_Y, x3a + w3_col1, ROW3_Y + ROW3_H], radius=8, fill="#FFFFFF", outline="#E2E8F0", width=1)
    draw.text((x3a + 16, ROW3_Y + 14), "Báo cáo phân loại (Classification Report)", fill="#0B1F46", font=font_card_title)
    draw.text((x3a + 16, ROW3_Y + 34), "Nhãn, Precision, Recall, F1-score, Support (Tập Test 944)", fill="#64748B", font=font_card_sub)

    # Khung 3B: Ma trận nhầm lẫn (Confusion Matrix)
    x3b = x3a + w3_col1 + GAP
    draw.rounded_rectangle([x3b, ROW3_Y, x3b + w3_col2, ROW3_Y + ROW3_H], radius=8, fill="#FFFFFF", outline="#E2E8F0", width=1)
    draw.text((x3b + 16, ROW3_Y + 14), "Ma trận nhầm lẫn (Confusion Matrix)", fill="#0B1F46", font=font_card_title)
    draw.text((x3b + 16, ROW3_Y + 34), "Nhãn thực tế vs Dự đoán quay lại / không mua lại", fill="#64748B", font=font_card_sub)

    # Khung 3C: Phân phối xác suất (Probability Summary)
    x3c = x3b + w3_col2 + GAP
    draw.rounded_rectangle([x3c, ROW3_Y, x3c + w3_col3, ROW3_Y + ROW3_H], radius=8, fill="#FFFFFF", outline="#E2E8F0", width=1)
    draw.text((x3c + 16, ROW3_Y + 14), "Tóm tắt phân phối xác suất (Probability Summary)", fill="#0B1F46", font=font_card_title)
    draw.text((x3c + 16, ROW3_Y + 34), "Phạm vi: test_historical (Không gộp train vào test)", fill="#64748B", font=font_card_sub)

    # Khung 3D: CALLOUT CONTAINER ĐẶC BIỆT DÀNH CHO TEXT BOX DIỄN GIẢI CHUYÊN GIA
    x3d = x3c + w3_col3 + GAP
    draw.rounded_rectangle([x3d, ROW3_Y, x3d + w3_col4, ROW3_Y + ROW3_H], radius=8, fill="#FFFBEB", outline="#F59E0B", width=2)
    # Banner nhỏ trên đầu
    draw.rounded_rectangle([x3d, ROW3_Y, x3d + w3_col4, ROW3_Y + 44], radius=8, fill="#FEF3C7")
    draw.rectangle([x3d, ROW3_Y + 30, x3d + w3_col4, ROW3_Y + 44], fill="#FEF3C7") # che góc bo dưới của banner
    draw.text((x3d + 16, ROW3_Y + 12), "⚠ LƯU Ý HỌC THUẬT & DIỄN GIẢI MÔ HÌNH", fill="#92400E", font=font_card_title)
    draw.text((x3d + 16, ROW3_Y + 52), "(Dán nội dung Text box diễn giải kiểm định mô hình vào khung này)", fill="#B45309", font=font_card_sub)

    # Lưu ảnh nền Canvas Trang 5
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    bg.save(out_path, "PNG")
    print(f"Đã tạo thành công ảnh nền Trang 5 hoàn hảo: {out_path}")

if __name__=='__main__': main()
