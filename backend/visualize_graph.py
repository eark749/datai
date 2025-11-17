"""
Visualize the LangGraph Agent Workflow
Run this to see the graph structure
"""

import sys
from app.database import SessionLocal
from app.agents.graph import create_agent_graph


def visualize_graph():
    """Generate and display the agent workflow graph"""
    
    # Create a database session (needed for graph creation)
    db = SessionLocal()
    
    try:
        print("Creating agent graph...")
        graph = create_agent_graph(db)
        
        print("\n" + "="*60)
        print("AGENT WORKFLOW GRAPH (ASCII)")
        print("="*60 + "\n")
        
        # Draw ASCII representation
        try:
            ascii_graph = graph.get_graph().draw_ascii()
            print(ascii_graph)
        except Exception as e:
            print(f"ASCII visualization not available: {e}")
        
        print("\n" + "="*60)
        print("AGENT WORKFLOW GRAPH (Mermaid)")
        print("="*60 + "\n")
        
        # Draw Mermaid diagram
        try:
            mermaid = graph.get_graph().draw_mermaid()
            print(mermaid)
            print("\n✨ Copy the Mermaid code above to https://mermaid.live to see the visual diagram!")
        except Exception as e:
            print(f"Mermaid visualization error: {e}")
        
        # Try to save as PNG (requires graphviz)
        print("\n" + "="*60)
        print("SAVING PNG...")
        print("="*60 + "\n")
        
        try:
            from langchain_core.runnables.graph import MermaidDrawMethod
            
            png_data = graph.get_graph().draw_mermaid_png(
                draw_method=MermaidDrawMethod.API
            )
            
            with open("agent_workflow.png", "wb") as f:
                f.write(png_data)
            
            print("✅ Graph saved as 'agent_workflow.png'!")
            print("   Open it to see your agent workflow diagram.")
        except Exception as e:
            print(f"⚠️ PNG generation failed: {e}")
            print("   Install graphviz if you want PNG output: pip install graphviz")
        
    finally:
        db.close()


if __name__ == "__main__":
    visualize_graph()


