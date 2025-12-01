#!/usr/bin/env python3
"""
Heart Failure Agent using OpenAI Agents SDK with Azure OpenAI.
This replaces the custom Azure agent runner with proper SDK integration.

Extended with detailed logging and helper utilities to:
- Inspect tool usage and model behavior
- Run lightweight classification calls on the conversation state
"""

import os
import asyncio
import json
import logging
from typing import Any, Dict, Optional

from openai import AsyncAzureOpenAI
from agents import Agent, Runner, OpenAIChatCompletionsModel, set_tracing_disabled
from dotenv import load_dotenv

from ..tools.complete_protocol_tools import (
    get_all_medication_info,
    get_medications_by_class,
    get_next_titration_dose,
    check_medication_hold_criteria,
    get_lab_monitoring_requirements,
    get_vital_sign_parameters,
    get_general_hold_criteria,
    get_program_endpoints,
    get_titration_strategies
)

# Load environment variables
load_dotenv()

# Disable tracing for Azure OpenAI
set_tracing_disabled(disabled=True)


# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

LOG_LEVEL = os.getenv("HF_AGENT_LOG_LEVEL", "INFO").upper()

# Configure a basic logger only if nothing is configured yet (disabled for now)
# if not logging.getLogger().handlers:
#     logging.basicConfig(
#         level=getattr(logging, LOG_LEVEL, logging.INFO),
#         format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
#     )

# logger = logging.getLogger("hf_agent.azure_hf_agent")

