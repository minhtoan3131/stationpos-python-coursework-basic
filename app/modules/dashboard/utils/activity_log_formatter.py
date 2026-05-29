from app.modules.dashboard.dtos.activity_log_dto import ActivityLogDTO


class ActivityLogFormatter:
    @staticmethod
    def format_to_ui_string(log: ActivityLogDTO) -> str:
        # Tách chuỗi thời gian lấy giờ hiển thị trực quan [HH:MM:SS]
        time_part = log.created_at.strftime('%H:%M:%S')
        time_display = f'[{time_part}] '

        # Cấu hình Map Icon tương ứng từng hành vi biến động hệ thống
        prefix_map = {
            'SALE': '🛒 Hóa đơn',
            'CANCEL_SALE': '❌ HỦY HÓA ĐƠN',
            'IMPORT': '📦 Phiếu nhập',
            'CANCEL_IMPORT': '🗑️ HỦY PHIẾU NHẬP',
            'ADJUST': '🔧 Kiểm kho',
            'TAX_CLOSE': '🔒 Khóa sổ thuế',
            'SYSTEM': '🔔 Hệ thống'
        }

        prefix = prefix_map.get(log.action_type, '📝 Sự kiện')
        ref_text = f' #{log.reference_code}' if log.reference_code else ''

        return f'{time_display}{prefix}{ref_text} | {log.description}'