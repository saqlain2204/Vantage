import os
from rich import print
from rich.panel import Panel
from dotenv import load_dotenv

from vantage import run_yaml_agent, WeatherTool, save_trace_png


def main() -> None:
    load_dotenv()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cfg_path = os.path.join(base_dir, "weather_agent.yaml")

    prompt = "What is the weather like in New York?"
    resp = run_yaml_agent(cfg_path, "weather_agent", prompt, tools=[WeatherTool()])
    print(Panel(resp.content, title="[bold][green]Final Response[/green][/bold]", border_style="green"))
    
    # Save a visual trace of the execution
    trace_path = os.path.join(base_dir, "trace.png")
    save_trace_png(resp.trace, trace_path)
    print(f"\n[bold][green]Visual trace saved to {trace_path}[/green][/bold]")


if __name__ == "__main__":
    main()

