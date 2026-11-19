#!/usr/bin/env python3
"""Fetch the LeetCode daily question and write Java and C++ solutions.

The script calls a free OpenAI-compatible model, compiles both files, and runs
the example checks the model wrote. It copies files into solutions/ only after
those checks pass. It does not submit anything to LeetCode and does not git push.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

LEETCODE_URL = "https://leetcode.com/graphql"
DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
DEFAULT_MODEL = "gemini-3.5-flash-lite"
MAX_ATTEMPTS = 2
MODEL_RETRY_LIMIT = 4
MODEL_RETRY_WAIT = 8
STATEMENT_LIMIT = 12000
EXAMPLES_LIMIT = 4000
ROOT = Path(__file__).resolve().parents[1]
SOLUTIONS_DIR = ROOT / "solutions"

DAILY_QUERY = """
query questionOfToday {
  activeDailyCodingChallengeQuestion {
    date
    link
    question {
      questionFrontendId
      title
      titleSlug
      difficulty
      content
      isPaidOnly
      exampleTestcases
      metaData
      codeSnippets {
        lang
        langSlug
        code
      }
    }
  }
}
"""

BLOCKED_SNIPPETS = (
    "Runtime.getRuntime",
    "ProcessBuilder",
    "HttpURLConnection",
    "java.net.",
    "system(",
    "popen(",
    "fork(",
    "socket(",
)


class AttemptFailed(Exception):
    """One generation failed to parse, compile, or pass its samples."""


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip = False

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style"}:
            self.skip = True
        if tag in {"p", "br", "li", "pre", "div", "h1", "h2", "h3", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"}:
            self.skip = False
        if tag in {"p", "li", "pre", "div", "tr"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.parts.append(data)


def log(message: str) -> None:
    print(message, flush=True)


def html_to_text(value: str) -> str:
    parser = TextExtractor()
    parser.feed(value or "")
    text = "".join(parser.parts)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def post_json(
    url: str,
    payload: dict,
    headers: dict,
    timeout: int,
    waiting_for: str = "",
) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers=headers,
        method="POST",
    )
    stop = threading.Event()
    started = time.monotonic()

    def heartbeat() -> None:
        while not stop.wait(15):
            elapsed = int(time.monotonic() - started)
            log(f"Still waiting for {waiting_for} ({elapsed}s, timeout {timeout}s)...")

    beater = None
    if waiting_for:
        beater = threading.Thread(target=heartbeat, daemon=True)
        beater.start()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode()
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")
        raise AttemptFailed(f"HTTP {error.code} from {url}\n{detail[:2000]}") from error
    except urllib.error.URLError as error:
        raise AttemptFailed(f"Could not reach {url}: {error.reason}") from error
    except (TimeoutError, socket.timeout) as error:
        raise AttemptFailed(f"Timed out after {timeout}s waiting for {url}: {error}") from error
    finally:
        stop.set()
        if beater is not None:
            beater.join(timeout=1)
    try:
        return json.loads(body)
    except json.JSONDecodeError as error:
        raise AttemptFailed(f"Response from {url} was not JSON.") from error


def fetch_daily() -> dict:
    log("Fetching today's question from LeetCode...")
    try:
        payload = post_json(
            LEETCODE_URL,
            {"query": DAILY_QUERY},
            {
                "Content-Type": "application/json",
                "Referer": "https://leetcode.com",
                "Origin": "https://leetcode.com",
                "User-Agent": "leetcode-daily",
            },
            timeout=30,
        )
    except AttemptFailed as error:
        raise SystemExit(f"Could not fetch the daily question.\n{error}") from error
    if payload.get("errors"):
        raise SystemExit(f"LeetCode returned an error: {payload['errors']}")
    daily = (payload.get("data") or {}).get("activeDailyCodingChallengeQuestion")
    if not daily or not daily.get("question"):
        raise SystemExit("LeetCode did not return a daily question.")
    question = daily["question"]
    if question.get("isPaidOnly"):
        raise SystemExit(f"Today's question ({question.get('title')}) is premium-only.")

    snippets = {
        item.get("langSlug"): item.get("code") or ""
        for item in question.get("codeSnippets") or []
    }
    slug = question.get("titleSlug") or ""
    if not re.fullmatch(r"[a-z0-9-]+", slug):
        raise SystemExit(f"Unexpected problem slug: {slug!r}")

    return {
        "date": daily.get("date") or "",
        "id": question.get("questionFrontendId") or "",
        "title": question.get("title") or slug,
        "slug": slug,
        "difficulty": question.get("difficulty") or "",
        "statement": html_to_text(question.get("content") or "")[:STATEMENT_LIMIT],
        "examples": (question.get("exampleTestcases") or "")[:EXAMPLES_LIMIT],
        "metadata": question.get("metaData") or "",
        "java_starter": snippets.get("java") or "",
        "cpp_starter": snippets.get("cpp") or "",
        "url": f"https://leetcode.com/problems/{slug}/",
    }


def load_env_file() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip("'").strip('"')
        if name and name not in os.environ:
            os.environ[name] = value


def env_or_default(name: str, default: str) -> str:
    value = os.environ.get(name, "").strip()
    return value or default


def call_model(messages: list[dict], use_json_mode: bool) -> str:
    api_key = os.environ.get("LLM_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            f"LLM_API_KEY is missing. Paste it in {ROOT / '.env'}"
        )
    base = env_or_default("LLM_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    model = env_or_default("LLM_MODEL", DEFAULT_MODEL)
    payload: dict = {
        "model": model,
        "temperature": 0.2,
        "messages": messages,
    }
    if use_json_mode:
        payload["response_format"] = {"type": "json_object"}
    response = None
    url = f"{base}/chat/completions"
    for try_index in range(MODEL_RETRY_LIMIT):
        mode = "JSON mode" if use_json_mode else "plain text"
        log(
            f"Calling {model} ({mode}, request {try_index + 1} of {MODEL_RETRY_LIMIT}, "
            f"timeout 180s)..."
        )
        started = time.monotonic()
        try:
            response = post_json(
                url,
                payload,
                {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                timeout=180,
                waiting_for=model,
            )
            elapsed = time.monotonic() - started
            log(f"{model} responded in {elapsed:.0f}s.")
            break
        except AttemptFailed as error:
            message = str(error)
            retryable = (
                "HTTP 429" in message
                or "HTTP 503" in message
                or message.startswith("Timed out")
            )
            if not retryable or try_index == MODEL_RETRY_LIMIT - 1:
                raise
            wait = MODEL_RETRY_WAIT * (try_index + 1)
            reason = "timed out" if message.startswith("Timed out") else "is busy"
            log(f"Model endpoint {reason}. Retrying in {wait}s...")
            time.sleep(wait)
    if response.get("error"):
        message = response["error"].get("message", response["error"])
        raise AttemptFailed(f"Model API error: {message}")
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise AttemptFailed(f"Model response had no message content: {response}") from error
    if isinstance(content, list):
        content = "".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
    if not isinstance(content, str) or not content.strip():
        raise AttemptFailed("Model returned an empty response.")
    return content


def strip_fences(code: str) -> str:
    text = code.strip()
    text = re.sub(r"^```[A-Za-z0-9_+-]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip() + "\n"


def parse_solution(raw: str) -> dict[str, str]:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise AttemptFailed("Model response did not contain a JSON object.")
    try:
        payload = json.loads(text[start : end + 1])
    except json.JSONDecodeError as error:
        raise AttemptFailed(f"Model JSON could not be parsed: {error}") from error
    files = {}
    for key in ("java", "cpp", "java_test", "cpp_test"):
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise AttemptFailed(f"Model JSON is missing a non-empty '{key}' field.")
        files[key] = strip_fences(value)
    return files


def reject_unsafe(files: dict[str, str]) -> None:
    combined = "\n".join(files.values())
    for snippet in BLOCKED_SNIPPETS:
        if snippet in combined:
            raise AttemptFailed(f"Generated code contained a blocked call: {snippet}")


def check_shape(files: dict[str, str]) -> None:
    reject_unsafe(files)
    java = files["java"]
    cpp = files["cpp"]
    if "class Solution" not in java:
        raise AttemptFailed("Java solution has no class Solution.")
    if re.search(r"\bmain\s*\(", java):
        raise AttemptFailed("Java solution must not contain a main method.")
    if "package " in java:
        raise AttemptFailed("Java solution must not declare a package.")
    if "class Solution" not in cpp:
        raise AttemptFailed("C++ solution has no class Solution.")
    if re.search(r"\bmain\s*\(", cpp):
        raise AttemptFailed("C++ solution must not contain main.")
    if "class Main" not in files["java_test"] or "main" not in files["java_test"]:
        raise AttemptFailed("Java test must be a Main class with a main method.")
    if "class Solution" in files["java_test"]:
        raise AttemptFailed("Java test must use the existing Solution class, not redefine it.")
    if not re.search(r"\bmain\s*\(", files["cpp_test"]):
        raise AttemptFailed("C++ test must define main.")
    if "class Solution" in files["cpp_test"]:
        raise AttemptFailed("C++ test must not define a second Solution class.")


def run_command(command: list[str], cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or ""
        stderr = error.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        raise AttemptFailed(
            f"Command timed out after {timeout}s: {' '.join(command)}\n{stdout}\n{stderr}"
        ) from error
    except FileNotFoundError as error:
        raise SystemExit(
            f"'{command[0]}' was not found on PATH. Install a JDK 17+ and g++ before running."
        ) from error


def require_success(result: subprocess.CompletedProcess[str], label: str) -> None:
    if result.returncode == 0:
        return
    output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
    raise AttemptFailed(f"{label} failed with exit code {result.returncode}.\n{output[-4000:]}")


def compile_and_test(files: dict[str, str]) -> None:
    with tempfile.TemporaryDirectory(prefix="leetcode-daily-") as directory:
        work = Path(directory)
        (work / "Solution.java").write_text(files["java"], encoding="utf-8")
        (work / "Main.java").write_text(files["java_test"], encoding="utf-8")
        (work / "check.cpp").write_text(files["cpp"] + "\n" + files["cpp_test"], encoding="utf-8")

        log("Compiling the Java solution and its sample checks...")
        require_success(
            run_command(["javac", "--release", "17", "Solution.java", "Main.java"], work, 60),
            "javac",
        )
        log("Running the Java sample checks...")
        require_success(run_command(["java", "-cp", str(work), "Main"], work, 20), "Java samples")
        log("Java sample checks passed.")
        binary = work / "check"
        log("Compiling the C++ solution and its sample checks...")
        require_success(
            run_command(["g++", "-std=c++17", "-O2", "-o", str(binary), "check.cpp"], work, 60),
            "g++",
        )
        log("Running the C++ sample checks...")
        require_success(run_command([str(binary)], work, 20), "C++ samples")
        log("C++ sample checks passed.")


def prompt_for(question: dict, feedback: str) -> list[dict]:
    starter_java = question["java_starter"] or "(no Java starter was provided; use class Solution)"
    starter_cpp = question["cpp_starter"] or "(no C++ starter was provided; use class Solution)"
    correction = ""
    if feedback:
        correction = (
            "\nThe previous attempt failed. Fix the code and the tests.\n"
            f"Failure:\n{feedback[-5000:]}\n"
        )
    user = f"""
