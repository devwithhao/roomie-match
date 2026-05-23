from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.rooms.room import Room
from app.models.users.preference import UserPreference
from app.schemas.matching.schemas import RoomMatchRequest, RoomMatchResult

class RoomMatcherService:
    def __init__(self, db: Session):
        self.db = db

    def match_rooms(self, request: RoomMatchRequest) -> List[RoomMatchResult]:
        # 1. Rule-based filtering
        stmt = select(Room).where(Room.status == "available")
        
        if request.budget is not None:
            stmt = stmt.where(Room.price <= request.budget)
        if request.city:
            stmt = stmt.where(Room.city == request.city)
        if request.district:
            stmt = stmt.where(Room.district == request.district)
            
        candidate_rooms = self.db.scalars(stmt).all()
        
        results = []
        for room in candidate_rooms:
            score = 0.0
            matched_criteria = []
            
            # Price (50%)
            if request.budget and room.price:
                # Max 50 points, based on how much cheaper it is
                price_diff = request.budget - room.price
                price_score = 25 + (price_diff / request.budget) * 50
                price_score = min(50, max(0, price_score))
                score += price_score
                matched_criteria.append(f"Price ({price_score:.1f}/50)")
            elif room.price:
                score += 25 # default score if no budget provided
                matched_criteria.append("Price (25.0/50)")
            
            # Location (35%)
            loc_score = 0
            if request.city and room.city == request.city:
                loc_score += 15
            if request.district and room.district == request.district:
                loc_score += 20
            score += loc_score
            if loc_score > 0:
                matched_criteria.append(f"Location ({loc_score}/35)")
            # Amenities: Wifi (10%), Parking (5%)
            # Since we don't have direct access to amenities without querying, we can do a subquery or lazy load
            # For simplicity, if request doesn't specify, we don't score. Or we just give points if room has them.
            if request.require_wifi or request.require_parking:
                # Assume room.description has keywords as fallback if room_amenities is hard to query here
                # Or query RoomAmenity joined with Amenity
                # Here we just use a placeholder logic or check text
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
