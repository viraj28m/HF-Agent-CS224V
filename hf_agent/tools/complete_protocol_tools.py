"""Complete protocol tools using the comprehensive medication database.

Extended with logging so that tool calls, parameters, and outputs are visible
when the HF agent invokes them. This is helpful for debugging titration
behavior and ensuring that the LLM is actually using these tools.
"""

from typing import Dict, List, Optional, Any, Union
import logging

from pydantic import BaseModel, ConfigDict
from agents import function_tool

from ..data.complete_protocols import (
    ALL_MEDICATIONS,
    MEDICATION_CLASSES,
    VITAL_SIGN_PARAMETERS,
    LAB_MONITORING,
    GENERAL_HOLD_CRITERIA,
    PROGRAM_ENDPOINTS,
    TITRATION_SEQUENCES,
)


logger = logging.getLogger("hf_agent.tools.complete_protocol_tools")


class PatientVitals(BaseModel):
    """Patient vitals for medication assessment."""
    model_config = ConfigDict(extra='forbid')
    
    systolic_bp: Optional[float] = None
    diastolic_bp: Optional[float] = None  
    heart_rate: Optional[float] = None
    weight: Optional[float] = None


class PatientLabs(BaseModel):
    """Patient lab values for medication assessment."""
    model_config = ConfigDict(extra='forbid')
    
    potassium: Optional[float] = None
    creatinine: Optional[float] = None
    egfr: Optional[float] = None
    sodium: Optional[float] = None
    hemoglobin: Optional[float] = None
    bun: Optional[float] = None


class PatientMedication(BaseModel):
    """Current medication info for progress assessment."""
    model_config = ConfigDict(extra='forbid')
    
    name: str
    current_dose: float
    target_dose: float
    weeks_on_current_dose: int = 0


def _get_all_medication_info_impl(medication_name: str) -> Dict[str, Any]:
    """
    Get complete information for any heart failure medication including dosing, contraindications, and hold criteria.
    
    Args:
        medication_name: Name of medication (e.g. 'losartan', 'carvedilol', 'sacubitril_valsartan')
    
    Returns:
        Complete medication protocol information or error if not found
    """
    logger.info("Tool get_all_medication_info called with medication_name=%s", medication_name)

    med_key = medication_name.lower().replace(" ", "_").replace("/", "_").replace("-", "_")
    
    if med_key not in ALL_MEDICATIONS:
        result = {
            "error": f"Medication '{medication_name}' not found",
            "available_medications": list(ALL_MEDICATIONS.keys())
        }
        logger.info("Tool get_all_medication_info result: %s", result)
        return result
    
    med_info = ALL_MEDICATIONS[med_key].copy()
    
    # Add standardized fields for easier processing
    result = {
        "name": med_info.get("name", medication_name.title()),
        "class": med_info["class"],
        "starting_dose": med_info["starting_dose"],
        "maximum_dose": med_info["maximum_dose"],
        "contraindications": med_info["contraindications"],
        "hold_criteria": med_info["hold_criteria"]
    }
    
    # Add incremental doses if available
    if "incremental_doses" in med_info:
        result["incremental_doses"] = med_info["incremental_doses"]
        result["requires_titration"] = True
    else:
        result["requires_titration"] = med_info.get("requires_titration", False)
    
    # Add special considerations
    if "special_requirements" in med_info:
        result["special_requirements"] = med_info["special_requirements"]
    
    if "special_considerations" in med_info:
        result["special_considerations"] = med_info["special_considerations"]
    
    if "special_monitoring" in med_info:
        result["special_monitoring"] = med_info["special_monitoring"]
    
    # Add weight-based dosing for carvedilol
    if "maximum_dose_high_weight" in med_info:
        result["maximum_dose_high_weight"] = med_info["maximum_dose_high_weight"]
    
    # Add ARNI-specific starting dose criteria
    if "starting_dose_criteria" in med_info:
        result["starting_dose_criteria"] = med_info["starting_dose_criteria"]
    
    if "starting_dose_low" in med_info:
        result["starting_dose_low"] = med_info["starting_dose_low"]
        result["starting_dose_high"] = med_info["starting_dose_high"]

    logger.info("Tool get_all_medication_info result: %s", result)
    return result


@function_tool
def get_all_medication_info(medication_name: str) -> Dict[str, Any]:
    """
    Tool-wrapped version of get_all_medication_info for the Agents SDK.
    """
    return _get_all_medication_info_impl(medication_name)


