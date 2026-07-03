# RoomieMatch - Tài liệu tổng quan luồng nghiệp vụ

Tài liệu này dùng để trình bày với giảng viên rằng mình hiểu project theo cả frontend và backend. Project được tổ chức theo kiến trúc thống nhất:

```text
Frontend React/Vite
  Page/Component -> RTK Query API -> baseApi -> /api/v1/*

Backend FastAPI
  router -> service -> repository -> model/database
```

Khi cô hỏi một chức năng, mình có thể mở theo thứ tự: màn hình FE, file gọi API FE, router BE, service BE, model DB.

## 1. Tổng quan kiến trúc

Backend nằm trong `roomie_match_project`:

- Entry app: `src/app/main.py`
- Gom router API v1: `src/app/api/v1/router.py`
- Cấu hình, bảo mật, email: `src/app/core/`
- Kết nối database: `src/app/database/`
- Module nghiệp vụ: `src/app/features/`
- Migration database: `src/migrations/versions/`
- Test tích hợp: `src/tests/integration/`

Frontend nằm trong `RoomieMatch-FE`:

- Router màn hình: `src/app/router.jsx`
- Redux store và RTK Query: `src/app/store.js`
- Base API tự gắn token: `src/shared/api/baseApi.js`
- Các màn hình: `src/pages/` và `src/features/*`
- API theo feature: `src/features/*/api/*.js`

Các nhóm vai trò chính:

- `tenant`: người thuê trọ, tìm phòng, lưu phòng, gửi yêu cầu thuê, dùng matching, chatbot.
- `landlord`: chủ trọ, tạo phòng, đăng bài, mua gói đăng tin, xem yêu cầu thuê, xác minh CCCD.
- `admin`: quản trị, duyệt bài, duyệt hồ sơ chủ trọ, quản lý gói, user, đơn hàng.

## 2. Luồng chạy chung của một request

Ví dụ landlord tạo bài đăng:

```text
FE page LandlordPostCreatePage
-> FE API createLandlordPost trong landlordApi.js
-> POST /api/v1/landlord/posts
-> landlord/router.py
-> LandlordService.create_post()
-> PackageService kiểm tra quota posts_limit
-> ghi Post vào DB trạng thái pending
```

Điểm quan trọng là frontend không thao tác trực tiếp database. Frontend chỉ gọi API. Backend kiểm tra quyền, quota, trạng thái dữ liệu rồi mới commit database.

## 3. Luồng đăng ký, đăng nhập, phân quyền

Màn hình FE:

- `RoomieMatch-FE/src/pages/LoginPage.jsx`
- `RoomieMatch-FE/src/pages/RegisterPage.jsx`
- `RoomieMatch-FE/src/features/auth/components/`
- API FE: `RoomieMatch-FE/src/features/auth/api/authApi.js`
- Auth state: `RoomieMatch-FE/src/features/auth/slice.js`

Backend:

- Router: `roomie_match_project/src/app/features/users/routers/auth.py`
- Service: `roomie_match_project/src/app/features/users/services/auth_service.py`
- Model: `accounts`, `roles`, `profiles`

Luồng đăng ký:

1. Người dùng nhập email, mật khẩu, tên hiển thị, loại tài khoản `tenant` hoặc `landlord`.
2. FE gọi `POST /api/v1/auth/register`.
3. Backend kiểm tra role tương ứng trong bảng `roles`.
4. Backend kiểm tra email và display name có bị trùng không.
5. Backend hash mật khẩu rồi tạo `Account`.
6. Backend tạo `Profile` mặc định với `full_name = display_name`.
7. Backend cấp miễn phí entitlement ban đầu cho user mới: `match = 5`, `chatbot = 5`.
8. Backend trả JWT access token và thông tin user.
9. FE lưu token vào Redux/localStorage, các request sau `baseApi` tự thêm header `Authorization: Bearer <token>`.

Luồng đăng nhập:

1. FE gọi `POST /api/v1/auth/login`.
2. Backend tìm account theo email đã normalize.
3. Nếu account active và mật khẩu đúng, backend tạo access token.
4. FE dùng role trong token/user để điều hướng đúng khu vực tenant, landlord hoặc admin.

Phân quyền route ở frontend:

- `ProtectedRoute`: yêu cầu đã đăng nhập.
- `RequireAuth`: kiểm tra role cụ thể, ví dụ `/landlord` chỉ cho landlord, `/admin` chỉ cho admin.

Phân quyền ở backend:

- `get_current_account`: lấy account từ JWT.
- `require_landlord_account`: chỉ cho landlord.
- `require_admin_account`: chỉ cho admin.

## 4. Luồng profile, avatar, đổi mật khẩu

Màn hình FE:

- User: `RoomieMatch-FE/src/features/user/components/Profile.jsx`
- Landlord profile: `RoomieMatch-FE/src/features/landlord/components/LandlordProfileForm.jsx`
- API FE: `RoomieMatch-FE/src/features/user/api/userApi.js`, `RoomieMatch-FE/src/features/landlord/api/landlordApi.js`

Backend:

- Router: `src/app/features/users/routers/users.py`
- Service profile: `src/app/features/users/services/profile_service.py`
- Service password: `src/app/features/users/services/auth_service.py`

Luồng profile:

1. FE gọi `GET /api/v1/users/me/profile` để lấy account và profile.
2. Người dùng sửa thông tin cá nhân.
3. FE gọi `PATCH /api/v1/users/me/profile`.
4. Backend upsert profile theo `account_id`.
5. Khi landlord đăng bài, backend yêu cầu profile có `full_name` và `phone`; nếu thiếu thì không cho đăng bài.

Luồng avatar:

1. FE gửi file qua `POST /api/v1/users/me/avatar`.
2. Backend upload ảnh bằng helper trong `landlord/image_uploader.py`.
3. Backend lưu `avatar_url` vào profile.

## 5. Luồng tìm phòng public

Màn hình FE:

- Trang chủ: `RoomieMatch-FE/src/features/homepage/Homepage.jsx`
- Tìm phòng: `RoomieMatch-FE/src/features/room/RoomPage.jsx`
- Chi tiết phòng: `RoomieMatch-FE/src/features/room/RoomDetailPage.jsx`
- API FE: `RoomieMatch-FE/src/features/homepage/api/postsApi.js`

Backend:

- Router: `src/app/features/rooms/routers/posts.py`
- Service: `src/app/features/rooms/services/post_service.py`
- Repository: `src/app/features/rooms/repositories/post_repository.py`
- Model: `Post`, `Room`, `RoomImage`, `Amenity`, `RoomAmenity`, `PostInteraction`

Luồng danh sách:

1. FE gọi `GET /api/v1/posts` với query như `city`, `district`, `room_type`, `min_price`, `max_price`, `amenity_ids`, `sort_by`, `page`.
2. Backend chỉ lấy bài có `Post.status = active`.
3. Backend join sang `Room` để lấy giá, diện tích, địa chỉ, loại phòng, ảnh đại diện.
4. Backend ưu tiên bài đang boost còn hạn, sau đó mới tới bài thường.
5. FE render danh sách card phòng.

Luồng chi tiết:

1. FE mở `/rooms/:roomId` và gọi `GET /api/v1/posts/{post_id}`.
2. Backend kiểm tra bài còn active.
3. Backend ghi một dòng `PostInteraction(kind="view")` để thống kê lượt xem.
4. Backend trả thông tin bài, phòng, ảnh, tiện ích, chủ trọ.

## 6. Luồng lưu phòng yêu thích

Màn hình FE:

- `RoomieMatch-FE/src/features/user/components/SavedRooms.jsx`
- API FE: `RoomieMatch-FE/src/features/user/api/userApi.js`

Backend:

- Router: `src/app/features/rooms/routers/posts.py`
- Service: `src/app/features/rooms/services/favorite_service.py`
- Model: `Favorite`

Luồng:

1. Tenant bấm lưu phòng.
2. FE gọi `POST /api/v1/posts/{post_id}/save`.
3. Backend kiểm tra user phải là `tenant`.
4. Backend kiểm tra post tồn tại.
5. Nếu chưa lưu thì tạo `Favorite(account_id, post_id)`.
6. Danh sách đã lưu lấy bằng `GET /api/v1/posts/saved`.
7. Bỏ lưu gọi `DELETE /api/v1/posts/{post_id}/save`.

## 7. Luồng landlord tạo trọ

Màn hình FE:

- Danh sách phòng: `RoomieMatch-FE/src/pages/landlord/LandlordRoomsPage.jsx`
- Form thêm/sửa phòng: `RoomieMatch-FE/src/pages/landlord/LandlordAddRoomPage.jsx`
- Component form nhiều bước: `RoomieMatch-FE/src/features/landlord/components/AddRoomForm/`
- API FE: `RoomieMatch-FE/src/features/landlord/api/landlordApi.js`

Backend:

- Router: `src/app/features/landlord/router.py`
- Service: `src/app/features/landlord/service.py`
- Model: `Room`, `RoomImage`, `Amenity`, `RoomAmenity`

Luồng tạo phòng:

1. Landlord nhập thông tin cơ bản, địa chỉ, giá, tiện ích, ảnh.
2. FE tạo `FormData` gồm:
   - `payload`: JSON thông tin phòng.
   - `images`: danh sách file ảnh.
   - `publish`: có đăng bài ngay hay chỉ lưu phòng.
3. FE gọi `POST /api/v1/landlord/rooms`.
4. Backend parse multipart form.
5. Nếu `publish = true`, backend kiểm tra landlord có profile đủ `full_name`, `phone`.
6. Backend kiểm tra quota:
   - `photo_limit`: đủ lượt upload cho số ảnh gửi lên.
   - `posts_limit`: nếu tạo phòng kèm đăng bài.
7. Backend tạo `Room`, sinh mã `room_code` dạng `TRO-000001`.
8. Backend đồng bộ tiện ích qua bảng `RoomAmenity`.
9. Backend upload và lưu ảnh vào `RoomImage`, mỗi ảnh trừ 1 quota `photo_limit`.
10. Nếu publish ngay, backend tạo thêm `Post` trạng thái `pending`, trừ 1 quota `posts_limit`.
11. Backend commit và trả thông tin phòng.

