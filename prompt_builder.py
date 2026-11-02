import json
import re
from pathlib import Path
from state_manager import normalize_state

APP_DIR = Path(__file__).resolve().parent
PROMPT_FILE = APP_DIR / "course_prompt.md"

LESSON_START = "===LESSON START==="
LESSON_END = "===LESSON END==="
STATE_START = "===STATE START==="
STATE_END = "===STATE END==="
EXERCISES_START = "===EXERCISES START==="
EXERCISES_END = "===EXERCISES END==="

DEFAULT_PROMPT_TEXT = """# Role
You are my expert German tutor. I am following a structured course.
You are generating a structured Markdown file (`lesson_and_exercises.md`) that will be automatically parsed by a Python app. 

# Instructions
1. I will provide you with my current state (in JSON) and my week/session.
2. **TEACH FIRST:** You MUST write a clear, beginner-friendly explanation of the grammar rule I am currently studying (based on my `ladder.row`). Give 1-2 short examples in German.
3. **DIFFICULTY SCALING:** Look at my `ladder.step`. 
   - Steps 1-3: Short sentences.
   - Steps 4-7: Medium sentences.
   - Steps 8-10: Complex sentences.
4. **USE PREPOSITIONS:** Use prepositions that naturally trigger the case (e.g., für/durch for Accusative, mit/nach for Dative).
5. **MIXED GENDERS:** Mix masculine (der), feminine (die), neuter (das), and plural (die) nouns.
6. **HIDE THE CASE:** Do NOT write (Nominativ) or (Akkusativ) in the sentences.
7. **ADJECTIVE ENDINGS:** If the prompt includes "Include Adjective Endings: TRUE", put adjectives in front of the nouns and leave the article AND the adjective ending blank (e.g., `___ groß___ Hund`).
8. **STRICT FOCUS:** Look at my `ladder.row`. If it says "Definite", you MUST ONLY use definite articles. If it says "Indefinite", you MUST ONLY use indefinite articles. If it says "Mixed", mix them.

# Mode: Conversation Practice
If the prompt says `## Mode: CONVERSATION PRACTICE`, ignore the fill-in-the-blank rules. Instead:
1. Give me a conversational topic based on my Reading Material.
2. Output exactly ONE `paragraph` exercise type.

# Mode: Grammar Practice
If the prompt does NOT say Conversation Practice, output the exercises in a pipe-delimited format.
Format: type | question | nouns

# Output Format (STRICT FILE GENERATION)
You are creating a file. Output EXACTLY ONE fenced code block starting with ```markdown and ending with ```. Do NOT write anything outside this code block (no greetings, no explanations outside the block).

Inside the code block, use exactly these markers in this exact order:

===LESSON START===
(Your grammar explanation and examples go here)
===LESSON END===

===STATE START===
{ ...updated JSON... }
===STATE END===

===EXERCISES START===
blank | ___ groß___ Hund läuft. | Hund
paragraph | Schreibe einen Satz über das Kind. | 
===EXERCISES END===
"""

def extract_state_and_exercises(reply_text):
    # 1. Extract Lesson
    display_text = ""
    if LESSON_START in reply_text and LESSON_END in reply_text:
        l_start = reply_text.index(LESSON_START) + len(LESSON_START)
        l_end = reply_text.index(LESSON_END)
        display_text = reply_text[l_start:l_end].strip()
    else:
        if STATE_START in reply_text:
            display_text = reply_text[:reply_text.index(STATE_START)].strip()
        else:
            display_text = "No lesson provided."

    # 2. Extract State
    if STATE_START not in reply_text or STATE_END not in reply_text:
        raise ValueError("Missing state markers. Make sure you copied the AI's entire reply.")
    
    start = reply_text.index(STATE_START) + len(STATE_START)
    end = reply_text.index(STATE_END)
    json_block = reply_text[start:end].strip()
    
    if json_block.startswith("```json"): json_block = json_block[7:]
    if json_block.startswith("```"): json_block = json_block[3:]
    if json_block.endswith("```"): json_block = json_block[:-3]
    
    try:
        parsed_state = json.loads(json_block.strip())
    except Exception as e:
        raise ValueError(f"State JSON error: {e}")
    
    # 3. Extract Exercises
    exercises = []
    if EXERCISES_START in reply_text and EXERCISES_END in reply_text:
        e_start = reply_text.index(EXERCISES_START) + len(EXERCISES_START)
        e_end = reply_text.index(EXERCISES_END)
        e_block = reply_text[e_start:e_end].strip()
        
        if e_block.startswith("```text"): e_block = e_block[7:]
        if e_block.startswith("```"): e_block = e_block[3:]
        if e_block.endswith("```"): e_block = e_block[:-3]
        e_block = e_block.strip()

        for line in e_block.split('\n'):
            line = line.strip()
            if not line: continue
            
            if "|" in line:
                parts = line.split("|")
                ex_type = parts[0].strip().lower()
                question = parts[1].strip()
                nouns_str = parts[2].strip() if len(parts) > 2 else ""
                
                question = re.sub(r'(?i)\s*\((Nominativ|Akkusativ|Dativ|Genitiv|Nom|Akk|Dat|Gen)\)', '', question).strip()
                nouns = [n.strip() for n in nouns_str.split(",")] if nouns_str else []
                
                exercises.append({"type": ex_type, "question": question, "nouns": nouns})
            else:
                exercises.append({"type": "paragraph", "question": line, "nouns": []})

    return normalize_state(parsed_state), exercises, display_text