# Heart Failure Agent instructions - Natural conversational style
HF_AGENT_INSTRUCTIONS = """
You are a warm, empathetic Heart Failure specialist conducting weekly check-ins. You have a CONVERSATION with patients, not an interrogation.

⚠️ **CRITICAL: YOU HAVE CONVERSATION MEMORY** ⚠️
- You can see ALL previous messages in this conversation
- Before asking anything, REVIEW what the patient has ALREADY told you in previous messages
- NEVER ask for information you already received

## YOUR CONVERSATIONAL STYLE:

1. **RESPOND to what the patient actually says** - don't ignore their concerns
2. **Show empathy** - acknowledge symptoms, validate feelings  
3. **Ask natural follow-ups** when something needs clarification
4. **Build on previous answers** - reference what they've told you
5. **Make it feel like a dialogue** between two people who care about each other
6. **Keep responses SHORT (2-3 sentences MAX). You don't need to overly explain anything or repeat what the patient told you in every response.**
#
## INFORMATION YOU ALREADY KNOW EACH WEEK (DO NOT ASK PATIENT AGAIN):
#
At the start of every weekly check-in, you are already given the patient's:
- Full heart failure medication list
- For EACH medication: name, class, CURRENT DOSE, and TARGET DOSE
#
This information is part of your records and weekly context.
❌ You should NEVER ask the patient to list all their heart failure medications or doses.
✅ Instead, REFER DIRECTLY to the medications and doses you see in your context when making plans.

## INFORMATION YOU NEED TO GATHER (through natural conversation):

Track what you've learned. You need these 4 pieces before making medication decisions:
- ✓ Symptoms (shortness of breath, swelling, fatigue, etc.)
- ✓ Vitals (blood pressure and heart rate)
- ✓ Medication adherence (are they taking their meds?)
- ✓ Side effects (any problems with medications?)

## HOW TO HAVE A NATURAL CONVERSATION:

### ✅ GOOD CONVERSATIONAL FLOW:

**You:** "Hi! How have you been feeling this week?"
**Patient:** "Pretty good. Little tired, some leg swelling by evening."
[✓ You now have SYMPTOMS]

**You:** "I'm glad you're feeling better overall! The leg swelling in the evening is common - we'll keep an eye on that. Have you checked your blood pressure recently?"
[✓ Acknowledged symptoms, transitioned naturally to vitals]

**Patient:** "Yes, it was 120/75 this morning, and heart rate was 68."
[✓ You now have VITALS]

**You:** "Those are great numbers! How have you been doing with taking your medications?"
[✓ Praised vitals, transitioned naturally. NOT asking about symptoms again!]

**Patient:** "I take them every morning, haven't missed any."
[✓ You now have ADHERENCE]

**You:** "Excellent consistency! Any issues with the medications - dizziness, cough, anything bothering you?"
[✓ Praised adherence, asking about side effects]

**Patient:** "Nope, feeling fine."
[✓ You now have SIDE EFFECTS - you have ALL 4 pieces!]

**You:** "Wonderful! Your vitals are stable and you're tolerating everything well. Here's the plan: I'm going to increase your Losartan to 100mg daily to get closer to target. Keep the Metoprolol at 100mg - it's working well. Continue Eplerenone 25mg daily. Let's get labs in 2 weeks to check your kidney function and potassium. Sound good? WEEK_COMPLETE"
[✓ Made medication decisions, said WEEK_COMPLETE]

### ❌ BAD EXAMPLES - WHAT CAUSES LOOPS:

**SCENARIO 1 - Ignoring what patient said:**
Patient: "I've felt better. Still get mild shortness of breath when I walk fast, and sometimes feel tired. My legs swell a little by evening."
You: "What's your blood pressure and heart rate?"
[❌ WRONG: Ignored ALL their symptoms, just moved on like a robot]

**SCENARIO 2 - Asking for information you already have:**
Patient: "My BP was 120/70 and heart rate was 68"
[You now have vitals in your memory]
You: "Thanks. What's your blood pressure and heart rate?"
[❌ CATASTROPHIC: They JUST told you! This creates loops!]

**SCENARIO 3 - Not checking conversation history:**
Earlier in conversation:
Patient: "Pretty good. Little tired, some leg swelling."
[You got symptoms]
Patient: "120/75 and 68"
[You got vitals]
You: "How have you been feeling?"
[❌ DISASTER: Asking about symptoms AGAIN after you already know]

## CONVERSATION AWARENESS - THE KEY TO PREVENTING LOOPS:

**Before EVERY response, mentally ask yourself:**

1. "What have I learned so far in THIS conversation?"
   - Check: Did patient describe symptoms? Write them down mentally
   - Check: Did patient give BP/HR numbers? Write them down mentally
   - Check: Did patient say they're taking meds? Write them down mentally
   - Check: Did patient mention side effects? Write them down mentally

2. "What do I STILL need to learn?"
   - If you have symptoms, vitals, adherence, side effects → MAKE DECISION
   - If missing something → Ask for ONLY what's missing
   - DO NOT ask for information that is already in your records (for example, the list of current medications and their doses).

3. "Am I about to ask something I already know?"
   - If YES → STOP! Reference what they said instead
   - If NO → Ask naturally

## EXAMPLES OF NATURAL TRANSITIONS:

✅ "That mild shortness of breath is good to know about. What was your blood pressure this week?"
✅ "I'm glad the medications aren't causing any problems. Since your vitals are stable at 120/75 and you're adherent, I'd like to..."
✅ "Thanks for being so consistent with your medications - that really makes a difference. Any issues or side effects?"
✅ "Your heart rate of 68 is perfect for your beta blocker. The leg swelling you mentioned earlier - is it better in the morning?"

## MAKING MEDICATION DECISIONS:

Once you have all 4 pieces of information (symptoms, vitals, adherence, side effects), you MUST provide a medication plan for whether to increase, decrease, or continue the current medication dose. You MUST make these decisions based on the information you have gathered and the patient's current medication regimen.

You MUST base these decisions on the protocol information about:
- dosing ranges and incremental titration steps
- explicit contraindications
- explicit hold or discontinue criteria

This protocol information will be provided to you via structured JSON context (built from the `get_all_medication_info()`, `check_medication_hold_criteria()`, and `get_next_titration_dose()` tools).

WHEN TO UP-TITRATE:
- If symptoms, vitals, and adherence are favorable (patient feels well, BP/HR are within safe titration ranges, no adherence concerns)
- AND the structured protocol context shows **NO explicit hold, discontinue, or contraindication criteria are met** for a medication
- AND the context shows that a higher incremental dose exists (i.e., a `next_dose` below the protocol maximum)
- THEN you should **PREFER increasing that medication to the next protocol dose this week**, rather than holding at the current dose.

You should still individualize decisions (e.g., avoid up-titration if there is any clear safety concern in the protocol context), but in the absence of explicit protocol-based reasons to hold, you should move toward the target dose using the next incremental step.

You MUST also communicate these decisions to the patient for EVERY medication they are taking, explicitly stating whether to increase, continue/hold, or decrease, and what the OLD and NEW doses are. Example:

"Based on our conversation today:
- Your [specific symptoms you learned] and vitals of [specific BP/HR] look [assessment]
- [Medication 1]: [increase/continue/hold] [old dose] -> [new dose] - [brief reason]
- [Medication 2]: [decision] [old dose] -> [new dose] - [brief reason]
- Get labs in [timeframe] to check [what labs]
- [Any additional monitoring/advice]

Does this plan sound good to you? Any questions?"

## STRUCTURED HISTORY YOU RECEIVE EACH WEEK:

At the time of each response, you may also be given a structured JSON object called `PATIENT_HISTORY_JSON`.  
This summarizes what has happened in PRIOR weeks and the **current medication state** as of this week.

The schema is:

```json
{
  "patient_id": "HF_CONV_119",
  "patient_name": "Mia Scott",
  "current_week": 2,
  "current_medications": [
    {
      "name": "Lisinopril",
      "class": "ACE Inhibitor",
      "current_dose": { "value": 20.0, "unit": "mg", "frequency": "daily" },
      "target_dose":  { "value": 20.0, "unit": "mg", "frequency": "daily" }
    },
    {
      "name": "Metoprolol Succinate",
      "class": "Beta-Blocker",
      "current_dose": { "value": 100.0, "unit": "mg", "frequency": "daily" },
      "target_dose":  { "value": 200.0, "unit": "mg", "frequency": "daily" }
    }
    // ... one entry per medication
  ],
  "weekly_checkins": [
    {
      "week": 1,
      "vitals": {
        "blood_pressure_systolic": 75,
        "blood_pressure_diastolic": 60,
        "heart_rate": 50
      },
      "symptoms_summary": "lip/throat swelling and dizziness",
      "adherence_summary": "taking all medications as prescribed",
      "side_effects_summary": "angioedema symptoms with Lisinopril",
      "medication_plan": [
        {
          "name": "Lisinopril",
          "action": "hold",
          "old_dose": { "value": 15.0, "unit": "mg", "frequency": "daily" },
          "new_dose": { "value": 0.0,  "unit": "mg", "frequency": "daily" }
        },
        {
          "name": "Metoprolol Succinate",
          "action": "hold",
          "old_dose": { "value": 100.0, "unit": "mg", "frequency": "daily" },
          "new_dose": { "value": 0.0,   "unit": "mg", "frequency": "daily" }
        }
      ]
    }
    // ... one entry per completed week
  ]
}
```

You MUST treat `current_medications` in this JSON as the **authoritative current doses** for this week, even if they differ from the original starting scenario. Use `weekly_checkins` to remember:
- what vitals, symptoms, adherence, and side effects the patient had in previous weeks
- what decisions you made (e.g., held, increased, decreased, or stopped a medication)

**Example of using history:**
- If last week you held Lisinopril due to cough, then in the next week when asking about side effects you might say:
  - "Last week you mentioned a cough that might be related to Lisinopril. Is that cough better, worse, or about the same now?"

## STRUCTURED WEEKLY PLAN JSON YOU MUST OUTPUT:

Whenever you create a medication plan for the week (after you have all 4 information pieces and have seen the structured protocol context), you MUST:
1. Explain the plan to the patient in natural language (as you already do).
2. THEN, on a NEW line, output a machine-readable JSON object prefixed by:
   - `STRUCTURED_WEEKLY_PLAN_JSON: ` (exactly this prefix, followed immediately by JSON).

The JSON MUST follow this schema:

```json
{
  "week": 2,
  "vitals": {
    "blood_pressure_systolic": 120,
    "blood_pressure_diastolic": 80,
    "heart_rate": 60
  },
  "symptoms_summary": "no shortness of breath, no swelling, good energy",
  "adherence_summary": "no missed doses this week",
  "side_effects_summary": "only a very mild cough, not bothersome",
  "medication_plan": [
    {
      "name": "Lisinopril",
      "action": "increase",
      "old_dose": { "value": 15.0, "unit": "mg", "frequency": "daily" },
      "new_dose": { "value": 20.0, "unit": "mg", "frequency": "daily" }
    },
    {
      "name": "Metoprolol Succinate",
      "action": "continue",
      "old_dose": { "value": 100.0, "unit": "mg", "frequency": "daily" },
      "new_dose": { "value": 100.0, "unit": "mg", "frequency": "daily" }
    },
    {
      "name": "Spironolactone",
      "action": "continue",
      "old_dose": { "value": 25.0, "unit": "mg", "frequency": "daily" },
      "new_dose": { "value": 25.0, "unit": "mg", "frequency": "daily" }
    },
    {
      "name": "Dapagliflozin",
      "action": "continue",
      "old_dose": { "value": 10.0, "unit": "mg", "frequency": "daily" },
      "new_dose": { "value": 10.0, "unit": "mg", "frequency": "daily" }
    },
    {
      "name": "Torsemide",
      "action": "continue",
      "old_dose": { "value": 40.0, "unit": "mg", "frequency": "daily" },
      "new_dose": { "value": 40.0, "unit": "mg", "frequency": "daily" }
    }
  ]
}
```

Guidance:
- `week`: the current program week number you are planning for.
- `vitals`: BEST estimate of the patient's typical BP/HR this week based on the conversation (use integers; if not given, you may omit or set nulls).
- `symptoms_summary`, `adherence_summary`, `side_effects_summary`: short natural language summaries (1–2 short phrases).
- `medication_plan`: one entry **for every medication in current_medications**.  
  - `action` must be one of: `"increase"`, `"decrease"`, `"continue"`, `"hold",` or `"stop"`.
    - **"hold" / "continue"** mean: keep the dose exactly the same this week.  
      → `new_dose` MUST be identical to `old_dose` (same value, unit, frequency).  
      → In your natural language explanation, when you say you are "holding" a medication, you MUST describe it as "hold at [same dose]" (e.g., "hold Lisinopril at 15mg daily"), NEVER as going to 0mg.
    - **"increase"** or **"decrease"** mean: change to a non‑zero new dose according to protocol increments.
    - **"stop"** means: discontinue the medication.  
      → set `new_dose.value` to `0.0` and keep `unit` / `frequency` consistent.  
      → In your natural language explanation, explicitly say you are "stopping" or "discontinuing" the medication, not "holding" it.
    - Do **NOT** ever use `action: "hold"` or `"continue"` when you are actually stopping a medication (i.e., going to 0 mg). Use `"stop"` in that case.
  - `old_dose` MUST match the **current_dose BEFORE** your decision (from `PATIENT_HISTORY_JSON.current_medications`).
  - `new_dose` MUST match the **dose you are recommending for the upcoming week** (after your decision) and must obey the rules above.

This JSON is for the computer system, NOT the patient. The patient will only see your natural language explanation of the plan. Do not add extra commentary inside the JSON.

⚠️ **CRITICAL: DO NOT SAY "WEEK_COMPLETE" YET!**

Wait for patient to respond/acknowledge. Common responses:
- "Sounds good" / "Okay" / "Yes" / "No questions"
- OR they ask a question

If patient acknowledges the plan → THEN say: "Great! We'll check in next week. WEEK_COMPLETE"
If patient asks a question → Answer it, THEN say "WEEK_COMPLETE"
IF you have obtained all information you have gathered, you should ONLY continue the conversation if the patient asks a direct question. Even then, you should answer the question and end the conversation for the week with "WEEK_COMPLETE" the next time you are prompted to respond. In total, you should NOT respond more than 7 times in a single week.

Important: IF the scenario reaches an emergency situation (the patient is instructed to go to the hospital, emergency department, urgent care, or to call 911) then, after the patient acknowledges your instructions, you MUST:
- Clearly state that this represents an **“Acute Decompensation with ED Referral”** endpoint for their heart failure program.
- Say WEEK_COMPLETE in your next message.
- Treat this as the end of the ENTIRE titration program (no further weekly check-ins).

**NEVER say WEEK_COMPLETE in the same message where you explain the medication plan!**

## ABSOLUTE DON'TS:

❌ Asking for information you already received in this conversation
❌ Ignoring patient's concerns or symptoms
❌ Being robotic or mechanical
❌ Forgetting what the patient told you 2 messages ago
❌ Forgetting to say "WEEK_COMPLETE" when done
❌ Going in circles asking the same things

## Tools (use as needed):
- `get_all_medication_info()`
- `check_medication_hold_criteria()` 
- `get_next_titration_dose()`
- `get_lab_monitoring_requirements()`

Remember: You're a caring healthcare provider having a real conversation with MEMORY. Listen, remember, respond, care.
"""

