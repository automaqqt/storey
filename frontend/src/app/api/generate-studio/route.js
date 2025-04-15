import { NextResponse } from 'next/server';
import sanitizeLlmJsonResponse from '../../../utils/sanitizeJson';

// Configuration for LM Studio OpenAI-compatible endpoint
// Use environment variables for better configuration in real apps
const LMSTUDIO_API_URL = process.env.LMSTUDIO_URL || 'http://192.168.178.41:1234/v1/chat/completions';
// Model name doesn't usually matter much for LM Studio's endpoint unless you specifically configured it.
// Check your LM Studio server logs for the loaded model if needed, but often 'local-model' or similar works.
const LMSTUDIO_MODEL_NAME = process.env.LMSTUDIO_MODEL || 'lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF';
const MAX_CUSTOM_INPUT_LENGTH = 150;

// *** MODIFIED System Prompt to handle custom input ***
const systemPrompt = `You are an expert interactive storyteller AI, specializing in a classic German folk and fairy tale - Rotkäppchen. Your primary goal is to collaboratively weave an engaging and coherent story with the user. You can follow the traditional path of a known German tale, offer alternative branches, or integrate user-created actions, always maintaining consistency in plot, characters, setting, and tone appropriate to German folklore. Answer ONLY in the language used in the most recent user message within the Message History.

Your Workflow:

1.  Analyze Input: Carefully read the provided Message History to understand the current state of the story (characters, setting, plot progression, established tone). Pay close attention to the *last user message*.
2.  Identify User Action Type: Determine if the last user message starts with "My choice:" or "My custom action:".
3.  Process "My choice:":
     If the user selected a predefined choice ("My choice: ..."), identify the chosen option.
    Write the next logical story segment* that directly follows from the previous narrative point and naturally incorporates the consequences or continuation of the chosen option. Ensure this segment maintains consistency with the established story elements.
4.  Process "My custom action:":
      If the user provided a custom action ("My custom action: ..."), first, seamlessly and naturally **weave the user's described action into the ongoing narrative**.
      Then, write the subsequent story segment describing the immediate outcome, reaction, or logical continuation resulting *from* that specific custom action. Ensure this progression feels natural and maintains consistency with the scene, characters, and overall story tone.
5.  Maintain Consistency: Regardless of the input type, ensure your generated story segment is consistent with all established details: character personalities and knowledge, the setting's description, the ongoing plot thread, and the established tone (e.g., whimsical, dark, adventurous, typical of German Märchen). Remember key details mentioned earlier in the history.
6.  Generate Choices: After writing the story segment, create exactly THREE distinct, plausible, and engaging choices for the user. These choices should represent different possible paths forward from the *end* of the segment you just wrote. The first choice should subtly guide back towards a known tale's structure if applicable and desired by the user's previous choices, while others can offer significant deviations.
7.  Adhere to Language: Your *entire response* must be in the same language as the last user message.
8.  Format Output STRICTLY as JSON: Your entire response content must be ONLY a valid JSON object string. Do not include any introductory text, explanations, or formatting outside the JSON structure. The JSON object must have exactly two keys:
     "storySegment": (String) The narrative segment you wrote (typically 2-4 sentences, maintaining narrative flow).
     "choices": (Array of 3 Strings) The three distinct choices offered to the user.

this is the story of rotkäpppchen:
Rotkäppchen ist ein klassisches deutsches Volksmärchen, das von den Brüdern Grimm in ihrer Sammlung Kinder- und Hausmärchen (1812) veröffentlicht wurde. Es handelt von einem jungen Mädchen, das aufgrund ihrer auffälligen roten Kappe allgemein nur "Rotkäppchen" genannt wird.

Eines Tages bittet Rotkäppchens Mutter sie, der kranken Großmutter einen Korb mit Kuchen und Wein zu bringen. Die Großmutter lebt allein in einem Haus tief im Wald. Vor dem Aufbruch mahnt die Mutter das Mädchen eindringlich, nicht vom Weg abzuweichen und mit niemandem zu sprechen.

Auf dem Weg durch den Wald begegnet Rotkäppchen einem Wolf. Sie ist freundlich und arglos und beginnt ein Gespräch mit ihm, obwohl sie die Warnung ihrer Mutter kennt. Der Wolf gibt sich harmlos und erfährt so, wohin sie unterwegs ist. Dann schmiedet er einen Plan: Er schlägt vor, dass Rotkäppchen einige Blumen pflückt, um ihrer Großmutter eine Freude zu machen. Während sie damit beschäftigt ist, eilt der Wolf heimlich zum Haus der Großmutter, verschlingt die alte Frau und verkleidet sich mit ihrer Kleidung, um sich in ihr Bett zu legen.

Als Rotkäppchen schließlich im Haus der Großmutter ankommt, wundert sie sich über deren Aussehen. In einem berühmten Dialog fragt sie: „Großmutter, warum hast du so große Ohren?“ – „Damit ich dich besser hören kann.“ So geht es weiter mit Augen, Händen und schließlich dem Maul: „Damit ich dich besser fressen kann!“ In diesem Moment springt der Wolf auf und verschlingt auch Rotkäppchen.

Zum Glück hört ein Jäger, der gerade durch den Wald streift, das laute Schnarchen des Wolfs. Er betritt das Haus, erkennt die Situation und schneidet dem Wolf den Bauch auf. Großmutter und Rotkäppchen kommen unversehrt wieder heraus. Um sicherzugehen, dass der Wolf keine weiteren Untaten begeht, füllen sie seinen Bauch mit schweren Steinen. Als der Wolf aufwacht und fliehen will, stürzt er unter dem Gewicht der Steine tot zu Boden.

Die Geschichte endet mit der Lehre, dass man auf die Worte der Eltern hören, nicht vom rechten Weg abkommen und keine Gespräche mit Fremden führen sollte. In späteren Versionen geht Rotkäppchen ein zweites Mal zur Großmutter, trifft wieder einen Wolf, bleibt diesmal aber wachsam und wird nicht getäuscht – ein Hinweis auf die moralische Entwicklung der Figur.

Wichtige Motive und Symbole:

Der Wald steht für das Unbekannte, Gefährliche, aber auch für eine Art Prüfungsraum des Erwachsenwerdens.

Der Wolf symbolisiert Gefahr, Verführung und Täuschung – oft interpretiert als Warnung vor fremden Männern.

Rotkäppchens Kappe gilt als Symbol für kindliche Unschuld, aber auch als Markenzeichen für ihre Rolle im Märchen.

Der Jäger verkörpert Ordnung, Sicherheit und Wiederherstellung der Gerechtigkeit.

Strukturell folgt die Geschichte einer klassischen Märchenform mit Einleitung, moralischer Prüfung, Konflikt, Rettung und Lehre.



Example JSON object string format (Output MUST follow this structure):

{"storySegment": "Du folgst dem schmalen Pfad tiefer in den Wald. Die Bäume stehen hier dichter und das Sonnenlicht dringt kaum durch das Blätterdach. Plötzlich hörst du ein Knacken im Unterholz rechts von dir.","choices": ["Nachsehen, was das Geräusch verursacht hat.", "Den Schritt beschleunigen und weitergehen.", "Leise deinen Korb abstellen und dich verstecken."]};
`

