import copy
import streamlit as st
import pandas as pd
from pathlib import Path
import re

import epub_parser
import state_manager
import prompt_builder

st.set_page_config(page_title="German course helper", page_icon="📓", layout="wide")

# --- CSS FOR WIDE SCREEN & STYLED INPUTS ---
st.markdown("""
<style>
    .block-container {
        max-width: 100% !important;
        padding-left: 1.5rem !important;
        padding-right: 1.5rem !important;
        padding-top: 2rem !important;
    }
    /* Style text areas to look like clean input lines but allow Enter for new lines */
    div[data-baseweb="textarea"] {
        border-bottom: 2px solid #ff4b4b !important; 
        background-color: transparent !important;
        min-height: 60px !important;
    }
    div[data-baseweb="textarea"] textarea {
        text-align: center !important;
        font-weight: bold !important;
        padding-top: 10px !important;
    }
    [data-testid="stSidebar"] {
        background-color: #1a1c24; 
        padding-top: 2rem;
    }
</style>
""", unsafe_allow_html=True)

state = state_manager.normalize_state(state_manager.load_state())

if "batch_id" not in st.session_state:
    st.session_state.batch_id = 0

# ---------- SIDEBAR ----------
with st.sidebar:
    st.markdown("### 📓 German Helper")
    st.caption("Daily dashboard")
    st.divider()

    st.markdown(f"**Week {state['week']}, Session {state['session']}**")
    st.markdown(f"Focus: `{state['ladder']['row']}`")
    
    streak = state.get("streak", 0)
    st.metric(label="Study Streak", value=f"🔥 {streak} Day{'s' if streak != 1 else ''}")

    done = state.get("exercises_done_today", 0)
    goal = state.get("daily_goal", 10)
    st.markdown(f"**Today's Goal:** {done} / {goal} exercises")
    st.progress(min(done / goal, 1.0))
    
    st.divider()

    st.markdown("**Settings**")
    prompt_week = st.number_input("Week", min_value=1, max_value=100, value=int(state.get("week", 1)), step=1)
    
    session_options = ["A", "B", "C", "Diagnostic"]
    if state["session"] not in session_options: session_options.insert(0, state["session"])
    prompt_session = st.selectbox("Session", session_options, index=session_options.index(state["session"]))
    
    row_options = [
        "1. Akk - Definite (den/die/das)",
        "2. Akk - Indefinite (einen/eine/ein)",
        "3. Akk - Mixed",
        "4. Dat - Definite (dem/der/den)",
        "5. Dat - Indefinite (einem/einer/einem)",
        "6. Dat - Mixed",
        "7. Gen - Definite (des/der)",
        "8. Gen - Indefinite (eines/einer)",
        "9. Gen - Mixed",
        "10. Master Mix (All Cases)"
    ]
    if state["ladder"]["row"] not in row_options: row_options.insert(0, state["ladder"]["row"])
    prompt_row = st.selectbox("Grammar Focus", row_options, index=row_options.index(state["ladder"]["row"]))
    
    test_adjectives = st.checkbox("Include Adjective Endings (-e, -en, -es)", value=False)
    
    step_options = list(range(1, 11))
    step_num = int(state["ladder"]["step"])
    if step_num not in step_options: step_options.append(step_num); step_options.sort()
    prompt_step = st.selectbox("Ladder step", step_options, index=step_options.index(step_num))

    st.divider()
    
    mode = st.radio("Select Mode:", ["Reading Grammar", "Quick Grammar", "Conversation Practice"], label_visibility="collapsed")

    extracted_text = ""
    if mode in ["Reading Grammar", "Conversation Practice"]:
        st.divider()
        st.markdown("**📚 EPUB Reader**")
        uploaded_epub = st.file_uploader("Upload an EPUB", type=["epub"], label_visibility="collapsed")
        
        if uploaded_epub is not None:
            if "epub_chapters" not in st.session_state or st.session_state.get("epub_name") != uploaded_epub.name:
                with st.spinner("Parsing EPUB..."):
                    st.session_state.epub_chapters = epub_parser.parse_epub(uploaded_epub)
                    st.session_state.epub_name = uploaded_epub.name
            
            chapters = st.session_state.epub_chapters
            if chapters and "Error" not in chapters:
                selected_chapter = st.selectbox("Select Chapter", list(chapters.keys()))
                raw_text = chapters[selected_chapter]
                load_whole = st.checkbox("Load entire chapter", value=False)
                
                if load_whole:
                    extracted_text = raw_text
                else:
                    char_limit = st.number_input("Chars per part", min_value=500, max_value=30000, value=4000, step=500)
                    chunks = epub_parser.chunk_text(raw_text, chunk_size=char_limit)
                    if len(chunks) > 1:
                        chunk_options = [f"Part {i+1} (of {len(chunks)})" for i in range(len(chunks))]
                        selected_chunk = st.selectbox("Select Part", chunk_options)
                        extracted_text = chunks[chunk_options.index(selected_chunk)]
                    else:
                        extracted_text = chunks[0]
            else:
                st.error("Could not parse EPUB.")
        else:
            st.info("Upload an EPUB or paste text manually.")

    st.divider()
    if st.button("🗑️ Reset Test Data", use_container_width=True):
        state_manager.reset_all_progress()
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.success("Wiped!"); st.rerun()

