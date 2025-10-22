# resume-mcp

`resume-mcp` makes resume tailoring absurdly easy. It wraps an [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) server around your Overleaf workspace so any MCP-compatible assistant can read and rewrite LaTeX files in-place. Drop in, point the server at your project, and start asking your AI sidekick to punch up bullet points, remix sections, or generate a brand-new variant without touching the Overleaf UI.

---

## Why it feels *ridiculously* simple

| You do this | The server quietly handles |
| --- | --- |
| Provide an Overleaf project name | Resolves the project ID, syncs the file tree, and caches it for snappy navigation. |
| Ask for a tweak | Calls purpose-built tools (list, read, write, resume helper) so the assistant can edit safely and atomically. |
| Paste your cookie once | Uses only the `OVERLEAF_SESSION_COOKIE`—no OAuth dance, no scraping hacks. |
| Run the tests | Spins through a full create → edit → cleanup cycle to prove your resume survives aggressive iteration. |

The net effect: tailoring variants for different roles feels like editing a chat transcript, not wrestling with LaTeX.

---

## Quick start (from zero to "tailor this" in minutes)

1. **Clone and install**
   ```bash
   git clone https://github.com/<you>/resume-mcp.git
   cd resume-mcp
   uv sync  # or `pip install -e .`
   ```

2. **Export your Overleaf session cookie**
   ```bash
   export OVERLEAF_SESSION_COOKIE="<value of overleaf_session2>"
   ```

3. **(Optional) Prime the test suite**
   ```bash
   export OVERLEAF_TEST_PROJECT="Your Resume Project"
   ```

4. **Launch the server**
   ```bash
   uv run resume-mcp
   ```
   - MCP stdio transport is enabled by default.
   - An HTTP transport is also exposed on `127.0.0.1:8000` with a `/health` endpoint.

5. **Connect from your MCP client** (`anthropic`, `bolt`, `cursor`, etc.) and start issuing prompts like:
   - "List my Overleaf projects."
   - "Read `sections/experience.tex` from `Infra Resume`."
   - "Rewrite the AWS bullets to scream platform automation."
   - "Draft a new section called `Impact Highlights` and fill it with 3 wins."

That is the whole setup. Once your cookie is exported, you can restart and reconnect in seconds.

---

## Configuration cheat sheet

| Setting | Required? | What it unlocks |
| --- | --- | --- |
| `OVERLEAF_SESSION_COOKIE` | ✅ | Core auth to Overleaf. Grab the `overleaf_session2` value from your browser. |
| `OVERLEAF_TEST_PROJECT` | ⚙️ Optional | Name of a real project to let `pytest` create and clean up files. |
| `PUBLIC_KEY_PATH` / `PRIVATE_KEY_PATH` | ⚙️ Optional | Enables bearer-token auth for HTTP clients (handy when exposing beyond localhost). |

All configuration happens through environment variables. If you like `.env` files, drop them in the repo root—`python-dotenv` will auto-load them.

---

## Tailoring tools at your fingertips

| Tool | Why you care |
| --- | --- |
| `list_overleaf_projects()` | Sanity-check that the cookie works and discover project slugs without opening the browser. |
| `list_files(project_name, path="")` | Peek inside any folder to target the exact `.tex` or asset you want to tweak. |
| `read_file(project_name, file_path)` | Pull pristine LaTeX into the conversation for critique, summarization, or rewriting. |
| `write_file(project_name, file_path, content)` | Atomically write a tailored version back—perfect for "update this section" loops. |
| `read_resume()` | Opinionated helper that fetches your primary resume file (defaults to `main.tex` in `CV-XeLate`). Customize it to match your project structure. |

Because the server caches directory metadata, repeated read/write cycles stay blazing fast.

---

## Build a repeatable tailoring ritual

1. **Snapshot the current section.** `read_file` the target LaTeX.
2. **Describe the role** (paste the job post, list keywords, etc.).
3. **Prompt your assistant** to punch up bullets or draft a fresh section.
4. **Write it back** with `write_file` and immediately diff in git.
5. **Commit variants** (`git commit -am "tailor: staff sre"`) so you can cherry-pick the perfect version later.

Need a new helper? Copy the `read_resume` tool, aim it at a cover letter, portfolio, or recruiter email template, and you have another one-command workflow.

---

## Running tests (because easy should also be safe)

```bash
pytest
```

The suite boots an `OverleafClient`, creates a disposable file inside your test project, verifies read/write fidelity, and then deletes it—so the only thing left behind is your smug grin at how painless the process was.

---

## License

[MIT](LICENSE)
