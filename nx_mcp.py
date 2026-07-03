r"""
MCP server for the NX tools — drive drawings and parameters from an AI agent
(Cursor, Claude Code, or any MCP client).

Zero dependencies: speaks MCP's stdio transport (newline-delimited JSON-RPC)
directly, so plain Python is enough. Each tool call launches a headless NX
session via run_journal.exe, so calls take ~30-90 seconds.

Client config (e.g. Cursor .cursor/mcp.json or Claude Code .mcp.json):

  {
    "mcpServers": {
      "nx": { "command": "python", "args": ["C:\\path\\to\\nx_mcp.py"] }
    }
  }

Tools:
  generate_drawing  ASME drawing (.prt + .pdf + coverage report) from a part
  list_parameters   all expressions: name, formula, value, units, depends_on
  edit_parameters   change values/formulas ("p5=180;p8=p5/2"), rename
                    ("p0->side_length"), or bulk-apply a JSON file
"""

import glob
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROTOCOL = "2024-11-05"


def log(msg):
    sys.stderr.write("[nx-mcp] %s\n" % msg)
    sys.stderr.flush()


def find_nx():
    cand = os.environ.get("NX_DIR", "")
    if cand and os.path.exists(os.path.join(cand, "NXBIN", "run_journal.exe")):
        return cand
    for d in sorted(glob.glob(r"C:\Program Files\Siemens\*")):
        if os.path.exists(os.path.join(d, "NXBIN", "run_journal.exe")):
            return d
    cand = os.environ.get("UGII_BASE_DIR", "")
    if cand and os.path.exists(os.path.join(cand, "NXBIN", "run_journal.exe")):
        return cand
    raise RuntimeError("Could not find NX. Set NX_DIR to the install folder "
                       "(the one containing NXBIN).")


def run_journal(script, extra_env):
    exe = os.path.join(find_nx(), "NXBIN", "run_journal.exe")
    env = dict(os.environ)
    env.update(extra_env)
    p = subprocess.run([exe, os.path.join(HERE, script)],
                       capture_output=True, text=True, timeout=900, env=env)
    return (p.stdout or "") + (p.stderr or "")


def check_model(args):
    model = os.path.abspath(args.get("model_path", ""))
    if not os.path.isfile(model):
        raise RuntimeError("model_path not found: %s" % model)
    return model


def read_if_exists(path, fallback=""):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return fallback


def tool_generate_drawing(args):
    model = check_model(args)
    out = run_journal("nx_drawing_generator.py", {"NXDRAW_MODEL": model})
    base = os.path.splitext(model)[0] + "_dwg"
    report = read_if_exists(base + "_report.txt", fallback=out[-3000:])
    ok = os.path.isfile(base + ".pdf")
    text = report + "\n"
    text += "PDF: %s\nDrawing part: %s\n" % (base + ".pdf", base + ".prt")
    if not ok:
        text += "\nWARNING: PDF missing — raw output:\n" + out[-3000:]
    return text, not ok


def tool_list_parameters(args):
    model = check_model(args)
    out = run_journal("nx_params.py",
                      {"NXPARAM_MODEL": model, "NXPARAM_ACTION": "list",
                       "NXPARAM_SET": "", "NXPARAM_JSON": ""})
    jpath = os.path.splitext(model)[0] + "_params.json"
    data = read_if_exists(jpath)
    if not data:
        return "Parameter listing failed — raw output:\n" + out[-3000:], True
    return data, False


def tool_edit_parameters(args):
    model = check_model(args)
    changes = args.get("changes", "") or ""
    json_file = args.get("json_file", "") or ""
    if not changes and not json_file:
        raise RuntimeError("Provide 'changes' (e.g. \"p5=180;p8=p5/2\" or "
                           "\"p0->side_length\") and/or 'json_file'.")
    if json_file and not os.path.isfile(json_file):
        raise RuntimeError("json_file not found: %s" % json_file)
    out = run_journal("nx_params.py",
                      {"NXPARAM_MODEL": model, "NXPARAM_ACTION": "set",
                       "NXPARAM_SET": changes, "NXPARAM_JSON": json_file})
    lines = [l for l in out.splitlines()
             if l.startswith(("SET", "RENAME", "FAIL", "SKIP", "JSON",
                              "Model rebuilt"))]
    jpath = os.path.splitext(model)[0] + "_params.json"
    text = "\n".join(lines) + "\n\nParameters after edit:\n" + read_if_exists(jpath)
    failed = any(l.startswith("FAIL") for l in lines) or \
        not any(l.startswith("Model rebuilt") for l in lines)
    return text, failed


TOOLS = [
    {
        "name": "generate_drawing",
        "description": "Generate an ASME-compliant engineering drawing from an "
                       "NX part file (headless). Produces <model>_dwg.prt (native "
                       "NX drawing), <model>_dwg.pdf, and a coverage report "
                       "listing every dimension/GD&T item placed or skipped. "
                       "Takes ~1-2 minutes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model_path": {"type": "string",
                               "description": "Absolute path to the .prt file"}
            },
            "required": ["model_path"],
        },
        "fn": tool_generate_drawing,
    },
    {
        "name": "list_parameters",
        "description": "List an NX model's parameters (expressions): name, "
                       "formula, value, units, and dependencies. Returns JSON.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model_path": {"type": "string",
                               "description": "Absolute path to the .prt file"}
            },
            "required": ["model_path"],
        },
        "fn": tool_list_parameters,
    },
    {
        "name": "edit_parameters",
        "description": "Change NX model parameters, then rebuild and save the "
                       "model. 'changes' is semicolon-separated: values or live "
                       "formulas (\"p5=180;p8=p5/2\") and renames "
                       "(\"p0->side_length\"). Optionally 'json_file' bulk-applies "
                       "an edited parameter JSON (format of list_parameters); "
                       "only changed formulas are applied. Returns the applied "
                       "changes and the updated parameter list.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model_path": {"type": "string",
                               "description": "Absolute path to the .prt file"},
                "changes": {"type": "string",
                            "description": "e.g. \"p5=180;p8=p5/2;p0->side_length\""},
                "json_file": {"type": "string",
                              "description": "Path to an edited parameter JSON"},
            },
            "required": ["model_path"],
        },
        "fn": tool_edit_parameters,
    },
]


def handle(req):
    method = req.get("method", "")
    rid = req.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": req.get("params", {}).get("protocolVersion",
                                                         PROTOCOL),
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "nx-tools", "version": "1.0.0"},
        }}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": rid, "result": {}}
    if method == "tools/list":
        pub = [{k: t[k] for k in ("name", "description", "inputSchema")}
               for t in TOOLS]
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": pub}}
    if method == "tools/call":
        params = req.get("params", {})
        name = params.get("name")
        tool = next((t for t in TOOLS if t["name"] == name), None)
        if tool is None:
            return {"jsonrpc": "2.0", "id": rid,
                    "error": {"code": -32602, "message": "unknown tool " + str(name)}}
        try:
            log("call %s" % name)
            text, is_err = tool["fn"](params.get("arguments", {}) or {})
        except Exception as ex:
            text, is_err = "Error: %s" % ex, True
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "content": [{"type": "text", "text": text}], "isError": is_err}}
    if method.startswith("notifications/"):
        return None
    if rid is None:
        return None
    return {"jsonrpc": "2.0", "id": rid,
            "error": {"code": -32601, "message": "method not found: " + method}}


def main():
    log("ready (NX at %s)" % find_nx())
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            log("dropped unparseable line: %r" % line[:120])
            continue
        resp = handle(req)
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
