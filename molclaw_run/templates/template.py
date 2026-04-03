"""
Workflow prompt templates for agent etc. to import.
"""
import json
import re

# System-level prompt constants
SYSTEM_PROMPT_MINIMAL = (
    "Complete the task as requested by the user with the given tools. "
    "Output in the required format."
)
PARAM_FILL_SYSTEM_PROMPT = (
    "Fill parameters according to tool schema; output in valid format. "
    "When a parameter lists valid_refs (previous tool output variables), prefer setting that parameter to one of the @var_name strings so the system can substitute the full data; do not paste long lists or paths yourself."
)
ACTION_SYSTEM_PROMPT = "Decide next action in ReAct mode; output in valid JSON format."
SUMMARY_SYSTEM_PROMPT_MINIMAL = "Summarize and extract key information."

ANSWER_OUTPUT_HINT = (
    "Output format (for evaluation): Put your final answer inside <answer>...</answer>. "
    "Use the exact format requested in the task."
)
# RDKit bench: few-shot so model always outputs <finish>...<answer>...</answer></finish>
RDKIT_ANSWER_HINT = (
    "Output format (required): When done, output <finish>brief summary<answer>SMILES1\nSMILES2\n...</answer></finish>. "
    "Example:\n"
    "<finish>Filtered molecules.<answer>COc1ccc(O)cc1\nCC(=O)Nc1ccc(O)cc1\n</answer></finish>"
)
# execute_python_code restricted environment (injected as temporary context when code tool is called)
EXECUTE_PYTHON_CODE_FORBIDDEN_HINT = (
    "execute_python_code restricted environment: "
    "Allowed imports: math, json, re, csv, datetime, collections, itertools, functools, typing. "
    "Do not import os/shutil/subprocess/ctypes/importlib or tools (e.g. read_variable). "
    "Environment provides open and os (open only within working dir; os has getcwd/listdir/chdir/path.join/path.exists etc., no delete or subprocess)."
)


def get_loop_task_prompt(
    loop_idx: int,
    loop_count: int,
    previous_loop_summary: str = "",
    previous_loop_finished: bool = False,
) -> str:
    """Generate task prompt for current round; working dir/file list are injected per round via variables_list_text, files_list_text."""
    round_label = f"Round {loop_idx + 1}/{loop_count}"
    if loop_idx == 0:
        strategy_block = "**This round:** First round, no prior context.\n"
    else:
        if previous_loop_summary and previous_loop_finished:
            strategy_block = f"""**Previous round (Loop {loop_idx}) summary:**
{previous_loop_summary}

**This round (Loop {loop_idx + 1}) strategy:** Previous round completed core task; this round can refine and improve on the results.

"""
        elif previous_loop_summary:
            strategy_block = f"""**Previous round (Loop {loop_idx}) summary:**
{previous_loop_summary}

**This round (Loop {loop_idx + 1}) strategy:** Previous round not fully completed; this round should continue unfinished work and avoid repeating completed work.

"""
        else:
            strategy_block = ""

    prompt = f"""{round_label}{' - continue optimization' if loop_idx > 0 else ''}

{strategy_block}**Task:** The task is given by the "Initial query" below. Use the variables, files and tools provided this round.

**Hint:** For file path parameters under the working dir, provide only the filename.

**Completion:** When done, output <finish>task summary</finish> in the finish field; if there is a final answer for evaluation, wrap it in <answer>...</answer> and include it in finish. If you need the full content of a registered variable (e.g. a prior tool output) before finalizing, use read_variable(variable_name) to retrieve it.
Do not use execute_python_code to view or read variable values; it has no access to tool outputs (@variables)."""
    return prompt


def get_loop_summary_prompt(
    loop_idx: int,
    user_query: str,
    completion_status: str,
    formatted_context: str,
    target_length: int = 200,
) -> str:
    """Generate summary prompt for this loop."""
    return f"""Summarize the execution result of round {loop_idx + 1} for the initial query: "{user_query}"

**Completion status**: {completion_status}

Work completed this round:
{formatted_context}

Generate a concise summary (approx. {target_length} chars) including:
1. Main work completed this round
2. Key results
3. Current state (main files, variables, etc.). Given the list of filenames under working_dir in the context above, add a short description of each file's current role/purpose based only on the provided context (do NOT guess roles without evidence) in the format:
   - filename_1: description_1
   - filename_2: description_2
   For example, if the files are tmp_ligands.smi and target_AlphaFold_fix.pdbqt, you might write:
   - tmp_ligands.smi: SMILES list of candidate ligands used as docking inputs this round.
   - target_AlphaFold_fix.pdbqt: prepared receptor structure (fixed + converted to PDBQT) used for docking this round.
4. Which core tasks are done and which are not

Requirements:
- Summary length approx. {target_length} chars
- Only key information, concise
- Highlight progress toward the initial query
- Clearly state completed vs. incomplete parts

Summary:"""


