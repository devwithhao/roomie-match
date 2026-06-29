from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, or_

from app.database.session import get_db
from app.features.admin.dependencies import require_admin_account
from app.features.users.models.account import Account

router = APIRouter()

@router.get("/analytics")
def get_analytics(
    year: int = 2026,
    _admin: Account = Depends(require_admin_account),
    db: Session = Depends(get_db),
):
    from app.features.rooms.models.post import Post
    from app.features.rooms.models.room import Room
    from app.features.packages.models.purchase import Purchase
    
    # Helpers
    def get_monthly_counts(model, filter_cond=None):
        query = db.query(extract('month', model.created_at).label('month'), func.count(model.id).label('count'))\
                  .filter(extract('year', model.created_at) == year)
        if filter_cond is not None:
            query = query.filter(filter_cond)
        rows = query.group_by('month').all()
        counts = [0] * 12
        for r in rows:
            if r.month:
                counts[int(r.month) - 1] = r.count
        return counts

    # --- Users ---
    total_users_all = db.query(Account).count()
    new_users = get_monthly_counts(Account)
    blocked_users = get_monthly_counts(Account, Account.status == 'blocked')
    
    # Calculate cumulative users
    total_users = [0] * 12
    # This is an approximation: we distribute total users backward based on new users, 
    # but for simplicity, we'll just build a cumulative array starting from base.
    base_users = total_users_all - sum(new_users)
    current_cumulative = base_users
    for i in range(12):
        current_cumulative += new_users[i]
        total_users[i] = current_cumulative

    # --- Posts ---
    approved_posts = get_monthly_counts(Post, Post.status == 'approved')
    pending_posts = get_monthly_counts(Post, Post.status == 'pending')
    rejected_posts = get_monthly_counts(Post, Post.status == 'rejected')

    # --- Categories Distribution ---
    # Area (City)
    area_dist = db.query(Room.city, func.count(Post.id))\
                  .join(Post, Post.room_id == Room.id)\
                  .group_by(Room.city).all()
    area_data = [{"name": a[0] or "Khác", "value": a[1]} for a in area_dist if a[1] > 0]
    
    # Room Type
    type_dist = db.query(Room.room_type, func.count(Post.id))\
                  .join(Post, Post.room_id == Room.id)\
                  .group_by(Room.room_type).all()
    room_type_data = [{"name": a[0] or "Khác", "value": a[1]} for a in type_dist if a[1] > 0]
    
    # Provide fallbacks if empty
    if not area_data:
        area_data = [{"name": "Chưa có dữ liệu", "value": 1}]
    if not room_type_data:
        room_type_data = [{"name": "Chưa có dữ liệu", "value": 1}]

    # --- Revenue ---
    revenue_rows = db.query(extract('month', Purchase.created_at).label('month'), func.sum(Purchase.amount_cents).label('sum'))\
                     .filter(extract('year', Purchase.created_at) == year, Purchase.status == 'paid')\
                     .group_by('month').all()
    revenue_points = [0] * 12
    for r in revenue_rows:
        if r.month:
            revenue_points[int(r.month) - 1] = int(r.sum or 0)
    
    total_revenue = sum(revenue_points)

    return {
        "monthlyUsers": {
            "labels": ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10', 'T11', 'T12'],
            "series": [
                { "label": 'Tổng người dùng', "color": '#4F6EF7', "points": total_users },
                { "label": 'Người dùng mới', "color": '#22c55e', "points": new_users },
                { "label": 'Tài khoản bị khoá', "color": '#f43f5e', "points": blocked_users },
            ]
        },
        "monthlyPosts": {
            "labels": ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10', 'T11', 'T12'],
            "series": [
                { "label": 'Đã duyệt', "color": '#22c55e', "points": approved_posts },
                { "label": 'Đang chờ duyệt', "color": '#f59e0b', "points": pending_posts },
                { "label": 'Bị từ chối', "color": '#f43f5e', "points": rejected_posts },
            ]
        },
        "categoriesDistribution": {
            "area": area_data,
            "roomType": room_type_data,
            "priceRange": [
                { "name": 'Dưới 2 triệu', "value": 10 },
                { "name": '2 - 4 triệu', "value": 40 },
                { "name": 'Trên 4 triệu', "value": 50 }
            ]
        },
        "revenue": {
            "labels": ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8', 'T9', 'T10', 'T11', 'T12'],
            "total": total_revenue,
            "points": revenue_points
        },
        "complaints": {
            "labels": ['Đã giải quyết', 'Đang xử lý', 'Chưa giải quyết'],
            "points": [0, 0, 0],
            "colors": ['#22c55e', '#f59e0b', '#f43f5e']
        }
    }

