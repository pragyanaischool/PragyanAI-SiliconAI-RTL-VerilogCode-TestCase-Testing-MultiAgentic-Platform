import os
import re
import subprocess
from pathlib import Path
from typing import TypedDict
import streamlit as st

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END

# -----------------------------------------------------------------------------
# Streamlit Page Configuration & Styling
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Agentic RTL Generator & Verifier",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Agentic RTL Design, Testbench & Verification Studio")
st.markdown(
    "Powered by **LangGraph**, **Groq (`openai/gpt-oss-120b`)**, and **Icarus Verilog**. "
    "Enter a hardware specification to automatically generate, test, debug, and verify your Verilog design and testbench."
)

# -----------------------------------------------------------------------------
# API Key Setup via Streamlit Secrets
# -----------------------------------------------------------------------------
groq_api_key = None
try:
    if "GROQ_API_KEY" in st.secrets:
        groq_api_key = st.secrets["GROQ_API_KEY"]
except Exception:
    pass

if not groq_api_key:
    groq_api_key = os.environ.get("GROQ_API_KEY")

if not groq_api_key:
    st.warning("⚠️ Groq API key not found in `st.secrets` or environment variables.")
    groq_api_key = st.text_input("Enter your Groq API Key:", type="password")
    if groq_api_key:
        os.environ["GROQ_API_KEY"] = groq_api_key
    else:
        st.info("Please provide a Groq API key to start the workflow.")
        st.stop()

# Ensure system dependencies (Icarus Verilog) are available
@st.cache_resource
def setup_environment():
    try:
        subprocess.run(["iverilog", "-V"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except (FileExistsError, FileNotFoundError, subprocess.SubprocessError):
        pass

setup_environment()

# -----------------------------------------------------------------------------
# Define LangGraph State Schema
# -----------------------------------------------------------------------------
class RTLState(TypedDict):
    prompt: str
    rtl_code: str
    test_code: str
    run_output: str
    error_log: str
    iteration: int
    max_iterations: int
    status: str

# Initialize Groq LLM with openai/gpt-oss-120b model
llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0.1, api_key=groq_api_key)

# -----------------------------------------------------------------------------
# Agent Nodes Definition
# -----------------------------------------------------------------------------
def rtl_generator_node(state: RTLState) -> dict:
    system_prompt = (
        "You are an expert Verilog RTL designer. Write synthesizable, clean Verilog code "
        "based on the user prompt. Return ONLY the raw Verilog code inside standard markdown "
        "code blocks (e.g. ```verilog ... ```). Do not include extraneous conversational text."
    )
    
    if state["error_log"]:
        user_msg = (
            f"Original Request: {state['prompt']}\n\n"
            f"Previous RTL Code:\n{state['rtl_code']}\n\n"
            f"Simulation/Compilation Failed with this error:\n{state['error_log']}\n\n"
            "Please fix the bugs in the Verilog RTL code."
        )
    else:
        user_msg = f"Write the Verilog RTL code for this specification: {state['prompt']}"

    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_msg)])
    content = response.content
    
    if "```verilog" in content:
        rtl = content.split("```verilog")[1].split("```")[0].strip()
    elif "```" in content:
        rtl = content.split("```")[1].split("```")[0].strip()
    else:
        rtl = content.strip()
        
    return {"rtl_code": rtl}

def testbench_generator_node(state: RTLState) -> dict:
    # Explicitly return an empty dictionary `{}` if already generated and looping back for RTL fixes
    if state["test_code"] and state["iteration"] > 0:
        return {}
        
    system_prompt = (
        "You are an expert hardware verification engineer. Write a self-checking Verilog testbench module "
        "that instantiates the design, applies clock/reset stimuli, monitors outputs using $display, "
        "and terminates simulation using $finish. Return ONLY raw Verilog testbench code inside "
        "```verilog ... ``` code blocks."
    )
    
    user_msg = (
        f"Write a self-checking Verilog testbench for this RTL design:\n{state['rtl_code']}\n"
        "Ensure it uses standard $display logs so output text shows simulation success or failure states."
    )
    
    response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_msg)])
    content = response.content
    
    if "```verilog" in content:
        tb = content.split("```verilog")[1].split("```")[0].strip()
    elif "```" in content:
        tb = content.split("```")[1].split("```")[0].strip()
    else:
        tb = content.strip()
        
    return {"test_code": tb}