# ---------- MAIN AREA ----------
st.title("Workspace")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["1. Start session", "2. Worksheet", "3. My progress", "4. 📝 Evaluation", "❓ Guide"])

# ---------- TAB 1 ----------
with tab1:
    if not prompt_builder.PROMPT_FILE.exists():
        st.warning("`course_prompt.md` was not found.")
        if st.button("Create starter course_prompt.md", type="primary"):
            prompt_builder.PROMPT_FILE.write_text(prompt_builder.DEFAULT_PROMPT_TEXT, encoding="utf-8")
            st.success("Created course_prompt.md!"); st.rerun()

    reading_text = ""
    if mode in ["Reading Grammar", "Conversation Practice"]:
        st.subheader("Study Material")
        reading_text = st.text_area("Reading Material (Review and edit before building prompt)", value=extracted_text, height=150)
    elif mode == "Quick Grammar":
        st.info("Quick Grammar mode: No book needed. The AI will generate exercises based on your grammar focus.")

    phrases = st.text_area("My collected phrases (Optional)", height=80)
    transcript = st.text_area("Speech transcript (Optional)", height=80)

    if st.button("Build prompt", type="primary"):
        p_state = copy.deepcopy(state)
        p_state["week"] = prompt_week
        p_state["session"] = prompt_session
        p_state["ladder"] = {"row": prompt_row, "step": prompt_step}
        
        extra = "\n## Include Adjective Endings: TRUE" if test_adjectives else ""
        st.session_state.built_prompt = prompt_builder.build_prompt(
            p_state, phrases, transcript, reading_text + extra, 
            mode=mode.lower().replace(" ", "_")
        )

    if st.session_state.get("built_prompt"):
        st.subheader("Prompt — copy this into the tutor chat")
        st.code(st.session_state.built_prompt, language="markdown")


