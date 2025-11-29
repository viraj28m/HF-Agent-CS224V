"""Protocol loading and management utilities."""

from typing import Dict, Optional, List

from ..models.medication import MedicationProtocol, MedicationClass, DoseInfo, HoldCriteria
from .complete_protocols import ALL_MEDICATIONS


class ProtocolLoader:
    """Loads and manages medication protocols from complete_protocols.py."""
    
    def __init__(self):
        """Initialize protocol loader."""
        self._protocols: Dict[str, MedicationProtocol] = {}
        self._load_protocols()
    
    def _load_protocols(self) -> None:
        """Load protocols from complete_protocols.py."""
        # Parse each medication from ALL_MEDICATIONS
        for med_name, med_data in ALL_MEDICATIONS.items():
            protocol = self._parse_protocol(med_name, med_data)
            self._protocols[med_name.lower()] = protocol
    
    def _parse_protocol(self, med_name: str, data: dict) -> MedicationProtocol:
        """Parse protocol data into MedicationProtocol object."""
        # Handle different dose structures
        if "starting_dose" in data:
            starting_dose = DoseInfo(**data["starting_dose"])
        elif "starting_dose_low" in data:  # For ARNI
            starting_dose = DoseInfo(**data["starting_dose_low"])
        else:
            raise ValueError(f"No starting dose found for {med_name}")
        
        maximum_dose = DoseInfo(**data["maximum_dose"])
        
        # Parse hold criteria
        hold_data = data["hold_criteria"]
        hold_criteria = HoldCriteria(
            potassium_high=hold_data.get("potassium_high"),
            creatinine_increase_percent=hold_data.get("creatinine_increase_percent"),
            egfr_low=hold_data.get("egfr_low"),
            sbp_low=hold_data.get("sbp_low"),
            hr_low=hold_data.get("hr_low"),
            other_criteria=hold_data.get("other_criteria", [])
        )
        
        return MedicationProtocol(
            name=data.get("name", med_name.title().replace("_", " ")),
            medication_class=MedicationClass(data["class"]),
            starting_dose=starting_dose,
            incremental_doses=data.get("incremental_doses", []),
            maximum_dose=maximum_dose,
            contraindications=data["contraindications"],
            hold_criteria=hold_criteria,
            special_instructions=data.get("special_requirements") or data.get("special_instructions")
        )
    
    def get_protocol(self, medication_name: str) -> Optional[MedicationProtocol]:
        """Get protocol for a specific medication."""
        return self._protocols.get(medication_name.lower())
    
    def get_protocols_by_class(self, med_class: MedicationClass) -> List[MedicationProtocol]:
        """Get all protocols for a medication class."""
        return [
            protocol for protocol in self._protocols.values()
            if protocol.medication_class == med_class
        ]
    
    def list_medications(self) -> List[str]:
        """List all available medications."""
        return list(self._protocols.keys())
    
    def get_next_dose(self, medication_name: str, current_dose) -> Optional:
        """Get next titration dose for a medication."""
        protocol = self.get_protocol(medication_name)
        if not protocol:
            return None
        
        doses = protocol.incremental_doses
        current_idx = None
        
        # Find current dose index
        for i, dose in enumerate(doses):
            if isinstance(dose, str) and isinstance(current_dose, str):
                # String comparison for combination doses (ARNI)
                if dose == current_dose:
                    current_idx = i
                    break
            elif isinstance(dose, (int, float)) and isinstance(current_dose, (int, float)):
                # Float comparison for regular doses
                if abs(dose - current_dose) < 0.001:
                    current_idx = i
                    break
        
        if current_idx is None or current_idx >= len(doses) - 1:
            return None
        
        return doses[current_idx + 1]


# Global protocol loader instance
PROTOCOL_LOADER = ProtocolLoader()