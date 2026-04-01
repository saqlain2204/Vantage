import os
from rich import print
from rich.panel import Panel
from dotenv import load_dotenv

from vantage import run_yaml_agent, save_trace_png
from .tools import StackOverflowToolAgent

def main() -> None:
    load_dotenv()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(base_dir, "stack_overflow_agent.yaml")

    prompt = "How do I reverse a list in Python?"
    resp = run_yaml_agent(cfg_path, "stack_overflow_agent", prompt, tools=[StackOverflowToolAgent()])
    print(Panel(resp.content, title="[bold][green]Final Response[/green][/bold]", border_style="green"))
    
    # Save a visual trace
    save_trace_png(resp.trace, "examples/stack_overflow_agent/trace.png")
    print("\n[bold][green]Visual trace saved to examples/stack_overflow_agent/trace.png[/green][/bold]")

if __name__ == "__main__":
    main()
