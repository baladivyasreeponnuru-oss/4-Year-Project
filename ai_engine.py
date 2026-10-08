from sentence_transformers import SentenceTransformer, util
bloom_verbs = {
    "Remember": ["define", "list", "state", "name", "recall", "identify"],
    "Understand": ["explain", "describe", "summarize", "discuss", "classify"],
    "Apply": ["solve", "calculate", "demonstrate", "use", "compute"],
    "Analyze": ["compare", "differentiate", "analyze", "examine", "distinguish"],
    "Evaluate": ["justify", "evaluate", "argue", "critique", "assess"],
    "Create": ["design", "create", "develop", "formulate", "construct"]
}

def classify_bloom(question_text):
    text = question_text.lower()
    for level, verbs in bloom_verbs.items():
        for verb in verbs:
            if verb in text:
                return level
    return "Understand"  # default fallback if no verb matches
model = SentenceTransformer('all-MiniLM-L6-v2')
def predict_difficulty(question_text, marks=None):
    word_count = len(question_text.split())
    text = question_text.lower()
    
    hard_keywords = ["derive", "prove", "optimize", "design", "justify", "evaluate"]
    easy_keywords = ["define", "state", "list", "name", "what is"]

    if marks is not None and marks >= 10:
        if any(k in text for k in hard_keywords) or word_count > 15:
            return "Hard"
        else:
            return "Medium"
    
    if any(k in text for k in hard_keywords) or word_count > 20:
        return "Hard"
    elif any(k in text for k in easy_keywords) or word_count < 8:
        return "Easy"
    else:
        return "Medium"

def check_duplicate(new_question, existing_questions, threshold=0.85):
    if not existing_questions:
        return False, None
    
    new_emb = model.encode(new_question, convert_to_tensor=True)
    existing_embs = model.encode(existing_questions, convert_to_tensor=True)
    
    similarities = util.cos_sim(new_emb, existing_embs)[0]
    
    max_score = similarities.max().item()
    max_index = similarities.argmax().item()
    
    if max_score > threshold:
        return True, existing_questions[max_index]
    return False, None

if __name__ == '__main__':
    test_questions = [
        "Define RAM",
        "Explain the working of a CPU in detail",
        "Design an algorithm to optimize memory allocation",
        "What is RAM?"
    ]
    
    existing = ["Define RAM", "Explain the working of a CPU", "What is cache memory?"]

def generate_paper(subject_id, questions_needed, db, Question):
    selected_questions = []
    part_a_result = []
    part_b_result = []

    for requirement in questions_needed:
        marks = requirement['marks']
        count_needed = requirement['count']
        pick_pairs = requirement.get('with_alternative', False)

        candidates = Question.query.filter_by(
            subject_id=subject_id,
            marks=marks,
            is_duplicate=False
        ).all()

        by_unit = {}
        for q in candidates:
            by_unit.setdefault(q.unit_id, []).append(q)

        units = list(by_unit.keys())
        picked_main = []
        picked_alt = []
        unit_index = 0

        needed_per_unit = 2 if pick_pairs else 1

        while len(picked_main) < count_needed and any(len(by_unit[u]) >= 1 for u in units):
            unit = units[unit_index % len(units)]
            if len(by_unit[unit]) >= needed_per_unit:
                picked_main.append(by_unit[unit].pop(0))
                if pick_pairs:
                    picked_alt.append(by_unit[unit].pop(0))
                else:
                    picked_alt.append(None)
            elif len(by_unit[unit]) == 1 and not pick_pairs:
                picked_main.append(by_unit[unit].pop(0))
                picked_alt.append(None)
            unit_index += 1
            if unit_index > len(units) * 20:
                break

        if pick_pairs:
            for main_q, alt_q in zip(picked_main, picked_alt):
                part_b_result.append({"main": main_q, "alt": alt_q})
        else:
            part_a_result.extend(picked_main)

        selected_questions.extend(picked_main)
        selected_questions.extend([a for a in picked_alt if a])

    return selected_questions, part_a_result, part_b_result
import re as _re

import random as _random

def generate_template_questions(unit_name, marks, topics=None):
    topic = _re.sub(r'UNIT\s*\d+[:\-]?\s*', '', unit_name, flags=_re.IGNORECASE).strip()

    if topics:
        topic_list = [t.strip() for t in topics.split(',') if t.strip()]
        if topic_list:
            topic = _random.choice(topic_list)

    templates_low = [f"Define {topic}.", f"What is {topic}?", f"List the key features of {topic}."]
    templates_high = [f"Explain {topic} in detail.", f"Discuss the significance of {topic} with examples.",
                       f"Describe the working principles of {topic}."]

    return templates_low if marks < 10 else templates_high

