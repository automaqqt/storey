import json
from fastapi import APIRouter, HTTPException, status
from ..models.schema import TaleRequest, TaleResponse, LlmJsonResponse
from ..services import rag_service, llm_service
from ..core.config import settings
from typing import List, Dict, Any, Optional

router = APIRouter()

MAX_HISTORY_FOR_PROMPT = 10 # Number of recent interactions to include directly
MAX_HISTORY_FOR_RAG_QUERY = 6 # Number of recent interactions for RAG query
SUMMARIZE_TURN_INTERVAL = 7 # How often to summarize

@router.get("/tales", response_model=List[str])
async def get_tales_list():
    """Returns a list of available tale titles."""
    tales = rag_service.get_available_tales()
    if not tales:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No tales found or metadata not loaded.")
    return tales

@router.post("/generate-tale", response_model=TaleResponse)
async def generate_tale_segment(request: TaleRequest):
    """Generates the next story segment based on user action and tale context."""
    print(f"\n--- Turn {request.currentTurnNumber} for Tale: {request.taleId} ---")
    
    # Extract debug configuration if present
    debug_config = request.debugConfig
    if debug_config:
        print(f"Debug config received: {debug_config}")

    # --- 1. Determine User Action ---
    last_user_action_text = ""
    if request.action.choice:
        last_user_action_text = f"My choice: {request.action.choice}"
        print(f"Action: Choice = '{request.action.choice}'")
    elif request.action.customInput:
        last_user_action_text = f"My custom action: {request.action.customInput}"
        print(f"Action: Custom = '{request.action.customInput}'")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid action (choice or customInput) provided.")

    # Append the user's textual action to the history *for this turn's processing*
    current_turn_history = request.storyHistory + [f"> {last_user_action_text}"] # Add prefix for clarity if needed

    # --- 2. Summarization ---
    print("Summarization triggered.")
    # Find history segments since last assumed summary point
    start_index = max(0, len(request.storyHistory) - SUMMARIZE_TURN_INTERVAL * 2) # Look back interval*2 turns roughly
    recent_developments = request.storyHistory[start_index:] + [f"> {last_user_action_text}"] # Include current action
    
    # Get summary model and temperature from debug config if available
    summary_model = None
    summary_system_prompt = None
    temperature = 0.7  # Default temperature
    
    if debug_config:
        # Access Pydantic model attributes directly
        summary_model = debug_config.summaryModel if hasattr(debug_config, 'summaryModel') else None
        summary_system_prompt = debug_config.summarySystemPrompt if hasattr(debug_config, 'summarySystemPrompt') else None
        temperature = debug_config.temperature if hasattr(debug_config, 'temperature') else temperature
        
        if summary_model:
            print(f"Using custom summary model: {summary_model}")
        if summary_system_prompt:
            print(f"Using custom summary system prompt")
        print(f"Using temperature: {temperature}")
            
        # Replace placeholders if they exist in the custom summary prompt
        if summary_system_prompt:
            summary_system_prompt = summary_system_prompt.replace("{tale_title}", request.taleId)
            summary_system_prompt = summary_system_prompt.replace("{existing_summary}", request.currentSummary)
    
    current_summary = await llm_service.summarize_story(
        request.currentSummary, 
        recent_developments, 
        request.taleId,
        model=summary_model,
        custom_system_prompt=summary_system_prompt,
        temperature=temperature
    )

    # --- 3. RAG Context Retrieval ---
    # Create query from most recent interactions
    rag_query_history = current_turn_history[-MAX_HISTORY_FOR_RAG_QUERY:]
    rag_query_text = "\n".join(rag_query_history)
    original_tale_context = rag_service.retrieve_relevant_chunks(
        request.taleId, rag_query_text, k=7 # Retrieve top 7 chunks
    )
    print(f"RAG Context: {original_tale_context[:200]}...")

    # --- 4. Construct LLM Prompt ---
    # Use custom system prompt if provided in debug config
    custom_system_prompt = None
    story_model = None
    if debug_config:
        # Access Pydantic model attributes directly
        custom_system_prompt = debug_config.systemPrompt if hasattr(debug_config, 'systemPrompt') else None
        story_model = debug_config.storyModel if hasattr(debug_config, 'storyModel') else None
        if custom_system_prompt:
            print(f"Using custom system prompt")
        if story_model:
            print(f"Using custom story model: {story_model}")
    
    if custom_system_prompt:
        # Use the custom system prompt (frontend is responsible for proper formatting)
        system_prompt = custom_system_prompt
        
        # Replace placeholders if they exist in the custom prompt
        system_prompt = system_prompt.replace("{request.taleId}", request.taleId)
        system_prompt = system_prompt.replace("{current_summary}", current_summary)
        system_prompt = system_prompt.replace("{original_tale_context}", original_tale_context)
    else:
        # Default system prompt
        system_prompt = f"""
Du bist ein klassischer Erzähler im Stil deutscher Volksmärchen. Deine Sprache ist kindgerecht, bildhaft und leicht verständlich geeignet für Kinder zwischen 6 und 10 Jahren. 
Du schreibst ausschließlich in: der dritten Person Singular, der Vergangenheitsform (Präteritum), einem märchentypischen Ton: ruhig, geheimnisvoll, poetisch, aber klar. Beispiel: „Der Mond schien silbern auf den moosigen Pfad, als Rotkäppchen ihren ersten Schritt ins Dunkel wagte.
Vermeide vollständig: moderne Begriffe, Konzepte oder Objekte (z.B. Handy, Firma, Polizei, Auto), Gewalt ohne moralischen Kontext, Ironie, Sarkasmus oder Meta-Kommentare, Fremdwörter, Anglizismen oder komplizierte Satzstrukturen. Negativ-Beispiel: „Plötzlich kam ein Polizeiwagen angerast."
Stilmittel, die bevorzugt verwendet werden sollen: stimmungsvolle Bilder, sanfte Wiederholungen und rhythmische Satzführung, archetypische Märchenfiguren und -orte
Aktuelles Märchen: "{request.taleId}"
Hier ist die bisherige Handlung: {current_summary}
{original_tale_context} 
Die Handlung soll sich besonders an den letzten Nutzerentscheidungen und history entries orientieren.
Verfasse eine neue kurze Szene mit 6 bis 10 Sätzen. Strukturiere jede Szene nach folgendem Muster:
1. Einstieg in die Situation oder Umgebung  
2. Ein zentrales Ereignis oder eine neue Wendung  
3. Abschluss mit offenem Ende, das eine neue Entscheidung oder Entwicklung vorbereitet
Diese Szene soll: logisch und kohärent auf den bisherigen Verlauf aufbauen, innerhalb des etablierten Märchenrahmens bleiben, eine originelle Wendung darstellen, offen genug enden, um eine weitere Entscheidung zu ermöglichen

Bevor du antwortest, prüfe: Ist die Szene stilistisch und thematisch einwandfrei im Märchengenre verankert? Ist sie altersgerecht, logisch und frei von modernen oder stilfremden Elementen?
Priorisiere in deiner Geschichte immer die letzte Auswahl "My Choice:". Falls du bei einer Frage unsicher bist: Überarbeite die Szene vollständig.
Gib ausschließlich den Märchentext aus. Verzicht auf Einleitungen, Erklärungen oder Meta-Kommentare. Liefere den Text als kohärente Erzählpassage " keine Aufzählung. Beginne direkt mit der ersten Zeile der Geschichte.
HANDLUNGSOPTIONEN
Erzeuge die Handlungsoptionen unmittelbar nach der Szene, ohne Zwischenkommentar oder Einleitung, gib drei Entscheidungsoptionen für die Nutzer aus, damit sie die Geschichte aktiv mitgestalten kann:
1. **Option A – Storynahe Fortsetzung**  
   Eine Handlung, die erwartbar und logisch auf die Szene folgt und den traditionellen Märchenverlauf weiterführt.
2. **Option B – Alternative Wendung**  
   Eine kreative, aber genre- und stilgerechte Abweichung vom bekannten Verlauf. Diese Option darf überraschend sein, aber muss in der Märchenwelt glaubwürdig bleiben. Stelle sicher, dass sich Option A und B in Handlung, Ton oder Risiko deutlich unterscheiden, um eine echte Wahlmöglichkeit zu bieten.
Jede Option soll sprachlich einfach, stimmungsvoll und kindgerecht formuliert sein. Die Vorschläge müssen **zur erzählten Szene passen**, dürfen aber **nicht deren Inhalt wiederholen**.
Format your entire response content ONLY as a valid JSON object string, DONT use markdown and keep the output format cause its very important: {{"storySegment": "...", "choices": ["...", "..."]}}"""
    
    # User prompt part contains recent history
    prompt_history = current_turn_history[-MAX_HISTORY_FOR_PROMPT:]
    user_prompt = f"""Recent Interaction History:
{'[Start of History]' if len(current_turn_history) <= MAX_HISTORY_FOR_PROMPT else '[... earlier history summarized ...]'}
{chr(10).join(prompt_history)}

(The user's most recent action is the last message in the history above)

Your JSON Response:"""
    
    print(f"System prompt length: {len(system_prompt)}")
    print(f"User prompt length: {len(user_prompt)}")
    
    # --- 5. Generate LLM Response ---
    llm_json_response, raw_llm_response = await llm_service.generate_llm_response(
        system_prompt, 
        user_prompt,
        model=story_model,
        temperature=temperature
    )

    if not llm_json_response:
         print("Error: Failed to get valid response from LLM.")
         raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="LLM service failed to generate a valid response.")

    print(f"Response generated with {len(llm_json_response['storySegment'])} chars in story segment")
    print(f"Number of choices: {len(llm_json_response['choices'])}")
    
    # --- 6. Prepare Response ---
    try:
        response_data = TaleResponse(
            storySegment=llm_json_response['storySegment'],
            choices=llm_json_response['choices'],
            updatedSummary=current_summary,
            nextTurnNumber=request.currentTurnNumber + 1,
            rawResponse=raw_llm_response if debug_config else None  # Only include raw response in debug mode
        )
        print(f"--- Turn End ---")
        return response_data
    except Exception as e:
         print(f"Error creating final response: {e}")
         raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to construct final response.")