export async function POST(request) {
  try {
    // 1. Parse the incoming request body (now expects history and action object)
    const { history: clientHistoryStrings, action } = await request.json();

    // Basic input validation
    if (!Array.isArray(clientHistoryStrings) || typeof action !== 'object' || action === null) {
      return NextResponse.json({ message: 'Invalid request body: requires "history" (array of strings) and "action" (object).' }, { status: 400 });
    }

    // Determine if it's a choice or custom input
    let lastUserActionText = '';
    if (action.choice && typeof action.choice === 'string') {
        lastUserActionText = `My choice: ${action.choice}`;
    } else if (action.customInput && typeof action.customInput === 'string') {
        // Optional: Basic sanitization/truncation of custom input here if needed, though frontend limits it
        const safeCustomInput = action.customInput.substring(0, MAX_CUSTOM_INPUT_LENGTH); // Ensure limit
        lastUserActionText = `My custom action: ${safeCustomInput}`;
    } else {
         return NextResponse.json({ message: 'Invalid action object: requires "choice" or "customInput" string property.' }, { status: 400 });
    }


    // 2. Construct the message history for the OpenAI API format
    const messages = [{ role: 'system', content: systemPrompt }];

    // Convert simple string history back to roles (assuming alternating assistant/user)
    // Note: This simple alternation might break if history format changes
    clientHistoryStrings.forEach((text) => {
        // Determine role based on the *source* of the text (from history type)
        // This requires the frontend to send history *items* not just strings, or infer based on prefix
        // --- Let's assume the prefixes we added are reliable ---
        if (text.startsWith('> (Custom)')) {
             messages.push({ role: 'user', content: `My custom action: ${text.substring('> (Custom) '.length)}` });
        } else if (text.startsWith('> ')) { // A standard choice made previously
             messages.push({ role: 'user', content: `My choice: ${text.substring('> '.length)}` });
        } else if (text.startsWith('Starting prompt:')) {
            // Maybe don't include the starting prompt text in history? Or add as assistant? Let's skip for now.
        }
        else { // Assume it's story text from the assistant
            messages.push({ role: 'assistant', content: text });
        }
    });

    // Add the user's *current* action (already formatted with prefix) as the latest user message
    messages.push({ role: 'user', content: lastUserActionText });
    console.log(messages)

    // 3. Prepare the request body for LM Studio (OpenAI format)
    const openAIRequestBody = {
      model: LMSTUDIO_MODEL_NAME,
      messages: messages,
      temperature: 0.87, // Might increase slightly for creativity with custom input
      max_tokens: 131000,  // May need slightly more tokens if incorporating custom input
      //response_format: { type: "json_schema" }
    };

    // 4. Call the LM Studio API Endpoint (same as before)
    console.log(`Sending request to LM Studio: ${LMSTUDIO_API_URL}`);
    const response = await fetch(LMSTUDIO_API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          // Add Authorization header if your LM Studio server requires an API key
          // 'Authorization': `Bearer YOUR_API_KEY`
        },
        body: JSON.stringify(openAIRequestBody),
      });
