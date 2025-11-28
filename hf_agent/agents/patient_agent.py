"""Patient Simulation Agent for heart failure medication titration."""

import os
import random
from agents import Agent
from typing import Dict, List, Optional, Any

from ..llm_client import get_llm_client

from ..models.patient import (
    PatientState, AdherencePattern, SymptomPattern, SideEffectPattern,
    VitalsPattern, LabPattern, Endpoint, WeeklyData, VitalSigns, LabValues
)


def generate_realistic_vitals(
    pattern: VitalsPattern,
    week: int,
    baseline_systolic: int = 140,
    baseline_diastolic: int = 85,
    baseline_hr: int = 75
) -> VitalSigns:
    """Generate realistic vital signs based on pattern."""
    
    if pattern == VitalsPattern.STABLE_IN_GOAL_RANGE:
        systolic = random.randint(110, 130)
        diastolic = random.randint(65, 80)
        hr = random.randint(60, 80)
    elif pattern == VitalsPattern.BP_TRENDING_LOW:
        # Gradual decrease over weeks
        systolic = max(85, baseline_systolic - (week * 5) + random.randint(-5, 5))
        diastolic = max(50, baseline_diastolic - (week * 3) + random.randint(-3, 3))
        hr = baseline_hr + random.randint(-5, 5)
    elif pattern == VitalsPattern.BP_TRENDING_HIGH:
        systolic = min(180, baseline_systolic + (week * 3) + random.randint(-5, 5))
        diastolic = min(100, baseline_diastolic + (week * 2) + random.randint(-3, 3))
        hr = baseline_hr + random.randint(-5, 10)
    elif pattern == VitalsPattern.WEIGHT_GAIN_FLUID_OVERLOAD:
        # Normal BP but concerning weight gain will be handled separately
        systolic = random.randint(120, 150)
        diastolic = random.randint(75, 90)
        hr = random.randint(70, 90)
    else:  # OSCILLATING
        # Varying week by week
        if week % 2 == 0:
            systolic = random.randint(95, 115)
            diastolic = random.randint(60, 75)
        else:
            systolic = random.randint(130, 150)
            diastolic = random.randint(80, 95)
        hr = random.randint(65, 85)
    
    return VitalSigns(
        systolic_bp=systolic,
        diastolic_bp=diastolic,
        heart_rate=hr,
        weight=None  # Will be set separately if needed
    )


def generate_symptoms(pattern: SymptomPattern, week: int) -> List[str]:
    """Generate symptoms based on pattern."""
    base_symptoms = [
        "mild shortness of breath with exertion",
        "some fatigue during daily activities",
        "occasional leg swelling"
    ]
    
    improving_symptoms = [
        "feeling much better than last week",
        "able to walk further without getting tired",
        "sleeping better at night"
    ]
    
    worsening_symptoms = [
        "more short of breath than usual",
        "increased swelling in legs",
        "waking up at night feeling breathless",
        "more tired than before"
    ]
    
    if pattern == SymptomPattern.STEADY_IMPROVEMENT:
        if week <= 2:
            return base_symptoms
        elif week <= 6:
            return improving_symptoms[:1] + base_symptoms[1:]
        else:
            return improving_symptoms
    
    elif pattern == SymptomPattern.PROGRESSIVE_WORSENING:
        if week <= 2:
            return base_symptoms
        elif week <= 4:
            return base_symptoms + worsening_symptoms[:1]
        else:
            return worsening_symptoms
    
    elif pattern == SymptomPattern.MIXED_RESPONSE:
        if week % 2 == 0:
            return improving_symptoms[:1] + base_symptoms[1:]
        else:
            return base_symptoms + worsening_symptoms[:1]
    
    elif pattern == SymptomPattern.PLATEAU:
        if week <= 4:
            return improving_symptoms[:2]
        else:
            return base_symptoms  # Stopped improving
    
    else:  # ACUTE_ESCALATION_TO_ED
        if week <= 6:
            return base_symptoms
        else:
            return [
                "severe chest pain that won't go away",
                "can barely catch my breath",
                "feel like I might pass out"
            ]
    
    return base_symptoms