Luồng sửa phòng:

1. FE gọi `PUT /api/v1/landlord/rooms/{room_id}`.
2. Backend kiểm tra phòng thuộc landlord hiện tại.
3. Backend cập nhật thông tin phòng, tiện ích, ảnh mới.
4. Ảnh mới vẫn bị trừ quota `photo_limit`.

Luồng xóa phòng:

1. FE gọi `DELETE /api/v1/landlord/rooms/{room_id}`.
2. Nếu phòng đã có lịch sử thuê hoặc review, backend không xóa cứng mà chuyển `Room.status = archived`, post liên quan chuyển `closed`.
3. Nếu chưa có dữ liệu lịch sử, backend xóa favorite, post, tiện ích, ảnh, room.

## 8. Luồng landlord tạo bài đăng và admin duyệt bài

Màn hình FE landlord:

- `RoomieMatch-FE/src/pages/landlord/LandlordPostsPage.jsx`
- `RoomieMatch-FE/src/pages/landlord/LandlordPostCreatePage.jsx`
- `RoomieMatch-FE/src/pages/landlord/LandlordPostDetailPage.jsx`
- API FE: `RoomieMatch-FE/src/features/landlord/api/landlordApi.js`

Màn hình FE admin:

- `RoomieMatch-FE/src/pages/AdminPage.jsx`
- Component tab bài đăng: `RoomieMatch-FE/src/features/admin/components/PostsTab.jsx`
- API FE: `RoomieMatch-FE/src/features/admin/api/adminApi.js`

Backend landlord:

- Router: `src/app/features/landlord/router.py`
- Service: `src/app/features/landlord/service.py`
- Model: `Post`, `Room`

Backend admin:

- Router: `src/app/features/admin/routers/moderation.py`
- Service: `src/app/features/admin/services/moderation.py`

Luồng tạo bài:

1. Landlord chọn phòng đã tạo và nhập title/description.
2. FE gọi `POST /api/v1/landlord/posts`.
3. Backend kiểm tra landlord đã có profile đủ họ tên và số điện thoại.
4. Backend kiểm tra phòng thuộc landlord.
5. Backend kiểm tra quota `posts_limit`.
6. Nếu phòng chưa có post, backend tạo `Post(status="pending")`.
7. Backend trừ 1 quota `posts_limit` bằng `PackageUsageEvent`.
8. Bài chưa hiện public vì public API chỉ lấy `active`.

Luồng admin duyệt bài:

1. Admin mở tab bài đăng.
2. FE gọi `GET /api/v1/admin/posts`.
3. Admin chọn duyệt hoặc từ chối.
4. FE gọi `PATCH /api/v1/admin/posts/{post_id}/status`.
5. Nếu admin gửi `approved`, backend lưu DB là `Post.status = active`.
6. Nếu admin gửi `rejected`, backend yêu cầu có lý do, lưu `moderation_reason`.
7. Nếu bài không active, backend tắt boost nếu có.
8. Backend tạo `Notification` cho landlord biết kết quả.
9. Bài active mới xuất hiện ở trang tìm phòng public.

Luồng sửa bài đã duyệt:

1. Landlord sửa title/description.
2. Nếu nội dung thay đổi và bài đang active/rejected/closed, backend chuyển lại `pending`.
3. Bài cần admin duyệt lại trước khi public.

## 9. Luồng mua gói, thanh toán, quota

Màn hình FE:

- Tenant: `RoomieMatch-FE/src/pages/PackageManagementPage.jsx`, `PackageHistoryPage.jsx`
- Landlord: `RoomieMatch-FE/src/pages/landlord/LandlordPackagesPage.jsx`, `LandlordPackagePaymentPage.jsx`, `LandlordPackageManagementPage.jsx`
- API FE tenant: `RoomieMatch-FE/src/features/user/api/userApi.js`
- API FE landlord: `RoomieMatch-FE/src/features/landlord/api/landlordApi.js`

Backend:

- Router package: `src/app/features/packages/routers/packages.py`
- Router VNPAY: `src/app/features/packages/routers/vnpay.py`
- Service: `src/app/features/packages/service.py`
- VNPAY helper: `src/app/features/packages/vnpay_service.py`
- Models: `Package`, `Purchase`, `Entitlement`, `PackageUsageEvent`

Các bảng chính:

- `packages`: định nghĩa gói, giá, role được mua, credits và features.
- `purchases`: đơn mua gói, trạng thái `pending`, `paid`, `failed`, `cancelled`.
- `entitlements`: quyền lợi/quota còn lại của user.
- `package_usage_events`: lịch sử trừ quota, biết trừ cho entity nào.

Luồng xem gói:

1. FE gọi `GET /api/v1/packages/?target_role=tenant` hoặc `target_role=landlord`.
2. Backend chỉ trả gói active và đúng role.
3. FE map package thành card gói.

Luồng tạo đơn mua thường:

1. FE gọi `POST /api/v1/packages/purchase` với `package_id`.
2. Backend kiểm tra package tồn tại.
3. Backend kiểm tra role user có được mua gói này không.
4. Backend tạo `Purchase(status="pending")`.
5. Chưa cấp quota ở bước này.