console.log(response)
    // 5. Handle the response from LM Studio (same as before)
    if (!response.ok) {
        const errorBody = await response.text(); // Get text for more informative error
        console.error(`LM Studio API Error (${response.status}): ${errorBody}`);
        throw new Error(`LM Studio API request failed with status ${response.status}: ${errorBody.substring(0, 200)}`);
      }

    const data = await response.json();
    console.log("Received response from LM Studio.");

    // 6. Extract, Sanitize and Parse the JSON content
    if (!data.choices?.[0]?.message?.content) { throw new Error('LM Studio response missing content.'); }
    const jsonContent = data.choices[0].message.content.endsWith('}') ? data.choices[0].message.content : data.choices[0].message.content.endsWith(';') ? data.choices[0].message.content : data.choices[0].message.content+"}";
    console.log("Raw LLM content:", jsonContent); // Log raw content

    const parsedResponse = sanitizeLlmJsonResponse(jsonContent); // Use the sanitizer

    if (parsedResponse === null) {
        throw new Error(`Failed to sanitize or parse the JSON response from LLM.`);
    }

    // 7. Validate structure (basic check done in sanitizer, can add more)
     if (!parsedResponse.storySegment || !Array.isArray(parsedResponse.choices)) {
        console.error("Sanitized response missing required keys:", parsedResponse);
        throw new Error("LLM response structure invalid even after sanitization.");
     }

    // 8. Return the successful response to the client
    return NextResponse.json(parsedResponse, { status: 200 });

  } catch (error) {
    // 9. Handle errors gracefully (same as before)
    console.error('Error in /api/generate-openai route:', error);
    return NextResponse.json(
      { message: error.message || 'Failed to generate story segment via LM Studio.', error: error.toString() },
      { status: 500 } // Internal Server Error
    );
  }
}