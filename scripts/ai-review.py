import argparse
import json
import os
import subprocess
from github import Github
from google import genai
from google.genai import types
from pathlib import Path

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")


def read_file(path):
    return Path(path).read_text(encoding="utf-8")


def get_rules():
    path = Path(".ai-review-rules.md")

    if path.exists():
        return path.read_text(encoding="utf-8")

    return "No additional project-specific rules."


def build_prompt(diff, rules):
    return f"""
You are an experienced senior Java and Spring Boot developer reviewing
a pull request.

Your job is to find meaningful opportunities to improve code that
already works.

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

Look specifically for:

1. Unnecessary complexity
2. Duplicated business logic
3. Poor separation of responsibilities
4. Unnecessary abstractions
5. Non-idiomatic Java where the alternative is substantially clearer
6. Spring Boot architectural problems
7. Incorrect Controller/Service/Repository responsibilities
8. Unnecessary database/repository calls
9. Difficult-to-test code
10. Existing project functionality that should be reused
11. Code that could be substantially simpler without losing clarity

Project-specific rules:

--- BEGIN RULES ---
{rules}
--- END RULES ---

Review ONLY these Java changes:

--- BEGIN DIFF ---
{diff}
--- END DIFF ---

Return ONLY valid JSON:

{{
  "findings": [
    {
    "severity": "HIGH|MEDIUM|LOW",
      "file": "src/main/java/example/CourseService.java",
      "line": 25,
      "title": "Unnecessary local variable",
      "problem": "The local variable is only used immediately in the return statement and adds no useful context.",
      "solution": "Return the repository call directly.",
      "suggested_code": "return repository.createCourse(course);"
    }
  ]
}}

Important:

- The line number MUST be a line from the changed Java code.
- Only comment on changed lines.
- Explain the actual problem, not just the rule being violated.
- Always provide a concrete solution.
- When appropriate, provide replacement Java code in suggested_code.
- suggested_code should contain ONLY the replacement code, without markdown fences.
- If showing code would not be appropriate, set suggested_code to null.
- Do not suggest a solution unless you are confident it is an improvement.
- If there is no meaningful improvement, return:
  {"findings": []}
"""


def get_diff(path):
    return read_file(path)


def review_with_gemini(diff, rules):
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=MODEL,
        contents=build_prompt(diff, rules),
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
        ),
    )

    return json.loads(response.text)


def get_github():
    token = os.environ.get("GITHUB_TOKEN")

    if not token:
        raise RuntimeError("GITHUB_TOKEN is not set")

    return Github(token)


def create_review_comments(result):
    repository_name = os.environ["GITHUB_REPOSITORY"]
    pr_number = int(os.environ["PR_NUMBER"])

    github = get_github()
    repository = github.get_repo(repository_name)
    pull_request = repository.get_pull(pr_number)

    findings = result.get("findings", [])

    if not findings:
        print("AI found no meaningful improvements.")
        return

    comments = []

    for finding in findings:
        solution = finding.get("solution", "")
        suggested_code = finding.get("suggested_code")

        body = (
            f"**🤖 {finding['severity']} — {finding['title']}**\n\n"
            f"**Problem**\n"
            f"{finding['problem']}\n\n"
            f"**Solution**\n"
            f"{solution}"
        )

        if suggested_code:
            body += (
                "\n\n**Suggested code**\n"
                f"```java\n{suggested_code}\n```"
            )

        comments.append({
            "path": finding["file"],
            "line": finding["line"],
            "body": body,
        })

    # GitHub requires the commit SHA for an inline review.
    commit = repository.get_commit(pull_request.head.sha)

    pull_request.create_review(
        commit=commit,
        body="### 🤖 AI Code Review\n\n"
             f"Found {len(comments)} potential improvement(s).",
        event="COMMENT",
        comments=comments,
    )

    print(f"Created {len(comments)} PR comments.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("diff")
    args = parser.parse_args()

    diff = get_diff(args.diff)

    if not diff.strip():
        print("No Java changes found.")
        return

    rules = get_rules()

    print("Sending Java changes to Gemini...")

    result = review_with_gemini(diff, rules)

    print(json.dumps(result, indent=2))

    create_review_comments(result)


if __name__ == "__main__":
    main()
