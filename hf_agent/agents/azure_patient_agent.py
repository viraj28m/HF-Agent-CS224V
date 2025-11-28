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
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1")
        
        # Create patient-specific tools
        self.tools = self._create_patient_tools()
        
        # Create agent with simplified context - NO TOOLS for now
        simplified_instructions = f"""
You are {patient_state.patient_name}, a heart failure patient.

Your medications: {', '.join([f"{med.name} {med.current_dose.value}mg" for med in patient_state.current_medications])}

Your patterns this week:
- Symptoms: {patient_state.profile.symptom_pattern.value}
- Adherence: {patient_state.profile.adherence_pattern.value}

Education: {patient_state.profile.education_level.value}
Medical literacy: {patient_state.profile.medical_literacy.value}

Respond naturally to ONE question at a time. Use conversational language, not medical lists.
"""
        
        self.agent = Agent(
            name=f"Patient: {patient_state.patient_name}",
            instructions=simplified_instructions,
            model=OpenAIChatCompletionsModel(
                model=self.deployment,
                openai_client=self.client,
            ),
            # Remove tools temporarily to test if they're causing issues
            # tools=self.tools
        )
    
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

## IMPORTANT INSTRUCTIONS FOR REALISTIC RESPONSES:
1. **Use your tools**: When asked about vitals, symptoms, or adherence, ALWAYS call the appropriate tool first
2. **Stay in character**: Respond according to your education level and medical literacy
3. **Follow patterns**: Your symptoms should progress according to your assigned pattern
4. **Be natural**: Use conversational language, not medical jargon
5. **Ask questions**: Real patients ask about medications, side effects, and treatment duration
6. **Express emotions**: Show appropriate worry, relief, or frustration

## CURRENT WEEK: {self.current_week}
Remember to call tools to get accurate information for this week!
"""
        
        return patient_context
    
    def update_week(self, week: int):
        """Update current week for patient progression."""
        self.current_week = week
        self.patient_state.current_week = week
        # Note: We'd need to recreate the agent with updated context for week changes
        # For now, we'll rely on the tools receiving the week parameter
    
    async def get_response_async(self, hf_agent_message: str) -> str:
        """Get async response from patient agent."""
        result = await Runner.run(self.agent, hf_agent_message)
        return result.final_output
    
    def get_response(self, hf_agent_message: str) -> str:
        """Get sync response from patient agent (wrapper for async)."""
        return asyncio.run(self.get_response_async(hf_agent_message))
    
    def reset_conversation(self):
        """Reset conversation - agent handles this internally."""
        # The SDK manages conversation state internally
        pass
    
    def get_agent(self) -> Agent:
        """Get the configured agent instance."""
        return self.agent

def create_azure_patient_agent(patient_state: PatientState) -> AzurePatientAgent:
    """Factory function to create Azure Patient Agent."""
    return AzurePatientAgent(patient_state)