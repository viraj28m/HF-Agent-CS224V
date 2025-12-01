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


def generate_symptoms(
    pattern: SymptomPattern,
    week: int,
    total_weeks: int
) -> List[str]:
    """Generate symptoms based on pattern and total program duration."""
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
    
    # Define generic phases based on total weeks
    early_phase_end = max(1, total_weeks // 3)
    mid_phase_end = max(early_phase_end + 1, (2 * total_weeks) // 3)
    
    if pattern == SymptomPattern.STEADY_IMPROVEMENT:
        if week <= early_phase_end:
            return base_symptoms
        elif week <= mid_phase_end:
            return improving_symptoms[:1] + base_symptoms[1:]
        else:
            return improving_symptoms
    
    elif pattern == SymptomPattern.PROGRESSIVE_WORSENING:
        if week <= early_phase_end:
            return base_symptoms
        elif week <= mid_phase_end:
            return base_symptoms + worsening_symptoms[:1]
        else:
            return worsening_symptoms
    
    elif pattern == SymptomPattern.MIXED_RESPONSE:
        if week % 2 == 0:
            return improving_symptoms[:1] + base_symptoms[1:]
        else:
            return base_symptoms + worsening_symptoms[:1]
    
    elif pattern == SymptomPattern.PLATEAU:
        # Initial improvement phase for roughly half of the program,
        # then return to a stable baseline (plateau).
        improvement_phase_end = max(1, total_weeks // 2)
        if week <= improvement_phase_end:
            return improving_symptoms[:2]
        else:
            return base_symptoms  # Stopped improving
    
    else:  # ACUTE_ESCALATION_TO_ED
        # Escalation occurs in the final quarter of the program.
        escalation_start = max(1, (3 * total_weeks) // 4)
        if week <= escalation_start:
            return base_symptoms
        else:
            return [
                "severe chest pain that won't go away",
                "can barely catch my breath",
                "feel like I might pass out"
            ]
    
    return base_symptoms


def generate_side_effects(
    pattern: SideEffectPattern,
    medications: List[str],
    week: int,
    total_weeks: int
) -> List[str]:
    """Generate side effects based on pattern, current medications, and program duration."""
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
        # Gradual escalation over the course of the program
        if not possible_effects:
            return []
        # Scale number of effects roughly linearly with program progress
        progress_ratio = min(1.0, max(0.0, week / max(1, total_weeks)))
        max_effects = len(possible_effects)
        num_effects = max(1, int(progress_ratio * max_effects))
        return random.sample(possible_effects, num_effects)
    elif pattern == SideEffectPattern.EARLY_INTOLERANCE:
        # More side effects early in the program, then mostly resolve
        early_phase_end = max(1, total_weeks // 3)
        if week <= early_phase_end:
            return random.sample(possible_effects, min(2, len(possible_effects)))
        else:
            return possible_effects[:1]  # Resolved mostly
    
    return []


def calculate_adherence(
    pattern: AdherencePattern,
    week: int,
    total_weeks: int,
    baseline: float = 0.95
) -> float:
    """Calculate adherence rate based on pattern and total program duration."""
    if pattern == AdherencePattern.CONSISTENTLY_HIGH:
        return max(0.9, baseline - random.uniform(0, 0.05))
    
    elif pattern == AdherencePattern.DECLINING:
        # Decline more smoothly over the full duration of the program
        progress_ratio = max(0.0, min(1.0, (week - 1) / max(1, total_weeks - 1)))
        decline = progress_ratio * 0.6  # Up to 60% absolute drop from baseline
        return max(0.3, baseline - decline)
    
    elif pattern == AdherencePattern.IMPROVING:
        if baseline < 0.8:  # Started low
            # Gradual improvement over the program, capped at +0.3
            progress_ratio = max(0.0, min(1.0, week / max(1, total_weeks)))
            improvement = min(progress_ratio * 0.3, 0.3)
            return min(0.95, baseline + improvement)
        return baseline
    
    elif pattern == AdherencePattern.FLUCTUATING:
        if week % 2 == 0:
            return max(0.6, baseline - 0.2)
        else:
            return baseline
    
    else:  # SINGLE_DROP_THEN_STABLE
        # Single bad week approximately one-third into the program
        drop_week = max(2, total_weeks // 3)
        if week == drop_week:
            return max(0.4, baseline - 0.4)
        return baseline
    
    return baseline


PATIENT_AGENT_INSTRUCTIONS = """
You are simulating a heart failure patient participating in a medication titration program. Your responses should be realistic, natural, and consistent with your assigned behavioral patterns.

## Your Role:
- Respond as a real patient would during weekly check-ins with your heart failure care team
- Be honest about your symptoms, medication adherence, and concerns
- Ask 1-2 relevant questions a patient would typically ask per week. DO NOT ask more than 1-2 questions per week. Patients often ask about:
   - Why medications are being changed
   - What side effects to watch for
   - How long treatment will take
   - Impact on daily activities
- Show appropriate emotions (worry, relief, frustration) when realistic
- **CRITICAL: Keep responses SHORT (2-3 sentences MAX). Real patients don't give lengthy reports.**

## Response Guidelines:
1. **Be Conversational and BRIEF**: Use natural language, not medical jargon. Answer directly and stop.
2. **Stay In Character**: Be consistent with your patient profile and behavioral patterns
3. **Provide Requested Information**: Give vital signs, symptoms, and adherence info when asked - but concisely

## Information You Can Provide:
- How you're feeling compared to last week
- Current symptoms and their severity
- Blood pressure and heart rate readings (from home monitoring)
- Weight changes
- Medication adherence (missed doses, reasons why)
- Side effects you're experiencing
- Questions or concerns about your treatment (limit these)

## Behavioral Consistency:
Your responses should align with your assigned patterns for:
- **Adherence Pattern**: How well you take medications (consistently_high, declining, improving, fluctuating, single_drop_then_stable)
- **Symptom Pattern**: How your symptoms progress (steady_improvement, progressive_worsening, mixed_response, plateau, acute_escalation_to_ed)
- **Side Effect Pattern**: What side effects you experience (none, mild_tolerable, side_effect_escalation, early_intolerance)
- **Vitals Pattern**: How your vital signs trend (stable_in_goal_range, bp_trending_low, bp_trending_high, weight_gain_fluid_overload, oscillating)
- **Target Endpoint**: Your overall trajectory (complete_success, partial_success, non_adherence_failure, side_effect_failure, acute_decompensation, etc.)

## Tool Usage for Realistic Data:
When discussing your status, use the provided tools to generate realistic, pattern-consistent data:
- Use `generate_realistic_vitals()` for current vital signs
- Use `generate_symptoms()` for current symptom status
- Use `calculate_adherence()` for medication adherence patterns
- Use `generate_side_effects()` for medication side effects

## Communication Style by Education/Medical Literacy:
- **High School/Low**: Use simple terms, ask basic questions, may misunderstand medical concepts
- **College/Moderate**: Mix of simple and medical terms, ask informed questions
- **Graduate/High**: Comfortable with medical terminology, ask detailed questions

## Response Length Examples:
✅ GOOD (concise): "I've been feeling a bit better. Still get short of breath climbing stairs though."
✅ GOOD: "My BP was 120 over 75 this morning. Heart rate was 68."
✅ GOOD: "Yeah, I've been taking everything. No side effects so far."

❌ BAD (too verbose): "Hi! Overall, I think I've been doing pretty well since starting the heart failure medications. I've been taking all my pills exactly as prescribed—haven't missed any doses so far. As for symptoms, I still get a little bit short of breath when I exert myself, and I feel some fatigue if I try to do a lot during the day. I have noticed occasional swelling in my legs, but it's not too bad. Honestly, I think it's slightly better than before I started the medication."

Remember: You're a patient, not a medical professional. Keep it conversational and brief - answer what's asked, then stop. Real patients don't give dissertations.
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
        total_weeks = getattr(self.patient_state, "total_weeks", 8)
        
        # Generate components
        vitals = generate_realistic_vitals(profile.vitals_pattern, self.current_week)
        symptoms = generate_symptoms(profile.symptom_pattern, self.current_week, total_weeks)
        side_effects = generate_side_effects(profile.side_effect_pattern, med_names, self.current_week, total_weeks)
        adherence = calculate_adherence(profile.adherence_pattern, self.current_week, total_weeks)
        
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
        total_weeks = getattr(self.patient_state, "total_weeks", 8)
        
        # Define trigger conditions for different endpoints
        if target_endpoint == Endpoint.ACUTE_DECOMPENSATION_ED:
            # Trigger in the final quarter of the program
            trigger_week = max(2, (3 * total_weeks) // 4)
            return self.current_week >= trigger_week
        elif target_endpoint == Endpoint.NON_ADHERENCE_FAILURE:
            # Non-adherence failure if declining pattern and past the middle of the program
            trigger_week = max(2, total_weeks // 2)
            return self.current_week >= trigger_week and self.patient_state.profile.adherence_pattern == AdherencePattern.DECLINING
        elif target_endpoint == Endpoint.SIDE_EFFECT_FAILURE:
            # Side effect failure if escalation pattern and into the latter half
            trigger_week = max(2, (total_weeks * 3) // 5)
            return self.current_week >= trigger_week and self.patient_state.profile.side_effect_pattern == SideEffectPattern.SIDE_EFFECT_ESCALATION
        
        return False


def create_patient_agent(patient_state: PatientState) -> PatientAgent:
    """Factory function to create Patient Agent."""
    return PatientAgent(patient_state)