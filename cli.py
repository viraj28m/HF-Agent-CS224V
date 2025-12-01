"""Command-line interface for Heart Failure Medication Titration Agent."""

import click
import json
import os
from dotenv import load_dotenv
from typing import Dict, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from hf_agent.models.patient import (
    PatientState, PatientProfile, CurrentMedication, WeeklyData,
    EducationLevel, MedicalLiteracy, AdherencePattern, SymptomPattern,
    SideEffectPattern, VitalsPattern, LabPattern, Endpoint
)
from hf_agent.models.medication import DoseInfo, MedicationClass
from hf_agent.agents.azure_hf_agent import create_azure_hf_agent
from hf_agent.agents.azure_patient_agent import create_azure_patient_agent
from hf_agent.tools.titration_planner import collect_titration_context

# Load environment variables
load_dotenv()

# Logging for CLI orchestration (disabled; left here for potential future use)
# import logging
# logger = logging.getLogger("hf_agent.cli")

# Rich console for better output
console = Console()


def load_patient_scenarios() -> Dict[str, Any]:
    """Load patient scenarios from all_conversations.json."""
    try:
        with open("all_conversations.json", "r") as f:
            data = json.load(f)
        return data.get("conversations", [])
    except FileNotFoundError:
        console.print("[red]Error: all_conversations.json not found[/red]")
        return []


def parse_dose_string(dose_str: str) -> DoseInfo:
    """Parse dose string handling edge cases like 'dose adjustment as needed' and combination doses."""
    if "dose adjustment" in dose_str.lower() or "as needed" in dose_str.lower():
        # For flexible dosing, use a placeholder value
        return DoseInfo(value="as needed", unit="mg", frequency="as directed")
    
    parts = dose_str.split()
    if not parts:
        return DoseInfo(value=0.0, unit="mg", frequency="daily")
    
    dose_part = parts[0]
    frequency = " ".join(parts[1:]) if len(parts) > 1 else "daily"
    
    # Handle combination doses like "24/26mg" (ARNI medications)
    if "/" in dose_part:
        # Keep the full combination string
        value = dose_part.replace("mg", "")
    else:
        # Regular single-value dose
        try:
            value = float(dose_part.replace("mg", ""))
        except ValueError:
            # Fallback for any unexpected format
            value = 0.0
    
    return DoseInfo(value=value, unit="mg", frequency=frequency)


def evaluate_clinical_outcome(conversation_log: list, patient_state: PatientState, weeks_completed: int) -> str:
    """Evaluate the final clinical outcome based on conversation patterns."""
    
    # Analyze conversation for key indicators
    missed_doses_mentions = 0
    emergency_symptoms = 0
    medication_increases = 0
    
    for entry in conversation_log:
        message = entry["message"].lower()
        
        # Check for adherence issues
        if "missed" in message or "forgot" in message or "skip" in message:
            missed_doses_mentions += 1
            
        # Check for emergency symptoms
        if any(symptom in message for symptom in ["chest pain", "can't breathe", "emergency", "urgent", "hospital"]):
            emergency_symptoms += 1
            
        # Check for medication increases
        if "increase" in message or "titrat" in message:
            medication_increases += 1
    
    # Determine outcome based on target endpoint and conversation patterns
    target = patient_state.profile.target_endpoint.value
    adherence_pattern = patient_state.profile.adherence_pattern.value
    symptom_pattern = patient_state.profile.symptom_pattern.value
    
    # Emergency outcomes take priority
    if emergency_symptoms > 0:
        return "ACUTE_DECOMPENSATION"
    
    # Check if we reached target endpoint
    if target == "complete_success":
        if weeks_completed >= 8 and missed_doses_mentions == 0:
            return "COMPLETE_SUCCESS"
        elif weeks_completed >= 6:
            return "PARTIAL_SUCCESS"
        else:
            return "IN_PROGRESS"
            
    elif target == "non_adherence_failure":
        if missed_doses_mentions >= 2 or adherence_pattern == "declining":
            return "NON_ADHERENCE_FAILURE"
        else:
            return "IN_PROGRESS"
            
    elif target == "side_effect_failure":
        return "SIDE_EFFECT_FAILURE"
        
    elif target == "acute_decompensation":
        if symptom_pattern == "progressive_worsening":
            return "ACUTE_DECOMPENSATION"
        else:
            return "IN_PROGRESS"
    
    # Default outcomes
    if weeks_completed >= 8:
        return "PARTIAL_SUCCESS"
    else:
        return "IN_PROGRESS"


def create_patient_state_from_scenario(
    scenario: Dict[str, Any],
    total_weeks: int = 8
) -> PatientState:
    """Create PatientState from scenario data."""
    clinical_scenario = scenario["clinical_scenario"]
    patient_profile_data = scenario["patient_profile"]
    
    # Create patient profile
    profile = PatientProfile(
        education_level=EducationLevel(patient_profile_data["education_level"]),
        medical_literacy=MedicalLiteracy(patient_profile_data["medical_literacy"]),
        description=patient_profile_data["description"]
    )
    
    # Create current medications
    current_medications = []
    for med_data in clinical_scenario["medications"]:
        # Parse doses using improved logic
        current_dose = parse_dose_string(med_data["current"])
        target_dose = parse_dose_string(med_data["target"])
        
        medication = CurrentMedication(
            name=med_data["name"],
            medication_class=MedicationClass(med_data["type"]),
            current_dose=current_dose,
            target_dose=target_dose,
            stage=med_data["stage"]
        )
        current_medications.append(medication)
    
    return PatientState(
        patient_id=scenario["id"],
        patient_name=clinical_scenario["patient_name"],
        profile=profile,
        current_medications=current_medications,
        current_week=1,
        total_weeks=total_weeks,
    )


