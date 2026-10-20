# offload

A Claude Code hook that keeps heavy work off a small laptop. When an agent tries to run an install, a build, a test suite, a headless browser, ffmpeg, OCR or a bulk `claude -p` locally, the hook refuses the command and tells the agent how to run it on a bigger machine over ssh. Every session also starts with a one-line reminder of the rule.

We built it for an 8 GB Mac that only has to hold a logged-in browser, a phone and some secrets, while a 30 GB Linux box sat idle.

## Install

```sh
git clone https://github.com/taktekhq/offload.git ~/offload
```

Add both hooks to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {"matcher": "Bash", "hooks": [{"type": "command", "command": "~/offload/offload hook", "timeout": 10}]}
    ],
    "SessionStart": [
      {"hooks": [{"type": "command", "command": "~/offload/offload remind", "timeout": 10}]}
    ]
  }
}
```

Needs Python 3.8 or later, standard library only. The swap warning reads `sysctl vm.swapusage` (macOS) and is skipped elsewhere.

## Configure

`~/.config/offload/config.json` (or the path in `OFFLOAD_CONFIG`). Every key is optional:

```json
{
  "host": "bigbox",
  "remote_dir": "~/src",
  "local_name": "this Mac",
  "needs_local": "the logged-in browser, the phone, local secrets, Xcode",
  "heavy": ["^my-render-tool\\b"],
  "allow": ["^npm test\\b"],
  "swap_warn": 50
}
```

- `host`: the ssh host the agent is told to use (`OFFLOAD_HOST` overrides it).
- `heavy`: extra regexes, matched against each simple command from its first word.
- `allow`: regexes for commands that may always run locally.
- `swap_warn`: above this swap percentage the message adds that even an override should go remote.

`OFFLOAD_OFF=1` turns the hook off for one session.

## What it refuses

Package installs (`npm install`, `pip install`, `uv sync`), builds and dev servers (`npm run build`, `go build`, `cargo build`, `make`, `docker build`), test suites (`npm test`, `go test`, `pytest`), headless Chrome, Playwright and Lighthouse, `ffmpeg`, `whisper`, `tesseract`, `ocrmypdf`, and `claude -p`. The full list is `HEAVY` at the top of `offload`.

It lets through:

- anything that already goes through `ssh`, `scp`, `rsync` or `mosh`, including heavy commands inside the quoted remote part;
- a line where a command starts with `MAC_OK=1`, which is how the agent says "this one needs the laptop" (it is asked to give the reason);
- heredoc bodies, quoted strings and comments, which are text, not commands.

It never blocks on its own error: bad input means the command runs.

## Try it

```sh
./offload check npm install        # prints the message, exit 2
./offload check ssh bigbox 'npm install'   # ok: runs here
./offload remind
python3 -m unittest discover -s tests
```

## License

MIT, Taktek and Nizar Mahmoud.