Luồng thanh toán VNPAY:

1. FE gọi `POST /api/v1/payments/vnpay/create_url` với `package_id`.
2. Backend tạo `Purchase(status="pending", provider="vnpay")`.
3. Backend tạo URL thanh toán VNPAY, trong đó `vnp_TxnRef` là `purchase.id`.
4. FE chuyển browser sang VNPAY.
5. VNPAY gọi IPN về `GET /api/v1/payments/vnpay/ipn`.
6. Backend verify checksum.
7. Backend kiểm tra đơn tồn tại, chưa paid, số tiền đúng.
8. Nếu `vnp_ResponseCode == "00"`, backend gọi `confirm_purchase()`.
9. `confirm_purchase()` đổi `Purchase.status = paid`, lưu `provider_payment_id`, `raw_payload`.
10. Backend cấp `Entitlement` theo package.
11. Nếu IPN lặp lại với đơn đã paid, backend không cấp entitlement lần hai.

Luồng cấp quota:

- Nếu package có `credits_match`, backend cấp entitlement `feature_key = "match"`.
- Nếu package có `credits_chatbot`, backend cấp entitlement `feature_key = "chatbot"`.
- Nếu package có `features` dạng số, ví dụ `posts_limit`, `photo_limit`, `boost_limit`, backend cấp entitlement tương ứng.
- Nếu package có kỳ hạn `30_days` hoặc `annual`, entitlement có `expires_at`.
- Backend thêm entitlement `active_subscription` để đánh dấu gói đang còn hạn.

Luồng trừ quota:

- Đăng bài: trừ `posts_limit`.
- Upload ảnh phòng: trừ `photo_limit` theo số ảnh.
- Đẩy tin nổi bật: trừ `boost_limit`.
- AI matching: trừ `match`.
- Chatbot AI: trừ `chatbot`.

Mỗi lần trừ quota, backend tạo `PackageUsageEvent` gồm:

- `account_id`
- `feature_key`
- `amount`
- `entity_type`
- `entity_id`
- `source_purchase_id`
- `metadata`

Nếu quota không đủ, backend trả HTTP `402 Payment Required`. FE hiển thị lỗi để người dùng biết cần mua hoặc nâng cấp gói.

Ví dụ gói landlord trong seed:

- Basic: `posts_limit = 3`, `photo_limit = 15`, `boost_limit = 0`.
- Pro: `posts_limit = 30`, `photo_limit = 60`, `boost_limit = 5`.
- VIP: `posts_limit = 100`, `photo_limit = 150`, `boost_limit = 20`.

## 10. Luồng boost/đẩy tin nổi bật

Màn hình FE:

- `RoomieMatch-FE/src/pages/landlord/LandlordPostsPage.jsx`
- `RoomieMatch-FE/src/pages/landlord/LandlordPostDetailPage.jsx`
- API FE: `boostLandlordPost`, `cancelPostBoost` trong `landlordApi.js`

Backend:

- Service: `src/app/features/landlord/service.py`
- Public ranking: `src/app/features/rooms/services/post_service.py`

Luồng:

1. Landlord chỉ boost được bài đã được duyệt, tức bài public đang `active`.
2. FE gửi cập nhật bài để bật trạng thái nổi bật.
3. Backend kiểm tra quota `boost_limit`.
4. Backend trừ 1 lượt boost và đọc `boost_duration_days` từ package nếu có, mặc định 3 ngày.
5. Backend set:
   - `post.is_vip = True`
   - `post.boosted_at = now`
   - `post.boost_expires_at = now + duration`
6. API public xếp bài boost còn hạn lên trước bài thường.
7. Nếu bài bị reject, closed hoặc hết hạn boost, backend/public service xem như không còn nổi bật.

## 11. Luồng tenant gửi yêu cầu thuê và landlord xử lý

Màn hình FE tenant:

- Chi tiết phòng: `RoomieMatch-FE/src/features/room/RoomDetailPage.jsx`
- Rental history/request: `RoomieMatch-FE/src/features/user/components/RentalHistory.jsx`
- API FE: `createRentalRequest`, `getMyRentalRequests`, `cancelRentalRequest` trong `userApi.js`

Màn hình FE landlord:

- `RoomieMatch-FE/src/pages/landlord/LandlordRentalRequestsPage.jsx`
- API FE: `getLandlordRentalRequests`, `decideLandlordRentalRequest`, `endLandlordRentalRequest` trong `landlordApi.js`

Backend:

- Router tenant: `src/app/features/rooms/routers/posts.py`, `src/app/features/users/routers/users.py`
- Router landlord: `src/app/features/landlord/router.py`
- Service: `src/app/features/rental_requests/services/request_service.py`
- Models: `RentalRequest`, `RentalHistory`, `Notification`

Luồng tenant gửi yêu cầu:

1. Tenant mở chi tiết bài active.
2. Tenant gửi ngày bắt đầu thuê và ghi chú.
3. FE gọi `POST /api/v1/posts/{post_id}/rental-requests`.
4. Backend kiểm tra user là tenant.
5. Backend kiểm tra post active và room available.
6. Backend không cho tenant có nhiều yêu cầu `pending` cùng lúc.
7. Backend tạo `RentalRequest(status="pending")`.
8. Backend tạo notification cho landlord.

