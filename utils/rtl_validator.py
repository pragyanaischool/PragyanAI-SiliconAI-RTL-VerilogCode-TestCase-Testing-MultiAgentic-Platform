import subprocess
import tempfile
import os
from typing import Tuple

class RTLValidator:
    """
    Validates and lints Verilog/SystemVerilog RTL code using open-source EDA tools.
    """
    @staticmethod
    def check_syntax(rtl_code: str) -> Tuple[bool, str]:
        """
        Performs static syntax and compilation checks using Icarus Verilog (-g2012).
        Returns (is_valid: bool, output_message: str).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            rtl_path = os.path.join(tmpdir, "design.v")
            with open(rtl_path, "w", encoding="utf-8") as f:
                f.write(rtl_code)
                
            # -g2012 enables modern SystemVerilog parsing features
            # -t null parses and checks syntax without generating output binaries
            cmd = ["iverilog", "-g2012", "-t", "null", rtl_path]
            try:
                result = subprocess.run(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True, 
                    timeout=10
                )
                if result.returncode != 0:
                    return False, result.stderr.strip()
                return True, "Syntax check passed successfully."
            except FileNotFoundError:
                return False, "Error: Icarus Verilog ('iverilog') is not installed or not in system PATH."
            except subprocess.TimeoutExpired:
                return False, "Error: RTL compilation check timed out."

    @staticmethod
    def run_simulation(rtl_code: str, testbench_code: str) -> Tuple[bool, str, str]:
        """
        Compiles and simulates RTL together with its testbench.
        Returns (success: bool, simulation_output: str, error_log: str).
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            rtl_path = os.path.join(tmpdir, "design.v")
            tb_path = os.path.join(tmpdir, "tb.v")
            sim_out = os.path.join(tmpdir, "sim.out")

            with open(rtl_path, "w", encoding="utf-8") as f:
                f.write(rtl_code)
            with open(tb_path, "w", encoding="utf-8") as f:
                f.write(testbench_code)

            # Compile design + testbench
            comp_cmd = ["iverilog", "-g2012", "-o", sim_out, tb_path, rtl_path]
            comp_res = subprocess.run(comp_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            if comp_res.returncode != 0:
                return False, "", f"Compilation Failed:\n{comp_res.stderr.strip()}"

            # Run compiled simulation
            sim_cmd = [sim_out]
            sim_res = subprocess.run(sim_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
            
            if sim_res.returncode != 0:
                return False, sim_res.stdout, f"Simulation Runtime Error:\n{sim_res.stderr.strip()}"

            return True, sim_res.stdout.strip(), "Simulation passed successfully."
