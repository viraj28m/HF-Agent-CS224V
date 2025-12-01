"""Patient models for heart failure titration system."""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from datetime import datetime

from .medication import CurrentMedication, VitalSigns, LabValues


class AdherencePattern(str, Enum):
    """Patient adherence patterns."""
    CONSISTENTLY_HIGH = "consistently_high"
    DECLINING = "declining"
    IMPROVING = "improving"
    FLUCTUATING = "fluctuating"
    SINGLE_DROP_THEN_STABLE = "single_drop_then_stable"


class SymptomPattern(str, Enum):
    """Patient symptom patterns."""
    STEADY_IMPROVEMENT = "steady_improvement"
    MIXED_RESPONSE = "mixed_response"
    PLATEAU = "plateau"
    PROGRESSIVE_WORSENING = "progressive_worsening"
    ACUTE_ESCALATION_TO_ED = "acute_escalation_to_ed"


class SideEffectPattern(str, Enum):
    """Side effect patterns."""
    NONE = "none"
    MILD_TOLERABLE = "mild_tolerable"
    SIDE_EFFECT_ESCALATION = "side_effect_escalation"
    EARLY_INTOLERANCE = "early_intolerance"


class VitalsPattern(str, Enum):
    """Vital signs patterns."""
    STABLE_IN_GOAL_RANGE = "stable_in_goal_range"
    BP_TRENDING_LOW = "bp_trending_low"
    BP_TRENDING_HIGH = "bp_trending_high"
    WEIGHT_GAIN_FLUID_OVERLOAD = "weight_gain_fluid_overload"
    OSCILLATING = "oscillating"


class LabPattern(str, Enum):
    """Lab value patterns."""
    LABS_NORMAL = "labs_normal"
    MILD_RENAL_DRIFT = "mild_renal_drift"
    PROGRESSIVE_RENAL_IMPAIRMENT = "progressive_renal_impairment"
    ELECTROLYTE_INSTABILITY = "electrolyte_instability"
    LABS_MISSING_OR_DELAYED = "labs_missing_or_delayed"


class Endpoint(str, Enum):
    """Possible endpoints for titration program."""
    COMPLETE_SUCCESS = "complete_success"
    PARTIAL_SUCCESS = "partial_success"
    NON_ADHERENCE_FAILURE = "non_adherence_failure"
    SIDE_EFFECT_FAILURE = "side_effect_failure"
    ACUTE_DECOMPENSATION_ED = "acute_decompensation_ed"
    HOSPITALIZATION_PAUSE = "hospitalization_pause"
    PATIENT_WITHDRAWAL = "patient_withdrawal"
    IN_PROGRESS = "in_progress"


class EducationLevel(str, Enum):
    """Patient education levels."""
    HIGH_SCHOOL = "High School"
    COLLEGE = "College"
    GRADUATE = "Graduate"
    SOME_COLLEGE = "Some College"


class MedicalLiteracy(str, Enum):
    """Patient medical literacy levels."""
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"


class PatientProfile(BaseModel):
    """Patient demographic and behavioral profile."""
    model_config = ConfigDict(extra='forbid')
    
    education_level: EducationLevel
    medical_literacy: MedicalLiteracy
    description: str
    
    # Behavior patterns for simulation
    adherence_pattern: AdherencePattern = AdherencePattern.CONSISTENTLY_HIGH
    symptom_pattern: SymptomPattern = SymptomPattern.STEADY_IMPROVEMENT
    side_effect_pattern: SideEffectPattern = SideEffectPattern.NONE
    vitals_pattern: VitalsPattern = VitalsPattern.STABLE_IN_GOAL_RANGE
    lab_pattern: LabPattern = LabPattern.LABS_NORMAL
    target_endpoint: Endpoint = Endpoint.COMPLETE_SUCCESS


class WeeklyData(BaseModel):
    """Weekly patient data collection."""
    model_config = ConfigDict(extra='forbid')
    
    week_number: int
    vitals: VitalSigns
    labs: Optional[LabValues] = None
    symptoms: List[str] = Field(default_factory=list)
    side_effects: List[str] = Field(default_factory=list)
    adherence_rate: float = Field(ge=0.0, le=1.0, default=1.0)
    patient_concerns: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


class PatientState(BaseModel):
    """Current patient state."""
    model_config = ConfigDict(extra='forbid')
    
    patient_id: str
    patient_name: str
    profile: PatientProfile
    current_medications: List[CurrentMedication]
    current_week: int
    total_weeks: int = 8
    weekly_data: List[WeeklyData] = Field(default_factory=list)
    endpoint: Endpoint = Endpoint.IN_PROGRESS
    
    # Medical history
    comorbidities: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    baseline_vitals: Optional[VitalSigns] = None
    baseline_labs: Optional[LabValues] = None


class ConversationContext(BaseModel):
    """Context for ongoing conversation."""
    model_config = ConfigDict(extra='forbid')
    
    patient_state: PatientState
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    pending_actions: List[str] = Field(default_factory=list)
    safety_flags: List[str] = Field(default_factory=list)