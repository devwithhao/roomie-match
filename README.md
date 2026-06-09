# RoomieMatch Backend

RoomieMatch là backend FastAPI theo hướng modular monolith. Project vẫn giữ một service và một database chính, nhưng code được chia theo feature để team có thể thêm `admin`, `landlord`, payment, matching, chatbot... mà không làm rối các lớp nghiệp vụ.

## Kiến Trúc

Public API v1 hiện được giữ nguyên để tương thích frontend:

- `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`
- `/api/v1/users/*`
- `/api/v1/posts/*`
- `/api/v1/rooms/*`
- `/api/v1/matching/*`
- `/api/v1/packages/*`
- `/api/v1/chatbot/*`

Code chính nằm trong `src/app/features`:

```text
src/app/
|-- api/v1/router.py              # aggregate router cho API v1
|-- core/                         # config, security
|-- database/                     # Base, session, model registry
|-- features/
|   |-- users/                    # auth, account, role, profile
|   |-- rooms/                    # posts, saved rooms, reviews, amenities
|   |-- matching/                 # matching profile, rooms, roommates
|   |-- packages/                 # packages, purchases, entitlements, webhook
|   |-- rental_requests/          # rental history và request flow sau này
|   `-- chatbot/                  # chat sessions, messages, tools
|-- shared/                       # pagination và helper dùng chung
src/migrations/                   # Alembic migrations
src/tests/                        # integration tests
docs/                             # tài liệu API/database bổ sung
```

Mỗi feature gồm các nhóm quen thuộc: `routers`, `schemas`, `services`, `repositories`, `models` khi feature đó cần. Luồng phụ thuộc mặc định:

```text
router -> service -> repository -> model/database
```

Feature được dùng `core`, `database`, `shared`. Khi cần dùng logic của feature khác, ưu tiên gọi qua service/public contract thay vì import sâu vào repository nội bộ.

## Chạy Local Bằng Python

Yêu cầu Python 3.10+ và MySQL 8+.

Nên dùng virtual environment để thư viện của project không bị cài vào Python global của máy.

Tạo và bật venv trên Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Nếu đang dùng Command Prompt:

```bat
python -m venv .venv
.venv\Scripts\activate.bat
```

Kiểm tra Python đang trỏ vào venv:

```bash
python -c "import sys; print(sys.executable)"
```

Kết quả nên nằm trong `.venv`, ví dụ `...\roomie_match_project\.venv\Scripts\python.exe`.

Sau khi đã bật venv:

```bash
cp .env.example .env
python -m pip install -U pip
python -m pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --app-dir src
```

Mặc định app chạy ở `http://127.0.0.1:8000`.

Kiểm tra nhanh:

```bash
curl http://127.0.0.1:8000/health
```

## Migration

Project dùng Alembic. Revision hiện được đặt theo dạng tuần tự để dễ đọc:

```text
001_initial_roles_accounts
002_add_rooms_and_favorites
...
010_add_suggested_accounts
```

Quy tắc làm việc:

- Migration đã apply lên production thì không sửa trực tiếp; tạo revision mới.
- Khi sửa ORM model, tạo migration bằng `alembic revision --autogenerate -m "message"` rồi review file sinh ra.
- Data bắt buộc cho hệ thống, ví dụ role mặc định, có thể nằm trong migration.
- Data mẫu/demo/local không đặt trong migration; dùng seed script ở phần dưới.

Lưu ý: các revision id đã được chuẩn hóa lại. Nếu database local của bạn đã migrate bằng revision id cũ, cách gọn nhất là drop/recreate DB local rồi chạy lại `alembic upgrade head`. Nếu cần giữ data cũ, cần stamp lại Alembic version thủ công sau khi đổi revision.

## Chạy Bằng Docker Compose

Docker Compose sẽ start MySQL, chờ DB healthy, tự chạy migration, rồi start FastAPI.

```bash
cp .env.example .env
docker compose up --build
```

