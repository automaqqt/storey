"use client"

import { useState, useEffect, useRef } from 'react';
import styles from '../styles/Home.module.css';

// MAX_CUSTOM_INPUT_LENGTH (same as before)
const MAX_CUSTOM_INPUT_LENGTH = 150;
// Define backend URL (use environment variable in real app)
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

// Development authentication credentials
const DEV_USERNAME = "admin";
const DEV_PASSWORD = "storyteller123";

// Default system prompts for debugging purposes
const DEFAULT_SYSTEM_PROMPTS = {
  default: `
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
  Format your entire response content ONLY as a valid JSON object string, DONT use markdown and keep the output format cause its very important: {{"storySegment": "...", "choices": ["...", "..."]}}`,
  short: `Erzähle eine kurze kindgerechte Version dieser Geschichte im Märchenstil. Gib genau zwei Optionen zur Auswahl.`,
  experimental: `Sei ein kreativer, moderner Märchenerzähler. Füge unerwartete Wendungen ein, während du einen kindgerechten Ton beibehältst.`
};

// Available models for selection
const AVAILABLE_MODELS = {
  story: [
    { id: "google/gemini-2.5-pro-exp-03-25:free", name: "Gemini 2.5 Pro" },
    { id: "google/gemini-2.0-flash-exp:free", name: "Gemini 2.0 Flash" },
    { id: "google/gemini-2.0-flash-thinking-exp-1219:free", name: "Gemini 2.0 Flash Thinking" },
    { id: "deepseek/deepseek-chat-v3-0324:free", name: "Deepseek V3" },
    { id: "deepseek/deepseek-r1:free", name: "Deepseek R1" },
    { id: "qwen/qwq-32b:free", name: "QwQ 32b" },
    { id: "google/gemma-3-27b-it:free", name: "Gemma 3 27b" },
    { id: "meta-llama/llama-3.3-70b-instruct:free", name: "Llama 3.3 70b" }
  ],
  summary: [
    { id: "google/gemini-2.0-flash-exp:free", name: "Gemini 2.0 Flash" },
    { id: "meta-llama/llama-3.2-3b-instruct:free", name: "Llama 3.2 3b" }
  ]
};