@function_tool
def get_medications_by_class(medication_class: str) -> Dict[str, Any]:
    """
    Get all medications in a specific class with their key information.
    
    Args:
        medication_class: Class name (e.g. 'ACE-I', 'ARB', 'Beta Blocker', 'Aldosterone Antagonist')
    
    Returns:
        Dictionary of medications in the class with basic info
    """
    logger.info("Tool get_medications_by_class called with medication_class=%s", medication_class)

    if medication_class not in MEDICATION_CLASSES:
        result = {
            "error": f"Medication class '{medication_class}' not found",
            "available_classes": list(MEDICATION_CLASSES.keys())
        }
        logger.info("Tool get_medications_by_class result: %s", result)
        return result
    
    medications = MEDICATION_CLASSES[medication_class]
    result = {
        "class": medication_class,
        "medications": {}
    }
    
    for med_name in medications:
        if med_name in ALL_MEDICATIONS:
            med_info = ALL_MEDICATIONS[med_name]
            result["medications"][med_name] = {
                "starting_dose": med_info["starting_dose"],
                "maximum_dose": med_info["maximum_dose"],
                "requires_titration": "incremental_doses" in med_info
            }

    logger.info("Tool get_medications_by_class result: %s", result)
    return result


def _get_next_titration_dose_impl(medication_name: str, current_dose: float) -> Dict[str, Any]:
    """
    Get the next appropriate dose for medication titration based on protocol.
    
    Args:
        medication_name: Name of the medication
        current_dose: Current dose value as number
    
    Returns:
        Next dose information or indication if at maximum
    """
    logger.info(
        "Tool get_next_titration_dose called with medication_name=%s, current_dose=%s",
        medication_name,
        current_dose,
    )

    med_key = medication_name.lower().replace(" ", "_").replace("/", "_").replace("-", "_")
    
    if med_key not in ALL_MEDICATIONS:
        result = {"error": f"Medication '{medication_name}' not found"}
        logger.info("Tool get_next_titration_dose result: %s", result)
        return result
    
    med_info = ALL_MEDICATIONS[med_key]
    
    if "incremental_doses" not in med_info:
        result = {
            "requires_titration": False,
            "message": f"{medication_name} does not require titration - use standard dose"
        }
        logger.info("Tool get_next_titration_dose result: %s", result)
        return result
    
    incremental_doses = med_info["incremental_doses"]
    
    # Find current dose index
    current_idx = None
    for i, dose in enumerate(incremental_doses):
        # Handle string doses (like ARNI) or numeric doses
        dose_value = float(dose) if isinstance(dose, (int, float)) else dose
        current_value = current_dose if isinstance(current_dose, (int, float)) else str(current_dose)
        
        if str(dose_value) == str(current_value):
            current_idx = i
            break
    
    if current_idx is None:
        result = {
            "error": f"Current dose {current_dose} not found in protocol",
            "valid_doses": incremental_doses
        }
        logger.info("Tool get_next_titration_dose result: %s", result)
        return result
    
    if current_idx >= len(incremental_doses) - 1:
        result = {
            "at_maximum": True,
            "current_dose": current_dose,
            "maximum_dose": med_info["maximum_dose"],
            "message": "Patient is at maximum protocol dose"
        }
        logger.info("Tool get_next_titration_dose result: %s", result)
        return result
    
    next_dose = incremental_doses[current_idx + 1]
    
    result = {
        "current_dose": current_dose,
        "next_dose": next_dose,
        "maximum_dose": med_info["maximum_dose"],
        "dose_unit": med_info["starting_dose"]["unit"],
        "frequency": med_info["starting_dose"]["frequency"]
    }
    logger.info("Tool get_next_titration_dose result: %s", result)
    return result


@function_tool
def get_next_titration_dose(medication_name: str, current_dose: float) -> Dict[str, Any]:
    """
    Tool-wrapped version of get_next_titration_dose for the Agents SDK.
    """
    return _get_next_titration_dose_impl(medication_name, current_dose)