# ---------- TAB 2 (WORKSHEET) ----------
with tab2:
    st.markdown("**Step 1: Paste the AI's reply**")
    reply_text = st.text_area("Paste the full reply from the AI here.", height=150, label_visibility="collapsed", placeholder="Paste the AI's full reply here…")
    
    if st.button("Read & Save Reply", type="primary"):
        try:
            parsed, exercises, display_text = prompt_builder.extract_state_and_exercises(reply_text)
            
            num_exercises = len(exercises)
            parsed = state_manager.update_streak_and_daily_goal(parsed, exercises_completed=num_exercises)
            
            changes = state_manager.describe_changes(state, parsed)
            state_manager.save_state(parsed, backup=True)
            fname = state_manager.save_reply_to_session(reply_text, parsed)
            
            st.session_state.last_ai_text = display_text if display_text.strip() else " "
            st.session_state.current_exercises = exercises
            st.session_state.last_changes = changes if changes else ["No progress changes detected."]
            
            st.session_state.batch_id += 1
            
            st.success(f"Progress saved! Session file: {fname}")
            st.rerun()
        except Exception as e:
            st.error("Could not read the reply. Error: " + str(e))

    if "current_exercises" in st.session_state:
        st.divider()
        
        with st.expander("📊 Grammar Cheat Sheet (Click to view tables)", expanded=False):
            st.markdown("### Definite Articles")
            st.markdown("""
            | Case | Masculine | Feminine | Neuter | Plural |
            | :--- | :--- | :--- | :--- | :--- |
            | **Nominative** | der | die | das | die |
            | **Accusative** | den | die | das | die |
            | **Dative** | dem | der | dem | den |
            | **Genitive** | des | der | des | der |
            """)
            st.markdown("### Indefinite / Possessive Articles")
            st.markdown("""
            | Case | Masculine | Feminine | Neuter | Plural |
            | :--- | :--- | :--- | :--- | :--- |
            | **Nominative** | ein | eine | ein | meine |
            | **Accusative** | einen | eine | ein | meine |
            | **Dative** | einem | einer | einem | meinen |
            | **Genitive** | eines | einer | eines | meiner |
            """)
            st.markdown("### Prepositions (Triggers)")
            st.markdown("""
            *   **Accusative:** durch, für, gegen, ohne, um
            *   **Dative:** aus, bei, mit, nach, seit, von, zu
            *   **Genitive:** wegen, während, trotz
            """)

        with st.expander("See what changed in your progress", expanded=False):
            for line in st.session_state.get("last_changes", []): st.markdown("- " + line)
                
        if st.session_state.get("last_ai_text", "").strip():
            st.markdown("### 📖 Lesson & Theory")
            with st.container(border=True):
                st.markdown(st.session_state.last_ai_text)
            st.divider()
        else:
            st.warning("⚠️ The AI did not provide a grammar lesson this time. It jumped straight to the exercises.")
            st.divider()
        
        exercises = st.session_state.current_exercises
        b_id = st.session_state.batch_id
        
        if exercises:
            with st.form("worksheet_form"):
                st.markdown("### Part 1: Fill in the Articles / Answer the prompt")
                
                part1_answers = [] 
                all_nouns = [] 
                
                for i, ex in enumerate(exercises):
                    ex_type = ex.get("type", "paragraph")
                    question = ex.get("question", "").strip()
                    
                    if not question: continue

                    if ex_type == "blank":
                        parts = question.split("___")
                        num_blanks = len(parts) - 1
                        
                        if num_blanks > 0:
                            weights = []
                            for j in range(len(parts)):
                                weights.append(5) 
                                if j < num_blanks: weights.append(1) 
                            
                            cols = st.columns(weights)
                            col_idx = 0
                            for j, part in enumerate(parts):
                                cols[col_idx].markdown(f"<div style='padding-top: 10px; font-size: 1.1rem;'>{part}</div>", unsafe_allow_html=True)
                                col_idx += 1
                                
                                if j < num_blanks:
                                    ans = cols[col_idx].text_area(f"Blank {i}.{j}", key=f"ans_{b_id}_{i}_{j}", label_visibility="collapsed", placeholder="...", height=68)
                                    col_idx += 1
                                    part1_answers.append(ans)
                            
                            for n in ex.get("nouns", []):
                                all_nouns.append(n)
                            st.write("") 
                            
                    elif ex_type == "paragraph":
                        st.markdown(f"**{question}**")
                        ans = st.text_area(f"Answer {i}", key=f"ans_{b_id}_{i}", height=100, label_visibility="collapsed", placeholder="Write your answer here...")
                        part1_answers.append(ans)
                        st.write("")
                
                if all_nouns:
                    st.divider()
                    st.markdown("### Part 2: What is the gender of the nouns?")
                    
                    part2_genders = []
                    cols = st.columns(min(len(all_nouns), 4)) 
                    for idx, noun in enumerate(all_nouns):
                        col = cols[idx % 4]
                        with col:
                            st.markdown(f"**{idx+1}. {noun}**")
                            gen_ans = st.text_area(f"Gender for {noun} {idx}", key=f"gen_{b_id}_{idx}", placeholder="der/die/das", label_visibility="collapsed", height=68)
                            part2_genders.append(gen_ans)
                else:
                    part2_genders = []
                
                st.write("")
                submitted = st.form_submit_button("Submit Answers", type="primary")
                
            if submitted:
                has_answer = any(ans.strip() for ans in part1_answers)
                
                if not has_answer:
                    st.error("Please answer at least one exercise first.")
                else:
                    current_state = state_manager.load_state()
                    st.session_state.next_prompt = prompt_builder.build_answer_prompt(current_state, exercises, part1_answers, part2_genders)
                    st.success("Answers submitted! Copy the prompt below.")
                    
            if st.session_state.get("next_prompt"):
                st.markdown("### Step 3: Build the next prompt")
                st.code(st.session_state.next_prompt, language="markdown")

# ---------- TAB 3 (MY PROGRESS) ----------
with tab3:
    st.subheader("Edit your progress")
    
    def list_to_df(data, default_cols):
        if not data: return pd.DataFrame(columns=default_cols)
        df = pd.DataFrame(data)
        for col in default_cols:
            if col not in df.columns: df[col] = None
        return df

    def df_to_list(df):
        clean_df = df.dropna(how="all")
        return clean_df.where(pd.notnull(clean_df), None).to_dict(orient="records")

    df_mistakes = list_to_df(state.get("mistake_log", []), ["pattern", "my_error", "correct", "count", "mode", "streak"])
    df_nouns = list_to_df(state.get("my_nouns", []), ["noun", "article", "plural", "translation"])
    df_baseline = list_to_df(state.get("baseline", []), ["structure", "initial_errors", "example"])

    st.markdown("**Mistake Log**")
    edited_mistakes = st.data_editor(df_mistakes, num_rows="dynamic", use_container_width=True)
    st.markdown("**My Nouns**")
    edited_nouns = st.data_editor(df_nouns, num_rows="dynamic", use_container_width=True)
    st.markdown("**Baseline**")
    edited_baseline = st.data_editor(df_baseline, num_rows="dynamic", use_container_width=True)
    
    st.markdown("**Speaking Plan**")
    plan_text = "\n".join(state.get("speaking_plan", []))
    edited_plan = st.text_area("One plan item per line", value=plan_text, height=150)

    if st.button("Save progress changes", type="primary"):
        new_state = copy.deepcopy(state)
        new_state["mistake_log"] = df_to_list(edited_mistakes)
        new_state["my_nouns"] = df_to_list(edited_nouns)
        new_state["baseline"] = df_to_list(edited_baseline)
        new_state["speaking_plan"] = [line for line in edited_plan.split("\n")]
        state_manager.save_state(new_state, backup=True)
        st.success("Progress saved and backed up."); st.rerun()

    st.divider()
    st.subheader("⚠️ Danger Zone")
    confirm_reset = st.checkbox("Yes, I want to delete all my progress and start fresh.")
    if st.button("Delete All Progress", disabled=not confirm_reset):
        state_manager.reset_all_progress()
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.success("All progress deleted."); st.rerun()