def get_intention_identification_prompt(
    user_input: str,
    all_tools_description: str
) -> str:
    """Generate intention identification prompt.
    
    Args:
        user_input: User input.
        all_tools_description: Description of all available tools.
    
    Returns:
        Intention identification prompt string.
    """
    prompt = f"""
Analyze the user input, identify the task the user wants to complete, and determine which tools need to be executed.

User input: {user_input}

Available tools:
{all_tools_description}

Return the analysis in the following JSON format:
{{
"task_type": "task type",
"required_tools": ["list of tool names to execute"],
"parameters": {{
    "tool_name": {{
    "param_name": "param value or info extracted from user input"
    }}
}},
"dependencies": {{
    "tool_name": ["list of dependent tool names"]
}},
"execution_plan": ["tool names in execution order"]
}}
"""
    return prompt


def get_task_planning_prompt(
    user_input: str,
    intention: dict,
    context: dict,
    all_tools_description: str
) -> str:
    """Generate task planning prompt.
    
    Args:
        user_input: User input.
        intention: Intention analysis result.
        context: Current context.
        all_tools_description: Description of all available tools.
    
    Returns:
        Task planning prompt string.
    """
    context_str = json.dumps(context, indent=2, ensure_ascii=False)
    intention_str = json.dumps(intention, ensure_ascii=False)
    
    prompt = f"""
Generate a detailed execution plan from the user input and intention analysis.
User input: {user_input}
Intention: {intention_str}
Current context: {context_str}

Available tools:
{all_tools_description}

Consider:
1. Dependencies between tools

Generate a detailed execution plan.
For tools that need a previous step's result as input, use placeholders like {{tool_name.field_name}}.

Return the plan in the following JSON format:
[
{{
    "step": 1,
    "tool_name": "tool name",
    "description": "description of what the tool does",
    "params": {{
    "param_name": "param value or dependency ref {{tool_name.field_name}}"
    }},
    "dependencies": ["list of dependent tool names (base names)"]
}}
]
"""
    return prompt


def get_task_summary_prompt(
    prompt: str,
    semantic_plan: dict,
    action_history: list,
    results: dict,
    context: dict
) -> str:
    """Generate task summary prompt.
    
    Args:
        prompt: Original requirement.
        semantic_plan: Semantic plan.
        action_history: Execution history.
        results: Execution results.
        context: Current context.
    
    Returns:
        Task summary prompt string.
    """
    context_str = json.dumps(context, indent=2, ensure_ascii=False)
    
    summary_prompt = f"""Generate a task summary based on the current execution context.

Original requirement:
{prompt}

Semantic plan:
{json.dumps(semantic_plan, ensure_ascii=False)}

Execution history ({len(action_history)} steps):
{json.dumps(action_history[-10:], ensure_ascii=False, indent=2)}

Execution results:
{json.dumps({k: str(v)[:500] for k, v in list(results.items())[-10:]}, ensure_ascii=False, indent=2)}

Current context:
{context_str[:2000]}

Generate a concise but complete task summary including:
1. Main tasks completed
2. Key results obtained
3. Issues or incomplete parts
4. Suggested next steps (if any)

Return the summary text."""
    
    return summary_prompt


