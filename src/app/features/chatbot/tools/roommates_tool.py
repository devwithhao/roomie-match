import json
from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.features.matching.services.roommate_matcher import RoommateMatcherService


class RoommateSearchInput(BaseModel):
    query: Optional[str] = Field(
        default=None,
        description="Optional text query or intent (e.g. 'find me a roommate')",
    )


def get_roommate_search_tool(db: Session, current_account_id: int) -> StructuredTool:
    def search_roommates(query: Optional[str] = None) -> str:
        """Search for potential roommates using the matching engine and return compact JSON."""
        try:
            service = RoommateMatcherService(db)
            # Fetch top 5 from matching engine
            results, total = service.get_suggestions(current_account_id, page=1, size=5)

            if not results:
                return json.dumps(
                    {
                        "message": "No matching roommates found. Tell the user they might need to update their matching profile or wait for more users.",
                        "profiles_data": [],
                    },
                    ensure_ascii=False,
                )

            profiles_data = []
            for r in results:
                profiles_data.append(
                    {
                        "id": r.id,
                        "account_id": r.account_id,
                        "full_name": r.full_name,
                        "score": r.score,
                        "area": r.area,
                        "avatar_url": r.avatar_url,
                        "matched_criteria": r.matched_criteria,
                    }
                )

            return json.dumps(
                {
                    "message": f"Found {len(profiles_data)} potential roommates. Reply briefly because the frontend renders the roommate cards.",
                    "profiles_data": profiles_data,
                },
                ensure_ascii=False,
            )
        except Exception as exc:
            return json.dumps(
                {"message": f"Roommate query failed: {exc}", "profiles_data": []},
                ensure_ascii=False,
            )

    return StructuredTool.from_function(
        func=search_roommates,
        name="search_roommates_tool",
        description="Search for potential roommates for the current user based on their matching profile.",
        args_schema=RoommateSearchInput,
    )