Luồng tenant hủy yêu cầu:

1. FE gọi `PATCH /api/v1/users/me/rental-requests/{id}/cancel`.
2. Backend chỉ cho hủy nếu request đang `pending`.
3. Backend chuyển status thành `cancelled`.
4. Backend tạo notification cho landlord.

Luồng landlord chấp nhận:

1. Landlord xem danh sách yêu cầu thuê qua `GET /api/v1/landlord/rental-requests`.
2. Landlord chấp nhận một yêu cầu.
3. FE gọi `PATCH /api/v1/landlord/rental-requests/{id}` với `decision = accepted`.
4. Backend lock request, room, post để tránh xử lý trùng.
5. Nếu room còn available:
   - request thành `accepted`
   - room thành `rented`
   - `current_people` tối thiểu là 1
   - post thành `closed`
   - tắt boost
   - tạo `RentalHistory(status="active")`
   - các request pending khác của cùng phòng bị reject với lý do phòng đã có người thuê
6. Backend tạo notification cho tenant.

Luồng landlord từ chối:

1. FE gửi `decision = rejected` và reason nếu có.
2. Backend cập nhật request, không đổi trạng thái phòng.
3. Backend thông báo kết quả cho tenant.

Luồng kết thúc lượt thuê:

1. Landlord gọi `PATCH /api/v1/landlord/rental-requests/{id}/end`.
2. Backend chỉ cho kết thúc request đã `accepted`.
3. Request thành `ended`.
4. Room trở lại `available`, `current_people = 0`.
5. RentalHistory active chuyển `ended`, có `end_date`.

## 12. Luồng mở thông tin liên hệ chủ trọ

Màn hình FE:

- Chi tiết phòng tenant.
- API FE: `revealPostContact` trong `userApi.js`

Backend:

- Router: `src/app/features/rooms/routers/posts.py`
- Model: `PostInteraction`

Luồng:

1. Tenant bấm xem liên hệ.
2. FE gọi `POST /api/v1/posts/{post_id}/contact-view`.
3. Backend kiểm tra tenant, post active.
4. Backend ghi `PostInteraction(kind="contact")`.
5. Backend trả `contact_name`, `contact_phone`, `contact_social` của phòng.
6. Landlord xem thống kê contact trong dashboard.

## 13. Luồng xác minh CCCD landlord

Màn hình FE:

- Modal xác minh: `RoomieMatch-FE/src/features/landlord/components/VerificationModal.jsx`
- API FE: `getLandlordVerification`, `submitLandlordVerification` trong `landlordApi.js`
- Admin duyệt: `RoomieMatch-FE/src/features/admin/components/UsersTab.jsx` hoặc khu vực verification trong admin.

Backend:

- Landlord router: `src/app/features/landlord/router.py`
- Workflow service: `src/app/features/landlord/workflow_service.py`
- Admin router: `src/app/features/admin/routers/moderation.py`
- Admin service: `src/app/features/admin/services/moderation.py`
- Model: `LandlordVerification`, `Notification`

Luồng landlord gửi hồ sơ:

1. Landlord nhập họ tên pháp lý, số CCCD, ngày cấp, nơi cấp.
2. Landlord upload ảnh mặt trước và mặt sau.
3. FE gửi multipart tới `POST /api/v1/landlord/verification`.
4. Backend kiểm tra file là JPG/PNG/WEBP và mỗi ảnh tối đa 5MB.
5. Backend lưu ảnh private/public-storage helper, tạo hoặc cập nhật hồ sơ.
6. Hồ sơ có trạng thái `pending`.
7. Nếu hồ sơ đã `approved`, landlord không gửi lại được.

Luồng admin duyệt:

1. Admin gọi `GET /api/v1/admin/landlord-verifications`.
2. Admin xem ảnh qua endpoint riêng.
3. Admin gọi `PATCH /api/v1/admin/landlord-verifications/{id}`.
4. Nếu approved, hồ sơ thành `approved`.
5. Nếu rejected, bắt buộc có lý do.
6. Backend tạo notification cho landlord.

## 14. Luồng notification landlord

Màn hình FE:

- `RoomieMatch-FE/src/features/landlord/components/NotificationPanel.jsx`
- API FE: `getLandlordNotifications`, `markLandlordNotificationRead` trong `landlordApi.js`

Backend:

- Router: `src/app/features/landlord/router.py`
- Service: `src/app/features/landlord/workflow_service.py`
- Model: `Notification`

Notification được tạo khi:

- Admin duyệt/từ chối bài đăng.
- Admin duyệt/từ chối CCCD.
- Tenant gửi hoặc hủy yêu cầu thuê.
- Landlord xử lý yêu cầu thuê thì tenant cũng nhận thông báo nghiệp vụ qua cùng model.

Luồng đọc:

1. FE gọi `GET /api/v1/landlord/notifications`.
2. Backend trả `items`, `total`, `unread`.
3. FE gọi `PATCH /api/v1/landlord/notifications/{id}` để đánh dấu đã đọc.

