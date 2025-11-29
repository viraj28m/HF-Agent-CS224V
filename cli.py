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

# Load environment variables
load_dotenv()

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


def create_patient_state_from_scenario(scenario: Dict[str, Any]) -> PatientState:
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
        current_week=1
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
    patient_state = create_patient_state_from_scenario(scenario)
    
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
            # Create detailed patient context with medications
            med_list = "\n".join([f"- {med.name} ({med.medication_class.value}): Currently {med.current_dose.value}{med.current_dose.unit} {med.current_dose.frequency}, Target {med.target_dose.value}{med.target_dose.unit} {med.target_dose.frequency}" for med in patient_state.current_medications])
            
            initial_prompt = f"""You are beginning week {week} check-in for {patient_state.patient_name}.

PATIENT'S CURRENT MEDICATIONS (THIS IS WHAT THEY ARE ACTUALLY TAKING):
{med_list}

Patient Background:
- Education Level: {patient_state.profile.education_level.value}
- Medical Literacy: {patient_state.profile.medical_literacy.value}

This is week {week} of their {weeks}-week medication titration program. Begin the check-in naturally by greeting them and asking how they've been feeling."""
            
            response = hf_agent.get_response(initial_prompt)
            console.print(f"[bold cyan]HF Agent:[/bold cyan] {response}\n")
            
            # Interactive conversation loop for current week
            week_complete = False
            while not week_complete:
                user_input = input("You: ")
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    console.print("[yellow]Ending session...[/yellow]")
                    return
                
                try:
                    response = hf_agent.get_response(user_input)
                    console.print(f"\n[bold cyan]HF Agent:[/bold cyan] {response}\n")
                    
                    # Check if agent indicated week completion with proper decisions
                    if "WEEK_COMPLETE" in response:
                        # Verify the response contains medication decisions before allowing completion
                        has_med_decision = (
                            "increase" in response.lower() or
                            "decrease" in response.lower() or
                            "continue" in response.lower() or
                            "hold" in response.lower() or
                            "maintain" in response.lower() or
                            "keep" in response.lower() or
                            "titration" in response.lower() or
                            "mg" in response.lower()  # Dose mentions
                        )
                        
                        if has_med_decision:
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
    patient_state = create_patient_state_from_scenario(scenario)
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
    for week in range(1, weeks + 1):
        console.print(f"\n[bold blue]--- Week {week} ---[/bold blue]")
        
        # Update both agents for current week
        patient_agent.update_week(week)
        patient_state.current_week = week
        
        try:
            # Create detailed patient context with medications
            med_list = "\n".join([f"- {med.name} ({med.medication_class.value}): Currently {med.current_dose.value}{med.current_dose.unit} {med.current_dose.frequency}, Target {med.target_dose.value}{med.target_dose.unit} {med.target_dose.frequency}" for med in patient_state.current_medications])
            
            initial_prompt = f"""You are beginning week {week} check-in for {patient_state.patient_name}.

PATIENT'S CURRENT MEDICATIONS (THIS IS WHAT THEY ARE ACTUALLY TAKING):
{med_list}

Patient Background:
- Education Level: {patient_state.profile.education_level.value}
- Medical Literacy: {patient_state.profile.medical_literacy.value}

This is week {week} of their medication titration program. Begin the check-in naturally by greeting them and asking how they've been feeling."""
            
            hf_message = hf_agent.get_response(initial_prompt)
            console.print(f"[bold cyan]HF Agent:[/bold cyan] {hf_message}\n")
            conversation_log.append({"week": week, "speaker": "HF Agent", "message": hf_message})
            
            # Agent-to-agent conversation exchanges (conversational but efficient)
            max_exchanges = 8  # Maximum 8 exchanges to allow natural back-and-forth
            for exchange in range(max_exchanges):
                # Patient responds using Azure AI
                patient_message = patient_agent.get_response(hf_message)
                console.print(f"[bold green]Patient ({patient_state.patient_name}):[/bold green] {patient_message}\n")
                conversation_log.append({"week": week, "speaker": "Patient", "message": patient_message})
                
                # HF Agent responds  
                hf_message = hf_agent.get_response(patient_message)
                console.print(f"[bold cyan]HF Agent:[/bold cyan] {hf_message}\n")
                conversation_log.append({"week": week, "speaker": "HF Agent", "message": hf_message})
                
                # Break ONLY if agent signals completion with proper titration decisions
                if "WEEK_COMPLETE" in hf_message:
                    # Verify the message contains medication decisions before allowing completion
                    # Check for medication-related keywords indicating decisions were made
                    has_med_decision = (
                        "increase" in hf_message.lower() or
                        "decrease" in hf_message.lower() or
                        "continue" in hf_message.lower() or
                        "hold" in hf_message.lower() or
                        "maintain" in hf_message.lower() or
                        "keep" in hf_message.lower() or
                        "titration" in hf_message.lower() or
                        "mg" in hf_message.lower()  # Dose mentions
                    )
                    
                    if has_med_decision:
                        console.print(f"\n[bold green]✅ Week {week} completed with titration decisions![/bold green]")
                        break
                    else:
                        # Agent said WEEK_COMPLETE but didn't make proper decisions - continue
                        console.print(f"[yellow]⚠️  Agent said WEEK_COMPLETE but didn't make titration decisions - continuing...[/yellow]")
                        
            # If we reached max exchanges without completion, warn but continue
            if exchange == max_exchanges - 1 and "WEEK_COMPLETE" not in hf_message:
                console.print(f"[yellow]⚠️  Week {week} reached maximum exchanges without completion signal[/yellow]")
            
            # Reset both agents for next week (SDK handles internally)
            hf_agent.reset_conversation()
            patient_agent.reset_conversation()
                    
        except Exception as e:
            console.print(f"[red]Error in week {week}: {e}[/red]")
            continue
        
        console.print("\n" + "="*50)
    
    # Evaluate final clinical outcome
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
    import json
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