export default function HomePage() {
  // --- Authentication State ---
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState("");

  // --- Existing State ---
  const [storyHistory, setStoryHistory] = useState([]);
  const [currentChoices, setCurrentChoices] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isStarted, setIsStarted] = useState(false);
  const [customInput, setCustomInput] = useState('');
  const [lastAttemptedAction, setLastAttemptedAction] = useState(null);
  const [isCustomInputVisible, setIsCustomInputVisible] = useState(false);

  // --- New State for Tales & Progress ---
  const [availableTales, setAvailableTales] = useState([]);
  const [selectedTaleId, setSelectedTaleId] = useState(null);
  const [currentSummary, setCurrentSummary] = useState('');
  const [currentTurnNumber, setCurrentTurnNumber] = useState(0);
  const [talesLoading, setTalesLoading] = useState(true);
  const [talesError, setTalesError] = useState(null);

  // --- Debug UI State ---
  const [debugPanelVisible, setDebugPanelVisible] = useState(false);
  const [selectedStoryModel, setSelectedStoryModel] = useState(AVAILABLE_MODELS.story[0].id);
  const [selectedSummaryModel, setSelectedSummaryModel] = useState(AVAILABLE_MODELS.summary[0].id);
  const [useCustomPrompt, setUseCustomPrompt] = useState(false);
  const [systemPrompt, setSystemPrompt] = useState(DEFAULT_SYSTEM_PROMPTS.default);
  const [useCustomSummaryPrompt, setUseCustomSummaryPrompt] = useState(false);
  const [summarySystemPrompt, setSummarySystemPrompt] = useState("");
  const [temperature, setTemperature] = useState(0.7); // Default temperature value
  const [rawResponse, setRawResponse] = useState(null);

  const storyEndRef = useRef(null);
  const systemPromptRef = useRef(null);

  // --- Authentication ---
  useEffect(() => {
    // Check if already authenticated in session storage
    const isAuth = sessionStorage.getItem('isAuthenticated') === 'true';
    setIsAuthenticated(isAuth);
  }, []);

  const handleLogin = (e) => {
    e.preventDefault();
    if (username === DEV_USERNAME && password === DEV_PASSWORD) {
      setIsAuthenticated(true);
      setAuthError("");
      // Save authentication status to session storage
      sessionStorage.setItem('isAuthenticated', 'true');
    } else {
      setAuthError("Invalid username or password");
    }
  };

  // --- Fetch Available Tales on Mount ---
  useEffect(() => {
    // Only fetch tales if authenticated
    if (!isAuthenticated) return;

    const fetchTales = async () => {
      setTalesLoading(true);
      setTalesError(null);
      try {
        const response = await fetch(`${API_BASE_URL}/tales`);
        if (!response.ok) {
           let errorMsg = `Failed to fetch tales list: ${response.statusText}`;
           try {
               const errData = await response.json();
               errorMsg = errData.detail || errorMsg;
           } catch (e) { /* ignore json parse error */ }
           throw new Error(errorMsg);
        }
        const data = await response.json();
        setAvailableTales(data || []);
      } catch (err) {
        setTalesError(err.message);
        console.error("Error fetching tales:", err);
      } finally {
        setTalesLoading(false);
      }
    };

    fetchTales();
  }, [isAuthenticated]);

  // Auto-scroll useEffect
  useEffect(() => {
    storyEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [storyHistory]);

  // Reset default prompt when toggling custom mode
  useEffect(() => {
    if (!useCustomPrompt) {
      setSystemPrompt(DEFAULT_SYSTEM_PROMPTS.default);
    }
  }, [useCustomPrompt]);

  // --- Update API Call Function ---
  const fetchNextSegment = async (taleId, history, summary, turn, action) => {
    if (!taleId) {
        setError("No taleId provided to fetchNextSegment.");
        setIsLoading(false);
        return;
    }

    const requestBody = {
      taleId: taleId,
      storyHistory: history,
      currentSummary: summary,
      currentTurnNumber: turn,
      action: action,
      // Add debug config
      debugConfig: {
        storyModel: selectedStoryModel,
        summaryModel: selectedSummaryModel,
        systemPrompt: useCustomPrompt ? systemPrompt : undefined,
        summarySystemPrompt: useCustomSummaryPrompt ? summarySystemPrompt : undefined,
        temperature: temperature // Add temperature to debug config
      }
    };

    setLastAttemptedAction({ taleId, history, summary, turn, action });
    setIsLoading(true);
    setError(null);
    setRawResponse(null);

    console.log('Sending request body:', JSON.stringify(requestBody, null, 2));
    
    try {
      const response = await fetch(`${API_BASE_URL}/generate-tale`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        let errorMsg = `API Error: ${response.statusText}`;
        try { 
          const errData = await response.json(); 
          errorMsg = errData.detail || errorMsg; 
        } catch(e){}
        throw new Error(errorMsg);
      }

      const data = await response.json();

      // Update state using response data
      setStoryHistory(prev => [...prev, { type: 'story', text: data.storySegment }]);
      setCurrentChoices(data.choices);
      setCurrentSummary(data.updatedSummary);
      setCurrentTurnNumber(data.nextTurnNumber);
      setLastAttemptedAction(null);
      
      // Store raw response for debugging
      if (data.rawResponse) {
        setRawResponse(data.rawResponse);
      }

    } catch (err) {
      setError(err.message);
      console.error("Error fetching next segment:", err);
    } finally {
      setIsLoading(false);
    }
  };

  // --- Event Handlers ---
  const handleTaleSelect = async (taleId) => {
    console.log("Selected Tale:", taleId);
    setSelectedTaleId(taleId);
    setIsStarted(true);
    setStoryHistory([]);
    setCurrentChoices([]);
    setCustomInput('');
    setIsCustomInputVisible(false);
    setError(null);
    setLastAttemptedAction(null);
    setCurrentTurnNumber(0);
    setRawResponse(null);

    const initialSummary = `The story of "${taleId}" begins...`;
    setCurrentSummary(initialSummary);
    const initialHistory = [];
    const initialTurn = 0;
    const startAction = { choice: "Rottkäppchen bekommt den Kuchen von Mutter übergeben und soll nun zu Großmutter gehen ohne im Wald vom Weg abzukommen." };

    await fetchNextSegment(
        taleId,
        initialHistory,
        initialSummary,
        initialTurn,
        startAction
    );
  };

  const handleChoiceClick = async (choice) => {
    if (isLoading) return;

    const choiceText = `> ${choice}`;
    const newVisualHistory = [...storyHistory, { type: 'choice', text: choiceText }];
    setStoryHistory(newVisualHistory);

    const historyForAPI = storyHistory
      .filter(item => item.type === 'story' || item.type === 'choice' || item.type === 'userInput')
      .map(item => item.text);

    setCurrentChoices([]);
    setCustomInput('');
    setIsCustomInputVisible(false);

    await fetchNextSegment(
        selectedTaleId,
        historyForAPI,
        currentSummary,
        currentTurnNumber,
        { choice: choice }
    );
  };

  const handleCustomSubmit = async (e) => {
    e.preventDefault();
    const trimmedInput = customInput.trim();
    if (!trimmedInput || isLoading) return;

    const userText = `> (Custom) ${trimmedInput}`;
    const newVisualHistory = [...storyHistory, { type: 'userInput', text: userText }];
    setStoryHistory(newVisualHistory);

    const historyForAPI = storyHistory
      .filter(item => item.type === 'story' || item.type === 'choice' || item.type === 'userInput')
      .map(item => item.text);

    setCurrentChoices([]);
    setCustomInput('');
    setIsCustomInputVisible(false);

    await fetchNextSegment(
        selectedTaleId,
        historyForAPI,
        currentSummary,
        currentTurnNumber,
        { customInput: trimmedInput }
    );
  };

  const handleRetry = () => {
    if (!lastAttemptedAction || isLoading) {
       console.warn("Retry called inappropriately.");
       return;
    }
    console.log("Retrying action:", lastAttemptedAction);
    setError(null);

    fetchNextSegment(
        lastAttemptedAction.taleId,
        lastAttemptedAction.history,
        lastAttemptedAction.summary,
        lastAttemptedAction.turn,
        lastAttemptedAction.action
    );
  };

  const handleInputChange = (e) => {
    if (e.target.value.length <= MAX_CUSTOM_INPUT_LENGTH) {
        setCustomInput(e.target.value);
    }
  };

  const toggleCustomInput = () => {
    setIsCustomInputVisible(prev => !prev);
  };

  const toggleDebugPanel = () => {
    setDebugPanelVisible(!debugPanelVisible);
  };

  const handleSystemPromptChange = (e) => {
    setSystemPrompt(e.target.value);
  };

  const handleSummarySystemPromptChange = (e) => {
    setSummarySystemPrompt(e.target.value);
  };

  const handleTemperatureChange = (e) => {
    setTemperature(parseFloat(e.target.value));
  };

  const toggleCustomPrompt = () => {
    setUseCustomPrompt(!useCustomPrompt);
    if (systemPromptRef.current) {
      setTimeout(() => {
        systemPromptRef.current.style.height = 'auto';
        systemPromptRef.current.style.height = systemPromptRef.current.scrollHeight + 'px';
      }, 0);
    }
  };
  
  const toggleCustomSummaryPrompt = () => {
    setUseCustomSummaryPrompt(!useCustomSummaryPrompt);
  };

  // Auto-resize textarea
  const autoResizeTextarea = (e) => {
    e.target.style.height = 'auto';
    e.target.style.height = e.target.scrollHeight + 'px';
  };

  // If not authenticated, show login screen
  if (!isAuthenticated) {
    return (
      <div className={styles.pageContainer}>
        <div className={styles.authContainer}>
          <h1 className={styles.authTitle}>Interactive Storyteller</h1>
          <h2>Development Access</h2>
          
          <form onSubmit={handleLogin} className={styles.authForm}>
            {authError && <p className={styles.authError}>{authError}</p>}
            
            <div className={styles.formGroup}>
              <label htmlFor="username">Username</label>
              <input 
                type="text" 
                id="username" 
                value={username} 
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
            
            <div className={styles.formGroup}>
              <label htmlFor="password">Password</label>
              <input 
                type="password" 
                id="password" 
                value={password} 
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            
            <button type="submit" className={styles.authButton}>Login</button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.pageContainer}>
      <div className={`${styles.bookContainer} ${debugPanelVisible ? styles.withDebugPanel : ''}`}>
        <div className={styles.headerArea}>
          <h1 className={styles.title}>Interactive Chronicle</h1>
          <button 
            className={styles.debugToggleButton} 
            onClick={toggleDebugPanel}
          >
            {debugPanelVisible ? "Hide Debug" : "Show Debug Panel"}
          </button>
        </div>

        {/* Debug Panel */}
        {debugPanelVisible && (
          <div className={styles.debugPanel}>
            <h3>Debug Controls</h3>
            
            <div className={styles.debugSection}>
              <h4>Models</h4>
              <div className={styles.modelSelectors}>
                <div className={styles.modelSelector}>
                  <label>Story Generation Model:</label>
                  <select 
                    value={selectedStoryModel} 
                    onChange={(e) => setSelectedStoryModel(e.target.value)}
                  >
                    {AVAILABLE_MODELS.story.map(model => (
                      <option key={model.id} value={model.id}>{model.name}</option>
                    ))}
                  </select>
                </div>
                
                <div className={styles.modelSelector}>
                  <label>Summary Generation Model:</label>
                  <select 
                    value={selectedSummaryModel} 
                    onChange={(e) => setSelectedSummaryModel(e.target.value)}
                  >
                    {AVAILABLE_MODELS.summary.map(model => (
                      <option key={model.id} value={model.id}>{model.name}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
            
            <div className={styles.debugSection}>
              <h4>Temperature</h4>
              <div className={styles.temperatureControl}>
                <div className={styles.sliderContainer}>
                  <input 
                    type="range" 
                    min="0" 
                    max="1" 
                    step="0.01"
                    value={temperature}
                    onChange={handleTemperatureChange}
                    className={styles.slider}
                  />
                  <div className={styles.sliderLabels}>
                    <span>More Predictable</span>
                    <span>{temperature.toFixed(2)}</span>
                    <span>More Random</span>
                  </div>
                </div>
              </div>
            </div>
            
            <div className={styles.debugSection}>
              <h4>System Prompts</h4>
              
              <div className={styles.promptToggle}>
                <label>
                  <input 
                    type="checkbox" 
                    checked={useCustomPrompt} 
                    onChange={toggleCustomPrompt}
                  />
                  Use Custom Story Prompt
                </label>
              </div>
              
              {useCustomPrompt && (
                <div className={styles.promptEditor}>
                  <label>Custom Story System Prompt:</label>
                  <textarea
                    ref={systemPromptRef}
                    value={systemPrompt}
                    onChange={handleSystemPromptChange}
                    onInput={autoResizeTextarea}
                    className={styles.systemPromptTextarea}
                    rows={5}
                  />
                </div>
              )}
              
              <div className={styles.promptToggle}>
                <label>
                  <input 
                    type="checkbox" 
                    checked={useCustomSummaryPrompt} 
                    onChange={toggleCustomSummaryPrompt}
                  />
                  Use Custom Summary Prompt
                </label>
              </div>
              
              {useCustomSummaryPrompt && (
                <div className={styles.promptEditor}>
                  <label>Custom Summary System Prompt:</label>
                  <textarea
                    value={summarySystemPrompt}
                    onChange={handleSummarySystemPromptChange}
                    onInput={autoResizeTextarea}
                    className={styles.systemPromptTextarea}
                    rows={3}
                    placeholder="Enter your custom summary prompt here"
                  />
                </div>
              )}
            </div>
            
            {rawResponse && (
              <div className={styles.debugSection}>
                <h4>Raw LLM Response</h4>
                <pre className={styles.rawResponseDisplay}>
                  {typeof rawResponse === 'object' 
                    ? JSON.stringify(rawResponse, null, 2) 
                    : rawResponse}
                </pre>
              </div>
            )}
            
            <div className={styles.debugSection}>
              <h4>Current State</h4>
              <div className={styles.stateDisplay}>
                <div><strong>Tale:</strong> {selectedTaleId || 'None'}</div>
                <div><strong>Turn:</strong> {currentTurnNumber}</div>
                <div className={styles.summaryDisplay}>
                  <strong>Current Summary:</strong>
                  <div className={styles.summaryText}>{currentSummary}</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {!isStarted ? (
          // Initial Tale Selection Screen
          <div className={styles.startContainer}>
            <h2 className={styles.startTitle}>Choose Your Tale</h2>
            {talesLoading && <p className={styles.loading}>Loading tales...</p>}
            {talesError && <p className={styles.error}>Error loading tales: {talesError}</p>}
            {!talesLoading && !talesError && availableTales.length === 0 && (
              <p>No tales found. Ensure the backend is running and data is processed.</p>
            )}
            {!talesLoading && !talesError && availableTales.length > 0 && (
              <div className={styles.taleListContainer}>
                 {availableTales.map((taleTitle) => (
                  <button
                    key={taleTitle}
                    onClick={() => handleTaleSelect(taleTitle)}
                    className={styles.startButton}
                    disabled={isLoading}
                  >
                    {taleTitle}
                  </button>
                ))}
              </div>
            )}
             {isLoading && <p className={styles.loading}>Conjuring story...</p>}
             {error && !talesError && <p className={styles.error}>Error starting story: {error}</p>}
          </div>
        ) : (
          <div className={styles.contentContainer}>
            <div className={styles.storyArea}>
              {storyHistory.map((item, index) => (
                <p key={index} className={`${styles.storyText} ${styles[item.type]}`}>
                  {item.text}
                </p>
              ))}
              <div ref={storyEndRef} />
            </div>

            <div className={styles.interactionArea}>
                {isLoading && <p className={styles.loading}>The quill scribbles furiously...</p>}

                {error && (
                    <div className={styles.errorContainer}>
                       <p className={styles.error}>A smudge on the page: {error}</p>
                       {lastAttemptedAction && !isLoading && (
                          <button
                              onClick={handleRetry}
                              className={styles.retryButton}
                              disabled={isLoading}
                          >
                              Retry Last Action
                          </button>
                       )}
                    </div>
                )}

                {!isLoading && !error && currentChoices.length > 0 && (
                    <div className={styles.choicesArea}>
                    <h3 className={styles.interactionPrompt}>What happens next?</h3>
                    <div className={styles.choiceButtonsContainer}>
                        {currentChoices.map((choice, index) => (
                        <button
                            key={index}
                            onClick={() => handleChoiceClick(choice)}
                            className={styles.choiceButton}
                            disabled={isLoading}
                        >
                            {choice}
                        </button>
                        ))}
                    </div>

                    {isCustomInputVisible && (
                            <div className={styles.customInputContainer}>
                                <label htmlFor="customAction" className={styles.customInputLabel}>Or, dictate your own fate:</label>
                                <textarea
                                    id="customAction"
                                    value={customInput}
                                    onChange={handleInputChange}
                                    placeholder={`Max ${MAX_CUSTOM_INPUT_LENGTH} characters...`}
                                    rows="3"
                                    className={styles.customInputTextarea}
                                    maxLength={MAX_CUSTOM_INPUT_LENGTH}
                                    disabled={isLoading}
                                    autoFocus
                                />
                                <div className={styles.customInputFooter}>
                                    <span className={styles.customInputCounter}>
                                        {customInput.length}/{MAX_CUSTOM_INPUT_LENGTH}
                                    </span>
                                    <button
                                        onClick={handleCustomSubmit}
                                        className={styles.customInputButton}
                                        disabled={isLoading || !customInput.trim()}
                                    >
                                        Declare Action
                                    </button>
                                </div>
                            </div>
                        )}

                        <div className={styles.toggleCustomContainer}>
                             <button
                                onClick={toggleCustomInput}
                                className={styles.toggleCustomInputButton}
                                disabled={isLoading}
                            >
                                {isCustomInputVisible ? 'Cancel Custom Action' : 'Write Custom Action'}
                            </button>
                        </div>
                    </div>
                )}

                {!isLoading && !error && currentChoices.length === 0 && storyHistory.length > 0 && (
                    <p className={styles.endMessage}>The ink dries... for now.</p>
                )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}