## 15. Luồng thống kê landlord

Màn hình FE:

- `RoomieMatch-FE/src/pages/landlord/LandlordStatsPage.jsx`
- Component chart: `RoomieMatch-FE/src/features/landlord/components/StatsCharts.jsx`
- API FE: `getLandlordStats` trong `landlordApi.js`

Backend:

- Router: `src/app/features/landlord/router.py`
- Service: `src/app/features/landlord/service.py`
- Models: `Room`, `Post`, `Favorite`, `PostInteraction`, `RentalHistory`, `Review`

Luồng:

1. FE gọi `GET /api/v1/landlord/stats?range=30d` hoặc có `date`.
2. Backend lấy room/post thuộc landlord.
3. Backend đếm:
   - tổng phòng
   - tổng bài
   - lượt lưu
   - lượt xem
   - lượt liên hệ
   - review
   - tenant đã thuê
4. Backend tính trạng thái phòng: rented, available, negotiating.
5. Backend trả dữ liệu summary, chart tương tác theo tuần, top post.

## 16. Luồng review phòng

Màn hình FE:

- Component review trong chi tiết phòng: `RoomieMatch-FE/src/features/room/components/RoomDetailReviews.jsx`
- API FE: `getRoomReviews`, `addRoomReview`, `editRoomReview` trong `postsApi.js`

Backend:

- Router: `src/app/features/rooms/routers/reviews.py`
- Service: `src/app/features/rooms/services/review_service.py`
- Model: `Review`

Luồng:

1. Người dùng xem review bằng `GET /api/v1/rooms/{room_id}/reviews`.
2. Người dùng đăng nhập có thể thêm review bằng `POST /api/v1/rooms/{room_id}/reviews`.
3. Người dùng sửa review của mình bằng `PUT /api/v1/rooms/{room_id}/reviews/{review_id}`.
4. Landlord stats dùng số review để thống kê.

## 17. Luồng AI Matching

Màn hình FE:

- Trang tìm bạn: `RoomieMatch-FE/src/pages/FindMatePage.jsx`
- Feature matching: `RoomieMatch-FE/src/features/matching/`
- API FE: `RoomieMatch-FE/src/features/matching/api/matchingApi.js`

Backend:

- Router: `src/app/features/matching/routers/matching.py`
- Services:
  - `services/profile_service.py`
  - `services/room_matcher.py`
  - `services/roommate_matcher.py`
  - `services/match_interaction_service.py`
- Models: `Preference`, `Match`, `Reject`
- Quota service: `src/app/features/packages/service.py`

Luồng tạo profile matching:

1. User nhập thông tin sở thích, nhu cầu ở ghép.
2. FE gọi `POST /api/v1/matching/profile`.
3. Backend tạo hoặc cập nhật profile matching theo account.
4. FE lấy lại bằng `GET /api/v1/matching/profile`.

Luồng gợi ý roommate:

1. FE gọi `GET /api/v1/matching/roommates/suggestions`.
2. Backend lấy profile của user hiện tại.
3. Backend tính danh sách roommate phù hợp.
4. FE hiển thị dạng card để accept/reject.

Luồng matching có trừ quota:

1. FE gọi `POST /api/v1/matching/rooms` hoặc `POST /api/v1/matching/roommates`.
2. Backend kiểm tra entitlement `match`.
3. Nếu còn lượt, backend trừ 1 quota và ghi usage event.
4. Backend trả kết quả matching.
5. Nếu hết lượt, backend trả HTTP 402.

Luồng accept/reject/unmatch:

- Accept: `POST /api/v1/matching/roommates/accept`
- Reject: `POST /api/v1/matching/roommates/reject`
- Unmatch: `POST /api/v1/matching/roommates/unmatch`
- Lịch sử match: `GET /api/v1/matching/roommates/history`
- Lịch sử reject: `GET /api/v1/matching/roommates/rejects`

## 18. Luồng Chatbot AI

Màn hình FE:

- Widget: `RoomieMatch-FE/src/features/chatbot/components/ChatbotWidget.jsx`

Backend:

- Router: `src/app/features/chatbot/routers/chatbot.py`
- Service: `src/app/features/chatbot/service.py`
- Repository: `src/app/features/chatbot/repositories/chat_repository.py`
- Tools: `src/app/features/chatbot/tools/`
- Models: `ChatSession`, `ChatMessage`
- Quota service: `src/app/features/packages/service.py`

Luồng:

1. User tạo session bằng `POST /api/v1/chatbot/sessions`.
2. FE lấy session bằng `GET /api/v1/chatbot/sessions`.
3. FE lấy message bằng `GET /api/v1/chatbot/sessions/{session_id}/messages`.
4. Khi user gửi tin nhắn, FE gọi `POST /api/v1/chatbot/sessions/{session_id}/chat`.
5. Backend kiểm tra quota `chatbot`.
6. Nếu còn lượt, backend trừ 1 và ghi usage event.
7. Backend lưu message user.
8. Backend gọi Groq/LangGraph agent.
9. Nếu user hỏi tìm phòng, agent dùng tool `search_available_rooms`.
10. Backend lưu message assistant dạng JSON gồm `content` và `rooms_data`.
11. FE hiển thị câu trả lời và danh sách phòng nếu có.