def generate_side_effects(pattern: SideEffectPattern, medications: List[str], week: int) -> List[str]:
    """Generate side effects based on pattern and current medications."""
    if pattern == SideEffectPattern.NONE:
        return []
    
    # Common side effects by medication class
    med_side_effects = {
        "ace": ["dry cough", "dizziness when standing"],
        "arb": ["dizziness when standing", "mild fatigue"],
        "beta": ["feeling more tired than usual", "cold hands and feet"],
        "aldosterone": ["mild nausea", "breast tenderness"],
        "sglt2": ["mild increased urination", "occasional dizziness"]
    }
    
    possible_effects = []
    for med in medications:
        med_lower = med.lower()
        if any(ace_med in med_lower for ace_med in ["lisinopril", "enalapril"]):
            possible_effects.extend(med_side_effects["ace"])
        elif any(arb_med in med_lower for arb_med in ["losartan", "valsartan"]):
            possible_effects.extend(med_side_effects["arb"])
        elif any(bb_med in med_lower for bb_med in ["carvedilol", "metoprolol"]):
            possible_effects.extend(med_side_effects["beta"])
        elif any(aldo_med in med_lower for aldo_med in ["spironolactone", "eplerenone"]):
            possible_effects.extend(med_side_effects["aldosterone"])
        elif any(sglt2_med in med_lower for sglt2_med in ["dapagliflozin", "empagliflozin"]):
            possible_effects.extend(med_side_effects["sglt2"])
    
    if pattern == SideEffectPattern.MILD_TOLERABLE:
        return random.sample(possible_effects, min(1, len(possible_effects)))
    elif pattern == SideEffectPattern.SIDE_EFFECT_ESCALATION:
        num_effects = min(week // 2 + 1, len(possible_effects))
        return random.sample(possible_effects, num_effects)
    elif pattern == SideEffectPattern.EARLY_INTOLERANCE:
        if week <= 3:
            return random.sample(possible_effects, min(2, len(possible_effects)))
        else:
            return possible_effects[:1]  # Resolved mostly
    
    return []


def calculate_adherence(pattern: AdherencePattern, week: int, baseline: float = 0.95) -> float:
    """Calculate adherence rate based on pattern."""
    if pattern == AdherencePattern.CONSISTENTLY_HIGH:
        return max(0.9, baseline - random.uniform(0, 0.05))
    
    elif pattern == AdherencePattern.DECLINING:
        decline = (week - 1) * 0.1
        return max(0.3, baseline - decline)
    
    elif pattern == AdherencePattern.IMPROVING:
        if baseline < 0.8:  # Started low
            improvement = min(week * 0.1, 0.3)
            return min(0.95, baseline + improvement)
        return baseline
    
    elif pattern == AdherencePattern.FLUCTUATING:
        if week % 2 == 0:
            return max(0.6, baseline - 0.2)
        else:
            return baseline
    
    else:  # SINGLE_DROP_THEN_STABLE
        if week == 3:  # Single bad week
            return max(0.4, baseline - 0.4)
        return baseline
    
    return baseline


PATIENT_AGENT_INSTRUCTIONS = """
You are simulating a heart failure patient in natural conversation. Respond conversationally to ONE question at a time.

## CONVERSATIONAL RESPONSE STYLE:
- Answer only what's asked in each message
- Use natural, patient-like language 
- Share relevant details but don't over-explain
- Ask occasional questions like real patients do

## WHEN ASKED ABOUT:
- **Symptoms**: Describe how you're feeling naturally, use tools for accurate data
- **Vitals**: Give numbers conversationally ("My blood pressure was...")
- **Adherence**: Talk about medication-taking naturally ("I've been pretty good about...")
- **Side effects**: Describe any issues in your own words

## BEHAVIORAL PATTERNS:
Follow your assigned patterns consistently but naturally:
- Adherence pattern (declining, improving, etc.)
- Symptom pattern (worsening, improving, etc.)
- Express appropriate emotions and concerns

## CRITICAL RULES:
- Answer ONE category per response
- Use conversational language, not bullet points
- Don't list things robotically
- Use tools to get accurate week data
- Stay in character as real patient

Be natural and human, not a medical report.
"""


class PatientAgent:
    """Simulates a heart failure patient with configurable behavior patterns."""
    
    def __init__(self, patient_state: PatientState):
        """Initialize patient agent with specific behavioral patterns."""
        self.patient_state = patient_state
        self.current_week = patient_state.current_week
        
        # Create agent with patient-specific context
        context = self._create_patient_context()
        
        # Get deployment name from client
        client = get_llm_client()
        
        self.agent = Agent(
            name=f"Patient: {patient_state.patient_name}",
            instructions=PATIENT_AGENT_INSTRUCTIONS + "\n\n" + context,
            model=client.get_deployment_name()
        )
    
    def _create_patient_context(self) -> str:
        """Create patient-specific context for the agent."""
        profile = self.patient_state.profile
        
        context_parts = [
            f"## Your Patient Profile:",
            f"Name: {self.patient_state.patient_name}",
            f"Education: {profile.education_level.value}",
            f"Medical Understanding: {profile.medical_literacy.value}",
            f"Description: {profile.description}",
            "",
            f"## Your Behavioral Patterns:",
            f"Adherence Pattern: {profile.adherence_pattern.value}",
            f"Symptom Pattern: {profile.symptom_pattern.value}",
            f"Side Effect Pattern: {profile.side_effect_pattern.value}",
            f"Vitals Pattern: {profile.vitals_pattern.value}",
            f"Lab Pattern: {profile.lab_pattern.value}",
            f"Target Outcome: {profile.target_endpoint.value}",
            "",
            f"## Current Medications:"
        ]
        
        for med in self.patient_state.current_medications:
            med_info = f"- {med.name}: {med.current_dose.value}{med.current_dose.unit} {med.current_dose.frequency}"
            context_parts.append(med_info)
        
        return "\n".join(context_parts)
    
    def get_agent(self) -> Agent:
        """Get the configured patient agent."""
        return self.agent
    
    def generate_weekly_data(self) -> WeeklyData:
        """Generate realistic weekly data based on patient patterns."""
        profile = self.patient_state.profile
        med_names = [med.name for med in self.patient_state.current_medications]
        
        # Generate components
        vitals = generate_realistic_vitals(profile.vitals_pattern, self.current_week)
        symptoms = generate_symptoms(profile.symptom_pattern, self.current_week)
        side_effects = generate_side_effects(profile.side_effect_pattern, med_names, self.current_week)
        adherence = calculate_adherence(profile.adherence_pattern, self.current_week)
        
        # Generate weight if needed
        if profile.vitals_pattern == VitalsPattern.WEIGHT_GAIN_FLUID_OVERLOAD:
            baseline_weight = 180  # Default baseline
            weight_gain = self.current_week * 0.5  # Gradual gain
            vitals.weight = baseline_weight + weight_gain
        
        return WeeklyData(
            week_number=self.current_week,
            vitals=vitals,
            symptoms=symptoms,
            side_effects=side_effects,
            adherence_rate=adherence,
            patient_concerns=[]  # Will be filled based on conversation
        )
    
    def update_week(self):
        """Advance to next week."""
        self.current_week += 1
        self.patient_state.current_week = self.current_week
    
    def should_trigger_endpoint(self) -> bool:
        """Check if patient should trigger their target endpoint."""
        target_endpoint = self.patient_state.profile.target_endpoint
        
        # Define trigger conditions for different endpoints
        if target_endpoint == Endpoint.ACUTE_DECOMPENSATION_ED:
            return self.current_week >= 7  # Trigger after week 7
        elif target_endpoint == Endpoint.NON_ADHERENCE_FAILURE:
            return self.current_week >= 6 and self.patient_state.profile.adherence_pattern == AdherencePattern.DECLINING
        elif target_endpoint == Endpoint.SIDE_EFFECT_FAILURE:
            return self.current_week >= 5 and self.patient_state.profile.side_effect_pattern == SideEffectPattern.SIDE_EFFECT_ESCALATION
        
        return False


def create_patient_agent(patient_state: PatientState) -> PatientAgent:
    """Factory function to create Patient Agent."""
    return PatientAgent(patient_state)