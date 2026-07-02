import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy import select
from app.database.session import SessionLocal
from app.features.users.models.account import Account
from app.features.users.models.profile import Profile
from app.features.users.models.role import Role
from app.features.matching.models.preference import UserPreference


def get_or_create_tenant_role(db):
    role = db.scalar(select(Role).where(Role.name == "tenant"))
    if role is None:
        role = Role(name="tenant", description="Nguoi thue tro")
        db.add(role)
        db.flush()
    return role

def seed_roommates():
    db = SessionLocal()
    
    try:
        tenant_role = get_or_create_tenant_role(db)
        # Allow appending new mock users

        mock_data = [
            {
                "email": "nam.nguyen@example.com", "name": "Nguyễn Hoàng Nam", "gender": "male", "target_gender": "male",
                "city": "Thành Phố Hồ Chí Minh", "district": "Quận 1",
                "min": 2500000, "max": 4500000, "habits": ["Không hút thuốc", "Gọn gàng", "Ngủ sớm", "Thích nấu ăn"],
                "intro": "Chào mọi người, mình là nhân viên văn phòng. Mình cần tìm roommate sạch sẽ, tôn trọng không gian riêng tư. Mình thường nấu ăn vào cuối tuần và thích không gian yên tĩnh.",
                "avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=Nam", "facebook": "https://fb.com/nam.nguyen", "instagram": "https://instagram.com/nam_n"
            },
            {
                "email": "mai.tran@example.com", "name": "Trần Ngọc Mai", "gender": "female", "target_gender": "female",
                "city": "Thành Phố Hồ Chí Minh", "district": "Quận 3",
                "min": 3000000, "max": 5000000, "habits": ["Yêu động vật", "Thích trồng cây", "Không dẫn bạn về phòng"],
                "intro": "Mình đang tìm một bạn nữ ở ghép. Mình có nuôi một bé mèo rất ngoan. Tính mình thoải mái, thích cây cối và nghe nhạc indie.",
                "avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=Mai", "facebook": "https://fb.com/mai.tran", "instagram": ""
            },
            {
                "email": "tuan.le@example.com", "name": "Lê Anh Tuấn", "gender": "male", "target_gender": "any",
                "city": "Thành Phố Hồ Chí Minh", "district": "Quận Bình Thạnh",
                "min": 2000000, "max": 3500000, "habits": ["Sinh viên", "Hay đi làm thêm", "Ngủ muộn", "Thoải mái"],
                "intro": "Sinh viên HUTECH, tính tình xởi lởi dễ chịu. Đi học và đi làm thêm suốt nên chỉ cần chỗ ngủ tối, mong tìm được anh em hợp tính thi thoảng nhậu lai rai.",
                "avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=Tuan", "facebook": "", "instagram": ""
            },
            {
                "email": "quynh.pham@example.com", "name": "Phạm Như Quỳnh", "gender": "female", "target_gender": "female",
                "city": "Thành Phố Hồ Chí Minh", "district": "Quận 10",
                "min": 3500000, "max": 5500000, "habits": ["Sạch sẽ", "Sống khép kín", "Không ồn ào"],
                "intro": "Mình làm freelance nên hay ở nhà làm việc. Cần tìm phòng hoặc roommate tại quận 10. Tiêu chí hàng đầu là sạch sẽ và không ồn ào ảnh hưởng công việc.",
                "avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=Quynh", "facebook": "https://fb.com/quynhpham", "instagram": "https://instagram.com/quynh_p"
            },
            {
                "email": "minh.hoang@example.com", "name": "Hoàng Minh", "gender": "male", "target_gender": "male",
                "city": "Thành Phố Hồ Chí Minh", "district": "Quận 1",
                "min": 4000000, "max": 6500000, "habits": ["Đi làm giờ hành chính", "Thể thao", "Không hút thuốc"],
                "intro": "Nhân viên IT, sáng đi tối về. Cuối tuần hay đi đá bóng. Cần tìm roommate chia sẻ tiền phòng chung cư mini ở Quận 1 hoặc Bình Thạnh.",
                "avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=Minh", "facebook": "https://fb.com/hoangminh", "instagram": ""
            },
            {
                "email": "thao.nguyen@example.com", "name": "Nguyễn Thu Thảo", "gender": "female", "target_gender": "female",
                "city": "Thành Phố Hồ Chí Minh", "district": "Quận 7",
                "min": 2500000, "max": 4000000, "habits": ["Thích nấu ăn", "Gọn gàng", "Vui vẻ"],
                "intro": "Mình là sinh viên năm 3 đại học Tôn Đức Thắng. Mong tìm được bạn nữ ở chung quanh khu vực Quận 7 để tiện đi học.",
                "avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=Thao", "facebook": "https://fb.com/thao.ng", "instagram": "https://instagram.com/thaonguyen"
            },
            {
                "email": "hai.tran@example.com", "name": "Trần Thanh Hải", "gender": "male", "target_gender": "male",
                "city": "Thành Phố Hồ Chí Minh", "district": "Quận Tân Bình",
                "min": 1500000, "max": 2500000, "habits": ["Dễ tính", "Ít đồ đạc", "Hay vắng nhà"],
                "intro": "Công việc của mình hay phải đi công tác tỉnh. Mình cần tìm một góc nhỏ để đồ và nghỉ ngơi những ngày ở lại Sài Gòn.",
                "avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=Hai", "facebook": "", "instagram": ""
            },
            {
                "email": "linh.vu@example.com", "name": "Vũ Thùy Linh", "gender": "female", "target_gender": "female",
                "city": "Thành Phố Hồ Chí Minh", "district": "Quận Phú Nhuận",
                "min": 3000000, "max": 5000000, "habits": ["Thích yên tĩnh", "Sạch sẽ", "Không đưa bạn về phòng"],
                "intro": "Mình đã đi làm, tính khá trầm. Rất chú trọng vệ sinh chung, hy vọng tìm được bạn cùng phòng có ý thức tốt.",
                "avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=Linh", "facebook": "https://fb.com/thuylinh", "instagram": ""
            },
            {
                "email": "dat.nguyen@example.com", "name": "Nguyễn Tiến Đạt", "gender": "male", "target_gender": "any",
                "city": "Thành Phố Hà Nội", "district": "Quận Cầu Giấy",
                "min": 2000000, "max": 3500000, "habits": ["Sinh viên", "Thích chơi game", "Vui vẻ"],
                "intro": "Sinh viên Bách Khoa, đang tìm phòng quanh Cầu Giấy hoặc Hai Bà Trưng. Anh em nào có dư slot thì cho mình xin ké nhé.",
                "avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=Dat", "facebook": "https://fb.com/datnguyen", "instagram": ""
            },
            {
                "email": "hang.pham@example.com", "name": "Phạm Thu Hằng", "gender": "female", "target_gender": "female",
                "city": "Thành Phố Hà Nội", "district": "Quận Đống Đa",
                "min": 2500000, "max": 4500000, "habits": ["Sống gọn gàng", "Yêu động vật", "Hay nấu ăn"],
                "intro": "Mình vừa ra trường, cần tìm bạn nữ ở ghép share phòng chung cư khu vực Đống Đa. Nhà đã có đủ đồ đạc cơ bản.",
                "avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=Hang", "facebook": "", "instagram": "https://instagram.com/hangpham"
            },
            {
                "email": "khiem.vu@example.com", "name": "Vũ Trung Khiêm", "gender": "male", "target_gender": "male",
                "city": "Thành Phố Hồ Chí Minh", "district": "Quận Thủ Đức",
                "min": 1500000, "max": 2200000, "habits": ["Sinh viên", "Ngủ sớm", "Ít nói"],
                "intro": "Mình là sinh viên năm nhất ĐHQG, cần tìm 1-2 bạn nam ở ghép ký túc xá hoặc phòng trọ sinh viên gần trường.",
                "avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=Khiem", "facebook": "", "instagram": ""
            },
            {
                "email": "tram.le@example.com", "name": "Lê Bảo Trâm", "gender": "female", "target_gender": "female",
                "city": "Thành Phố Hồ Chí Minh", "district": "Quận Gò Vấp",
                "min": 2000000, "max": 3000000, "habits": ["Thích mua sắm", "Gọn gàng", "Sạch sẽ"],
                "intro": "Nhân viên sale, hay đi sớm về muộn. Tìm phòng Gò Vấp có chỗ để xe rộng rãi.",
                "avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=Tram", "facebook": "", "instagram": ""
            },
            {
                "email": "khoa.bui@example.com", "name": "Bùi Đăng Khoa", "gender": "male", "target_gender": "male",
                "city": "Thành Phố Hà Nội", "district": "Quận Hai Bà Trưng",
                "min": 3000000, "max": 4500000, "habits": ["Đi làm giờ hành chính", "Không hút thuốc", "Gọn gàng"],
                "intro": "Đã đi làm, cần tìm 1 bạn nam ở chung CCMN khu vực Hai Bà Trưng, tiện di chuyển lên phố.",
                "avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=Khoa", "facebook": "", "instagram": ""
            },
            {
                "email": "uyen.do@example.com", "name": "Đỗ Tú Uyên", "gender": "female", "target_gender": "any",
                "city": "Thành Phố Đà Nẵng", "district": "Quận Hải Châu",
                "min": 2000000, "max": 4000000, "habits": ["Yêu động vật", "Hay đi du lịch", "Thoải mái"],
                "intro": "Đang làm remote, hay xê dịch. Tìm bạn ở ghép tại Đà Nẵng, có thể cùng nhau cafe làm việc.",
                "avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=Uyen", "facebook": "", "instagram": ""
            },
            {
                "email": "phong.truong@example.com", "name": "Trương Thanh Phong", "gender": "male", "target_gender": "male",
                "city": "Thành Phố Hồ Chí Minh", "district": "Quận 10",
                "min": 4000000, "max": 5000000, "habits": ["Thích nấu ăn", "Thể thao", "Không ồn ào"],
                "intro": "Mình làm PT gym, lịch sinh hoạt rất đều đặn và lành mạnh. Đang tìm một bạn nam cùng chung chí hướng sống healthy.",
                "avatar": "https://api.dicebear.com/9.x/avataaars/svg?seed=Phong", "facebook": "", "instagram": ""
            }
        ]

        for i, data in enumerate(mock_data):
            # Try to fetch existing by email to avoid unique constraint if re-running
            acc = db.query(Account).filter(Account.email == data["email"]).first()
            if not acc:
                acc = Account(
                    email=data["email"],
                    username=f"mockuser{i}",
                    password_hash="hash",
                    role_id=tenant_role.id,
                    email_verified=True,
                    status="active",
                )
                db.add(acc)
                db.flush()

            prof = db.get(Profile, acc.id)
            if not prof:
                prof = Profile(account_id=acc.id)
                db.add(prof)

            prof.full_name = data["name"]
            prof.gender = data.get("gender")
            prof.phone = f"09876543{i:02d}"
            prof.avatar_url = data["avatar"]
            prof.bio = data["intro"]
            prof.facebook = data["facebook"]
            prof.instagram = data["instagram"]

            pref = db.get(UserPreference, acc.id)
            if not pref:
                pref = UserPreference(account_id=acc.id)
                db.add(pref)

            pref.target_city = data["city"]
            pref.target_district = data["district"]
            pref.budget_min = data["min"]
            pref.budget_max = data["max"]
            pref.habit = data["habits"]
            pref.introduce = data["intro"]
            pref.target_gender = data.get("target_gender", "any")
            
        db.commit()
        print("Successfully added mock roommates!")
    except Exception as e:
        db.rollback()
        print("Error:", e)
    finally:
        db.close()

if __name__ == "__main__":
    seed_roommates()
