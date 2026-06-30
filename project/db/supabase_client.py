import os
import uuid
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Setup logs directory and logger
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(PROJECT_DIR, "logs", "agent_activity.log")
IS_VERCEL = "VERCEL" in os.environ

activity_logger = logging.getLogger("agent_activity")
if not activity_logger.handlers:
    activity_logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    if IS_VERCEL:
        sh = logging.StreamHandler()
        sh.setFormatter(formatter)
        activity_logger.addHandler(sh)
    else:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        fh = logging.FileHandler(LOG_FILE)
        fh.setFormatter(formatter)
        activity_logger.addHandler(fh)


SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = None  # type: ignore

if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        activity_logger.error(f"Failed to initialize Supabase client: {e}")
else:
    activity_logger.warning("Supabase URL and/or Key not found. Client not initialized.")

def clean_uuid(raw_id: str) -> str:
    """Helper to convert any user/session ID into a valid UUID string deterministically."""
    if not raw_id:
        return str(uuid.uuid4())
    try:
        return str(uuid.UUID(raw_id))
    except ValueError:
        # Generate a deterministic UUID based on the string name
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, raw_id))

def get_user_profile(user_id: str) -> dict | None:
    """Fetches user profile from user_profile table."""
    if not supabase:
        return None
    uid = clean_uuid(user_id)
    try:
        res = supabase.table("user_profile").select("*").eq("id", uid).execute()
        activity_logger.info(f"Fetched user profile for user_id={uid}")
        if res.data and len(res.data) > 0:
            return res.data[0]
        return None
    except Exception as e:
        activity_logger.error(f"Error fetching user profile for user_id={uid}: {e}")
        return None

def upsert_user_profile(user_id: str, skill_level: str, language_pref: str):
    """Inserts or updates user's profile."""
    if not supabase:
        return
    uid = clean_uuid(user_id)
    try:
        data = {
            "id": uid,
            "skill_level": skill_level,
            "language_pref": language_pref,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        supabase.table("user_profile").upsert(data).execute()
        activity_logger.info(f"Upserted user profile for user_id={uid} (skill_level={skill_level})")
    except Exception as e:
        activity_logger.error(f"Error upserting user profile for user_id={uid}: {e}")

def create_session(user_id: str) -> str:
    """Inserts new row into sessions table and returns the session ID."""
    uid = clean_uuid(user_id)
    session_uuid = str(uuid.uuid4())
    if not supabase:
        return session_uuid
    try:
        # First ensure user profile exists to satisfy foreign key
        profile = get_user_profile(uid)
        if not profile:
            upsert_user_profile(uid, "beginner", "python")
            
        data = {
            "id": session_uuid,
            "user_id": uid,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "context": {}
        }
        supabase.table("sessions").insert(data).execute()
        activity_logger.info(f"Created session id={session_uuid} for user_id={uid}")
        return session_uuid
    except Exception as e:
        activity_logger.error(f"Error creating session for user_id={uid}: {e}")
        return session_uuid

def save_code_review(user_id: str, session_id: str, code: str, bugs: list, security_issues: list, optimizations: list, skill_level: str) -> str:
    """Inserts a code review row into the database."""
    uid = clean_uuid(user_id)
    sid = clean_uuid(session_id)
    review_uuid = str(uuid.uuid4())
    if not supabase:
        return review_uuid
    try:
        # Ensure user profile and session exist
        profile = get_user_profile(uid)
        if not profile:
            upsert_user_profile(uid, skill_level, "python")
            
        data = {
            "id": review_uuid,
            "user_id": uid,
            "session_id": sid,
            "code_snippet": code,
            "bugs_found": bugs,
            "security_issues": security_issues,
            "optimization_tips": optimizations,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        supabase.table("code_reviews").insert(data).execute()
        activity_logger.info(f"Saved code review id={review_uuid} for user_id={uid}")
        return review_uuid
    except Exception as e:
        activity_logger.error(f"Error saving code review for user_id={uid}: {e}")
        return review_uuid

def get_recurring_mistakes(user_id: str) -> list:
    """Fetches from recurring_mistakes table, ordered by occurrence_count descending."""
    if not supabase:
        return []
    uid = clean_uuid(user_id)
    try:
        res = supabase.table("recurring_mistakes").select("*").eq("user_id", uid).order("occurrence_count", desc=True).execute()
        activity_logger.info(f"Fetched recurring mistakes for user_id={uid}")
        return res.data or []
    except Exception as e:
        activity_logger.error(f"Error fetching recurring mistakes for user_id={uid}: {e}")
        return []

def update_recurring_mistake(user_id: str, mistake_type: str):
    """Increments occurrence count of a mistake, or inserts it if new."""
    if not supabase:
        return
    uid = clean_uuid(user_id)
    try:
        # Check if mistake exists
        res = supabase.table("recurring_mistakes").select("*").eq("user_id", uid).eq("mistake_type", mistake_type).execute()
        current_time = datetime.now(timezone.utc).isoformat()
        if res.data and len(res.data) > 0:
            row = res.data[0]
            new_count = row["occurrence_count"] + 1
            supabase.table("recurring_mistakes").update({
                "occurrence_count": new_count,
                "last_seen": current_time
            }).eq("id", row["id"]).execute()
            activity_logger.info(f"Updated recurring mistake: {mistake_type} count={new_count} for user_id={uid}")
        else:
            # Ensure user profile exists
            profile = get_user_profile(uid)
            if not profile:
                upsert_user_profile(uid, "beginner", "python")
                
            supabase.table("recurring_mistakes").insert({
                "id": str(uuid.uuid4()),
                "user_id": uid,
                "mistake_type": mistake_type,
                "occurrence_count": 1,
                "last_seen": current_time
            }).execute()
            activity_logger.info(f"Created recurring mistake: {mistake_type} count=1 for user_id={uid}")
    except Exception as e:
        activity_logger.error(f"Error updating recurring mistake for user_id={uid}: {e}")
