# RoomieMatch API Guide

Tài liệu này giải thích cách dùng các API đang có trong project, nhất là khi bạn mở `/docs` của FastAPI nhưng chưa rõ field nào phải nhập số, field nào phải nhập chuỗi, và field nào có thể để trống.

## Cách đọc `/docs`

FastAPI sinh OpenAPI từ schema Pydantic:
- `int` nghĩa là gửi số, ví dụ `1`, `20`, `0`.
- `float` nghĩa là gửi số thực, ví dụ `12.5`.
- `str` nghĩa là gửi chuỗi, ví dụ `"Ha Noi"`.
- `bool` nghĩa là `true` hoặc `false`.
- `list[int]` nghĩa là mảng số, ví dụ `[1, 2, 3]`.
- `Literal[...]` hoặc `Enum` nghĩa là chỉ được chọn đúng giá trị trong danh sách cho phép.
- Trường `optional` có thể bỏ trong request; nếu là PATCH thì thường nên omit field không cần cập nhật, không cần nhập `0` nếu nó không phải kiểu số.

Quy tắc nhanh:
- Nếu schema là `int`, không bỏ dấu ngoặc kép. Dùng `123`, không phải `"123"`.
- Nếu schema là `str`, phải là chuỗi, ví dụ `"tenant"`.
- Nếu field không bắt buộc, thường có thể để trống.
- Nếu bạn không chắc, mở Swagger UI trong `/docs` và nhìn phần Example Value để lấy mẫu.

## Nhóm API hiện có

Base URL: `/api/v1`

### 1. Auth

#### `POST /api/v1/auth/register`
Tạo tài khoản mới.

Request body:
- `email`: `str`, bắt buộc, phải là email hợp lệ.
- `password`: `str`, bắt buộc, tối thiểu 8 ký tự.
- `display_name`: `str`, bắt buộc.
- `account_type`: chỉ nhận `tenant` hoặc `landlord`.

Ví dụ:
```json
{
  "email": "user@example.com",
  "password": "12345678",
  "display_name": "Nguyen Van A",
  "account_type": "tenant"
}
```

#### `POST /api/v1/auth/login`
Đăng nhập để lấy token.

Request body:
- `email`: `str`, bắt buộc.
- `password`: `str`, bắt buộc.

Ví dụ:
```json
{
  "email": "user@example.com",
  "password": "12345678"
}
```

#### `GET /api/v1/auth/me`
Lấy thông tin tài khoản hiện tại.

Header bắt buộc:
- `Authorization: Bearer <access_token>`

### 2. Users / Profile

#### `GET /api/v1/users/me/profile`
Lấy thông tin profile của bạn.

Header bắt buộc:
- `Authorization: Bearer <access_token>`

#### `PATCH /api/v1/users/me/profile`
Cập nhật profile.

Request body:
- `full_name`: `str | null`, tối đa 100 ký tự.
- `phone`: `str | null`, tối đa 20 ký tự.
- `gender`: chỉ nhận `male`, `female`, `other`.
- `avatar_url`: `str | null`, tối đa 500 ký tự.

Quan trọng:
- Phải gửi ít nhất 1 field.
- Nếu muốn cập nhật, gửi field cần đổi; không cần gửi `0`.
- Nếu field là chuỗi, gửi chuỗi; nếu field là gender thì gửi đúng một trong 3 giá trị hợp lệ.

Ví dụ:
```json
{
  "full_name": "Nguyen Van A",
  "gender": "male",
  "phone": "0901234567"
}
```

#### `GET /api/v1/users/me/rental-history`
Lấy lịch sử thuê của bạn.

Query params:
- `limit`: `int`, mặc định `20`, tối thiểu `1`, tối đa `100`.
- `offset`: `int`, mặc định `0`.
- `status`: `str | null`.
- `q`: `str | null`.

Ví dụ:
- `/api/v1/users/me/rental-history?limit=20&offset=0`
- `/api/v1/users/me/rental-history?status=confirmed&q=quan 7`

### 3. Posts / Rooms

#### `GET /api/v1/posts`
Danh sách bài đăng phòng.