@click.group()
def cli():
    """Heart Failure Medication Titration Agent CLI."""
    pass


@click.command()
def list_scenarios():
    """List available patient scenarios."""
    scenarios = load_patient_scenarios()
    
    if not scenarios:
        console.print("[yellow]No scenarios found.[/yellow]")
        return
    
    table = Table(title="Available Patient Scenarios")
    table.add_column("ID", style="cyan")
    table.add_column("Patient Name", style="green") 
    table.add_column("Education", style="blue")
    table.add_column("Medical Literacy", style="magenta")
    table.add_column("Medications", style="yellow")
    
    for scenario in scenarios:
        clinical = scenario["clinical_scenario"]
        profile = scenario["patient_profile"]
        med_count = len(clinical.get("medications", []))
        
        table.add_row(
            scenario["id"],
            clinical["patient_name"],
            profile["education_level"],
            profile["medical_literacy"],
            f"{med_count} medications"
        )
    
    console.print(table)


@click.command()
@click.option("--patient-id", required=True, help="Patient ID from scenarios")
@click.option("--weeks", default=8, help="Number of weeks to simulate")
def interactive(patient_id: str, weeks: int):
    """Interactive mode - you act as the patient."""
    scenarios = load_patient_scenarios()
    scenario = next((s for s in scenarios if s["id"] == patient_id), None)
    
    if not scenario:
        console.print(f"[red]Patient ID {patient_id} not found[/red]")
        return
    
    # Create patient state
    patient_state = create_patient_state_from_scenario(scenario, total_weeks=weeks)
    
    # Create Azure SDK-based HF agent
    hf_agent = create_azure_hf_agent()
    
    console.print(Panel.fit(
        f"[bold green]Heart Failure Medication Titration Program[/bold green]\n"
        f"Patient: {patient_state.patient_name}\n"
        f"Starting Week 1 of {weeks} week program\n\n"
        f"[yellow]Instructions:[/yellow]\n"
        f"- You are acting as {patient_state.patient_name}\n"
        f"- Respond naturally to the agent's questions\n"
        f"- Provide realistic vital signs and symptoms\n"
        f"- Type 'quit' to exit\n",
        title="Interactive Mode"
    ))
    
    # Display patient information
    med_table = Table(title="Current Medications")
    med_table.add_column("Medication", style="cyan")
    med_table.add_column("Current Dose", style="green")
    med_table.add_column("Target Dose", style="yellow")
    med_table.add_column("Class", style="magenta")
    
    for med in patient_state.current_medications:
        med_table.add_row(
            med.name,
            f"{med.current_dose.value}{med.current_dose.unit} {med.current_dose.frequency}",
            f"{med.target_dose.value}{med.target_dose.unit} {med.target_dose.frequency}",
            med.medication_class.value
        )
    
    console.print(med_table)
    
    # Start conversation
    for week in range(1, weeks + 1):
        console.print(f"\n[bold blue]--- Week {week} Check-in ---[/bold blue]\n")
        
        # Create session context
        context = f"""
        Patient Context:
        - Week {week} of medication titration program
        - Patient: {patient_state.patient_name}
        - Education: {patient_state.profile.education_level.value}
        - Medical Literacy: {patient_state.profile.medical_literacy.value}
        
        Current Medications: {[f"{med.name} {med.current_dose.value}mg" for med in patient_state.current_medications]}
        
        Please begin the weekly check-in by greeting the patient and asking how they've been feeling.
        """
        
        # Start conversation with HF agent
        try:
            # Build and maintain a structured patient history across weeks so
            # the HF agent can remember prior decisions and context.
            if week == 1:
                patient_history = {
                    "patient_id": patient_state.patient_id,
                    "patient_name": patient_state.patient_name,
                    "current_week": week,
                    "current_medications": [
                        {
                            "name": med.name,
                            "class": med.medication_class.value,
                            "current_dose": {
                                "value": med.current_dose.value,
                                "unit": med.current_dose.unit,
                                "frequency": med.current_dose.frequency,
                            },
                            "target_dose": {
                                "value": med.target_dose.value,
                                "unit": med.target_dose.unit,
                                "frequency": med.target_dose.frequency,
                            },
                        }
                        for med in patient_state.current_medications
                    ],
                    "weekly_checkins": [],
                }
            else:
                # Ensure current_week is up to date at the start of each week
                patient_history["current_week"] = week
            # Create detailed patient context with medications
            med_list = "\n".join([f"- {med.name} ({med.medication_class.value}): Currently {med.current_dose.value}{med.current_dose.unit} {med.current_dose.frequency}, Target {med.target_dose.value}{med.target_dose.unit} {med.target_dose.frequency}" for med in patient_state.current_medications])
            
            initial_prompt = f"""You are beginning week {week} check-in for {patient_state.patient_name}.

PATIENT'S CURRENT MEDICATIONS (THIS IS WHAT THEY ARE ACTUALLY TAKING):
{med_list}

Patient Background:
- Education Level: {patient_state.profile.education_level.value}
- Medical Literacy: {patient_state.profile.medical_literacy.value}

This is week {week} of their {weeks}-week medication titration program. Begin the check-in naturally by greeting them and asking how they've been feeling."""
            
            history_json = json.dumps(patient_history, indent=2)
            response = hf_agent.get_response(initial_prompt, history_json=history_json)
            console.print(f"[bold cyan]HF Agent:[/bold cyan] {response}\n")
            
            # Interactive conversation loop for current week
            week_complete = False
            week_protocol_context_provided = False
            week_has_med_decision = False
            program_terminated_for_emergency = False
            while not week_complete:
                user_input = input("You: ")
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    console.print("[yellow]Ending session...[/yellow]")
                    return
                
                try:
                    # Get the HF agent's immediate response to the patient's input,
                    # always providing structured history so it can remember prior
                    # weeks and decisions.
                    history_json = json.dumps(patient_history, indent=2)
                    response = hf_agent.get_response(user_input, history_json=history_json)

                    # Emergency termination heuristic: if the HF agent is
                    # directing the patient to the emergency department, ER,
                    # urgent care, or to call 911, we treat this as the
                    # endpoint "Acute Decompensation with ED Referral" and end
                    # the entire program immediately after the patient
                    # acknowledges.
                    lower_resp = response.lower()
                    if any(
                        phrase in lower_resp
                        for phrase in [
                            "go to the nearest emergency room",
                            "go to the emergency room",
                            "go to the er",
                            "call 911",
                            "go to urgent care",
                            "go to an urgent care",
                            "emergency department",
                        ]
                    ):
                        console.print(f"\n[bold cyan]HF Agent:[/bold cyan] {response}\n")
                        console.print(
                            "[bold red]🚨 Emergency endpoint reached: Acute Decompensation with ED Referral. "
                            "Ending the titration program now.[/bold red]"
                        )
                        program_terminated_for_emergency = True
                        return

                    # By default, we will show the HF agent's direct response.
                    # However, if we already have ALL four required information
                    # categories for titration, we instead run the protocol
                    # tools and ask the HF agent for a single, protocol-informed
                    # medication plan. This avoids showing TWO separate plans
                    # (one pre-tool and one post-tool).
                    display_response = response

                    # After each HF Agent reply + patient reply, check if we've
                    # collected all required information for titration. If so,
                    # force the protocol tools to run and provide structured
                    # context back to the HF agent to make its own decisions.
                    if not week_protocol_context_provided:
                        # logger.info(
                        #     "Week %s: evaluating information completeness for titration",
                        #     week,
                        # )
                        info_status = hf_agent.classify_information_status()
                        # logger.info("Information status: %s", info_status)

                        have_all_info = (
                            info_status.get("have_symptoms_info")
                            and info_status.get("have_vitals_info")
                            and info_status.get("have_adherence_info")
                            and info_status.get("have_side_effects_info")
                        )

                        if have_all_info:
                            # logger.info(
                            #     "Week %s: all required info present; collecting titration protocol context",
                            #     week,
                            # )

                            # Force protocol tools to run in Python to gather
                            # medication-specific context (contraindications,
                            # incremental doses, lab requirements, etc.).
                            protocol_context = collect_titration_context(patient_state)
                            # logger.info(
                            #     "Week %s: collected titration protocol context for %d medications",
                            #     week,
                            #     len(protocol_context.get("medications", [])),
                            # )

                            # Ask HF Agent to use this CONTEXT (not decisions)
                            # to determine hold/increase/decrease actions.
                            context_prompt = f"""You now have all necessary clinical information for this week's check-in for {patient_state.patient_name} (symptoms, vitals, adherence, and medication side effects).

A separate protocol engine has gathered the following STRUCTURED PROTOCOL CONTEXT about the patient's medications using your tools (dosing ranges, contraindications, incremental titration steps, and lab monitoring needs). This context does NOT contain any final clinical decisions; it only summarizes the available protocol information:

STRUCTURED_PROTOCOL_CONTEXT_JSON:
{json.dumps(protocol_context, indent=2)}

Using ONLY this structured protocol context together with what you have learned from the patient in this week's conversation:
- For EACH current medication, decide whether to increase, decrease, continue/hold, or stop it this week.
- Base your decisions on the protocol information (including incremental doses and maximum/target doses) and the patient's symptoms, vitals, adherence, and side effects.
- Clearly state for each medication the OLD dose and the NEW dose (if changed), along with a brief rationale.
- Include a brief lab/monitoring plan using the lab monitoring overview in the structured context.
- Speak to the patient in your usual warm, concise style.
- Do NOT say WEEK_COMPLETE in this message."""

                            # Ask the HF Agent for a single, protocol-informed
                            # plan, again providing the structured history.
                            context_response = hf_agent.get_response(
                                context_prompt,
                                history_json=json.dumps(patient_history, indent=2),
                            )

                            # Only override the previous conversational response
                            # if the protocol-informed call actually returned
                            # non-empty content. This prevents a rare model
                            # hiccup where an empty string is returned.
                            if context_response and context_response.strip():
                                # Use the protocol-informed plan as the ONLY plan
                                # the patient sees for this week.
                                display_response = context_response

                                week_protocol_context_provided = True
                                # We know this response SHOULD contain explicit
                                # medication decisions for all meds.
                                week_has_med_decision = True

                                # Attempt to parse a structured weekly plan JSON so
                                # that we can update medication doses and store
                                # vitals/symptoms/adherence/side effects history.
                                plan_marker = "STRUCTURED_WEEKLY_PLAN_JSON"
                                structured_plan = None
                                if plan_marker in display_response:
                                    try:
                                        marker_index = display_response.index(plan_marker)
                                        json_start = display_response.find("{", marker_index)
                                        if json_start != -1:
                                            depth = 0
                                            json_end = None
                                            for idx, ch in enumerate(
                                                display_response[json_start:], start=json_start
                                            ):
                                                if ch == "{":
                                                    depth += 1
                                                elif ch == "}":
                                                    depth -= 1
                                                    if depth == 0:
                                                        json_end = idx + 1
                                                        break
                                            if json_end is not None:
                                                json_str = display_response[json_start:json_end]
                                                structured_plan = json.loads(json_str)
                                    except Exception:
                                        structured_plan = None

                                if structured_plan:
                                    # Record this week's summary in history
                                    week_entry = {
                                        "week": week,
                                        "vitals": structured_plan.get("vitals"),
                                        "symptoms_summary": structured_plan.get(
                                            "symptoms_summary"
                                        ),
                                        "adherence_summary": structured_plan.get(
                                            "adherence_summary"
                                        ),
                                        "side_effects_summary": structured_plan.get(
                                            "side_effects_summary"
                                        ),
                                        "medication_plan": structured_plan.get(
                                            "medication_plan", []
                                        ),
                                    }
                                    patient_history.setdefault("weekly_checkins", []).append(
                                        week_entry
                                    )

                                    # Update current medication doses in both the
                                    # patient_state model and the history so that
                                    # next week's starting doses are correct.
                                    current_meds_by_name = {
                                        med.name: med for med in patient_state.current_medications
                                    }
                                    history_meds_by_name = {
                                        m["name"]: m
                                        for m in patient_history.get(
                                            "current_medications", []
                                        )
                                    }
                                    for decision in structured_plan.get(
                                        "medication_plan", []
                                    ):
                                        name = decision.get("name")
                                        new_dose = decision.get("new_dose")
                                        if not name or not isinstance(new_dose, dict):
                                            continue

                                        med_model = current_meds_by_name.get(name)
                                        if med_model:
                                            if "value" in new_dose:
                                                med_model.current_dose.value = new_dose[
                                                    "value"
                                                ]
                                            if "unit" in new_dose:
                                                med_model.current_dose.unit = new_dose[
                                                    "unit"
                                                ]
                                            if "frequency" in new_dose:
                                                med_model.current_dose.frequency = new_dose[
                                                    "frequency"
                                                ]

                                        history_med = history_meds_by_name.get(name)
                                        if history_med is not None:
                                            history_med["current_dose"] = new_dose
                            else:
                                # logger.warning(
                                #     "Week %s: protocol-informed titration call returned empty content; "
                                #     "keeping prior conversational response instead.",
                                #     week,
                                # )
                                pass

                    # Show whichever response we decided to surface (either the
                    # direct conversational reply or the single, protocol-
                    # informed plan).
                    # For protocol-informed plans, we may have a hidden
                    # STRUCTURED_WEEKLY_PLAN_JSON block that is meant for the
                    # system, not the patient. Strip that JSON before
                    # displaying to the user while still keeping it available
                    # in `display_response` for parsing and state updates.
                    patient_visible_response = display_response
                    plan_marker = "STRUCTURED_WEEKLY_PLAN_JSON"
                    if week_protocol_context_provided and plan_marker in patient_visible_response:
                        marker_index = patient_visible_response.index(plan_marker)
                        patient_visible_response = patient_visible_response[:marker_index].rstrip()

                    if week_protocol_context_provided:
                        console.print(f"\n[bold cyan]HF Agent (protocol-informed plan):[/bold cyan] {patient_visible_response}\n")
                    else:
                        console.print(f"\n[bold cyan]HF Agent:[/bold cyan] {patient_visible_response}\n")

                    # Check if agent indicated week completion with proper decisions
                    if "WEEK_COMPLETE" in display_response:
                        # Heuristic: consider the week validly completed if we
                        # have seen a medication decision message at any point
                        # this week (e.g., the protocol-informed plan), OR if
                        # this particular message itself clearly contains med
                        # decisions.
                        message_has_med_decision = (
                            "increase" in display_response.lower() or
                            "decrease" in display_response.lower() or
                            "continue" in display_response.lower() or
                            "hold" in display_response.lower() or
                            "maintain" in display_response.lower() or
                            "keep" in display_response.lower() or
                            "titration" in display_response.lower() or
                            "mg" in display_response.lower()  # Dose mentions
                        )
                        
                        if week_has_med_decision or message_has_med_decision:
                            week_complete = True
                            console.print(f"[bold green]✅ Week {week} completed with titration decisions! Moving to next week...[/bold green]")
                            
                            # Update patient state for next week
                            patient_state.current_week = week + 1
                            
                            # Reset agent conversation for next week (SDK handles internally)
                            hf_agent.reset_conversation()
                            
                            # Brief pause between weeks
                            import time
                            time.sleep(1)
                        else:
                            # Agent said WEEK_COMPLETE but didn't make proper decisions
                            console.print(f"[yellow]⚠️  Please make explicit medication decisions before ending the week.[/yellow]")
                            console.print("[yellow]The agent should specify hold/increase/decrease for each medication.[/yellow]")
                    
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")
                    
        except Exception as e:
            console.print(f"[red]Error starting conversation: {e}[/red]")
            return


