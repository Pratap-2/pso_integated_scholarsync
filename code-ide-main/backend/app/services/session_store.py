from app.services.cosmos_services import get_container


def save_session(state):
    container = get_container()
    if not container:
        return

    session_id = state.get("session_id", state.get("id"))
    if not session_id:
        return

    # To preserve fields like resume_data, progress_scores, evaluation
    existing = load_session(session_id)
    
    if existing:
        item = existing[-1] if isinstance(existing, list) else existing
        for k, v in state.items():
            item[k] = v
        item["id"] = session_id
        if "user_id" in state and state["user_id"]:
            item["user_id"] = state["user_id"]
    else:
        item = dict(state)
        item["id"] = session_id
        if "user_id" in item and not item["user_id"]:
            item.pop("user_id", None)

    try:
        container.upsert_item(item)
    except Exception as e:
        print(f"Error saving session: {e}")


def load_session(session_id):
    container = get_container()
    if not container:
        return []

    query = "SELECT * FROM c WHERE c.session_id=@session_id"

    try:
        items = list(container.query_items(
            query=query,
            parameters=[{"name": "@session_id", "value": session_id}],
            enable_cross_partition_query=True
        ))
        return items
    except Exception as e:
        print(f"Error loading session: {e}")
        return []

def load_candidate_history(user_id: str):
    container = get_container()
    if not container:
        return []

    # Retrieve the single document where id or user_id is the user
    query = "SELECT c.eval_history, c.evaluation, c.coding_score, c.communication_score, c.problem_solving_score, c.efficiency_score, c.overall_score, c.time_taken, c.hint_level FROM c WHERE c.user_id=@user_id"
    
    try:
        items = list(container.query_items(
            query=query,
            parameters=[{"name": "@user_id", "value": user_id}],
            enable_cross_partition_query=True
        ))
        
        if not items:
            return []
            
        doc = items[0]
        eval_history = doc.get("eval_history", [])
        
        # Fallback for backward compatibility (sessions before the array logic)
        if not eval_history and doc.get("evaluation"):
            eval_history.append({
                "evaluation": doc.get("evaluation"),
                "coding_score": doc.get("coding_score", 0),
                "communication_score": doc.get("communication_score", 0),
                "problem_solving_score": doc.get("problem_solving_score", 0),
                "efficiency_score": doc.get("efficiency_score", 0),
                "overall_score": doc.get("overall_score", 0),
                "time_taken": doc.get("time_taken", 0),
                "hint_level": doc.get("hint_level", 0),
                "_ts": 0
            })
        
        # Sort history by _ts
        eval_history.sort(key=lambda x: x.get("_ts", 0), reverse=True)
        
        # We only want the last 5 attempts
        attempts = eval_history[:5]
        
        # For graphing, chronological order (older to newer)
        attempts.reverse()
        return attempts
        
    except Exception as e:
        print(f"Error loading candidate history: {e}")
        return []