Query params:
- `page`: `int`, mặc định `1`, tối thiểu `1`.
- `page_size`: `int`, mặc định `20`, tối thiểu `1`, tối đa `100`.
- `city`: `str | null`.
- `district`: `str | null`.
- `ward`: `str | null`.
- `room_type`: `str | null`.
- `min_price`: `int | null`.
- `max_price`: `int | null`.
- `amenity_ids`: `list[int] | null`.
- `sort_by`: `newest`, `price_asc`, hoặc `price_desc`.

Ví dụ:
- `/api/v1/posts?page=1&page_size=20&city=Ho%20Chi%20Minh&sort_by=newest`
- `/api/v1/posts?min_price=2000000&max_price=5000000&amenity_ids=1&amenity_ids=3`

Lưu ý:
- `amenity_ids` là mảng số, không phải chuỗi.
- Nếu chỉ cần lọc một phòng, gửi số trong query param, không dùng chuỗi.

#### `GET /api/v1/posts/{post_id}`
Lấy chi tiết một bài đăng.

Path param:
- `post_id`: `int`

Ví dụ:
- `/api/v1/posts/12`

#### `POST /api/v1/posts/{post_id}/save` 
Lưu bài đăng vào danh sách đã lưu.

Path param:
- `post_id`: `int`

Header bắt buộc:
- `Authorization: Bearer <access_token>`

#### `DELETE /api/v1/posts/{post_id}/save`
Bỏ lưu bài đăng.

Path param:
- `post_id`: `int`

Header bắt buộc:
- `Authorization: Bearer <access_token>`

#### `GET /api/v1/posts/saved`
Lấy danh sách bài đăng đã lưu.

Query params:
- `limit`: `int`, mặc định `20`, tối thiểu `1`, tối đa `100`.
- `offset`: `int`, mặc định `0`.

Header bắt buộc:
- `Authorization: Bearer <access_token>`

### 4. Packages

#### `GET /api/v1/packages/`
Lấy danh sách gói.

Không cần request body.

#### `POST /api/v1/packages/purchase`
Tạo giao dịch mua gói.

Request body:
- `package_id`: `int`, bắt buộc.

Ví dụ:
```json
{
  "package_id": 1
}
```

Header bắt buộc:
- `Authorization: Bearer <access_token>`

#### `GET /api/v1/packages/me/purchases`
Lấy lịch sử mua gói của bạn.

Header bắt buộc:
- `Authorization: Bearer <access_token>`

#### `GET /api/v1/packages/me/entitlements`
Lấy quyền lợi đang có của bạn.

Header bắt buộc:
- `Authorization: Bearer <access_token>`

#### `POST /api/v1/packages/webhook`
Webhook cho nhà cung cấp thanh toán.

Request body có thể gồm:
- `provider`: `str`.
- `provider_payment_id`: `str`.
- `purchase_id`: `int`.

Ít nhất một trong các trường trên phải có giá trị để hệ thống tìm được purchase.

## Câu trả lời API

Phần lớn endpoint trả về JSON và FastAPI sẽ hiển thị response schema trong `/docs`.

Một số quy ước cơ bản:
- `id`, `post_id`, `room_id`, `package_id`, `account_id` là số nguyên.
- `price`, `deposit`, `credits_match`, `credits_chatbot` là số nguyên.
- `created_at`, `updated_at`, `joined_at`, `saved_at` là thời gian.
- `gender` chỉ nhận `male`, `female`, `other`.
- `account_type` chỉ nhận `tenant`, `landlord`.

## Mẫu dùng nhanh khi còn băn khoăn kiểu dữ liệu

- Số nguyên: `1`, `20`, `0`.
- Chuỗi: `"abc"`, `"Ha Noi"`.
- Boolean: `true`, `false`.
- Mảng số: `[1, 2, 3]`.
- Optional field: có thể bỏ qua thay vì nhập `0`.

Nếu bạn đang test trên Swagger UI, cách đơn giản nhất là:
1. Mở `/docs`.
2. Bấm endpoint cần test.
3. Bấm `Try it out`.
4. Xem Example Value hoặc Schema để biết chính xác field nào là số, field nào là chuỗi.
