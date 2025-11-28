"""Safety validation for heart failure medication titration decisions."""

from typing import Dict, List, Tuple, Any
from enum import Enum

from ..models.patient import PatientState, WeeklyData, Endpoint
from ..models.medication import TitrationAction
from ..data.protocol_loader import PROTOCOL_LOADER


class SafetyLevel(Enum):
    """Safety assessment levels."""
    SAFE = "safe"
    CAUTION = "caution"
    UNSAFE = "unsafe"
    EMERGENCY = "emergency"


class SafetyViolation:
    """Represents a safety protocol violation."""
    
    def __init__(self, level: SafetyLevel, rule: str, details: str):
        self.level = level
        self.rule = rule
        self.details = details
    
    def __str__(self):
        return f"{self.level.value.upper()}: {self.rule} - {self.details}"


class SafetyValidator:
    """Validates medication titration decisions against safety protocols."""
    
    def __init__(self):
        """Initialize safety validator."""
        self.safety_rules = self._load_safety_rules()
    
    def _load_safety_rules(self) -> Dict[str, Any]:
        """Load safety rules and thresholds."""
        return {
            "vital_signs": {
                "systolic_bp_min": 80,
                "systolic_bp_max": 200,
                "diastolic_bp_min": 40,
                "diastolic_bp_max": 110,
                "heart_rate_min": 45,
                "heart_rate_max": 120,
                "emergency_systolic_low": 70,
                "emergency_systolic_high": 220,
                "emergency_hr_low": 40,
                "emergency_hr_high": 150
            },
            "labs": {
                "potassium_min": 3.5,
                "potassium_max": 5.5,
                "potassium_critical": 6.0,
                "creatinine_increase_threshold": 30,  # percent
                "egfr_min": 20
            },
            "emergency_symptoms": [
                "chest pain", "severe chest pain", "crushing chest pain",
                "severe shortness of breath", "can't breathe", 
                "syncope", "fainting", "passed out",
                "severe confusion", "unable to walk"
            ]
        }
    
    def validate_weekly_data(self, weekly_data: WeeklyData) -> List[SafetyViolation]:
        """Validate weekly patient data for safety concerns."""
        violations = []
        
        # Check vital signs
        violations.extend(self._check_vital_signs(weekly_data.vitals))
        
        # Check lab values if available
        if weekly_data.labs:
            violations.extend(self._check_lab_values(weekly_data.labs))
        
        # Check symptoms for emergency indicators
        violations.extend(self._check_emergency_symptoms(weekly_data.symptoms))
        
        # Check adherence
        if weekly_data.adherence_rate < 0.5:
            violations.append(SafetyViolation(
                SafetyLevel.UNSAFE,
                "Poor Adherence",
                f"Adherence rate {weekly_data.adherence_rate*100:.0f}% is dangerously low"
            ))
        
        return violations
    
    def _check_vital_signs(self, vitals) -> List[SafetyViolation]:
        """Check vital signs for safety violations."""
        violations = []
        rules = self.safety_rules["vital_signs"]
        
        if vitals.systolic_bp is not None:
            if vitals.systolic_bp <= rules["emergency_systolic_low"]:
                violations.append(SafetyViolation(
                    SafetyLevel.EMERGENCY,
                    "Critical Hypotension",
                    f"Systolic BP {vitals.systolic_bp} mmHg - immediate medical attention required"
                ))
            elif vitals.systolic_bp < rules["systolic_bp_min"]:
                violations.append(SafetyViolation(
                    SafetyLevel.UNSAFE,
                    "Hypotension",
                    f"Systolic BP {vitals.systolic_bp} mmHg below safe range"
                ))
            elif vitals.systolic_bp >= rules["emergency_systolic_high"]:
                violations.append(SafetyViolation(
                    SafetyLevel.EMERGENCY,
                    "Severe Hypertension",
                    f"Systolic BP {vitals.systolic_bp} mmHg - immediate medical attention required"
                ))
            elif vitals.systolic_bp > rules["systolic_bp_max"]:
                violations.append(SafetyViolation(
                    SafetyLevel.UNSAFE,
                    "Hypertension",
                    f"Systolic BP {vitals.systolic_bp} mmHg above safe range"
                ))
        
        if vitals.heart_rate is not None:
            if vitals.heart_rate <= rules["emergency_hr_low"]:
                violations.append(SafetyViolation(
                    SafetyLevel.EMERGENCY,
                    "Severe Bradycardia",
                    f"Heart rate {vitals.heart_rate} bpm - immediate medical attention required"
                ))
            elif vitals.heart_rate < rules["heart_rate_min"]:
                violations.append(SafetyViolation(
                    SafetyLevel.UNSAFE,
                    "Bradycardia",
                    f"Heart rate {vitals.heart_rate} bpm below safe range"
                ))
            elif vitals.heart_rate >= rules["emergency_hr_high"]:
                violations.append(SafetyViolation(
                    SafetyLevel.EMERGENCY,
                    "Severe Tachycardia",
                    f"Heart rate {vitals.heart_rate} bpm - immediate medical attention required"
                ))
        
        return violations
    
    def _check_lab_values(self, labs) -> List[SafetyViolation]:
        """Check laboratory values for safety violations."""
        violations = []
        rules = self.safety_rules["labs"]
        
        if labs.potassium is not None:
            if labs.potassium >= rules["potassium_critical"]:
                violations.append(SafetyViolation(
                    SafetyLevel.EMERGENCY,
                    "Critical Hyperkalemia",
                    f"Potassium {labs.potassium} mEq/L - immediate intervention required"
                ))
            elif labs.potassium > rules["potassium_max"]:
                violations.append(SafetyViolation(
                    SafetyLevel.UNSAFE,
                    "Hyperkalemia",
                    f"Potassium {labs.potassium} mEq/L above safe range"
                ))
            elif labs.potassium < rules["potassium_min"]:
                violations.append(SafetyViolation(
                    SafetyLevel.CAUTION,
                    "Hypokalemia",
                    f"Potassium {labs.potassium} mEq/L below normal range"
                ))
        
        if labs.egfr is not None:
            if labs.egfr < rules["egfr_min"]:
                violations.append(SafetyViolation(
                    SafetyLevel.UNSAFE,
                    "Severe Renal Impairment",
                    f"eGFR {labs.egfr} mL/min - medication adjustment required"
                ))
        
        return violations
    
    def _check_emergency_symptoms(self, symptoms: List[str]) -> List[SafetyViolation]:
        """Check symptoms for emergency indicators."""
        violations = []
        emergency_symptoms = self.safety_rules["emergency_symptoms"]
        
        for symptom in symptoms:
            symptom_lower = symptom.lower()
            for emergency_indicator in emergency_symptoms:
                if emergency_indicator in symptom_lower:
                    violations.append(SafetyViolation(
                        SafetyLevel.EMERGENCY,
                        "Emergency Symptom",
                        f"Patient reports: '{symptom}' - immediate medical evaluation required"
                    ))
                    break
        
        return violations
    
    def validate_titration_action(
        self,
        action: Dict[str, Any],
        patient_state: PatientState,
        weekly_data: WeeklyData
    ) -> List[SafetyViolation]:
        """Validate a proposed titration action."""
        violations = []
        
        medication_name = action.get("medication", "").lower()
        proposed_action = action.get("action", "")
        
        protocol = PROTOCOL_LOADER.get_protocol(medication_name)
        if not protocol:
            violations.append(SafetyViolation(
                SafetyLevel.UNSAFE,
                "Unknown Medication",
                f"No protocol found for medication: {medication_name}"
            ))
            return violations
        
        # Check if action violates hold criteria
        if proposed_action == "increase":
            # Verify it's safe to increase
            hold_criteria = protocol.hold_criteria
            
            # Check potassium
            if (weekly_data.labs and weekly_data.labs.potassium and
                hold_criteria.potassium_high and
                weekly_data.labs.potassium > hold_criteria.potassium_high):
                violations.append(SafetyViolation(
                    SafetyLevel.UNSAFE,
                    "Hold Criteria Violation",
                    f"Cannot increase {protocol.name}: potassium {weekly_data.labs.potassium} > {hold_criteria.potassium_high}"
                ))
            
            # Check blood pressure
            if (weekly_data.vitals.systolic_bp and
                hold_criteria.sbp_low and
                weekly_data.vitals.systolic_bp < hold_criteria.sbp_low):
                violations.append(SafetyViolation(
                    SafetyLevel.UNSAFE,
                    "Hold Criteria Violation",
                    f"Cannot increase {protocol.name}: SBP {weekly_data.vitals.systolic_bp} < {hold_criteria.sbp_low}"
                ))
            
            # Check heart rate (for beta blockers)
            if (weekly_data.vitals.heart_rate and
                hold_criteria.hr_low and
                weekly_data.vitals.heart_rate < hold_criteria.hr_low):
                violations.append(SafetyViolation(
                    SafetyLevel.UNSAFE,
                    "Hold Criteria Violation",
                    f"Cannot increase {protocol.name}: HR {weekly_data.vitals.heart_rate} < {hold_criteria.hr_low}"
                ))
        
        # Check adherence before any dose increase
        if proposed_action == "increase" and weekly_data.adherence_rate < 0.8:
            violations.append(SafetyViolation(
                SafetyLevel.CAUTION,
                "Poor Adherence",
                f"Consider addressing adherence ({weekly_data.adherence_rate*100:.0f}%) before dose increase"
            ))
        
        return violations
    
    def assess_overall_safety(self, patient_state: PatientState) -> Tuple[SafetyLevel, List[str]]:
        """Assess overall patient safety status."""
        if not patient_state.weekly_data:
            return SafetyLevel.CAUTION, ["No patient data available for assessment"]
        
        latest_data = patient_state.weekly_data[-1]
        violations = self.validate_weekly_data(latest_data)
        
        if not violations:
            return SafetyLevel.SAFE, ["No safety concerns identified"]
        
        # Determine highest severity level
        max_level = SafetyLevel.SAFE
        concerns = []
        
        for violation in violations:
            if violation.level == SafetyLevel.EMERGENCY:
                max_level = SafetyLevel.EMERGENCY
            elif violation.level == SafetyLevel.UNSAFE and max_level != SafetyLevel.EMERGENCY:
                max_level = SafetyLevel.UNSAFE
            elif violation.level == SafetyLevel.CAUTION and max_level == SafetyLevel.SAFE:
                max_level = SafetyLevel.CAUTION
            
            concerns.append(str(violation))
        
        return max_level, concerns