def get_next_action_prompt(
    prompt: str,
    semantic_plan: dict,
    context: dict,
    all_tools_description: str,
    last_observation: str = None,
    action_history: list = None
) -> str:
    """Generate next-action decision prompt (ReAct mode).
    
    Args:
        prompt: Original requirement.
        semantic_plan: Semantic plan.
        context: Current context.
        all_tools_description: Description of all available tools.
        last_observation: Last tool execution result (external feedback).
        action_history: History of execution (all Thought-Action-Observation cycles).
    
    Returns:
        Next-action decision prompt string.
    """
    context_str = json.dumps(context, indent=2, ensure_ascii=False)
    
    # Build execution history in ReAct format
    react_history_section = ""
    if action_history:
        react_history_section = "\n**Execution history:**\n"
        for idx, action_entry in enumerate(action_history, 1):
            thought = action_entry.get('thought', '')
            action = action_entry.get('action', {})
            observation = action_entry.get('observation', '')
            
            # Extract thought content (strip XML tags)
            thought_match = re.search(r'<thought>(.*?)</thought>', thought, re.DOTALL)
            thought_content = thought_match.group(1).strip() if thought_match else thought
            
            # Extract action info
            tool_name = action.get('tool_name', '') if isinstance(action, dict) else ''
            reasoning = action.get('reasoning', '') if isinstance(action, dict) else ''
            
            react_history_section += f"\n--- Iteration {idx} ---\n"
            react_history_section += f"Thought: {thought_content}\n"
            if tool_name:
                react_history_section += f"Action: call tool {tool_name}\n"
                if reasoning:
                    react_history_section += f"Reasoning: {reasoning}\n"
            if observation:
                react_history_section += f"Observation: {observation[:500]}{'...' if len(observation) > 500 else ''}\n"
    
    # If there is a last observation, list it separately (as latest external feedback)
    last_obs_section = ""
    if last_observation:
        last_obs_section = f"\n**Last execution result (Observation, external feedback):**\n{last_observation}\n"
    
    action_prompt = f"""Work in Reasoning + Acting mode.

Original requirement:
{prompt}

Semantic plan:
{json.dumps(semantic_plan, ensure_ascii=False)}
{react_history_section}
{last_obs_section}
Current execution context (results so far):
{context_str}

Available tools:
{all_tools_description}

Analyze current state and decide next step in Reasoning + Acting format:
1. <thought>Based on context and semantic plan, think about what to do next</thought>
2. <action>Decide which tool to call and with what parameters</action>

Note:
- <observation> is external feedback from tool execution; you do not generate it
- You only generate <thought> and <action>

Safety: Do not use delete operations (rm, rmdir, etc.).

**Task completion:** When the goal is reached (e.g. file created, data processed), you can output <finish>task summary</finish> in the finish field and the loop will stop.

Return the following JSON (action needs only tool_name and reasoning; params will be filled later):
{{
    "thought": "<thought>what to do next</thought>",
    "action": {{
        "tool_name": "tool name to call (or null if none)",
        "reasoning": "why this tool"
    }},
    "should_continue": true/false,
    "finish": null  // If task is done, output <finish>task summary</finish> here; otherwise null
}}"""
    
    return action_prompt



def get_reinvent_task_prompt(
    results_dir: str,
    dataset_filename: str
) -> str:
    """Generate base prompt for Reinvent task (example; adjust as needed)."""
    return f"""Task: Given molecules, generate structurally modified molecules and evaluate/compare them.

Working dir: {results_dir}
Dataset file: {dataset_filename}

Plan and execute the task with available tools. You may:
- Read and process molecule data
- Generate new molecular structures
- Evaluate and analyze properties
- Compare and filter molecules
- Save result files

Note: exec_command should not be used for delete operations (rm, rmdir, etc.)."""


def get_action_prompt(
    task_prompt: str,
    tools_list_text: str,
    context_str: str,
    files_list_text: str = "",
    variables_list_text: str = "",
    action_history_in_round: str = "",
) -> str:
    """Generate action prompt. When there is action history, CL observations (variables_list_text) are merged under Actions (2-in-1)."""
    action_block = ""
    variables_section = variables_list_text
    if action_history_in_round:
        action_block = f"""
**Actions already taken in this round (each step above; do not repeat the same tool with same inputs):**
{action_history_in_round}
"""
        if variables_list_text.strip():
            action_block += f"""
{variables_list_text}
"""
        variables_section = ""  # already merged above; avoid duplicate listing
    return f"""{task_prompt}
{action_block}
Available files (use #filename for path param; read_file(filename) for content)
{files_list_text}

Available tools
{tools_list_text}

Variables and files (for tool input: @name or @name.field in tool params for content; #filename in tool params for path; read_file(filename) for content)
{variables_section}

Current context (full data of executed results):
{context_str}

Decide what to do next. Return JSON:
{{
    "thought": "your reasoning",
    "tool_name": "tool name to call",
    "reasoning": "why this tool",
    "should_continue": true/false,
    "finish": null or "<finish>task summary</finish>". If there is a clear final answer for evaluation, wrap it in <answer>...</answer> and include it in the finish field.
}}"""