## 19. Luồng admin quản lý hệ thống

Màn hình FE:

- `RoomieMatch-FE/src/pages/AdminPage.jsx`
- Components: `RoomieMatch-FE/src/features/admin/components/`
- API FE: `RoomieMatch-FE/src/features/admin/api/adminApi.js`

Backend:

- Users: `src/app/features/admin/routers/users.py`, `services/user_service.py`
- Packages: `src/app/features/admin/routers/packages.py`, `services/packages.py`
- Role features: `src/app/features/admin/routers/role_features.py`
- Moderation: `src/app/features/admin/routers/moderation.py`, `services/moderation.py`
- Analytics: `src/app/features/admin/routers/analytics.py`
- Orders: `src/app/features/admin/routers/orders.py`
- Categories: `src/app/features/admin/routers/categories.py`
- Complaints: `src/app/features/admin/routers/complaints.py`

Các luồng chính:

- Quản lý user: xem danh sách, xem chi tiết, tạo/sửa, đổi trạng thái, xóa.
- Quản lý bài đăng: xem post pending/approved/featured, duyệt/từ chối/đóng bài.
- Quản lý phòng: xem room, đổi trạng thái available/rented/archived.
- Quản lý gói: tạo/sửa/bật tắt/xóa package.
- Quản lý quyền theo role: cấu hình feature theo role.
- Quản lý đơn hàng: xem purchase, chỉ được đổi pending/failed/cancelled theo rule, không sửa đơn đã paid.
- Duyệt CCCD landlord: approved/rejected.
- Dashboard/analytics: tổng hợp số liệu cho admin.

## 20. Luồng upload và metadata dùng chung

Backend shared:

- Upload: `src/app/shared/routers/upload.py`
- Metadata: `src/app/shared/routers/metadata.py`
- Storage config: `src/app/main.py`, `src/app/core/config.py`
- Image helper: `src/app/features/landlord/image_uploader.py`

Frontend:

- Upload API chung: `RoomieMatch-FE/src/shared/api/uploadApi.js`
- Province/category API: `RoomieMatch-FE/src/shared/api/provincesApi.js`

Luồng:

1. FE gửi file qua multipart.
2. Backend dùng Cloudinary nếu cấu hình có, hoặc lưu local storage.
3. `main.py` mount static files theo `settings.public_storage_url`.
4. Metadata/category giúp FE lấy danh mục tiện ích, loại phòng, khu vực.

## 21. Bảng mở code nhanh khi cô hỏi

| Cô hỏi về | Mở frontend | Mở backend |
|---|---|---|
| Route màn hình | `RoomieMatch-FE/src/app/router.jsx` | `roomie_match_project/src/app/api/v1/router.py` |
| Gọi API và token | `RoomieMatch-FE/src/shared/api/baseApi.js` | `users/dependencies.py`, `core/security.py` |
| Đăng ký đăng nhập | `features/auth/api/authApi.js` | `features/users/routers/auth.py`, `services/auth_service.py` |
| Profile | `features/user/api/userApi.js` | `features/users/routers/users.py`, `services/profile_service.py` |
| Tìm phòng | `features/homepage/api/postsApi.js` | `features/rooms/routers/posts.py`, `services/post_service.py` |
| Lưu phòng | `features/user/api/userApi.js` | `features/rooms/services/favorite_service.py` |
| Tạo phòng trọ | `pages/landlord/LandlordAddRoomPage.jsx` | `features/landlord/router.py`, `service.py` |
| Đăng bài | `pages/landlord/LandlordPostCreatePage.jsx` | `features/landlord/service.py` |
| Duyệt bài | `features/admin/components/PostsTab.jsx` | `features/admin/services/moderation.py` |
| Mua gói | `pages/landlord/LandlordPackagesPage.jsx` | `features/packages/service.py` |
| VNPAY | `pages/VnpayReturnPage.jsx` | `features/packages/routers/vnpay.py`, `vnpay_service.py` |
| Quota | `features/landlord/api/landlordApi.js` | `features/packages/models/entitlement.py`, `usage_event.py`, `service.py` |
| Boost bài | `features/landlord/api/landlordApi.js` | `features/landlord/service.py`, `rooms/services/post_service.py` |
| Yêu cầu thuê | `pages/landlord/LandlordRentalRequestsPage.jsx` | `features/rental_requests/services/request_service.py` |
| CCCD landlord | `features/landlord/components/VerificationModal.jsx` | `features/landlord/workflow_service.py`, `admin/services/moderation.py` |
| Admin | `features/admin/api/adminApi.js` | `features/admin/routers/*`, `features/admin/services/*` |
| Matching | `features/matching/api/matchingApi.js` | `features/matching/routers/matching.py` |
| Chatbot | `features/chatbot/components/ChatbotWidget.jsx` | `features/chatbot/routers/chatbot.py`, `service.py` |

## 22. Các trạng thái quan trọng cần nhớ

Post:

