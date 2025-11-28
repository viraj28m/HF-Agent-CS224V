# Heart Failure Medication Titration Agent

A sophisticated AI-powered system for simulating heart failure medication titration conversations using the OpenAI Agents SDK. This system implements evidence-based protocols for safe medication optimization through conversational AI.

## Features

- **Two Operation Modes:**
  - **Interactive Mode**: You act as the patient, conversing with the HF agent
  - **Automated Mode**: Two AI agents (HF agent + patient agent) converse autonomously

- **Evidence-Based Protocols**: Complete implementation of heart failure medication protocols including:
  - ACE Inhibitors (Enalapril, Lisinopril, Ramipril, Captopril)
  - ARBs (Losartan, Valsartan, Candesartan) 
  - Beta Blockers (Carvedilol, Metoprolol Succinate, Bisoprolol)
  - Aldosterone Antagonists (Spironolactone, Eplerenone)
  - SGLT2 Inhibitors (Dapagliflozin, Empagliflozin, Sotagliflozin)
  - ARNI (Sacubitril/Valsartan with special ACE-I washout requirements)
  - Vasodilators (Hydralazine, Isosorbide Dinitrate, BiDil combination)
  - sGC Stimulators (Vericiguat)

- **Safety Features:**
  - Real-time safety monitoring
  - Emergency symptom detection
  - Hold criteria validation
  - Lab monitoring schedules

- **Realistic Patient Simulation:**
  - Configurable behavior patterns
  - Adherence simulation
  - Symptom progression
  - Side effect modeling

## Installation

1. **Clone the repository:**
```bash
git clone <repository-url>
cd HF_Agent_CS224V
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables:**
```bash
cp .env.example .env
# Edit .env file with your API credentials
```

Required environment variables:
- `AZURE_OPENAI_API_KEY`: Your Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT`: Your Azure OpenAI endpoint
- `AZURE_OPENAI_DEPLOYMENT_NAME`: Your deployment name
- `AZURE_OPENAI_API_VERSION`: API version

## Testing

Before using the system, you can test that all protocols are properly loaded:

```bash
# Test the comprehensive protocol system
python test_comprehensive_protocols.py

# Test all system components
python test_system.py
```

## Usage

### List Available Patient Scenarios
```bash
python3 cli.py list-scenarios
```

### Interactive Mode (Human as Patient)
```bash
python3 cli.py interactive --patient-id HF_CONV_001 --weeks 8
```

In interactive mode:
- You act as the patient from the selected scenario
- Respond naturally to the HF agent's questions
- Provide realistic vital signs and symptoms
- Type 'quit' to exit early

### Automated Mode (Agent-to-Agent)
```bash
python3 cli.py automated --patient-id HF_CONV_001 --weeks 8 \
  --adherence-pattern consistently_high \
  --symptom-pattern steady_improvement \
  --endpoint complete_success
```

Available patterns:
- **Adherence**: `consistently_high`, `declining`, `improving`, `fluctuating`, `single_drop_then_stable`
- **Symptoms**: `steady_improvement`, `mixed_response`, `plateau`, `progressive_worsening`, `acute_escalation_to_ed`
- **Endpoints**: `complete_success`, `partial_success`, `non_adherence_failure`, `side_effect_failure`, `acute_decompensation_ed`, `hospitalization_pause`, `patient_withdrawal`

## Project Structure

```
hf_agent/
├── agents/
│   ├── hf_agent.py          # Heart Failure Agent
│   └── patient_agent.py     # Patient Simulation Agent
├── models/
│   ├── patient.py           # Patient data models
│   ├── medication.py        # Medication models
├── tools/
│   ├── protocol_tools.py    # Medical protocol tools
│   ├── safety_tools.py      # Safety assessment tools
│   └── titration_tools.py   # Titration decision tools
├── data/
│   ├── complete_protocols.py      # Comprehensive protocol definitions (18+ medications)
│   └── protocol_loader.py         # Protocol management utilities
├── evaluation/
│   └── safety_validator.py        # Safety validation
cli.py                       # Command-line interface
main.py                      # Entry point
```

## Key Components

### Heart Failure Agent
- Conversational AI specialized in HF medication titration
- Uses evidence-based protocols for decision making
- Prioritizes patient safety with emergency detection
- Provides clear explanations and education

### Patient Agent
- Simulates realistic patient responses
- Configurable behavioral patterns
- Generates realistic vital signs and symptoms
- Models different adherence and outcome scenarios

### Medical Protocol Tools
- Complete medication protocol database
- Safety assessment functions
- Titration decision logic
- Lab monitoring schedules

### Safety Validation
- Real-time safety monitoring
- Emergency symptom detection
- Hold criteria enforcement
- Comprehensive violation tracking

## Example Conversation Flow

1. **Weekly Check-in**: Agent asks about symptoms, adherence, vitals
2. **Data Collection**: Patient provides requested information
3. **Safety Assessment**: Agent evaluates safety using protocol tools
4. **Titration Decision**: Evidence-based medication adjustment
5. **Patient Education**: Explanation of changes and rationale
6. **Follow-up Planning**: Schedule next appointment and monitoring

## Safety Features

- **Emergency Detection**: Automatic recognition of severe symptoms requiring immediate care
- **Hold Criteria**: Protocol-based medication holding for safety concerns  
- **Lab Monitoring**: Appropriate scheduling based on medication classes
- **Vital Sign Thresholds**: Real-time monitoring of BP, HR, and other parameters

## Development

The system is built using:
- **Python 3.11+**
- **OpenAI Agents Python SDK**: For agent orchestration
- **Pydantic**: For type-safe data models
- **Rich**: For enhanced CLI output
- **Click**: For command-line interface

## Clinical Accuracy

All medication protocols are based on current heart failure guidelines and include:
- Appropriate starting doses
- Incremental titration schedules
- Maximum target doses
- Contraindications and hold criteria
- Laboratory monitoring requirements

## Contributing

When adding new medications or protocols:
1. Add to `hf_agent/data/complete_protocols.py` 
2. Update relevant models if needed
3. Add appropriate safety validation
4. Test with various patient scenarios

## License

This project is for educational and research purposes as part of CS224V coursework.