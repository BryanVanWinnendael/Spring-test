import argparse
import json
import os
import sys
from google import genai
from google.genai import types
from pathlib import Path

MODEL = "gemini-3.6-flash"


def read_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def build_prompt(diff: str, rules: str) -> str:
    return f"""
You are an experienced senior Java and Spring Boot developer performing
a code review.

Your purpose is to find meaningful opportunities to improve code that
already works.

This is NOT a generic linting review.

Only report a finding when an experienced developer would reasonably
consider changing the code during a pull request.

Do NOT report:

- formatting preferences
- trivial variable renaming
- minor stylistic preferences
- changes merely because another implementation is possible
- changes that only reduce the number of lines
- subjective personal preferences
- hypothetical future requirements
- issues already handled by normal static analysis unless they have
  an important design implication

Look specifically for:

1. Unnecessary complexity
2. Duplicated business logic
3. Poor separation of responsibilities
4. Unnecessary or incorrect abstractions
5. Missing abstractions where duplication is significant
6. Non-idiomatic Java where the alternative is substantially clearer
7. Spring Boot architectural problems
8. Incorrect Controller/Service/Repository responsibilities
9. Unnecessary database/repository calls
10. Difficult-to-test code
11. Existing project functionality that should be reused
12. Code that could be substantially simpler without losing clarity

IMPORTANT:

Prefer the existing architecture and conventions of the project.

Do not recommend introducing a new design pattern simply because it is
theoretically cleaner.

Only make a recommendation when you can explain a concrete benefit.

Project-specific review rules:

--- BEGIN PROJECT RULES ---
{rules}
--- END PROJECT RULES ---

Pull request diff:

--- BEGIN DIFF ---
{diff}
--- END DIFF ---

Return ONLY valid JSON.

Use this exact structure:

{{
  "findings": [
    {{
      "severity": "HIGH",
      "file": "src/main/java/example/OrderService.java",
      "line": 42,
      "title": "Short title",
      "body": "Explain the problem and provide a concrete suggestion."
    }}
  ]
}}

Severity meanings:

HIGH:
A significant maintainability/design problem that should probably be
addressed in this PR.

MEDIUM:
A worthwhile refactoring that would materially improve the code, but
the current implementation is still acceptable.

LOW:
A useful improvement but genuinely optional.

Remember:
If there are no meaningful improvements, return:

{{"findings": []}}
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("diff")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        print("GEMINI_API_KEY is not set", file=sys.stderr)
        sys.exit(1)

    diff = read_file(args.diff)

    rules_path = Path(".ai-review-rules.md")

    if rules_path.exists():
        rules = rules_path.read_text(encoding="utf-8")
    else:
        rules = "No additional project-specific rules."

    if not diff.strip():
        print("No changes found.")
        return

    client = genai.Client(api_key=api_key)

    prompt = build_prompt(diff, rules)

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )

    result = json.loads(response.text)

    findings = result.get("findings", [])

    if not findings:
        print("AI review found no meaningful refactoring opportunities.")
        return

    print(f"AI review found {len(findings)} finding(s):")
    print()

    for finding in findings:
        print(
            f"[{finding['severity']}] "
            f"{finding['file']}:{finding['line']} "
            f"{finding['title']}"
        )
        print(f"  {finding['body']}")
        print()


if __name__ == "__main__":
    main()
