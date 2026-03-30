import os
from rich import print
from rich.panel import Panel
from dotenv import load_dotenv

from vantage import run_yaml_agent, save_trace_png
from .tools import WordCountTool


def main() -> None:
    load_dotenv()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(base_dir, "word_agent.yaml")

    prompt = "How many words are in: 'Groq makes agents fast and precise'?"
    resp = run_yaml_agent(cfg_path, "word_agent", prompt, tools=[WordCountTool()])
    print(Panel(resp.content, title="[bold][green]Final Response[/green][/bold]", border_style="green"))
    
    # Save a visual trace
    save_trace_png(resp.trace, "examples/custom_tool_agent/trace.png")
    print("\n[bold][green]Visual trace saved to examples/custom_tool_agent/trace.png[/green][/bold]")


if __name__ == "__main__":
    main()