- `pending`: landlord vừa tạo, chờ admin duyệt.
- `active`: đã duyệt, public nhìn thấy.
- `rejected`: admin từ chối, có lý do.
- `closed`: bài đóng, không public.
- `boosted`: không phải status DB riêng; FE/backend suy ra từ `active + is_vip + boost_expires_at > now`.

Room:

- `available`: phòng trống.
- `rented`: đã có người thuê.
- `archived`: đã ẩn/lưu trữ.
- `negotiating`: trạng thái thống kê/thương lượng nếu có dữ liệu.

Purchase:

- `pending`: tạo đơn nhưng chưa xác nhận thanh toán.
- `paid`: đã thanh toán, đã cấp quyền lợi.
- `failed`: thanh toán thất bại.
- `cancelled`: đã hủy.

RentalRequest:

- `pending`: tenant gửi, chờ landlord xử lý.
- `accepted`: landlord chấp nhận.
- `rejected`: landlord từ chối hoặc phòng đã có người thuê.
- `cancelled`: tenant hủy.
- `ended`: landlord kết thúc lượt thuê.

LandlordVerification:

- `pending`: chờ admin duyệt.
- `approved`: đã xác minh.
- `rejected`: bị từ chối, có lý do.

## 23. Kịch bản demo ngắn để trình bày

Kịch bản landlord:

1. Đăng nhập landlord.
2. Mua gói hoặc dùng seed có sẵn entitlement.
3. Vào quản lý phòng, tạo phòng và upload ảnh.
4. Tạo bài đăng từ phòng.
5. Bài ở trạng thái pending.
6. Đăng nhập admin, duyệt bài.
7. Quay lại trang public, bài xuất hiện.
8. Landlord boost bài, bài nổi bật lên trước.
9. Tenant gửi yêu cầu thuê.
10. Landlord chấp nhận, phòng thành rented, bài closed, lịch sử thuê được tạo.

Kịch bản tenant:

1. Đăng ký hoặc đăng nhập tenant.
2. Tìm phòng theo khu vực/giá/loại phòng.
3. Mở chi tiết phòng, hệ thống ghi lượt xem.
4. Lưu phòng yêu thích.
5. Bấm xem liên hệ, hệ thống ghi lượt contact.
6. Gửi yêu cầu thuê.
7. Theo dõi yêu cầu và lịch sử thuê.
8. Dùng matching hoặc chatbot, mỗi lần dùng sẽ trừ quota tương ứng.

## 24. Câu trả lời nhanh khi cô hỏi "quota hoạt động thế nào?"

Quota không lưu trực tiếp trong user. Quota nằm trong bảng `entitlements`. Khi user mua gói thành công, backend tạo các entitlement tương ứng với quyền lợi của gói. Khi user thực hiện hành động có giới hạn, backend kiểm tra còn entitlement không, sau đó trừ số lượng và ghi lại `package_usage_events`. Vì vậy hệ thống biết được user còn bao nhiêu lượt, lượt đó đến từ đơn mua nào, và đã dùng cho bài/ảnh/chức năng nào.

Ví dụ landlord đăng bài:

```text
Landlord tạo post
-> LandlordService._ensure_package_credit(account, "posts_limit", 1)
-> nếu đủ thì tạo Post pending
-> LandlordService._consume_package_credit(..., "posts_limit", entity_type="post", entity_id=post.id)
-> Entitlement.quantity giảm 1
-> PackageUsageEvent ghi lại lịch sử
```

Ví dụ tenant dùng AI matching:

```text
POST /api/v1/matching/rooms
-> PackageService.has_credit(account.id, "match")
-> PackageService.consume_credit_with_event(account.id, "match")
-> chạy RoomMatcherService
```

Ví dụ chatbot:

```text
POST /api/v1/chatbot/sessions/{id}/chat
-> kiểm tra entitlement "chatbot"
-> trừ 1 lượt
-> lưu message user
-> gọi AI agent
-> lưu message assistant
```

## 25. Câu trả lời nhanh khi cô hỏi "vì sao bài mới tạo chưa hiện public?"

Vì landlord tạo bài thì backend để `Post.status = pending`. API public `/api/v1/posts` chỉ lấy bài `active`. Admin phải duyệt bài bằng `/api/v1/admin/posts/{post_id}/status` với trạng thái `approved`, backend mới đổi DB thành `active`. Sau đó bài mới xuất hiện ở trang tìm phòng.

## 26. Câu trả lời nhanh khi cô hỏi "FE và BE thống nhất ở đâu?"

FE dùng `baseApi` để gọi chung prefix `/api/v1`, tự gắn JWT token. Các feature FE gọi đúng endpoint của backend:

- Landlord FE gọi `/landlord/*`.
- Admin FE gọi `/admin/*`.
- User/Tenant FE gọi `/users/*`, `/posts/*`, `/packages/*`.
- Matching FE gọi `/matching/*`.
- Chatbot FE gọi `/chatbot/*`.

Backend gom toàn bộ endpoint trong `src/app/api/v1/router.py`, rồi chia vào từng feature. Do đó kiến trúc nhất quán: frontend theo feature nào thì backend cũng có feature tương ứng.
