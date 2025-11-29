# 🫀 Heart Failure Medication Titration System - Final Architecture

## **📋 Overview**
This system provides AI-powered heart failure medication titration support for CS224V research. It uses the OpenAI Agents SDK with Azure OpenAI for realistic patient-agent conversations.

## **🚀 Usage**

### **Interactive Mode** (Human as Patient)
```bash
python3 cli.py interactive --patient-id HF_CONV_001 --weeks 4
```
- You act as the patient
- HF Agent provides clinical guidance
- Automatic week progression when agent says "WEEK_COMPLETE"

### **Automated Mode** (AI Patient vs AI Doctor)
```bash
python3 cli.py automated --patient-id HF_CONV_001 --weeks 4
```
- Two AI agents converse automatically
- Realistic patient behavioral patterns
- Complete conversation logs saved

### **List Patient Scenarios**
```bash
python3 cli.py list-scenarios
```
- Shows all 149 available patient scenarios
- Different education levels, medical literacy, medication combinations

## **🏗️ System Architecture**

### **Core Components**
- **CLI Interface** (`cli.py`) - Main entry point for all interactions
- **HF Agent** (`hf_agent/agents/azure_hf_agent.py`) - Clinical decision support agent
- **Patient Agent** (`hf_agent/agents/azure_patient_agent.py`) - Simulates realistic patients
- **Clinical Tools** (`hf_agent/tools/complete_protocol_tools.py`) - Evidence-based protocols

### **Key Features**
✅ **20+ Heart Failure Medications** with complete clinical protocols  
✅ **149 Patient Scenarios** with varied backgrounds and medication regimens  
✅ **Behavioral Patterns** (adherence, symptoms, side effects, outcomes)  
✅ **Safety Validation** with emergency detection and lab monitoring  
✅ **Time-based Lab Monitoring** (1-2 weeks for ACE/ARB, 2-4 weeks for others)  
✅ **Evidence-based Titration** using clinical guidelines  
✅ **Rich CLI Interface** with progress tracking and conversation logs  

### **Data Sources**
- **Patient Scenarios** (`all_conversations.json`) - 149 realistic clinical cases
- **Medication Protocols** (`hf_agent/data/complete_protocols.py`) - Complete clinical data
- **Clinical Guidelines** - Built into agent instructions and tools

## **🛠️ Technical Implementation**

### **OpenAI Agents SDK with Azure OpenAI**
- Uses `AsyncAzureOpenAI` client for proper Azure integration
- Function calling for clinical tools and patient data generation
- Conversation state management handled by SDK

### **Patient Behavioral Modeling**
- **Adherence Patterns**: consistently_high, declining, improving, fluctuating
- **Symptom Patterns**: steady_improvement, progressive_worsening, mixed_response
- **Vital Signs Patterns**: stable, trending_low/high, oscillating
- **Target Endpoints**: complete_success, side_effect_failure, acute_decompensation

### **Clinical Decision Support**
- **Mandatory Tool Usage**: Agents must use specific tools for safety checks
- **Evidence-based Protocols**: All recommendations follow clinical guidelines
- **Safety-first Approach**: Emergency detection with immediate referral triggers
- **Lab Monitoring**: Automated reminders based on medication timing requirements

## **📁 File Structure**
```
HF_Agent_CS224V/
├── cli.py                          # Main CLI interface
├── all_conversations.json          # 149 patient scenarios
├── requirements.txt               # Python dependencies
├── .env                          # Azure OpenAI credentials
└── hf_agent/
    ├── agents/
    │   ├── azure_hf_agent.py      # Heart Failure specialist agent
    │   ├── azure_patient_agent.py # Patient simulation agent  
    │   └── patient_agent.py       # Utility functions for patient data
    ├── data/
    │   ├── complete_protocols.py  # All 20+ medication protocols
    │   └── protocol_loader.py     # Protocol access utilities
    ├── models/
    │   ├── medication.py          # Pydantic models for medications
    │   └── patient.py            # Pydantic models for patients
    ├── tools/
    │   └── complete_protocol_tools.py # Clinical decision support tools
    ├── evaluation/
    │   └── safety_validator.py    # Safety validation utilities
    └── llm_client.py             # Azure OpenAI client wrapper
```

## **🎯 Research Applications**
- **Medication Adherence Studies**: Simulate different patient compliance patterns
- **Clinical Decision Support**: Test AI-guided medication titration algorithms  
- **Patient Education Research**: Analyze communication effectiveness across education levels
- **Safety Protocol Validation**: Test emergency detection and intervention triggers
- **Multi-agent Healthcare**: Study AI-AI medical conversations and handoffs

## **✨ Key Innovations**
1. **Realistic Patient Simulation** with behavioral consistency over time
2. **Evidence-based Clinical Tools** integrated via function calling
3. **Multi-week Progression** with automatic state management
4. **Safety-first Architecture** with mandatory protocol compliance
5. **Rich Conversational Interface** supporting both human and AI interactions

This system demonstrates sophisticated AI agents working together to provide realistic, clinically-accurate heart failure medication management scenarios for research and education.