Solve this LeetCode question in Java and C++.

Title: {question['id']}. {question['title']}
Difficulty: {question['difficulty']}
URL: {question['url']}

Method metadata:
{question['metadata']}

Official example inputs:
{question['examples']}

Java starter:
{starter_java}

C++ starter:
{starter_cpp}

Problem:
{question['statement']}
{correction}
Return one JSON object and nothing else. Use these string fields:
- java: the complete Solution.java source. No package. Class name Solution. No main method. Java 17. Keep the starter method signature.
- cpp: the complete Solution.cpp source. Class name Solution. No main. C++17. Include the standard headers you use. Do not include bits/stdc++.h. Keep the starter method signature.
- java_test: a complete Main.java. public class Main with public static void main. Construct Solution and check every official example. On a mismatch, print the expected and actual values, then System.exit(1). No package. Do not define class Solution.
- cpp_test: only main and helpers. This text is compiled in the same file after the C++ solution, so do not define class Solution again and do not repeat includes that the solution already has. Return a non-zero status and print expected versus actual on a mismatch.

The programs must not read files, use the network, or spawn processes. Cover every official example, including list, tree, and design-problem examples when the question has them.
""".strip()
    return [
        {
            "role": "system",
            "content": (
                "You write correct LeetCode solutions. "
                "Respond with a single JSON object and no markdown."
            ),
        },
        {"role": "user", "content": user},
    ]


def with_header(question: dict, source: str) -> str:
    header = f"// {question['id']}. {question['title']}\n// {question['url']}\n"
    if question["url"] in source:
        return source
    return header + "\n" + source


def write_solution(question: dict, files: dict[str, str]) -> Path:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", question["date"]):
        raise SystemExit(f"Unexpected daily date: {question['date']!r}")
    destination = solution_dir(question)
    staging = destination.with_name(destination.name + ".tmp")
    if staging.exists():
        shutil.rmtree(staging)
    log(f"Writing solution files to {destination.relative_to(ROOT)}...")
    staging.mkdir(parents=True)
    readme = (
        f"# {question['id']}. {question['title']}\n\n"
        f"Difficulty: {question['difficulty']}\n\n"
        f"{question['url']}\n\n"
        "Sample checks passed in this run. This solution was not submitted to LeetCode.\n"
    )
    (staging / "Solution.java").write_text(with_header(question, files["java"]), encoding="utf-8")
    (staging / "Solution.cpp").write_text(with_header(question, files["cpp"]), encoding="utf-8")
    (staging / "README.md").write_text(readme, encoding="utf-8")
    if destination.exists():
        shutil.rmtree(destination)
    staging.rename(destination)
    return destination


def solution_dir(question: dict) -> Path:
    return SOLUTIONS_DIR / f"{question['date']}-{question['slug']}"


def already_solved(question: dict) -> Path | None:
    folder = solution_dir(question)
    if (folder / "Solution.java").exists() and (folder / "Solution.cpp").exists():
        return folder
    return None


def generate(question: dict) -> dict[str, str]:
    feedback = ""
    json_mode = True
    attempt = 1
    while attempt <= MAX_ATTEMPTS:
        log(f"Attempt {attempt} of {MAX_ATTEMPTS}...")
        try:
            raw = call_model(prompt_for(question, feedback), json_mode)
        except AttemptFailed as error:
            message = str(error)
            if json_mode and "HTTP 400" in message:
                json_mode = False
                log("The model endpoint rejected JSON mode. Retrying without it.")
                continue
            raise SystemExit(f"The model request failed.\n{message}") from error
        try:
            log(f"Parsing the model response ({len(raw)} characters)...")
            files = parse_solution(raw)
            log("Checking that the Java and C++ files have the expected shape...")
            check_shape(files)
            compile_and_test(files)
            return files
        except AttemptFailed as error:
            feedback = str(error)
            log(feedback)
            if attempt == MAX_ATTEMPTS:
                raise SystemExit(f"Stopped after {MAX_ATTEMPTS} attempts.\n{feedback}") from error
        attempt += 1
    raise SystemExit("No solution was produced.")


def main() -> None:
    load_env_file()
    if shutil.which("javac") is None or shutil.which("g++") is None or shutil.which("java") is None:
        raise SystemExit("This script needs javac, java, and g++ on PATH.")
    question = fetch_daily()
    log(f"Today: {question['date']} {question['id']}. {question['title']} ({question['difficulty']})")
    existing = already_solved(question)
    if existing is not None:
        log(f"Already solved: {existing.relative_to(ROOT)}")
        return
    files = generate(question)
    destination = write_solution(question, files)
    log(f"Wrote {destination.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