# ---------- TAB 4 (EVALUATION) ----------
with tab4:
    st.subheader("📝 Daily Evaluation")
    
    if state.get("exercises_done_today", 0) >= state.get("daily_goal", 10):
        st.success("🎉 You've reached your daily goal! Great job today.")
    else:
        st.info(f"You've completed {state.get('exercises_done_today', 0)} out of {state.get('daily_goal', 10)} exercises today.")

    st.markdown("### Today's Mistakes")
    if state.get("mistake_log"):
        df = pd.DataFrame(state["mistake_log"])
        st.dataframe(df, use_container_width=True)
    else:
        st.write("No mistakes logged yet. Keep up the good work!")

    st.divider()
    st.markdown("### Generate Study Report")
    
    if st.button("Build Report Prompt", type="primary"):
        st.session_state.review_prompt = prompt_builder.build_evaluation_prompt(state)
        
    if st.session_state.get("review_prompt"):
        st.code(st.session_state.review_prompt, language="markdown")
        
        st.divider()
        st.markdown("### 📥 Import Study Report")
        report_text = st.text_area("Paste the AI's report here:", height=200, placeholder="# Daily Study Report...")
        
        if report_text:
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="⬇️ Download as Markdown (.md)",
                    data=report_text,
                    file_name=f"german_study_report_{state['last_study_date']}.md",
                    mime="text/markdown",
                    type="secondary",
                    use_container_width=True
                )
            with col2:
                if st.button("💾 Save to History", type="primary", use_container_width=True):
                    fname = state_manager.save_evaluation(report_text, state)
                    st.success(f"Saved! ({fname})")
            
            if st.checkbox("🖨️ Show Print Preview (Light Mode)"):
                def md_to_html(md):
                    md = re.sub(r'^# (.*?)$', r'<h1 style="color: black; margin-bottom: 1rem;">\1</h1>', md, flags=re.MULTILINE)
                    md = re.sub(r'^## (.*?)$', r'<h2 style="color: black; margin-top: 1.5rem; margin-bottom: 0.5rem;">\1</h2>', md, flags=re.MULTILINE)
                    md = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', md)
                    md = re.sub(r'\*(.*?)\*', r'<em>\1</em>', md)
                    md = md.replace('\n', '<br>')
                    return md
                
                html_report = md_to_html(report_text)
                st.markdown(f"""
                <div style="background-color: white; color: black; padding: 40px; border-radius: 8px; font-family: Georgia, serif; line-height: 1.6; border: 1px solid #ddd; margin-top: 20px;">
                    {html_report}
                </div>
                """, unsafe_allow_html=True)
                st.caption("Press Ctrl + P (or Cmd + P) to print this page or save it as a PDF.")

    st.divider()
    st.markdown("### 📚 Past Evaluations")
    eval_files = sorted(state_manager.EVALUATIONS_DIR.glob("*.md"), reverse=True)
    
    if not eval_files:
        st.info("No saved evaluations yet. Generate a report above and click 'Save to History'.")
    else:
        selected_eval = st.selectbox("Select a saved evaluation to view", [f.name for f in eval_files])
        if selected_eval:
            past_text = (state_manager.EVALUATIONS_DIR / selected_eval).read_text(encoding="utf-8")
            with st.expander("View Report", expanded=True):
                st.markdown(past_text)

# ---------- TAB 5 (GUIDE) ----------
with tab5:
    st.subheader("How to use the App")
    st.markdown("""
    **The Daily Loop:**
    1. **Sidebar:** Set your week, grammar focus, and toggle adjective endings if desired.
    2. **Tab 1:** Click *Build prompt* and paste it to the AI.
    3. **Tab 2:** Paste the AI's full reply. Fill in Part 1 and Part 2 (if applicable).
    4. Click *Submit Answers*. Copy the generated prompt, paste it to the AI, and get graded.
    5. **Tab 4:** Generate a "Review Prompt", paste the AI's response, and click *Save to History* for a printable study report.
    """)