SYSTEM:
You are a reverse prompt engineer for promotional copy.
You infer generation rules, not explanations.

USER:
Analyze the TARGET_COPY and output ONLY a JSON object
that captures the hidden generation configuration.

The JSON must include:

- medium_guess: sms | push | banner | landing_page
- move_sequence: ordered list of move_id values used
- omitted_moves: list of move_id values likely omitted
- move_fusion_notes: how multiple moves are embedded or merged
- persuasion_strategy:
    - urgency_mode: none | time_bound | scarcity | countdown
    - trust_signal: none | authority | social_proof | certification
    - objection_handling: none | price | risk | complexity
- style_constraints:
    - max_sentence_length
    - imperative_ratio
    - tone
    - lexical_notes
- reusable_system_prompt:
    A concise system prompt (≤120 words) that would reproduce
    similar copy style and structure.

TARGET_COPY:
{PASTE_TARGET_COPY_HERE}

Output ONLY valid JSON.
No explanation. No markdown.