def simulation_runner_node(state: RTLState) -> dict:
    # Write files locally for direct compilation
    with open("design.v", "w") as f:
        f.write(state["rtl_code"])
        
    with open("test_bench.v", "w") as f:
        f.write(state["test_code"])

    try:
        # Compile design and testbench using Icarus Verilog
        compile_cmd = ["iverilog", "-g2012", "-o", "sim_output", "design.v", "test_bench.v"]
        compile_res = subprocess.run(compile_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20)
        
        if compile_res.returncode != 0:
            error_msg = f"COMPILATION ERROR:\n{compile_res.stderr}"
            return {
                "run_output": error_msg,
                "error_log": error_msg,
                "status": "FAILED",
                "iteration": state["iteration"] + 1
            }
        
        # Run compiled simulation using vvp
        sim_cmd = ["vvp", "sim_output"]
        sim_res = subprocess.run(sim_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20)
        output = sim_res.stdout + "\n" + sim_res.stderr
        
        # Check simulation status based on execution output and return code
        if sim_res.returncode == 0 and "ERROR" not in output.upper() and "FAILED" not in output.upper():
            return {
                "run_output": output,
                "error_log": "",
                "status": "PASSED",
                "iteration": state["iteration"] + 1
            }
        else:
            return {
                "run_output": output,
                "error_log": output,
                "status": "FAILED",
                "iteration": state["iteration"] + 1
            }
    except Exception as e:
        err_str = str(e)
        return {
            "run_output": err_str,
            "error_log": err_str,
            "status": "FAILED",
            "iteration": state["iteration"] + 1
        }

def should_continue(state: RTLState) -> str:
    if state["status"] == "PASSED":
        return "end"
    elif state["iteration"] >= state["max_iterations"]:
        return "end"
    else:
        return "fix"

# Build LangGraph workflow
workflow = StateGraph(RTLState)
workflow.add_node("rtl_generator", rtl_generator_node)
workflow.add_node("testbench_generator", testbench_generator_node)
workflow.add_node("simulation_runner", simulation_runner_node)

workflow.set_entry_point("rtl_generator")
workflow.add_edge("rtl_generator", "testbench_generator")
workflow.add_edge("testbench_generator", "simulation_runner")
workflow.add_conditional_edges(
    "simulation_runner",
    should_continue,
    {
        "fix": "rtl_generator",
        "end": END
    }
)
app = workflow.compile()

# -----------------------------------------------------------------------------
# Streamlit User Interface Flow
# -----------------------------------------------------------------------------
user_prompt = st.text_area(
    "Describe your hardware requirement:",
    value="Design a 4-bit synchronous up-counter in Verilog with an active-low asynchronous reset (rst_n) and an enable signal (en)."
)

col1, col2 = st.columns(2)
max_iter = col1.slider("Max Auto-Correction Iterations", 1, 5, 3)
run_btn = col2.button("🚀 Generate, Test & Verify RTL", type="primary")

if run_btn:
    initial_state = {
        "prompt": user_prompt,
        "rtl_code": "",
        "test_code": "",
        "run_output": "",
        "error_log": "",
        "iteration": 0,
        "max_iterations": max_iter,
        "status": "PENDING"
    }
    
    progress_container = st.container()
    
    with progress_container:
        with st.status("Running Multi-Agent Hardware Verification Workflow...", expanded=True) as status_box:
            st.write("🤖 Initializing LangGraph state graph...")
            
            # Stream execution states safely with guarded update checks
            current_state = initial_state
            for step in app.stream(initial_state):
                node_name = list(step.keys())[0]
                node_update = step[node_name]
                
                if node_update:
                    current_state.update(node_update)
                    
                st.write(f"-> Executed **{node_name}** (Attempt: {current_state['iteration']})")
                if current_state.get("status") == "PASSED":
                    status_box.update(label="✅ Verification Completed Successfully!", state="complete", expanded=False)
                elif current_state.get("error_log") and node_name == "simulation_runner":
                    st.warning(f"⚠️ Simulation failed on attempt {current_state['iteration']}. Routing back to RTL Generator...")

            if current_state["status"] != "PASSED":
                status_box.update(label="❌ Verification Loop Finished with Errors or Max Iterations Reached", state="error", expanded=False)

    # Display Final Results in Tabs
    st.markdown("---")
    tab1, tab2, tab3, tab4 = st.tabs(["📂 Final Verilog RTL", "🧪 Verilog Testbench", "📊 Simulation Log", "📌 Status & Summary"])
    
    with tab1:
        st.code(current_state["rtl_code"], language="verilog")
        
    with tab2:
        st.code(current_state["test_code"], language="verilog")
        
    with tab3:
        st.text(current_state["run_output"])
        
    with tab4:
        if current_state["status"] == "PASSED":
            st.success("🎉 **Verified Result:** The Verilog RTL code compiled, executed native testbench assertions, and passed simulation successfully!")
        else:
            st.error("⚠️ **Status:** Reached max correction loops or encountered persistent errors. Check the simulation log tab for compiler traces.")
