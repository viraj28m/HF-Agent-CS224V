"""Medication protocol context collector.

This module forces calls to the protocol tools in order to gather structured
INFORMATION about each medication (dosing, contraindications, titration steps,
lab monitoring, etc.). It does NOT make titration decisions.

The HF conversational agent then uses this structured context, together with
the conversation, to decide whether to hold, increase, or decrease doses.
"""

from typing import Dict, Any, List
import logging

from hf_agent.models.patient import PatientState, CurrentMedication
from hf_agent.tools.complete_protocol_tools import (
    _get_all_medication_info_impl,
    _get_next_titration_dose_impl,
    _get_lab_monitoring_requirements_impl,
)


logger = logging.getLogger("hf_agent.tools.titration_planner")


def _is_numeric_dose(value: Any) -> bool:
    """Return True if value looks like a numeric dose."""
    return isinstance(value, (int, float))


def _build_dose_dict(med: CurrentMedication, use_target: bool = False) -> Dict[str, Any]:
    """Helper to build a consistent dose dict from a CurrentMedication."""
    dose = med.target_dose if use_target else med.current_dose
    return {
        "value": dose.value,
        "unit": dose.unit,
        "frequency": dose.frequency,
    }


def collect_titration_context(patient_state: PatientState) -> Dict[str, Any]:
    """
    Collect structured PROTOCOL CONTEXT for all current medications using the
    protocol tools directly in Python.

    This function does NOT decide increase/decrease/hold. Instead, it returns
    the information the HF agent should use to make those decisions.

    The context format:
        {
          "patient_id": ...,
          "patient_name": ...,
          "current_week": ...,
          "medications": [
             {
               "name": ...,
               "class": ...,
               "current_dose": {...},
               "target_dose": {...},
               "protocol_info": {...},           # from get_all_medication_info
               "next_titration_step": {...}|None # from get_next_titration_dose
             },
             ...
          ],
          "lab_monitoring_overview": {...}  # from get_lab_monitoring_requirements
        }
    """
    logger.info(
        "Collecting titration protocol context for patient %s (%s)",
        patient_state.patient_name,
        patient_state.patient_id,
    )

    med_contexts: List[Dict[str, Any]] = []

    # Build a list of medication names for lab monitoring calculation
    med_names = [med.name for med in patient_state.current_medications]

    # Lab monitoring plan across all meds
    try:
        lab_overview = _get_lab_monitoring_requirements_impl(med_names)
    except Exception:
        logger.exception("Failed to compute lab monitoring requirements")
        lab_overview = {
            "immediate_labs_needed": False,
            "timeline": "routine",
            "required_labs": [],
            "medication_specific_requirements": {},
            "general_schedule": {},
        }

    for med in patient_state.current_medications:
        current_dose = med.current_dose

        try:
            med_info = _get_all_medication_info_impl(med.name)
        except Exception:
            logger.exception("Error getting protocol info for medication %s", med.name)
            med_info = {"error": "exception_during_lookup"}

        next_step = None
        if not med_info.get("error") and med_info.get("requires_titration") and _is_numeric_dose(current_dose.value):
            try:
                titration_info = _get_next_titration_dose_impl(
                    medication_name=med.name,
                    current_dose=float(current_dose.value),
                )
            except Exception:
                logger.exception(
                    "Error getting next titration dose for medication %s", med.name
                )
                titration_info = {"error": "exception_during_titration_lookup"}

            # We pass through whatever titration_info returned; the HF agent will
            # interpret whether there is a next dose or if the patient is at max.
            next_step = titration_info

        med_ctx = {
            "name": med.name,
            "class": med.medication_class.value,
            "current_dose": _build_dose_dict(med, use_target=False),
            "target_dose": _build_dose_dict(med, use_target=True),
            "protocol_info": med_info,
            "next_titration_step": next_step,
        }
        med_contexts.append(med_ctx)

    context: Dict[str, Any] = {
        "patient_id": patient_state.patient_id,
        "patient_name": patient_state.patient_name,
        "current_week": patient_state.current_week,
        "medications": med_contexts,
        "lab_monitoring_overview": lab_overview,
    }

    logger.info("Collected titration protocol context: %s", context)
    return context