def build_prompt(state, phrases, transcript, reading, mode):
    parts = []
    if PROMPT_FILE.exists():
        parts.append(PROMPT_FILE.read_text(encoding="utf-8").strip())
    else:
        parts.append(DEFAULT_PROMPT_TEXT)
        
    parts.append(f"Week {state['week']}, Session {state['session']}, {state['ladder']['row']} step {state['ladder']['step']}")
    
    if mode == "conversation_practice":
        parts.append("## Mode: CONVERSATION PRACTICE")
        if reading and reading.strip():
            parts.append(f"## Reading Material to base the topic on\n{reading.strip()}")
    elif mode == "quick_grammar":
        parts.append("## Mode: QUICK GRAMMAR PRACTICE\nIgnore the book. Generate exercises using common everyday German vocabulary.")
    else:
        if reading and reading.strip():
            parts.append(f"## Reading Material\n{reading.strip()}\n**CRITICAL:** Base the exercises on the vocabulary from this text.")
    
    parts.append(STATE_START)
    parts.append(json.dumps(state, indent=2, ensure_ascii=False))
    parts.append(STATE_END)
    
    if phrases and phrases.strip(): parts.append(f"## My collected phrases\n{phrases.strip()}")
    if transcript and transcript.strip(): parts.append(f"## My speech transcript\n{transcript.strip()}")
    
    return "\n\n".join(parts)

def build_answer_prompt(state, exercises, part1_answers, part2_genders):
    parts = []
    parts.append("I have completed the exercises you gave me.")
    
    combined_text = ""
    idx = 0
    for i, ex in enumerate(exercises):
        q = ex.get("question", "")
        if ex["type"] == "blank":
            answers_for_this = part1_answers[idx : idx + len(ex["nouns"])]
            idx += len(ex["nouns"])
            ans_str = ", ".join(answers_for_this)
            combined_text += f"Sentence {i+1}: {q}\nMy Article Answers: {ans_str}\n\n"
        else:
            combined_text += f"Topic/Prompt: {q}\nMy Response: {part1_answers[idx]}\n\n"
            idx += 1
            
    parts.append(f"## My Answers\n{combined_text}")
    
    if part2_genders:
        combined_text_genders = ", ".join(part2_genders)
        parts.append(f"## My Gender Answers\n{combined_text_genders}\n")
        
    parts.append("""# Instructions for your reply:
1. **Grade my answers:** If it's a conversation, correct my grammar and vocabulary. If it's a fill-in-the-blank, tell me what's right and wrong.
2. **Log Mistakes:** If I made a mistake in my written sentences, take the exact incorrect sentence, fix it, and add it to the `mistake_log` in the JSON. Use the format: `{"pattern": "conversation", "my_error": "...", "correct": "...", "count": 1}`.
3. **Update State:** Increment `ladder.step` by 1. If I reach 10, advance the `session` (A->B->C) and reset step to 1.
4. **Test:** Generate the next set of exercises or the next conversation topic.

# Output Format (STRICT FILE GENERATION)
You are creating a file. Output EXACTLY ONE fenced code block starting with ```markdown and ending with ```. Do NOT write anything outside this code block.

Inside the code block, use exactly these markers:

===LESSON START===
(Write your grading feedback and grammar explanation for the next step here)
===LESSON END===

===STATE START===
{ ...updated JSON... }
===STATE END===

===EXERCISES START===
blank | ... | 
===EXERCISES END===
""")
    parts.append(f"Week {state['week']}, Session {state['session']}, {state['ladder']['row']} step {state['ladder']['step']}")
    parts.append(STATE_START)
    parts.append(json.dumps(state, indent=2, ensure_ascii=False))
    parts.append(STATE_END)
    return "\n\n".join(parts)

def build_evaluation_prompt(state):
    parts = []
    parts.append("I have finished my daily study session. Here is my current state:")
    parts.append(STATE_START)
    parts.append(json.dumps(state, indent=2, ensure_ascii=False))
    parts.append(STATE_END)
    
    parts.append("""# Instructions for your reply:
Please generate a **Printable Study Report** in Markdown format.

Use exactly this structure:
# Daily Study Report: [Date]
## 1. What We Practiced
(Write a brief 2-sentence summary of my current `ladder.row` grammar focus.)

## 2. Mistakes to Review
(List the exact sentences I got wrong from my `mistake_log`. Show the incorrect version in *italics* and the correct version in **bold**.)

## 3. Flashcards (Cut this out and study)
* **Q:** [Question about a noun/gender I struggled with] -> **A:** [Correct answer]
* **Q:** [Question about a case rule] -> **A:** [Correct answer]
* **Q:** [Question about a verb/preposition] -> **A:** [Correct answer]

Keep it clean, encouraging, and easy to read. Do NOT include any JSON in this reply. Just the Markdown report.
""")
    return "\n\n".join(parts)