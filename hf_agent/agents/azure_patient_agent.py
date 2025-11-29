#!/usr/bin/env python3
"""
Patient Agent using OpenAI Agents SDK with Azure OpenAI.
This replaces the custom Azure patient runner with proper SDK integration.
"""

import os
import asyncio
from openai import AsyncAzureOpenAI
from agents import Agent, Runner, OpenAIChatCompletionsModel, set_tracing_disabled, function_tool
from dotenv import load_dotenv
from typing import Dict, List, Any

from .patient_agent import (
    generate_realistic_vitals, generate_symptoms, calculate_adherence, 
    generate_side_effects, PATIENT_AGENT_INSTRUCTIONS
)
from ..models.patient import PatientState

# Load environment variables
load_dotenv()

# Disable tracing for Azure OpenAI
set_tracing_disabled(disabled=True)

class AzurePatientAgent:
    """Patient Agent using OpenAI Agents SDK with Azure OpenAI."""
    
    def __init__(self, patient_state: PatientState):
        """Initialize the Azure Patient Agent."""
        self.patient_state = patient_state
        self.current_week = patient_state.current_week
        
        self.client = AsyncAzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            timeout=180.0,  # 3 minute timeout (increased from 2)
            max_retries=3
        )
        
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1")
        
        # Create patient-specific tools
        self.tools = self._create_patient_tools()
        
        # Create agent with comprehensive patient context
        patient_context = self._create_patient_context()
        full_instructions = PATIENT_AGENT_INSTRUCTIONS + "\n\n" + patient_context
        
        self.agent = Agent(
            name=f"Patient: {patient_state.patient_name}",
            instructions=full_instructions,
            model=OpenAIChatCompletionsModel(
                model=self.deployment,
                openai_client=self.client,
            ),
            tools=self.tools
        )
        
        # Initialize conversation context list to maintain state
        self.conversation_context = []
    
    def _create_patient_tools(self):
        """Create patient-specific tools using function_tool decorator."""
        
        @function_tool
        def get_current_vitals(week: int) -> Dict[str, Any]:
            """Get my current vital signs (blood pressure, heart rate, weight)"""
            vitals = generate_realistic_vitals(
                self.patient_state.profile.vitals_pattern, week
            )
            return {
                "systolic_bp": vitals.systolic_bp,
                "diastolic_bp": vitals.diastolic_bp, 
                "heart_rate": vitals.heart_rate,
                "weight": vitals.weight
            }
        
        @function_tool
        def get_current_symptoms(week: int) -> List[str]:
            """Get my current symptoms based on how I'm feeling"""
            return generate_symptoms(
                self.patient_state.profile.symptom_pattern, week
            )
        
        @function_tool
        def get_adherence_status(week: int) -> Dict[str, Any]:
            """Get information about how well I've been taking my medications"""
            adherence_rate = calculate_adherence(
                self.patient_state.profile.adherence_pattern, week
            )
            
            if adherence_rate > 0.9:
                status = "excellent"
                description = "taking all medications as prescribed"
            elif adherence_rate > 0.8:
                status = "good" 
                description = "missed 1-2 doses this week"
            elif adherence_rate > 0.6:
                status = "moderate"
                description = "missed several doses this week"
            else:
                status = "poor"
                description = "frequently missing doses"
            
            return {
                "adherence_rate": adherence_rate,
                "status": status,
                "description": description
            }
        
        @function_tool
        def get_side_effects(week: int) -> List[str]:
            """Get any side effects I'm experiencing from medications"""
            med_names = [med.name for med in self.patient_state.current_medications]
            return generate_side_effects(
                self.patient_state.profile.side_effect_pattern, med_names, week
            )
        
        return [get_current_vitals, get_current_symptoms, get_adherence_status, get_side_effects]
    
    def _create_patient_context(self) -> str:
        """Create patient-specific context."""
        profile = self.patient_state.profile
        
        patient_context = f"""
## YOUR SPECIFIC PATIENT PROFILE:
Name: {self.patient_state.patient_name}
Education: {profile.education_level.value}
Medical Literacy: {profile.medical_literacy.value}
Description: {profile.description}

## YOUR BEHAVIORAL PATTERNS (FOLLOW THESE CONSISTENTLY):
- Adherence Pattern: {profile.adherence_pattern.value}
- Symptom Pattern: {profile.symptom_pattern.value}  
- Side Effect Pattern: {profile.side_effect_pattern.value}
- Vital Signs Pattern: {profile.vitals_pattern.value}
- Target Endpoint: {profile.target_endpoint.value}

## YOUR CURRENT MEDICATIONS:
{chr(10).join([f"- {med.name}: {med.current_dose.value}mg {med.current_dose.frequency}" for med in self.patient_state.current_medications])}

## CURRENT WEEK: {self.current_week}

## CRITICAL INSTRUCTIONS - READ CAREFULLY:

### 1. **MAINTAIN CONSISTENCY WITHIN THE CONVERSATION**
⚠️ **YOU HAVE CONVERSATION MEMORY** - You can see all previous messages in this conversation!

- If you ALREADY told the doctor your vitals (BP/HR) → **USE THE SAME NUMBERS**
- If you ALREADY described your symptoms → **BE CONSISTENT** with what you said before
- If doctor asks "What's your BP?" and you ALREADY said it → say "Like I mentioned, it was [same numbers]"
- **DON'T give different vitals each time you're asked!**

Example of CORRECT consistency:
Doctor: "How are you feeling?"
You: "Pretty good. My BP this morning was 120/75 and HR was 68." [You call tool ONCE and remember result]
Doctor: "What's your blood pressure?"
You: "Like I said, it was 120/75 this morning" [SAME numbers, not calling tool again]

### 2. **USE TOOLS ONLY WHEN FIRST ASKED**
- **FIRST TIME** asked about vitals in a conversation → Call `get_current_vitals(week={self.current_week})`
- **FIRST TIME** asked about symptoms → Call `get_current_symptoms(week={self.current_week})`
- **FIRST TIME** asked about adherence → Call `get_adherence_status(week={self.current_week})`
- **FIRST TIME** asked about side effects → Call `get_side_effects(week={self.current_week})`
- **SUBSEQUENT TIMES** → Just remember and repeat what you already said

### 3. **BE BRIEF - KEEP RESPONSES SHORT**
Real patients give SHORT answers:
- "Pretty good" or "A little tired"
- "Yeah, been taking them all" 
- "No side effects"
- "Sounds good to me"

Don't overexplain unless asked follow-up questions. 1-2 sentences MAX unless doctor specifically asks for more details.

### 4. **WHEN DOCTOR EXPLAINS THE PLAN**
If the doctor explains medication changes and asks "Sound good?" or "Any questions?":
- If you understand and agree → Just say: "Sounds good!" or "Yes, that makes sense" or "Okay, I'll do that"
- If you have a question → Ask ONE brief question
- **Keep it SHORT** - real patients don't give long responses here

### 5. **ANSWER WHAT'S ASKED ONLY**
- If asked "How are you feeling?" → Talk about symptoms ONLY
- If asked "What's your BP/HR?" → Give numbers ONLY (call tool if first time, remember if already said)
- If asked "Taking your meds?" → "Yes" or describe adherence ONLY
- If asked "Any side effects?" → "No" or mention issues ONLY

Don't volunteer everything at once. Answer the specific question asked.

## CURRENT WEEK: {self.current_week}
Remember to call tools with week={self.current_week} parameter when you need information for the FIRST TIME in this conversation!
"""
        
        return patient_context
    
    def update_week(self, week: int):
        """Update current week for patient progression."""
        self.current_week = week
        self.patient_state.current_week = week
        # Note: We'd need to recreate the agent with updated context for week changes
        # For now, we'll rely on the tools receiving the week parameter
    
    async def get_response_async(self, hf_agent_message: str) -> str:
        """Get async response from patient agent with persistent conversation memory."""
        # Add HF agent message to context
        self.conversation_context.append(f"Doctor: {hf_agent_message}")
        
        # Keep only last 6 messages (3 exchanges) to avoid context overload
        recent_context = self.conversation_context[-6:]
        
        # Create concise context with conversation history
        if len(recent_context) > 0:
            full_context = "Recent conversation:\n" + "\n".join(recent_context) + f"\n\nRespond to the doctor's latest message."
        else:
            full_context = hf_agent_message
        
        # Run with timeout handling
        try:
            result = await Runner.run(self.agent, full_context)
            response = result.final_output
        except Exception as e:
            # Fallback for timeout - try with just the current message
            print(f"⚠️  Timeout with context, trying without history...")
            result = await Runner.run(self.agent, hf_agent_message)
            response = result.final_output
        
        # Add patient response to context
        self.conversation_context.append(f"You (Patient): {response}")
        
        return response
    
    def get_response(self, hf_agent_message: str) -> str:
        """Get sync response from patient agent (wrapper for async)."""
        return asyncio.run(self.get_response_async(hf_agent_message))
    
    def reset_conversation(self):
        """Reset conversation by clearing context."""
        self.conversation_context = []
    
    def get_agent(self) -> Agent:
        """Get the configured agent instance."""
        return self.agent

def create_azure_patient_agent(patient_state: PatientState) -> AzurePatientAgent:
    """Factory function to create Azure Patient Agent."""
    return AzurePatientAgent(patient_state)