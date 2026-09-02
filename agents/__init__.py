"""
PragyanAI SiliconAI
Autonomous RTL Verification Agent Package

This package contains all AI agents used by the
LangGraph-based autonomous RTL verification system.

Agent architecture:

    Specification
          |
          v
    RTL Analyzer
          |
          v
    Verification Planner
          |
          v
    Test Generator
          |
          v
    Testbench Generator
          |
          v
    Simulation Agent
          |
       +--+--+
       |     |
     PASS   FAIL
       |     |
       v     v
   Coverage Failure Analyzer
       |     |
       |     v
       | Bug Localization
       |     |
       |     v
       | RTL Repair
       |     |
       +-----+
          |
          v
      Red Team
          |
          v
      Mutation
          |
          v
       Formal
          |
          v
   Verification Judge
          |
          v
       Sign-off
"""

from .rtl_analyzer import RTLAnalyzerAgent
from .verification_planner import VerificationPlannerAgent
from .test_generator import TestGeneratorAgent
from .testbench_generator import TestbenchGeneratorAgent

from .red_team_agent import RedTeamAgent
from .simulator_agent import SimulatorAgent
from .failure_analyzer import FailureAnalyzerAgent
from .coverage_agent import CoverageAgent

from .mutation_agent import MutationAgent
from .formal_agent import FormalAgent
from .bug_localization_agent import BugLocalizationAgent

from .rtl_repair_agent import RTLRepairAgent
from .verification_judge import VerificationJudgeAgent


__all__ = [
    "RTLAnalyzerAgent",
    "VerificationPlannerAgent",
    "TestGeneratorAgent",
    "TestbenchGeneratorAgent",
    "RedTeamAgent",
    "SimulatorAgent",
    "FailureAnalyzerAgent",
    "CoverageAgent",
    "MutationAgent",
    "FormalAgent",
    "BugLocalizationAgent",
    "RTLRepairAgent",
    "VerificationJudgeAgent",
]