@function_tool
def check_medication_hold_criteria(
    medication_name: str,
    patient_vitals: PatientVitals,
    patient_labs: PatientLabs,
    baseline_creatinine: Optional[float] = None
) -> Dict[str, Any]:
    """
    Check if medication should be held based on current patient parameters and protocol hold criteria.
    
    Args:
        medication_name: Name of the medication
        patient_vitals: Dict with systolic_bp, diastolic_bp, heart_rate
        patient_labs: Dict with potassium, creatinine, egfr, etc.
        baseline_creatinine: Baseline creatinine for percentage calculation
    
    Returns:
        Hold recommendation with specific reasons
    """
    logger.info(
        "Tool check_medication_hold_criteria called with medication_name=%s, "
        "patient_vitals=%s, patient_labs=%s, baseline_creatinine=%s",
        medication_name,
        patient_vitals,
        patient_labs,
        baseline_creatinine,
    )

    med_key = medication_name.lower().replace(" ", "_").replace("/", "_").replace("-", "_")
    
    if med_key not in ALL_MEDICATIONS:
        result = {"error": f"Medication '{medication_name}' not found"}
        logger.info("Tool check_medication_hold_criteria result: %s", result)
        return result
    
    med_info = ALL_MEDICATIONS[med_key]
    hold_criteria = med_info["hold_criteria"]
    hold_reasons = []
    
    # Check potassium
    if patient_labs.potassium is not None:
        potassium = patient_labs.potassium
        
        if "potassium_discontinue" in hold_criteria and potassium >= hold_criteria["potassium_discontinue"]:
            hold_reasons.append(f"DISCONTINUE: Potassium {potassium} ≥ {hold_criteria['potassium_discontinue']} mEq/L")
        elif "potassium_high" in hold_criteria and potassium > hold_criteria["potassium_high"]:
            hold_reasons.append(f"HOLD: Potassium {potassium} > {hold_criteria['potassium_high']} mEq/L")
    
    # Check creatinine increase
    if (patient_labs.creatinine is not None and 
        baseline_creatinine is not None and 
        "creatinine_increase_percent" in hold_criteria):
        
        current_cr = patient_labs.creatinine
        percent_increase = ((current_cr - baseline_creatinine) / baseline_creatinine) * 100
        threshold = hold_criteria["creatinine_increase_percent"]
        
        if percent_increase > threshold:
            hold_reasons.append(f"HOLD: Creatinine increased {percent_increase:.1f}% (>{threshold}%) from baseline")
    
    # Check eGFR
    if patient_labs.egfr is not None and "egfr_low" in hold_criteria:
        egfr = patient_labs.egfr
        threshold = hold_criteria["egfr_low"]
        
        if egfr < threshold:
            hold_reasons.append(f"HOLD: eGFR {egfr} < {threshold} mL/min")
    
    # Check blood pressure
    if patient_vitals.systolic_bp is not None and "sbp_low" in hold_criteria:
        sbp = patient_vitals.systolic_bp
        threshold = hold_criteria["sbp_low"]
        
        if sbp < threshold:
            hold_reasons.append(f"HOLD: Systolic BP {sbp} < {threshold} mmHg")
    
    # Check heart rate (for beta blockers)
    if patient_vitals.heart_rate is not None:
        hr = patient_vitals.heart_rate
        
        if "hr_very_low" in hold_criteria and hr < hold_criteria["hr_very_low"]:
            hold_reasons.append(f"HOLD: Heart rate {hr} < {hold_criteria['hr_very_low']} bpm (critical)")
        elif "hr_low" in hold_criteria and hr < hold_criteria["hr_low"]:
            hold_reasons.append(f"HOLD: Heart rate {hr} < {hold_criteria['hr_low']} bpm")
    
    # Check special criteria
    special_holds = []
    for key, value in hold_criteria.items():
        if key not in ["potassium_high", "potassium_discontinue", "creatinine_increase_percent", 
                      "egfr_low", "sbp_low", "hr_low", "hr_very_low"] and value is True:
            special_holds.append(f"Monitor for {key.replace('_', ' ')}")
    
    result = {
        "medication": medication_name,
        "should_hold": len(hold_reasons) > 0,
        "hold_reasons": hold_reasons,
        "special_monitoring": special_holds,
        "hold_criteria_reference": hold_criteria
    }
    logger.info("Tool check_medication_hold_criteria result: %s", result)
    return result