@click.command()
@click.option("--patient-id", required=True, help="Patient ID from scenarios")
@click.option("--weeks", default=8, help="Number of weeks to simulate")
@click.option("--adherence-pattern", 
              type=click.Choice([p.value for p in AdherencePattern]),
              default="consistently_high",
              help="Patient adherence pattern")
@click.option("--symptom-pattern",
              type=click.Choice([p.value for p in SymptomPattern]),
              default="steady_improvement", 
              help="Patient symptom pattern")
@click.option("--endpoint",
              type=click.Choice([e.value for e in Endpoint]),
              default="complete_success",
              help="Target endpoint for simulation")
def automated(patient_id: str, weeks: int, adherence_pattern: str, 
              symptom_pattern: str, endpoint: str):
    """Automated mode - two agents converse with each other."""
    scenarios = load_patient_scenarios()
    scenario = next((s for s in scenarios if s["id"] == patient_id), None)
    
    if not scenario:
        console.print(f"[red]Patient ID {patient_id} not found[/red]")
        return
    
    # Create patient state with custom patterns
    patient_state = create_patient_state_from_scenario(scenario, total_weeks=weeks)
    patient_state.profile.adherence_pattern = AdherencePattern(adherence_pattern)
    patient_state.profile.symptom_pattern = SymptomPattern(symptom_pattern)
    patient_state.profile.target_endpoint = Endpoint(endpoint)
    
    # Create Azure SDK-based agents
    hf_agent = create_azure_hf_agent()
    patient_agent = create_azure_patient_agent(patient_state)
    
    console.print(Panel.fit(
        f"[bold green]Automated Heart Failure Simulation[/bold green]\n"
        f"Patient: {patient_state.patient_name}\n"
        f"Adherence Pattern: {adherence_pattern}\n"
        f"Symptom Pattern: {symptom_pattern}\n"
        f"Target Endpoint: {endpoint}\n"
        f"Duration: {weeks} weeks\n",
        title="Automated Mode"
    ))
    
    conversation_log = []
    
    # Run simulation
    program_terminated_for_emergency = False
    for week in range(1, weeks + 1):
        console.print(f"\n[bold blue]--- Week {week} ---[/bold blue]")
        
        # Update both agents for current week
        patient_agent.update_week(week)
        patient_state.current_week = week
        
        try:
            # Build and maintain a structured patient history across weeks so
            # the HF agent can remember prior decisions and context, mirroring
            # the interactive mode behavior.
            if week == 1:
                patient_history = {
                    "patient_id": patient_state.patient_id,
                    "patient_name": patient_state.patient_name,
                    "current_week": week,
                    "current_medications": [
                        {
                            "name": med.name,
                            "class": med.medication_class.value,
                            "current_dose": {
                                "value": med.current_dose.value,
                                "unit": med.current_dose.unit,
                                "frequency": med.current_dose.frequency,
                            },
                            "target_dose": {
                                "value": med.target_dose.value,
                                "unit": med.target_dose.unit,
                                "frequency": med.target_dose.frequency,
                            },
                        }
                        for med in patient_state.current_medications
                    ],
                    "weekly_checkins": [],
                }
            else:
                # Ensure current_week is up to date at the start of each week
                patient_history["current_week"] = week

            # Create detailed patient context with medications
            med_list = "\n".join(
                [
                    f"- {med.name} ({med.medication_class.value}): Currently {med.current_dose.value}{med.current_dose.unit} {med.current_dose.frequency}, "
                    f"Target {med.target_dose.value}{med.target_dose.unit} {med.target_dose.frequency}"
                    for med in patient_state.current_medications
                ]
            )
            
            initial_prompt = f"""You are beginning week {week} check-in for {patient_state.patient_name}.

PATIENT'S CURRENT MEDICATIONS (THIS IS WHAT THEY ARE ACTUALLY TAKING):
{med_list}

Patient Background:
- Education Level: {patient_state.profile.education_level.value}
- Medical Literacy: {patient_state.profile.medical_literacy.value}

This is week {week} of their medication titration program. Begin the check-in naturally by greeting them and asking how they've been feeling."""
            
            history_json = json.dumps(patient_history, indent=2)
            hf_message = hf_agent.get_response(initial_prompt, history_json=history_json)
            console.print(f"[bold cyan]HF Agent:[/bold cyan] {hf_message}\n")
            conversation_log.append(
                {"week": week, "speaker": "HF Agent", "message": hf_message}
            )
            
            # Agent-to-agent conversation exchanges (conversational but efficient)
            max_exchanges = 8  # Maximum 8 exchanges to allow natural back-and-forth
            week_completed_with_decisions = False
            # Track whether we've already seen a message this week from the HF
            # agent that clearly contains titration/medication decisions.
            # This allows the agent to say WEEK_COMPLETE in a brief follow-up
            # message (after the patient acknowledges the plan) without having
            # to repeat all medication details in the same message.
            week_has_med_decision = False
            # Track whether we've already provided the protocol context and
            # received a single, protocol-informed medication plan, mirroring
            # the interactive mode behavior.
            week_protocol_context_provided = False
            for exchange in range(max_exchanges):
                # Patient responds using Azure AI
                patient_message = patient_agent.get_response(hf_message)
                console.print(f"[bold green]Patient ({patient_state.patient_name}):[/bold green] {patient_message}\n")
                conversation_log.append({"week": week, "speaker": "Patient", "message": patient_message})
                
                # HF Agent responds, always with structured history context so
                # it can remember prior weeks and decisions.
                history_json = json.dumps(patient_history, indent=2)
                hf_raw_response = hf_agent.get_response(
                    patient_message, history_json=history_json
                )

                # Emergency termination heuristic: if the HF agent is clearly
                # directing the patient to the ED/ER/urgent care or to call
                # 911, immediately end the entire simulation with the endpoint
                # "Acute Decompensation with ED Referral".
                lower_resp = hf_raw_response.lower()
                if any(
                    phrase in lower_resp
                    for phrase in [
                        "go to the nearest emergency room",
                        "go to the emergency room",
                        "go to the er",
                        "call 911",
                        "go to urgent care",
                        "go to an urgent care",
                        "emergency department",
                    ]
                ):
                    console.print(f"[bold cyan]HF Agent:[/bold cyan] {hf_raw_response}\n")
                    conversation_log.append(
                        {"week": week, "speaker": "HF Agent", "message": hf_raw_response}
                    )
                    console.print(
                        "[bold red]🚨 Emergency endpoint reached: Acute Decompensation with ED Referral. "
                        "Ending the titration program now.[/bold red]"
                    )
                    program_terminated_for_emergency = True
                    break
                
                if program_terminated_for_emergency:
                    break

                # By default, we will show the HF agent's direct response.
                # However, if we already have ALL four required information
                # categories for titration, we instead run the protocol tools
                # and ask the HF agent for a single, protocol-informed
                # medication plan (mirroring interactive mode). This avoids
                # showing two separate plans (one pre-tool and one post-tool).
                display_response = hf_raw_response

                # After each HF Agent reply + patient reply, check if we've
                # collected all required information for titration. If so,
                # force the protocol tools to run and provide structured
                # context back to the HF agent to make its own decisions.
                if not week_protocol_context_provided:
                    # logger.info(
                    #     "Week %s (automated): evaluating information completeness for titration",
                    #     week,
                    # )
                    info_status = hf_agent.classify_information_status()
                    # logger.info("Information status: %s", info_status)

                    have_all_info = (
                        info_status.get("have_symptoms_info")
                        and info_status.get("have_vitals_info")
                        and info_status.get("have_adherence_info")
                        and info_status.get("have_side_effects_info")
                    )

                    if have_all_info:
                        # logger.info(
                        #     "Week %s (automated): all required info present; collecting titration protocol context",
                        #     week,
                        # )

                        # Force protocol tools to run in Python to gather
                        # medication-specific context (contraindications,
                        # incremental doses, lab requirements, etc.).
                        protocol_context = collect_titration_context(patient_state)
                        # logger.info(
                        #     "Week %s (automated): collected titration protocol context for %d medications",
                        #     week,
                        #     len(protocol_context.get("medications", [])),
                        # )

                        # Ask HF Agent to use this CONTEXT (not decisions) to
                        # determine hold/increase/decrease actions.
                        context_prompt = f"""You now have all necessary clinical information for this week's check-in for {patient_state.patient_name} (symptoms, vitals, adherence, and medication side effects).

A separate protocol engine has gathered the following STRUCTURED PROTOCOL CONTEXT about the patient's medications using your tools (dosing ranges, contraindications, incremental titration steps, and lab monitoring needs). This context does NOT contain any final clinical decisions; it only summarizes the available protocol information:

STRUCTURED_PROTOCOL_CONTEXT_JSON:
{json.dumps(protocol_context, indent=2)}

Using ONLY this structured protocol context together with what you have learned from the patient in this week's conversation:
- For EACH current medication, decide whether to increase, decrease, continue/hold, or stop it this week.
- Base your decisions on the protocol information (including incremental doses and maximum/target doses) and the patient's symptoms, vitals, adherence, and side effects.
- Clearly state for each medication the OLD dose and the NEW dose (if changed), along with a brief rationale.
- Include a brief lab/monitoring plan using the lab monitoring overview in the structured context.
- Speak to the patient in your usual warm, concise style.
- Do NOT say WEEK_COMPLETE in this message."""

                        context_response = hf_agent.get_response(
                            context_prompt,
                            history_json=json.dumps(patient_history, indent=2),
                        )

                        # Only override the previous conversational response if
                        # the protocol-informed call actually returned
                        # non-empty content. This prevents a rare model hiccup
                        # where an empty string is returned.
                        if context_response and context_response.strip():
                            # Use the protocol-informed plan as the ONLY plan the
                            # patient agent sees for this week.
                            display_response = context_response

                            week_protocol_context_provided = True
                            # We know this response SHOULD contain explicit
                            # medication decisions for all meds.
                            week_has_med_decision = True

                            # Attempt to parse a structured weekly plan JSON so
                            # that we can update medication doses and store
                            # vitals/symptoms/adherence/side effects history.
                            plan_marker = "STRUCTURED_WEEKLY_PLAN_JSON"
                            structured_plan = None
                            if plan_marker in display_response:
                                try:
                                    marker_index = display_response.index(plan_marker)
                                    json_start = display_response.find("{", marker_index)
                                    if json_start != -1:
                                        depth = 0
                                        json_end = None
                                        for idx, ch in enumerate(
                                            display_response[json_start:], start=json_start
                                        ):
                                            if ch == "{":
                                                depth += 1
                                            elif ch == "}":
                                                depth -= 1
                                                if depth == 0:
                                                    json_end = idx + 1
                                                    break
                                        if json_end is not None:
                                            json_str = display_response[json_start:json_end]
                                            structured_plan = json.loads(json_str)
                                except Exception:
                                    structured_plan = None

                            if structured_plan:
                                # Record this week's summary in history
                                week_entry = {
                                    "week": week,
                                    "vitals": structured_plan.get("vitals"),
                                    "symptoms_summary": structured_plan.get(
                                        "symptoms_summary"
                                    ),
                                    "adherence_summary": structured_plan.get(
                                        "adherence_summary"
                                    ),
                                    "side_effects_summary": structured_plan.get(
                                        "side_effects_summary"
                                    ),
                                    "medication_plan": structured_plan.get(
                                        "medication_plan", []
                                    ),
                                }
                                patient_history.setdefault("weekly_checkins", []).append(
                                    week_entry
                                )

                                # Update current medication doses in both the
                                # patient_state model and the history so that next
                                # week's starting doses are correct.
                                current_meds_by_name = {
                                    med.name: med for med in patient_state.current_medications
                                }
                                history_meds_by_name = {
                                    m["name"]: m
                                    for m in patient_history.get("current_medications", [])
                                }
                                for decision in structured_plan.get("medication_plan", []):
                                    name = decision.get("name")
                                    new_dose = decision.get("new_dose")
                                    if not name or not isinstance(new_dose, dict):
                                        continue

                                    med_model = current_meds_by_name.get(name)
                                    if med_model:
                                        if "value" in new_dose:
                                            med_model.current_dose.value = new_dose["value"]
                                        if "unit" in new_dose:
                                            med_model.current_dose.unit = new_dose["unit"]
                                        if "frequency" in new_dose:
                                            med_model.current_dose.frequency = new_dose[
                                                "frequency"
                                            ]

                                    history_med = history_meds_by_name.get(name)
                                    if history_med is not None:
                                        history_med["current_dose"] = new_dose
                        else:
                            # logger.warning(
                            #     "Week %s (automated): protocol-informed titration call returned empty content; "
                            #     "keeping prior conversational response instead.",
                            #     week,
                            # )
                            pass

                # Decide what to show the patient agent and what to log. For
                # protocol-informed plans, we hide the structured JSON from the
                # patient while preserving it in the conversation log.
                patient_visible_response = display_response
                plan_marker = "STRUCTURED_WEEKLY_PLAN_JSON"
                if week_protocol_context_provided and plan_marker in patient_visible_response:
                    marker_index = patient_visible_response.index(plan_marker)
                    patient_visible_response = patient_visible_response[:marker_index].rstrip()

                if week_protocol_context_provided:
                    console.print(f"[bold cyan]HF Agent (protocol-informed plan):[/bold cyan] {patient_visible_response}\n")
                else:
                    console.print(f"[bold cyan]HF Agent:[/bold cyan] {patient_visible_response}\n")

                # Log the full response (including any hidden JSON).
                conversation_log.append(
                    {"week": week, "speaker": "HF Agent", "message": display_response}
                )

                # For the next exchange, the patient agent should only see the
                # human-facing portion of the response.
                hf_message = patient_visible_response

                # Determine whether this HF Agent message (raw or protocol-
                # informed) appears to contain medication/titration decisions,
                # based on key phrases and dose mentions. Once we've seen a
                # decision message this week, we allow a later WEEK_COMPLETE
                # message (e.g., a brief acknowledgement/closing message) to
                # terminate the week even if that closing message itself
                # doesn't repeat all decisions.
                lower_display = display_response.lower()
                message_has_med_decision = (
                    "increase" in lower_display
                    or "decrease" in lower_display
                    or "continue" in lower_display
                    or "hold" in lower_display
                    or "maintain" in lower_display
                    or "keep" in lower_display
                    or "titration" in lower_display
                    or "mg" in lower_display  # Dose mentions
                )
                if message_has_med_decision:
                    week_has_med_decision = True

                # Break ONLY if agent signals completion with proper titration
                # decisions, mirroring the interactive mode heuristic.
                if "WEEK_COMPLETE" in display_response:
                    # Consider the week validly completed if either:
                    # - This message itself contains clear medication decisions, OR
                    # - We have ALREADY seen a decision-bearing message earlier
                    #   in the week and this is a short closing message that
                    #   simply says "WEEK_COMPLETE".
                    if week_has_med_decision or message_has_med_decision:
                        console.print(f"\n[bold green]✅ Week {week} completed with titration decisions![/bold green]")
                        week_completed_with_decisions = True
                        break
                    else:
                        # Agent said WEEK_COMPLETE but didn't make proper
                        # decisions - continue the conversation.
                        console.print(
                            "[yellow]⚠️  Agent said WEEK_COMPLETE but didn't make titration decisions - continuing...[/yellow]"
                        )
                        
            # If we reached max exchanges or never got proper titration decisions,
            # force the HF agent to provide a clear medication plan for all meds
            if not week_completed_with_decisions:
                console.print(f"[yellow]⚠️  Week {week} reached maximum exchanges without satisfactory titration decisions. Forcing final decision summary...[/yellow]")
                
                forced_prompt = f"""
You are at the end of week {week} of this heart failure titration check-in for {patient_state.patient_name}.

PATIENT'S CURRENT MEDICATIONS (THIS IS WHAT THEY ARE ACTUALLY TAKING):
{med_list}

You MUST NOW provide a clear, explicit titration plan for EVERY medication listed above, even if you already discussed options earlier.
For EACH medication, explicitly state whether you will increase, decrease, continue/hold, or stop it, and show the OLD dose and NEW dose.
Then, provide any brief monitoring or lab plans.

Finally, AFTER the patient acknowledges or asks a brief question, you MUST end the plan by saying "WEEK_COMPLETE" in your response, as specified in your instructions.

Respond now with the medication plan and include WEEK_COMPLETE in this response.
"""
                hf_message = hf_agent.get_response(forced_prompt)
                console.print(f"[bold cyan]HF Agent (forced plan):[/bold cyan] {hf_message}\n")
                conversation_log.append({"week": week, "speaker": "HF Agent", "message": hf_message})
                
                # Final check for decisions + WEEK_COMPLETE
                has_med_decision = (
                    "increase" in hf_message.lower() or
                    "decrease" in hf_message.lower() or
                    "continue" in hf_message.lower() or
                    "hold" in hf_message.lower() or
                    "maintain" in hf_message.lower() or
                    "keep" in hf_message.lower() or
                    "titration" in hf_message.lower() or
                    "mg" in hf_message.lower()
                )
                if "WEEK_COMPLETE" in hf_message and has_med_decision:
                    console.print(f"\n[bold green]✅ Week {week} forced to completion with titration decisions.[/bold green]")
                else:
                    console.print(f"[yellow]⚠️  Forced titration summary did not fully meet criteria, continuing to next week anyway.[/yellow]")
            
            # Reset both agents for next week (SDK handles internally)
            hf_agent.reset_conversation()
            patient_agent.reset_conversation()
                    
        except Exception as e:
            console.print(f"[red]Error in week {week}: {e}[/red]")
            continue
        
        console.print("\n" + "="*50)

        if program_terminated_for_emergency:
            break
    
    # Evaluate final clinical outcome
    if program_terminated_for_emergency:
        final_outcome = "ACUTE_DECOMPENSATION_WITH_ED_REFERRAL"
    else:
        final_outcome = evaluate_clinical_outcome(conversation_log, patient_state, weeks)
    
    # Summary
    console.print(f"\n[bold green]Automated Simulation Complete![/bold green]")
    console.print(f"Total weeks simulated: {weeks}")
    console.print(f"Total conversation exchanges: {len(conversation_log)}")
    
    # Show clinical outcome prominently
    outcome_color = "green" if "SUCCESS" in final_outcome else "red" if "FAILURE" in final_outcome or "DECOMPENSATION" in final_outcome else "yellow"
    console.print(f"\n[bold {outcome_color}]🎯 CLINICAL OUTCOME: {final_outcome}[/bold {outcome_color}]")
    
    # Show patient outcome summary
    console.print(Panel.fit(
        f"[bold yellow]Final Patient Status:[/bold yellow]\n"
        f"Adherence Pattern: {adherence_pattern}\n"
        f"Symptom Pattern: {symptom_pattern}\n"
        f"Target Endpoint: {endpoint}\n"
        f"Weeks Completed: {weeks}\n\n"
        f"[bold {outcome_color}]Clinical Outcome: {final_outcome}[/bold {outcome_color}]",
        title="Simulation Summary"
    ))
    
    # Save conversation log to subdirectory
    import os
    
    # Create subdirectory if it doesn't exist
    conversations_dir = "simulated_conversations"
    os.makedirs(conversations_dir, exist_ok=True)
    
    log_filename = f"simulation_{patient_id}_{weeks}weeks.json"
    full_path = os.path.join(conversations_dir, log_filename)
    with open(full_path, "w") as f:
        json.dump({
            "patient_id": patient_id,
            "patient_name": patient_state.patient_name,
            "parameters": {
                "adherence_pattern": adherence_pattern,
                "symptom_pattern": symptom_pattern,
                "target_endpoint": endpoint,
                "weeks": weeks
            },
            "clinical_outcome": final_outcome,
            "conversation_log": conversation_log
        }, f, indent=2)
    
    console.print(f"[yellow]Conversation log saved to {full_path}[/yellow]")


# Add commands to CLI group
cli.add_command(list_scenarios)
cli.add_command(interactive)
cli.add_command(automated)


if __name__ == "__main__":
    cli()