def generate_mixed_paper(subject_id, questions_needed, db, Question, SyllabusUnit):
    part_a_result = []
    part_b_result = []
    all_selected = []

    for requirement in questions_needed:
        marks = requirement['marks']
        count_needed = requirement['count']
        mix_with_syllabus = requirement.get('mix_with_syllabus', False)

        candidates = Question.query.filter_by(
            subject_id=subject_id, marks=marks, is_duplicate=False
        ).all()

        by_unit = {}
        for q in candidates:
            by_unit.setdefault(q.unit_id, []).append(q)

        units = SyllabusUnit.query.filter_by(subject_id=subject_id).all()
        picked = 0

        for unit in units:
            if picked >= count_needed:
                break
            unit_questions = by_unit.get(unit.id, [])
            if not unit_questions:
                continue

            import random
            main_q = unit_questions.pop(random.randrange(len(unit_questions)))
            all_selected.append(main_q)

            if mix_with_syllabus:
                templates = generate_template_questions(unit.unit_name, marks, unit.topics)
                alt_text = templates[0] if templates else None
                entry = {
                    "question": main_q.question_text,
                    "marks": main_q.marks,
                    "co": main_q.id
                }
                if alt_text:
                    entry['alt'] = {"question": alt_text, "marks": marks, "co": main_q.id}
                part_b_result.append(entry)
            else:
                part_a_result.append({
                    "question": main_q.question_text,
                    "marks": main_q.marks,
                    "co": main_q.id
                })
            picked += 1

    return all_selected, part_a_result, part_b_result

import random as _rnd2

def generate_mcqs_from_syllabus(subject_id, db, SyllabusUnit, target_total=30):
    """
    Always generates exactly `target_total` MCQs (bits), cycling through
    units round-robin, as long as the subject has at least 4 distinct
    syllabus topics in total. Wrong-option candidates are drawn from ALL
    topics (not just other units) so a unit is never skipped just because
    its sibling units are thin -- this is what previously made the count
    swing between ~20 and ~30 depending on syllabus shape.
    """
    units = SyllabusUnit.query.filter_by(subject_id=subject_id).all()
    unit_topics = {}
    all_topics = []
    for u in units:
        topics = [t.strip() for t in (u.topics or '').split(',') if t.strip()]
        if topics:
            unit_topics[u.unit_name] = topics
            all_topics.extend(topics)

    unit_names = list(unit_topics.keys())
    if not unit_names or len(set(all_topics)) < 4:
        return []

    mcqs = []
    idx = 0
    attempts = 0
    max_attempts = target_total * 20  # safety valve against infinite loops

    while len(mcqs) < target_total and attempts < max_attempts:
        attempts += 1
        unit_name = unit_names[idx % len(unit_names)]
        idx += 1

        correct_pool = unit_topics[unit_name]
        correct = _rnd2.choice(correct_pool)

        wrong_candidates = [t for t in all_topics if t != correct]
        if len(wrong_candidates) < 3:
            continue

        wrongs = _rnd2.sample(wrong_candidates, 3)
        options = wrongs + [correct]
        _rnd2.shuffle(options)
        correct_letter = ['A', 'B', 'C', 'D'][options.index(correct)]

        clean_unit = unit_name.split(':', 1)[-1].strip() if ':' in unit_name else unit_name
        mcqs.append({
            "question_text": f"Which of the following topics belongs to {clean_unit}?",
            "option_a": options[0], "option_b": options[1],
            "option_c": options[2], "option_d": options[3],
            "correct_option": correct_letter
        })

    return mcqs


# ============================================================
# Real AI-generated MCQs (uses OpenAI) — replaces the topic-
# matching generator above with genuine theory-based questions.
# ============================================================
import os
import json