App chạy ở `http://127.0.0.1:8000`. MySQL được expose qua port `3306` mặc định và có volume `mysql_data`.

## Test

Integration tests mặc định dùng SQLite in-memory, không cần MySQL:

```bash
python -m pytest
```

Nếu muốn test với database riêng:

```bash
set TEST_DATABASE_URL=mysql+pymysql://user:pass@127.0.0.1:3306/roomie_match_test?charset=utf8mb4
python -m pytest
```

## Data Mẫu

Migration chỉ nên seed dữ liệu bắt buộc cho hệ thống, ví dụ `roles`. Data demo/local nên đặt trong script riêng để tránh production bị chèn dữ liệu mẫu.

Sau khi chạy migration, seed data mẫu:

```bash
python scripts/seed_sample_data.py
```

Nếu đang dùng Docker Compose:

```bash
docker compose exec api python scripts/seed_sample_data.py
```

Script seed hiện tại idempotent, có thể chạy lại nhiều lần. Script tạo dữ liệu mẫu cho các bảng trong migration:

- `roles`, `accounts`, `profiles`
- `rooms`, `posts`, `room_images`, `amenities`, `room_amenities`
- `favorites`, `rental_history`, `reviews`
- `packages`, `purchases`, `entitlements`
- `user_preferences`, `user_matches`, `user_rejects`
- `chat_sessions`, `chat_messages`

Tài khoản mẫu:

- `tenant.demo@example.com` / `password123`
- `landlord.demo@example.com` / `password123`
- `admin.demo@example.com` / `password123`

Seed có 10 room và 10 post active. Địa chỉ room dùng chuỗi tiếng Việt có dấu để FE search theo API:

- `city=Thành Phố Hồ Chí Minh`: `Quận 1`, `Quận Bình Thạnh`, `Thành phố Thủ Đức`, `Quận 7`, `Quận Gò Vấp`, `Quận Tân Bình`
- `city=Đồng Nai`: `Thành phố Biên Hòa`, `Huyện Long Thành`, `Huyện Nhơn Trạch`, `Huyện Trảng Bom`

Vì API filter hiện tại so sánh exact match, khi test cần truyền đúng chuỗi:

```bash
curl "http://127.0.0.1:8000/api/v1/posts?city=Thành%20Phố%20Hồ%20Chí%20Minh"
curl "http://127.0.0.1:8000/api/v1/posts?city=Đồng%20Nai&district=Huyện%20Long%20Thành"
```

## Thêm Feature Mới

Ví dụ thêm `admin`:

1. Tạo `src/app/features/admin/`.
2. Thêm `routers`, `schemas`, `services`, `repositories`, `models` nếu cần.
3. Đăng ký router mới trong `src/app/api/v1/router.py`.
4. Nếu có model mới, import model trong `src/app/database/model_registry.py`.
5. Tạo migration Alembic nếu thay đổi DB.
6. Thêm tests trong `src/tests/integration/admin/`.

Với feature `landlord`, nên tách các use case chủ trọ như quản lý phòng, đăng tin, duyệt request vào feature riêng khi nghiệp vụ đủ lớn. Nếu endpoint chỉ là một phần của rooms/post hiện tại, đặt trong `features/rooms` trước để tránh tách quá sớm.

## Các Vấn Đề Cấu Trúc Đã Xử Lý

- Chuyển code từ layer top-level `models/schemas/services/repositories/api/v1/*` sang `features/*`.
- Tách `packages` ra file rõ nghĩa: `schemas.py`, `service.py`, `repositories.py`, `routers/*`.
- Xóa skeleton root `roomie_match/`, TODO test root, và script thử nghiệm `test_pydantic.py`.
- Xóa route matching rỗng/cũ và các folder API cũ không còn được import.
- Thêm `database/model_registry.py` để Alembic và tests luôn load đủ ORM metadata, bao gồm chatbot models.
- Sửa package tests dùng fixture `client/db_session` và path `/api/v1/packages/`.
- Giữ nguyên public API v1, table names, columns, migration history và JWT payload.