def validate_patient_safety(patient_state: PatientState) -> Dict[str, Any]:
    """Convenience function to validate patient safety and return results."""
    validator = SafetyValidator()
    
    if not patient_state.weekly_data:
        return {
            "safe": False,
            "level": "caution",
            "violations": ["No patient data available"],
            "recommendations": ["Collect baseline patient data before proceeding"]
        }
    
    latest_data = patient_state.weekly_data[-1]
    violations = validator.validate_weekly_data(latest_data)
    
    emergency_violations = [v for v in violations if v.level == SafetyLevel.EMERGENCY]
    unsafe_violations = [v for v in violations if v.level == SafetyLevel.UNSAFE]
    
    recommendations = []
    if emergency_violations:
        recommendations.append("IMMEDIATE: Refer to emergency department")
        recommendations.append("Do not proceed with medication changes")
    elif unsafe_violations:
        recommendations.append("Hold medication changes until safety concerns addressed")
        recommendations.append("Consider dose reduction or medication hold")
    elif violations:
        recommendations.append("Proceed with caution")
        recommendations.append("Increase monitoring frequency")
    else:
        recommendations.append("Safe to proceed with titration protocol")
    
    return {
        "safe": len(emergency_violations) == 0 and len(unsafe_violations) == 0,
        "level": "emergency" if emergency_violations else "unsafe" if unsafe_violations else "caution" if violations else "safe",
        "violations": [str(v) for v in violations],
        "recommendations": recommendations
    }