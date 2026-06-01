from typing import List
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.rooms.room import Room
from app.models.matching.preference import UserPreference
from app.schemas.matching.schemas import RoomMatchRequest, RoomMatchResult

class RoomMatcherService:
    def __init__(self, db: Session):
        self.db = db

    def match_rooms(self, current_account_id: int, request: RoomMatchRequest) -> List[RoomMatchResult]:
        # Fetch current user preference
        current_pref = self.db.scalar(select(UserPreference).where(UserPreference.account_id == current_account_id))
        
        if not current_pref:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Vui lòng tạo matching profile trước khi tìm phòng."
            )

        # 1. Rule-based filtering
        stmt = select(Room).where(Room.status == "available")
        
        # Use preference budget_max for filtering rooms
        if current_pref.budget_max is not None:
            stmt = stmt.where(Room.price <= current_pref.budget_max)
        if current_pref.target_city:
            stmt = stmt.where(Room.city == current_pref.target_city)
        if current_pref.target_district:
            stmt = stmt.where(Room.district == current_pref.target_district)
            
        candidate_rooms = self.db.scalars(stmt).all()
        
        results = []
        for room in candidate_rooms:
            score = 0.0
            matched_criteria = []
            
            # Price (50%)
            if current_pref.budget_max and room.price:
                # Max 50 points, based on how much cheaper it is
                price_diff = current_pref.budget_max - room.price
                price_score = 25 + (price_diff / current_pref.budget_max) * 50
                price_score = min(50, max(0, price_score))
                score += price_score
                matched_criteria.append(f"Price ({price_score:.1f}/50)")
            elif room.price:
                score += 25 # default score if no budget provided
                matched_criteria.append("Price (25.0/50)")
            
            # Location (35%)
            loc_score = 0
            if current_pref.target_city and room.city == current_pref.target_city:
                loc_score += 15
            if current_pref.target_district and room.district == current_pref.target_district:
                loc_score += 20
            score += loc_score
            if loc_score > 0:
                matched_criteria.append(f"Location ({loc_score}/35)")
                
            # Amenities: Wifi (10%), Parking (5%)
            if request.require_wifi or request.require_parking:
                desc = (room.description or "").lower()
                if request.require_wifi and ("wifi" in desc or "internet" in desc):
                    score += 10
                    matched_criteria.append("WiFi (10/10)")
                if request.require_parking and ("giữ xe" in desc or "parking" in desc or "để xe" in desc):
                    score += 5
                    matched_criteria.append("Parking (5/5)")
                    
            results.append(RoomMatchResult(
                room_id=room.id,
                title=room.title,
                price=room.price,
                city=room.city,
                district=room.district,
                score=round(score, 2),
                matched_criteria=matched_criteria
            ))
            
        # Sort and return top results
        results.sort(key=lambda x: x.score, reverse=True)
        return results
