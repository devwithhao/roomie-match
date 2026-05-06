# Database (MySQL)

RoomieMatch backend dung **MySQL 8+** lam database chinh (dialect Alembic/SQLAlchemy: `mysql+pymysql`).

## Bien moi truong

Dat trong `.env` (xem [`.env.example`](../.env.example) o root repo):

- `DATABASE_URL` — vi du: `mysql+pymysql://user:password@127.0.0.1:3306/roomie_match?charset=utf8mb4`
- `JWT_SECRET` — chuoi bi mat ky cho ky JWT (development: dat ngau nhien dai; production: quan ly bang secret manager)

## Migration

Tu thu muc goc repo (noi co `alembic.ini`):

```bash
alembic upgrade head
```

File `src/migrations/env.py` tu dong `load_dotenv` tu `.env` o thu muc goc repo, khong can `set DATABASE_URL` thu cong neu da co `.env`.

Migration dau tien tao bang `roles`, `accounts` va seed role `tenant`, `landlord`, `admin` (admin chua co API cong khai).

## Test tich hop

Test auth dung **SQLite in-memory** (`TEST_DATABASE_URL` mac dinh) de khong bat buoc MySQL khi chay `pytest`. Neu muon test tren MySQL that, dat `TEST_DATABASE_URL` tro toi database test rieng.

ORM dung `Integer` lam khoa chinh cho `roles`/`accounts` de SQLite autoincrement hoat dong on dinh; migration MySQL van dung `BIGINT` (du cho khoang gia tri id thuc te).