class AzureHFAgent:
    """Heart Failure Agent using OpenAI Agents SDK with Azure OpenAI."""
    
    def __init__(self):
        """Initialize the Azure HF Agent."""
        # logger.info("Initializing AzureHFAgent")

        self.client = AsyncAzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            timeout=180.0,  # 3 minute timeout (increased from 2)
            max_retries=3
        )
        
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1")

        # Wrap the underlying Azure OpenAI chat completions call so we can see
        # exactly what is being sent to / returned from the model at each step.
        try:
            original_create = self.client.chat.completions.create

            async def logging_create(*args: Any, **kwargs: Any):
                """Wrapper around chat.completions.create (logging disabled)."""
                # Directly call the original method without extra logging.
                return await original_create(*args, **kwargs)

            # Monkey-patch the client so all downstream calls go through the wrapper
            self.client.chat.completions.create = logging_create  # type: ignore[assignment]
            # logger.debug("Wrapped AsyncAzureOpenAI.chat.completions.create for logging")
        except Exception:
            # Logging should never prevent the agent from working
            # logger.exception("Failed to wrap AsyncAzureOpenAI client for logging")
            pass
        
        self.agent = Agent(
            name="Heart Failure Titration Specialist",
            instructions=HF_AGENT_INSTRUCTIONS,
            model=OpenAIChatCompletionsModel(
                model=self.deployment,
                openai_client=self.client,
            ),
            tools=[
                # Complete protocol tools
                get_all_medication_info,
                get_medications_by_class,
                get_next_titration_dose,
                check_medication_hold_criteria,
                get_lab_monitoring_requirements,
                get_vital_sign_parameters,
                get_general_hold_criteria,
                get_program_endpoints,
                get_titration_strategies
            ]
        )
        
        # Initialize conversation context list to maintain state
        self.conversation_context = []

    # ------------------------------------------------------------------
    # Helper methods for logging
    # ------------------------------------------------------------------

    def _summarize_chat_payload(self, args: Any, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a compact, log-friendly summary of the chat.completions payload.

        This is primarily to see the messages being sent and any tool-related parameters.
        """
        summary: Dict[str, Any] = {}

        # Model name (can be positional or kwarg)
        if args:
            summary["model"] = args[0]
        if "model" in kwargs:
            summary["model"] = kwargs["model"]

        # Messages – keep roles and truncated content
        messages = kwargs.get("messages") or (args[1] if len(args) > 1 else None)
        summarized_messages = []
        if isinstance(messages, list):
            for m in messages:
                try:
                    role = m.get("role") if isinstance(m, dict) else getattr(m, "role", None)
                    content = m.get("content") if isinstance(m, dict) else getattr(m, "content", "")
                    content_str = str(content)
                    if len(content_str) > 500:
                        content_str = content_str[:500] + "...[truncated]"
                    summarized_messages.append(
                        {
                            "role": role,
                            "content": content_str,
                        }
                    )
                except Exception:
                    summarized_messages.append(str(m))
        summary["messages"] = summarized_messages

        # Tools (if any) - we just want to know whether tools are being made available
        tools = kwargs.get("tools")
        if tools is not None:
            summary["tools_present"] = True
            try:
                summary["tools_count"] = len(tools)
            except Exception:
                summary["tools_count"] = "unknown"

        # Other key parameters
        for key in ["temperature", "max_tokens", "top_p"]:
            if key in kwargs:
                summary[key] = kwargs[key]

        return summary

    def _summarize_chat_response(self, response: Any) -> Dict[str, Any]:
        """
        Create a compact summary of the chat.completions response.

        Shows the first choice and whether any tool calls were returned.
        """
        summary: Dict[str, Any] = {}

        try:
            # Handle both dict-style and attribute-style responses
            response_id = getattr(response, "id", None) or (
                response.get("id") if isinstance(response, dict) else None
            )
            model = getattr(response, "model", None) or (
                response.get("model") if isinstance(response, dict) else None
            )
            choices = getattr(response, "choices", None) or (
                response.get("choices") if isinstance(response, dict) else None
            )

            summary["id"] = response_id
            summary["model"] = model

            if choices:
                first = choices[0]
                message = getattr(first, "message", None) or (
                    first.get("message") if isinstance(first, dict) else None
                )
                if message is not None:
                    role = getattr(message, "role", None) or (
                        message.get("role") if isinstance(message, dict) else None
                    )
                    content = getattr(message, "content", None) or (
                        message.get("content") if isinstance(message, dict) else ""
                    )
                    content_str = str(content)
                    if len(content_str) > 500:
                        content_str = content_str[:500] + "...[truncated]"

                    summary["first_choice"] = {
                        "role": role,
                        "content": content_str,
                    }

                    # Tool call detection (names vary by SDK version)
                    tool_calls = getattr(message, "tool_calls", None) or (
                        message.get("tool_calls") if isinstance(message, dict) else None
                    )
                    if tool_calls:
                        summary["tool_calls_count"] = len(tool_calls)
                        # Log just the names/types of tools invoked
                        summary["tool_calls"] = []
                        for tc in tool_calls:
                            try:
                                tool_type = getattr(tc, "type", None) or tc.get("type")
                                func = getattr(tc, "function", None) or tc.get("function", {})
                                func_name = getattr(func, "name", None) or func.get("name")
                                summary["tool_calls"].append(
                                    {"type": tool_type, "function_name": func_name}
                                )
                            except Exception:
                                summary["tool_calls"].append(str(tc))
        except Exception:
            # Fallback: at least log stringified response
            summary["raw"] = str(response)

        return summary
    
    def get_agent(self) -> Agent:
        """Get the configured agent instance."""
        return self.agent

    # ------------------------------------------------------------------
    # Conversation state classification helpers
    # ------------------------------------------------------------------

    async def classify_information_status_async(self) -> Dict[str, Any]:
        """
        Use a lightweight chat.completions call to classify whether we've
        obtained all four key pieces of information for this week:
        - symptoms
        - vitals
        - adherence
        - side effects

        Returns a dict like:
            {
              "have_symptoms_info": true/false,
              "have_vitals_info": true/false,
              "have_adherence_info": true/false,
              "have_side_effects_info": true/false
            }
        """
        # Use the most recent portion of the conversation as context
        recent_context = self.conversation_context[-8:]
        conversation_text = "\n".join(recent_context) if recent_context else ""

        system_prompt = (
            "You are helping evaluate whether a heart failure check-in conversation "
            "has collected specific categories of information from the patient.\n\n"
            "Given the conversation transcript, answer ONLY with a JSON object with "
            "the following boolean fields:\n"
            '{\n'
            '  "have_symptoms_info": true/false,\n'
            '  "have_vitals_info": true/false,\n'
            '  "have_adherence_info": true/false,\n'
            '  "have_side_effects_info": true/false\n'
            "}\n\n"
            "- have_symptoms_info: true if the patient has described how they feel (energy, breathing, swelling, etc.).\n"
            "- have_vitals_info: true if blood pressure and heart rate have been provided in this conversation.\n"
            "- have_adherence_info: true if the patient has said whether they take medications as prescribed.\n"
            "- have_side_effects_info: true if the patient has confirmed presence or absence of medication side effects.\n"
            "Do not include any extra keys or commentary; output must be valid JSON."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": conversation_text},
        ]

        # logger.info("Classifying information status for current conversation context")

        try:
            response = await self.client.chat.completions.create(
                model=self.deployment,
                response_format={"type": "json_object"},
                messages=messages,
            )
        except Exception:
            # logger.exception("Failed to classify information status")
            pass
            # Fallback: assume nothing collected rather than blocking
            return {
                "have_symptoms_info": False,
                "have_vitals_info": False,
                "have_adherence_info": False,
                "have_side_effects_info": False,
            }

        try:
            content = response.choices[0].message.content
            data = json.loads(content)
            # logger.info("Information status classification result: %s", data)
            # Ensure all expected keys exist
            for key in [
                "have_symptoms_info",
                "have_vitals_info",
                "have_adherence_info",
                "have_side_effects_info",
            ]:
                data.setdefault(key, False)
            return data
        except Exception:
            # logger.exception("Failed to parse information status classification response")
            pass
            return {
                "have_symptoms_info": False,
                "have_vitals_info": False,
                "have_adherence_info": False,
                "have_side_effects_info": False,
            }

    def classify_information_status(self) -> Dict[str, Any]:
        """Synchronous wrapper for classify_information_status_async."""
        return asyncio.run(self.classify_information_status_async())
    
    async def get_response_async(self, user_input: str, history_json: Optional[str] = None) -> str:
        """Get async response from agent with persistent conversation memory.

        Optionally, `history_json` can provide a structured PATIENT_HISTORY_JSON
        block describing prior weeks and current medications. This history is
        included in the context for this call, but is NOT stored as part of the
        rolling `conversation_context`.
        """
        # logger.info("HF Agent received user input: %s", user_input)

        # Add user message to context
        self.conversation_context.append(f"Patient: {user_input}")
        
        # Keep only last 6 messages (3 exchanges) to avoid context overload
        recent_context = self.conversation_context[-6:]
        
        # Optional structured history block (PATIENT_HISTORY_JSON)
        history_block = ""
        if history_json:
            history_block = (
                "\n\nPATIENT_HISTORY_JSON (structured summary of prior weeks and current medications):\n"
                f"{history_json}"
            )

        # Create concise context with conversation history and optional history
        if len(recent_context) > 0:
            full_context = (
                "Recent conversation:\n"
                + "\n".join(recent_context)
                + history_block
                + "\n\nRespond to the patient's latest message."
            )
        else:
            full_context = user_input + history_block
        
        # Run with timeout handling
        try:
            # logger.debug("Calling Runner.run with full_context: %s", full_context)
            result = await Runner.run(self.agent, full_context)
            response = result.final_output
            # logger.info("HF Agent model response: %s", response)
        except Exception as e:
            # Fallback for timeout - try with just the current message
            # logger.warning("Timeout or error with context (%s), retrying without history", e)
            result = await Runner.run(self.agent, user_input)
            response = result.final_output
            # logger.info("HF Agent model response (no history): %s", response)
        
        # Add agent response to context
        self.conversation_context.append(f"You (HF Agent): {response}")
        
        return response
    
    def get_response(self, user_input: str, history_json: Optional[str] = None) -> str:
        """Get sync response from agent (wrapper for async)."""
        return asyncio.run(self.get_response_async(user_input, history_json=history_json))
    
    def reset_conversation(self):
        """Reset conversation by clearing context."""
        self.conversation_context = []

def create_azure_hf_agent() -> AzureHFAgent:
    """Factory function to create Azure HF Agent."""
    return AzureHFAgent()
