"""Medication and protocol models for heart failure titration."""

from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class MedicationClass(str, Enum):
    """Heart failure medication classes."""
    ACE_I = "ACE-I"
    ACE_INHIBITOR = "ACE Inhibitor"  # JSON format
    ARB = "ARB" 
    ARNI = "ARNI"
    ALDOSTERONE_ANTAGONIST = "Aldosterone Antagonist"
    BETA_BLOCKER = "Beta Blocker"
    BETA_BLOCKER_JSON = "Beta-Blocker"  # JSON format
    VASODILATOR = "Vasodilator"
    NITRATE = "Nitrate"
    FIXED_DOSE_COMBINATION = "Fixed-Dose Combination"
    SGLT2_INHIBITOR = "SGLT-2 Inhibitor"
    SGLT2_INHIBITOR_JSON = "SGLT2 Inhibitor"  # JSON format
    SGC_STIMULATOR = "sGC Stimulator"
    LOOP_DIURETIC = "Loop Diuretic"
    THIAZIDE_DIURETIC = "Thiazide Diuretic"


class TitrationStrategy(str, Enum):
    """Titration strategies."""
    SINGLE_DRUG = "SINGLE_DRUG"
    MULTIPLE_BY_ORDER = "MULTIPLE_BY_ORDER" 
    MULTIPLE_ALTERNATING = "MULTIPLE_ALTERNATING"


class DoseInfo(BaseModel):
    """Dose information with value, unit, and frequency."""
    model_config = ConfigDict(extra='forbid')
    
    value: Union[float, str]  # String for combination doses like "24/26" (ARNI)
    unit: str
    frequency: str


class HoldCriteria(BaseModel):
    """Criteria for holding or discontinuing medication."""
    model_config = ConfigDict(extra='forbid')
    
    potassium_high: Optional[float] = None
    creatinine_increase_percent: Optional[float] = None
    egfr_low: Optional[float] = None
    sbp_low: Optional[float] = None
    hr_low: Optional[float] = None
    other_criteria: List[str] = Field(default_factory=list)


class MedicationProtocol(BaseModel):
    """Complete medication protocol definition."""
    model_config = ConfigDict(extra='forbid')
    
    name: str
    medication_class: MedicationClass
    starting_dose: DoseInfo
    incremental_doses: List[Union[float, str]]  # Strings for combination doses (ARNI)
    maximum_dose: DoseInfo
    contraindications: List[str]
    hold_criteria: HoldCriteria
    special_instructions: Optional[str] = None


class CurrentMedication(BaseModel):
    """Current medication state for a patient."""
    model_config = ConfigDict(extra='forbid')
    
    name: str
    medication_class: MedicationClass
    current_dose: DoseInfo
    target_dose: DoseInfo
    stage: str  # "early", "mid", "advanced"
    weeks_on_current_dose: int = 0


class VitalSigns(BaseModel):
    """Patient vital signs."""
    model_config = ConfigDict(extra='forbid')
    
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    heart_rate: Optional[int] = None
    weight: Optional[float] = None


class LabValues(BaseModel):
    """Laboratory values."""
    model_config = ConfigDict(extra='forbid')
    
    potassium: Optional[float] = None
    creatinine: Optional[float] = None
    egfr: Optional[float] = None
    sodium: Optional[float] = None
    hemoglobin: Optional[float] = None
    bun: Optional[float] = None


class TitrationAction(BaseModel):
    """Action to take for medication titration."""
    model_config = ConfigDict(extra='forbid')
    
    medication_name: str
    action: str  # "increase", "maintain", "decrease", "hold", "discontinue"
    new_dose: Optional[DoseInfo] = None
    reason: str
    safety_concern: bool = False
    next_followup_weeks: int = 2


class ProtocolConfig(BaseModel):
    """Protocol configuration."""
    model_config = ConfigDict(extra='forbid')
    
    strategy: TitrationStrategy
    max_weeks: int
    patient_id: str