# tests/dashboard/test_activity_log_service.py
import pytest
import datetime
from app.modules.dashboard.dtos.activity_log_dto import ActivityLogDTO
from app.modules.dashboard.services.impl.activity_log_service_impl import ActivityLogServiceImpl


# --- FAKE REPOSITORY TRÊN RAM ---
class FakeActivityLogRepository:
    def __init__(self):
        self.logs = []

    def add_log(self, action_type: str, reference_code: str | None, description: str) -> bool:
        mock_id = len(self.logs) + 1
        self.logs.append(ActivityLogDTO(
            id=mock_id, action_type=action_type, reference_code=reference_code,
            description=description, created_at=datetime.datetime.now()
        ))
        return True

    def get_logs_by_date(self, date_str: str):
        # Trả về toàn bộ danh sách trong RAM để tầng Service tự map
        return self.logs


class FakeUnitOfWork:
    def __init__(self, repo):
        self.activity_log_repo = repo

    def __enter__(self): return self

    def __exit__(self, exc_type, exc_val, exc_tb): pass


@pytest.fixture
def fake_repo(): return FakeActivityLogRepository()


@pytest.fixture
def log_service(fake_repo):
    return ActivityLogServiceImpl(uow_factory=lambda: FakeUnitOfWork(fake_repo))


# --- TEST CASES ---
def test_should_store_log_and_return_formatted_timeline(log_service, fake_repo):
    """UC_SV_1 & UC_SV_2: Bắn log nghiệp vụ và trích xuất dòng thời gian thành công"""
    # GIVEN: Hệ thống phát sinh hành vi bán hàng và hủy nhập kho
    log_service.log_event("SALE", "HD-888", "Khách mua sỉ tập vở")
    log_service.log_event("CANCEL_IMPORT", "PO-999", "NCC giao sai mẫu hàng")

    # WHEN: Dashboard quét dòng thời gian ngày hôm nay
    today_str = datetime.datetime.now().strftime('%Y-%m-%d')
    timeline = log_service.get_daily_activity_feed(today_str)

    # THEN: Kiểm chứng trạng thái để lại (State-based Assert)
    assert len(fake_repo.logs) == 2
    assert len(timeline) == 2

    # Kiểm tra xem bộ Formatter chạy thật có biên dịch đúng Emoji thiết kế không
    assert "🛒 Hóa đơn #HD-888 | Khách mua sỉ tập vở" in timeline[0]
    assert "🗑️ HỦY PHIẾU NHẬP #PO-999 | NCC giao sai mẫu hàng" in timeline[1]