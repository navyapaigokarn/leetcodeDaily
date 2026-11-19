# leetcodeDaily

Once a day, this repo fetches the public LeetCode daily question, asks a free Gemini model for a Java solution and a C++ solution, compiles both, runs the official examples, and stores the files under `solutions/`.

The problem statement stays in the model prompt. Each solution folder keeps the title, difficulty, and link. Nothing is submitted to LeetCode.

## What you need

- Python 3.9 or newer
- JDK 17 or newer (`java` and `javac` on your PATH)
- `g++` with C++17 support
- A free Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

## Run it once on your machine

Open `.env` in this folder and paste your key after `LLM_API_KEY=`. Then:

```bash
python3 scripts/solve_daily.py
```

A passing run creates `solutions/<date>-<slug>/` with `Solution.java`, `Solution.cpp`, and a short `README.md`. Running it again the same day prints `Already solved` and does nothing.

To use another OpenAI-compatible free endpoint, set `LLM_BASE_URL` and `LLM_MODEL` before the command. The defaults are Gemini's compatible endpoint and `gemini-3.5-flash-lite`. If that model name is rejected, set `LLM_MODEL` to a Flash model shown in AI Studio.

This command writes files. It does not commit or push.

## Run it from GitHub every day

1. Create a GitHub repository and push this folder to its default branch.
2. In the repository, open **Settings → Secrets and variables → Actions** and add a secret named `LLM_API_KEY`.
3. Open the **Actions** tab, choose **Daily question**, and press **Run workflow**.

The workflow also runs on its own at 00:15 UTC (5:45 AM IST). When the samples pass, GitHub Actions commits the new folder and pushes it. A failed compile or a failed sample leaves the repo unchanged and marks the run red.

Optional repository variables `LLM_BASE_URL` and `LLM_MODEL` override the defaults for the workflow.
