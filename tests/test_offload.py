import importlib.machinery
import importlib.util
import json
import os
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "offload")
loader = importlib.machinery.SourceFileLoader("offload", SCRIPT)
spec = importlib.util.spec_from_loader("offload", loader)
offload = importlib.util.module_from_spec(spec)
loader.exec_module(offload)

os.environ["OFFLOAD_CONFIG"] = "/nonexistent"
os.environ.pop("OFFLOAD_OFF", None)
CFG = offload.load_config()


def refused(cmd, cfg=CFG):
    return offload.judge(cmd, cfg) is not None


class Judge(unittest.TestCase):
    def test_heavy_commands_refused(self):
        for cmd in [
            "npm install",
            "npm ci",
            "cd app && npm run build",
            "pnpm test",
            "npx -y lighthouse https://example.com",
            "npx playwright test",
            "go test ./...",
            "cargo build --release",
            "pytest -q",
            "python3 -m pytest tests",
            "pip install requests",
            "uv sync",
            "make",
            "docker build .",
            "ffmpeg -i a.mp4 b.mp4",
            "tesseract scan.png out",
            "claude -p 'summarize'",
            "claude --model sonnet -p hi",
            "timeout 60 npm test",
            "sudo docker run x",
            "FOO=bar npm install",
            "/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --headless --screenshot x",
            "ls; npm install",
            "echo hi | npm install",
        ]:
            with self.subTest(cmd=cmd):
                self.assertTrue(refused(cmd))

    def test_light_and_mac_commands_allowed(self):
        for cmd in [
            "ls -la",
            "git status && git commit -m 'npm install docs'",
            "echo 'npm install'",
            "curl -s http://127.0.0.1:9222/json/version",
            "python3 -m unittest discover -s tests",
            "node scripts/tabs.mjs list",
            "xcodebuild -scheme App",
            "~/Library/Android/platform-tools/adb devices",
            "make -n",
            "grep -rn 'go test' .",
            "# npm install",
            "claude --version",
        ]:
            with self.subTest(cmd=cmd):
                self.assertFalse(refused(cmd))

    def test_remote_commands_allowed(self):
        for cmd in [
            "ssh xps 'cd ~/src/app && npm install && npm run build'",
            "ssh xps \"go test ./...\"",
            "git push && ssh xps 'cd x && pytest'",
            "rsync -a dist/ xps:dist/",
        ]:
            with self.subTest(cmd=cmd):
                self.assertFalse(refused(cmd))

    def test_override(self):
        self.assertFalse(refused("MAC_OK=1 npm install"))
        self.assertFalse(refused("cd app && MAC_OK=1 npm install"))
        self.assertTrue(refused("MAC_OK=0 npm install"))

    def test_heredoc_body_is_not_a_command(self):
        cmd = "cat > notes.md <<'EOF'\nnpm install\ngo test ./...\nEOF\necho done"
        self.assertFalse(refused(cmd))
        self.assertTrue(refused("cat > f <<EOF\nhello\nEOF\nnpm install"))

    def test_unbalanced_quotes_fall_back(self):
        self.assertTrue(refused("npm install && echo it's"))
        self.assertFalse(refused("echo it's fine"))

    def test_config_allow_and_heavy(self):
        cfg = dict(CFG, allow=[r"^npm test\b"], heavy=[r"^mytool\b"])
        self.assertFalse(refused("npm test", cfg))
        self.assertTrue(refused("mytool run", cfg))

    def test_off_switch(self):
        os.environ["OFFLOAD_OFF"] = "1"
        try:
            self.assertFalse(refused("npm install"))
        finally:
            del os.environ["OFFLOAD_OFF"]


class Hook(unittest.TestCase):
    def run_hook(self, payload):
        env = dict(os.environ, OFFLOAD_CONFIG="/nonexistent", OFFLOAD_HOST="bigbox")
        return subprocess.run([sys.executable, SCRIPT, "hook"], input=payload, capture_output=True, text=True, env=env)

    def test_refuses_with_exit_2_and_names_host(self):
        r = self.run_hook(json.dumps({"tool_name": "Bash", "tool_input": {"command": "npm install"}}))
        self.assertEqual(r.returncode, 2)
        self.assertIn("ssh bigbox", r.stderr)
        self.assertIn("MAC_OK=1", r.stderr)

    def test_allows_light(self):
        r = self.run_hook(json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}}))
        self.assertEqual(r.returncode, 0)

    def test_bad_input_never_blocks(self):
        self.assertEqual(self.run_hook("not json").returncode, 0)

    def test_remind(self):
        env = dict(os.environ, OFFLOAD_CONFIG="/nonexistent", OFFLOAD_HOST="bigbox")
        r = subprocess.run([sys.executable, SCRIPT, "remind"], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0)
        self.assertIn("ssh bigbox", r.stdout)


if __name__ == "__main__":
    unittest.main()
