from rich import print
from rich.panel import Panel
from dotenv import load_dotenv
from vantage import run_yaml_agent, Calculator, save_trace_png
from vantage.core.handovers import HandoverTool
from examples.custom_tool_agent.tools import WordCountTool

load_dotenv()

def main():
    cfg_path = "examples/multi_agent_flow/agents.yaml"
    
    # We define the handover tools and inject them at runtime
    math_handover = HandoverTool("math_expert", "Transfer to the math expert.")
    word_handover = HandoverTool("word_expert", "Transfer to the word expert.")
    
    tools = [
        Calculator(),
        WordCountTool(),
        math_handover,
        word_handover
    ]
    
    print("--- Vantage Multi-Agent Flow ---")
    prompt = "Can you count the words in 'Vantage is amazing' and then calculate 15 * 8?"
    
    resp = run_yaml_agent(cfg_path, "gatekeeper", prompt, tools=tools)
    
    print(Panel(resp.content, title="[bold][green]Final Response[/green][/bold]", border_style="green"))
    
    # Save trace
    save_trace_png(resp.trace, "examples/multi_agent_flow/trace.png")
    print("\n[bold][green]Visual trace saved to examples/multi_agent_flow/trace.png[/green][/bold]")

if __name__ == "__main__":
    main()
