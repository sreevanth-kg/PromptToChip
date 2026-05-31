# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Commands

### Setup and Installation
- Create virtual environment: `python -m venv gemini_v`
- Activate virtual environment: `.\gemini_v\Scripts\activate` (Windows) or `source gemini_v/bin/activate` (Unix)
- Install dependencies: `pip install -r requirements.txt`

### Running the Application
- Start the main chat app: `python project_test_1.py`

### Validation and Testing
- Run the board-package end-to-end validation: `python module3_validation.py`

## Architecture Overview

PromptToChip is a terminal-based chat application that integrates general-purpose LLMs (Google Gemini/Gemma) with a specialized local RTLH-coding LLM (Ollama `codev-rtl:latest`).

### Core Components
- **Main Orchestrator (`project_test_1.py`)**: Manages user sessions, chat history (`chat_memory.json`), and routing. It uses a heuristic to detect HDL/FPGA-related requests and delegates them to the Coder Agent.
- **Coder Agent (`coder_agent.py`)**: An adapter for the local Ollama model. It is responsible for generating Verilog/HDL and associated constraint files.
- **Hardware Bridge (`hardware_bridge/`)**: Provides physical hardware context (e.g., for Tang Nano 9K). This ensures that generated RTL uses correct pin mappings and clock frequencies by injecting board-package data into the Coder Agent's prompt.
- **Validation Layer (`module3_validation.py`)**: Performs automated checks on generated artifacts to verify that pin mappings match the hardware board package and that board profiles (like clock frequency) are correctly applied.

### Data Flow
1. User input $\rightarrow$ `project_test_1.py`.
2. Routing: General $\rightarrow$ Gemini API | RTL/HDL $\rightarrow$ `coder_agent.py`.
3. `coder_agent.py` $\rightarrow$ fetches board context from `hardware_bridge/` $\rightarrow$ calls Ollama $\rightarrow$ outputs Verilog/CST files.
4. (Optional) `module3_validation.py` $\rightarrow$ parses output $\rightarrow$ validates against `hardware_bridge/` data.