def _get_lab_monitoring_requirements_impl(medications: List[str]) -> Dict[str, Any]:
    """
    Get laboratory monitoring requirements for current medications.
    
    Args:
        medications: List of current medication names
    
    Returns:
        Monitoring schedule and required labs
    """
    logger.info("Tool get_lab_monitoring_requirements called with medications=%s", medications)

    monitoring_needs = {
        "immediate_labs_needed": False,
        "timeline": "routine",
        "required_labs": set(),
        "medication_specific_requirements": {},
        "general_schedule": LAB_MONITORING["monitoring_schedule"]
    }
    
    high_priority_meds = []
    
    for med_name in medications:
        med_key = med_name.lower().replace(" ", "_").replace("/", "_").replace("-", "_")
        
        if med_key in ALL_MEDICATIONS:
            med_class = ALL_MEDICATIONS[med_key]["class"]
            
            # Determine monitoring requirements based on class
            if med_class in ["ACE-I", "ARB", "ARNI"]:
                high_priority_meds.append(med_name)
                monitoring_needs["required_labs"].update(LAB_MONITORING["basic_panel"])
                monitoring_needs["required_labs"].update(LAB_MONITORING["renal_function"])
                monitoring_needs["medication_specific_requirements"][med_name] = "1-2 weeks after changes"
                
            elif med_class == "Aldosterone Antagonist":
                high_priority_meds.append(med_name)
                monitoring_needs["required_labs"].update(LAB_MONITORING["basic_panel"])
                monitoring_needs["required_labs"].update(LAB_MONITORING["renal_function"])
                monitoring_needs["medication_specific_requirements"][med_name] = "1-2 weeks after changes (K+ critical)"
                
            elif med_class == "SGLT-2 Inhibitor":
                monitoring_needs["required_labs"].update(LAB_MONITORING["basic_panel"])
                monitoring_needs["required_labs"].update(LAB_MONITORING["renal_function"])
                monitoring_needs["required_labs"].add("hemoglobin")
                monitoring_needs["medication_specific_requirements"][med_name] = "2-4 weeks after initiation"
                
            elif med_class == "sGC Stimulator":
                monitoring_needs["required_labs"].update(LAB_MONITORING["basic_panel"])
                monitoring_needs["required_labs"].add("hemoglobin")
                monitoring_needs["medication_specific_requirements"][med_name] = "2-4 weeks after initiation"
    
    if high_priority_meds:
        monitoring_needs["immediate_labs_needed"] = True
        monitoring_needs["timeline"] = "1-2 weeks"
    
    monitoring_needs["required_labs"] = list(monitoring_needs["required_labs"])
    
    logger.info("Tool get_lab_monitoring_requirements result: %s", monitoring_needs)
    return monitoring_needs


@function_tool
def get_lab_monitoring_requirements(medications: List[str]) -> Dict[str, Any]:
    """
    Tool-wrapped version of get_lab_monitoring_requirements for the Agents SDK.
    """
    return _get_lab_monitoring_requirements_impl(medications)


@function_tool
def get_vital_sign_parameters() -> Dict[str, Any]:
    """
    Get the vital sign parameters for heart failure medication titration.
    
    Returns:
        Blood pressure and heart rate parameters for titration safety
    """
    logger.info("Tool get_vital_sign_parameters called")
    logger.info("Tool get_vital_sign_parameters result: %s", VITAL_SIGN_PARAMETERS)
    return VITAL_SIGN_PARAMETERS


@function_tool
def get_general_hold_criteria() -> Dict[str, Any]:
    """
    Get general hold criteria that apply across multiple medication classes.
    
    Returns:
        General laboratory and vital sign thresholds for medication holds
    """
    logger.info("Tool get_general_hold_criteria called")
    logger.info("Tool get_general_hold_criteria result: %s", GENERAL_HOLD_CRITERIA)
    return GENERAL_HOLD_CRITERIA


@function_tool
def get_program_endpoints() -> Dict[str, str]:
    """
    Get definitions of all possible heart failure titration program endpoints.
    
    Returns:
        Dictionary of endpoint names and their definitions
    """
    logger.info("Tool get_program_endpoints called")
    logger.info("Tool get_program_endpoints result: %s", PROGRAM_ENDPOINTS)
    return PROGRAM_ENDPOINTS


@function_tool
def get_titration_strategies() -> Dict[str, Any]:
    """
    Get information about different titration strategies and their timelines.
    
    Returns:
        Available titration strategies with descriptions and examples
    """
    logger.info("Tool get_titration_strategies called")
    logger.info("Tool get_titration_strategies result: %s", TITRATION_SEQUENCES)
    return TITRATION_SEQUENCES