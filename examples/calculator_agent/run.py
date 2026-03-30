import os
from rich import print
from rich.panel import Panel
from dotenv import load_dotenv

from vantage import run_yaml_agent, Calculator, save_trace_png


def main() -> None:
    load_dotenv()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(base_dir, "calculator.yaml")

    prompt = "What is (12 + 8) / 5?"
    resp = run_yaml_agent(cfg_path, "calculator", prompt, tools=[Calculator()])
    print(Panel(resp.content, title="[bold][green]Final Response[/green][/bold]", border_style="green"))
    
    # Save a visual trace of the execution
    save_trace_png(resp.trace, "examples/calculator_agent/trace.png")
    print("\n[bold][green]Visual trace saved to examples/calculator_agent/trace.png[/green][/bold]")


if __name__ == "__main__":
    main()

