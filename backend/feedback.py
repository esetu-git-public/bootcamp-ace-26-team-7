from datetime import datetime, timezone

from backend.database import get_service_client


def submit_feedback(user_id: str, predicted_class: str, confidence: float, rating: int, comment: str = "") -> dict:
    supabase = get_service_client()
    try:
        result = supabase.table("feedback").insert({
            "user_id": user_id,
            "predicted_class": predicted_class,
            "confidence": round(confidence, 4),
            "rating": rating,
            "comment": comment,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
        return {"success": True, "message": "Feedback submitted"}
    except Exception as e:
        return {"success": False, "message": str(e)}


def get_feedback_stats() -> dict:
    supabase = get_service_client()
    try:
        result = supabase.table("feedback").select("*").execute()
        rows = result.data if result.data else []
        total = len(rows)
        if total == 0:
            return {
                "total": 0,
                "average_rating": 0,
                "by_class": [],
            }
        by_class: dict[str, list[int]] = {}
        for row in rows:
            cls = row.get("predicted_class", "Unknown")
            if cls not in by_class:
                by_class[cls] = []
            by_class[cls].append(row.get("rating", 0))
        class_stats = [
            {
                "defect": cls,
                "count": len(ratings),
                "average_rating": round(sum(ratings) / len(ratings), 2),
            }
            for cls, ratings in sorted(by_class.items())
        ]
        avg_rating = round(sum(r["rating"] for r in rows) / total, 2)
        return {"total": total, "average_rating": avg_rating, "by_class": class_stats}
    except Exception as e:
        return {"total": 0, "average_rating": 0, "by_class": [], "error": str(e)}