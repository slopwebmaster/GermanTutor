import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import copy

APP_DIR = Path(__file__).resolve().parent
STATE_FILE = APP_DIR / "state.json"
SESSIONS_DIR = APP_DIR / "sessions"
BACKUPS_DIR = APP_DIR / "backups"
EVALUATIONS_DIR = APP_DIR / "evaluations"

SESSIONS_DIR.mkdir(exist_ok=True)
BACKUPS_DIR.mkdir(exist_ok=True)
EVALUATIONS_DIR.mkdir(exist_ok=True)

DEFAULT_STATE = {
    "week": 1, 
    "session": "B", 
    "ladder": {"row": "1. Akk - Definite (den/die/das)", "step": 1},
    "mistake_log": [], 
    "my_nouns": [], 
    "baseline": [], 
    "speaking_plan": ["", "", ""],
    "streak": 0,
    "last_study_date": "",
    "daily_goal": 10,
    "exercises_done_today": 0
}

def save_state(state, backup=True):
    if backup and STATE_FILE.exists():
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        shutil.copy2(STATE_FILE, BACKUPS_DIR / f"state_{ts}.json")
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def load_state():
    if not STATE_FILE.exists():
        save_state(DEFAULT_STATE, backup=False)
        return copy.deepcopy(DEFAULT_STATE)
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def normalize_state(state):
    merged = copy.deepcopy(DEFAULT_STATE)
    if isinstance(state, dict): merged.update(state)
    
    ladder = merged.get("ladder")
    if not isinstance(ladder, dict): ladder = {"row": "1. Akk - Definite (den/die/das)", "step": 1}
    ladder.setdefault("row", "1. Akk - Definite (den/die/das)"); ladder.setdefault("step", 1)
    merged["ladder"] = ladder

    nouns = merged.get("my_nouns", [])
    fixed_nouns = []
    if isinstance(nouns, list):
        for item in nouns:
            if isinstance(item, dict):
                noun_val = item.get("noun", ""); article_val = item.get("article", "")
                if not article_val and isinstance(noun_val, str):
                    for art in ["der ", "die ", "das "]:
                        if noun_val.startswith(art):
                            item["article"] = art.strip(); item["noun"] = noun_val[len(art):]; break
                fixed_nouns.append(item)
            elif isinstance(item, str):
                parts = item.split(" ", 1)
                if len(parts) == 2: fixed_nouns.append({"noun": parts[1], "article": parts[0], "plural": ""})
                else: fixed_nouns.append({"noun": item, "article": "", "plural": ""})
    merged["my_nouns"] = fixed_nouns

    mistakes = merged.get("mistake_log", [])
    fixed_mistakes = [item for item in mistakes if isinstance(item, dict)] if isinstance(mistakes, list) else []
    merged["mistake_log"] = fixed_mistakes

    return merged

def update_streak_and_daily_goal(state, exercises_completed=0):
    today = datetime.now().date()
    last_date_str = state.get("last_study_date", "")
    
    if not last_date_str:
        state["streak"] = 1
        state["exercises_done_today"] = 0
    else:
        last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
        if today > last_date:
            if today == last_date + timedelta(days=1):
                state["streak"] += 1
            else:
                state["streak"] = 1
            state["exercises_done_today"] = 0
            
    state["last_study_date"] = today.strftime("%Y-%m-%d")
    state["exercises_done_today"] += exercises_completed
    
    return state

def describe_changes(old, new):
    lines = []
    if old.get("week") != new.get("week"): 
        lines.append(f"📅 Week: {old.get('week')} → {new.get('week')}")
    if old.get("session") != new.get("session"): 
        lines.append(f"📖 Session: {old.get('session')} → {new.get('session')}")
    if old.get("ladder") != new.get("ladder"): 
        lines.append(f"🪜 Ladder step: {old.get('ladder', {}).get('step', 1)} → {new.get('ladder', {}).get('step', 1)}")
    
    old_mistakes = old.get("mistake_log", []) or []
    new_mistakes = new.get("mistake_log", []) or []
    for item in new_mistakes:
        if item not in old_mistakes:
            lines.append(f"❌ New mistake logged: *'{item.get('my_error', '')}'* → **'{item.get('correct', '')}'**")
            
    old_nouns = old.get("my_nouns", []) or []
    new_nouns = new.get("my_nouns", []) or []
    for item in new_nouns:
        if item not in old_nouns:
            art = item.get("article", "")
            n = item.get("noun", "")
            pl = item.get("plural", "")
            plural_text = f" (plural: {pl})" if pl else ""
            lines.append(f"📚 New noun added: **{art} {n}**{plural_text}")
            
    return lines

def save_reply_to_session(reply_text, state):
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    fname = f"{ts}_week{state.get('week', 'x')}_session{state.get('session', 'x')}.md"
    (SESSIONS_DIR / fname).write_text(reply_text, encoding="utf-8")
    return fname

def save_evaluation(eval_text, state):
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    fname = f"{ts}_week{state.get('week', 'x')}_evaluation.md"
    (EVALUATIONS_DIR / fname).write_text(eval_text, encoding="utf-8")
    return fname

def reset_all_progress():
    if STATE_FILE.exists(): STATE_FILE.unlink()
    for f in SESSIONS_DIR.glob("*"): f.unlink()
    for f in BACKUPS_DIR.glob("*"): f.unlink()
    for f in EVALUATIONS_DIR.glob("*"): f.unlink()