def generate_mcqs_with_ai(subject_id, subject_name, db, SyllabusUnit, target_total=30, questions_per_call=5):
    """
    Generates real, theory-based MCQs (not topic-name-matching ones) by asking
    an LLM (Google Gemini) to write genuine conceptual questions about each
    syllabus unit's topics, using the model's own subject-matter knowledge.

    Requires the GEMINI_API_KEY environment variable to be set (e.g. via a
    local .env file loaded with python-dotenv). Raises ValueError (with the
    real underlying reason) on any failure, so the error reaches the browser
    directly instead of being swallowed silently.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. Add it to a .env file in the project "
            "folder (GEMINI_API_KEY=...) and restart the server."
        )

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash-lite")
    except Exception as e:
        raise ValueError(f"Could not create Gemini client: {type(e).__name__}: {e}")

    units = SyllabusUnit.query.filter_by(subject_id=subject_id).all()
    unit_data = []
    for u in units:
        topics = [t.strip() for t in (u.topics or '').split(',') if t.strip()]
        if topics:
            unit_data.append((u.unit_name, topics))

    if not unit_data:
        raise ValueError("No syllabus units with topics found for this subject.")

    mcqs = []
    idx = 0
    attempts = 0
    max_attempts = target_total * 4 + 20
    last_error = None

    while len(mcqs) < target_total and attempts < max_attempts:
        attempts += 1
        unit_name, topics = unit_data[idx % len(unit_data)]
        idx += 1
        n = min(questions_per_call, target_total - len(mcqs))
        clean_unit = unit_name.split(':', 1)[-1].strip() if ':' in unit_name else unit_name

        prompt = (
            f"You are writing simple, short multiple-choice questions (\"bits\") for a basic college "
            f"internal exam on the subject \"{subject_name}\", unit \"{clean_unit}\".\n"
            f"Topics covered in this unit: {', '.join(topics)}.\n\n"
            f"Generate exactly {n} distinct questions that test basic factual/conceptual recall.\n"
            f"STRICT STYLE RULES:\n"
            f"- Prefer fill-in-the-blank style statements (e.g. 'The ___ algorithm is used for...') "
            f"or short direct questions (e.g. 'Which of the following is a ...?').\n"
            f"- Question stem: ONE short sentence only. No scenarios, no stories, no worked examples.\n"
            f"- Options: EACH option must be a SINGLE WORD or a SINGLE TECHNICAL TERM ONLY "
            f"(e.g. 'Stack', 'O(log n)', 'Perceptron', 'Overfitting'). Never a phrase, never a "
            f"sentence, never more than 3 words.\n"
            f"- Keep difficulty at a basic undergraduate level.\n"
            f"- Do NOT ask which topic name belongs to this unit.\n\n"
            f"Example of the exact style expected:\n"
            f'{{"question_text": "Which data structure uses FIFO order?", "option_a": "Stack", '
            f'"option_b": "Queue", "option_c": "Tree", "option_d": "Graph", "correct_option": "B"}}\n'
            f'{{"question_text": "The time complexity of binary search is ___.", "option_a": "O(n)", '
            f'"option_b": "O(log n)", "option_c": "O(n^2)", "option_d": "O(1)", "correct_option": "B"}}\n\n'
            f"Each question must have exactly 4 options with only one correct answer.\n\n"
            f"Return ONLY a valid JSON array, no other text, no markdown fences, in this exact format:\n"
            f'[{{"question_text": "...", "option_a": "...", "option_b": "...", "option_c": "...", '
            f'"option_d": "...", "correct_option": "A"}}]'
        )

        try:
            response = model.generate_content(prompt)
            raw = response.text.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            batch = json.loads(raw)

            for item in batch:
                required = ["question_text", "option_a", "option_b", "option_c", "option_d", "correct_option"]
                if all(k in item for k in required) and str(item["correct_option"]).upper() in ["A", "B", "C", "D"]:
                    mcqs.append({
                        "question_text": item["question_text"],
                        "option_a": item["option_a"],
                        "option_b": item["option_b"],
                        "option_c": item["option_c"],
                        "option_d": item["option_d"],
                        "correct_option": str(item["correct_option"]).upper()
                    })
                if len(mcqs) >= target_total:
                    break

            if len(batch) < n:
                print(f"[generate_mcqs_with_ai] Unit '{clean_unit}': asked for {n}, Gemini returned only {len(batch)}.")
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            print(f"[generate_mcqs_with_ai] Gemini call failed for unit '{clean_unit}': {last_error}")
            continue

    if not mcqs and last_error:
        raise ValueError(f"Gemini generation failed: {last_error}")

    if len(mcqs) < target_total:
        print(f"[generate_mcqs_with_ai] Only generated {len(mcqs)} of {target_total} requested bits after {attempts} attempts.")

    return mcqs[:target_total]