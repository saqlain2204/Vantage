from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

from .config import load_agents_from_yaml


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="vantage")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="Run an agent from YAML")
    run.add_argument("--config", "-c", required=True, help="Path to YAML config")
    run.add_argument("--agent", "-a", required=True, help="Agent name in YAML")
    run.add_argument("--prompt", "-p", required=True, help="User prompt")

    args = parser.parse_args(argv)

    if args.cmd == "run":
        agents = {a.name: a.agent for a in load_agents_from_yaml(args.config)}
        if args.agent not in agents:
            raise SystemExit(f"Unknown agent: {args.agent}")
        resp = agents[args.agent].run(args.prompt)
        sys.stdout.write(resp.content.strip() + "\n")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())

