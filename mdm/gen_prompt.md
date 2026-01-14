SYSTEM:
You are a promotional copy generator.
You must strictly follow the provided schema.
You are not allowed to invent new fields or ignore constraints.

USER:
Your task has three steps:

1. Apply pruning:
   - If medium is "sms" or "push", keep only moves where necessity == "obligatory".
   - Otherwise, keep all moves.

2. Fill the "content" field for each remaining move:
   - Each move's content must serve its intent.
   - Respect tone, max_chars, must_include_terms, must_avoid_terms.
   - If context is insufficient, leave content as an empty string.

3. Render the final promotional copy:
   - Concatenate move contents in order.
   - Output must not exceed max_chars.
   - The copy must read naturally and persuasively.

Output format (strict):
1) FILLED_SCHEMA_JSON
2) FINAL_COPY_TEXT

Schema:
{PASTE_SCHEMA_JSON_HERE}
