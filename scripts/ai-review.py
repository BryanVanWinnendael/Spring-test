import argparse
import json
import os
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
You are an experienced senior Java and Spring Boot developer performing
a pull request code review.

Your purpose is to find meaningful opportunities to improve code that
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
- minor differences in coding style

Look specifically for:

1. Unnecessary complexity
2. Duplicated business logic
3. Poor separation of responsibilities
4. Unnecessary abstractions
5. Missing abstractions where duplication is significant
6. Non-idiomatic Java where the alternative is substantially clearer
7. Spring Boot architectural problems
8. Incorrect Controller/Service/Repository responsibilities
9. Unnecessary database/repository calls
10. Difficult-to-test code
11. Existing project functionality that should be reused
12. Code that could be substantially simpler without losing clarity
13. Code that could be made significantly more readable or maintainable

Project-specific rules:

--- BEGIN PROJECT RULES ---

{rules}

--- END PROJECT RULES ---

Review ONLY the Java changes below:

--- BEGIN DIFF ---

{diff}

--- END DIFF ---

Return ONLY valid JSON.

Use exactly this structure:

{{
  "findings": [
    {{
      "severity": "HIGH|MEDIUM|LOW",
      "file": "src/main/java/example/CourseService.java",
      "line": 25,
      "title": "Short description of the issue",
      "problem": "Explain clearly what is wrong or unnecessarily complicated.",
      "solution": "Explain what the developer should do instead.",
      "suggested_code": "return repository.createCourse(course);"
    }}
  ]
}}

Rules for findings:

- The file MUST be a Java file from the supplied diff.
- The line MUST be a changed line in the supplied diff.
- Only comment on code that was changed in this PR.
- Do not comment on unchanged surrounding code.
- Always explain the actual problem.
- Always provide a concrete solution.
- When appropriate, provide replacement Java code.
- suggested_code must contain ONLY Java code.
- Do not include markdown code fences inside suggested_code.
- If code replacement is not appropriate, use null for suggested_code.
- Do not suggest a solution unless it is genuinely better.
- Prefer simple solutions over introducing unnecessary abstractions.
- Follow the existing architecture and conventions.
- Do not introduce design patterns just because they exist.
- Do not suggest changes merely because another implementation is possible.

Severity:

HIGH:
A significant maintainability, architecture, or design problem that
should probably be addressed in this PR.

MEDIUM:
A meaningful improvement that would make the code substantially better,
but the current implementation is still acceptable.

LOW:
A useful but optional improvement.

If there are no meaningful improvements, return:

{{"findings": []}}
"""


def review_with_gemini(diff, rules):
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set.")

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


def create_github_review(result):
    github_token = os.environ.get("GITHUB_TOKEN")

    if not github_token:
        raise RuntimeError("GITHUB_TOKEN is not set.")

    repository_name = os.environ.get("GITHUB_REPOSITORY")
    pr_number = os.environ.get("PR_NUMBER")

    if not repository_name:
        raise RuntimeError("GITHUB_REPOSITORY is not set.")

    if not pr_number:
        raise RuntimeError("PR_NUMBER is not set.")

    github = Github(github_token)

    repository = github.get_repo(repository_name)
    pull_request = repository.get_pull(int(pr_number))

    findings = result.get("findings", [])

    if not findings:
        print("AI review found no meaningful improvements.")
        return

    comments = []

    for finding in findings:
        severity = finding.get("severity", "LOW")
        title = finding.get("title", "Potential improvement")
        problem = finding.get("problem", "")
        solution = finding.get("solution", "")
        suggested_code = finding.get("suggested_code")

        body = (
            f"**🤖 {severity} — {title}**\n\n"
            f"**Problem**\n"
            f"{problem}\n\n"
            f"**Solution**\n"
            f"{solution}"
        )

        if suggested_code:
            body += (
                "\n\n**Suggested code**\n"
                f"```java\n{suggested_code}\n```"
            )

        comments.append(
            {
                "path": finding["file"],
                "line": finding["line"],
                "body": body,
            }
        )

    commit = repository.get_commit(pull_request.head.sha)

    review_body = (
        "## 🤖 AI Code Review\n\n"
        f"Found **{len(comments)}** potential improvement"
        f"{'' if len(comments) == 1 else 's'}.\n\n"
        "These suggestions are advisory and should be evaluated by the "
        "developer."
    )

    try:
        pull_request.create_review(
            commit=commit,
            body=review_body,
            event="COMMENT",
            comments=comments,
        )

        print(f"Created GitHub review with {len(comments)} comment(s).")

    except Exception as error:
        print("Failed to create GitHub review.")
        print(error)

        print("\nFindings returned by Gemini:")
        print(json.dumps(result, indent=2))

        raise


def main():
    parser = argparse.ArgumentParser(
        description="Review Java changes using Gemini and post comments to GitHub."
    )

    parser.add_argument(
        "diff",
        help="Path to the git diff file.",
    )

    args = parser.parse_args()

    diff = read_file(args.diff)

    if not diff.strip():
        print("No Java changes found.")
        return

    print("Sending Java changes to Gemini...")

    rules = get_rules()

    result = review_with_gemini(
        diff=diff,
        rules=rules,
    )

    print("\nGemini response:")
    print(json.dumps(result, indent=2))

    create_github_review(result)


if __name__ == "__main__":
    main()
