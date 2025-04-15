import { NextResponse } from 'next/server';
import { Ollama } from 'ollama'; // Assuming you have the 'ollama' package installed

// Initialize Ollama client - Ensure Ollama server is running
// You might want to configure the host based on environment variables later
const ollama = new Ollama({ host: 'http://localhost:11434' });

// Your carefully crafted system prompt (same as before)
const systemPrompt = `You are an expert interactive storyteller AI. Your goal is to write engaging, coherent story segments based on user choices and maintain consistency in plot, characters, and tone.

**Your Task:**
1.  Read the provided Story History and the User's Last Choice.
2.  Write the *next* logical and creative segment of the story, directly continuing from the history and incorporating the user's choice naturally. Keep the segment concise, around 2-4 sentences.
3.  Maintain consistency with established characters, settings, tone (e.g., fantasy adventure, mystery), and plot points mentioned in the history. Remember key details.
4.  After writing the story segment, generate exactly THREE distinct, plausible, and engaging choices for the user to pick from to continue the story. Each choice should lead the story in a slightly different direction.
5.  Format your entire response ONLY as a JSON object with two keys: "storySegment" (string) and "choices" (array of strings).

**Example Response Format:**
{
  "storySegment": "Following the echoing howl, you cautiously push open the ancient stone door. Dust motes dance in the single beam of light illuminating a vast, silent chamber.",
  "choices": [
    "Light a torch and explore the chamber.",
    "Call out to see if anyone is there.",
    "Quietly retreat and find another way around."
  ]
}

**Constraint Checklist (Internal):**
*   Is the story segment a logical continuation? Yes/No
*   Does it incorporate the user's last choice? Yes/No
*   Is it consistent with history (characters, tone, plot)? Yes/No
*   Are there exactly 3 choices? Yes/No
*   Are the choices distinct and plausible? Yes/No
*   Is the output valid JSON with only 'storySegment' and 'choices' keys? Yes/No

Begin!`;

// Define the POST handler function for the '/api/generate' route
export async function POST(request) {
  try {
    // 1. Parse the request body
    // The 'request' object here is the standard Web API Request
    const { history, choice } = await request.json();

    // Basic input validation
    if (!Array.isArray(history) || typeof choice !== 'string') {
      return NextResponse.json(
        { message: 'Invalid request body: requires "history" (array) and "choice" (string).' },
        { status: 400 } // Bad Request
      );
    }

    // 2. Format the prompt for the LLM
    const historyString = history.join('\n'); // Combine history lines
    const userPrompt = `
**Story History So Far:**
${historyString}

**User's Last Choice:** ${choice}

**Your Turn (generate next segment and choices in JSON format):**
`;

    // 3. Call the local LLM API (Ollama)
    console.log("Sending request to Ollama..."); // Optional: Log for debugging
    console.log(systemPrompt)
    const response = await ollama.generate({
      model: 'deepseek-r1:7b', // Or your chosen model configured in Ollama
      system: systemPrompt,
      prompt: userPrompt,
      format: 'json', // Crucial: Instruct Ollama to ensure the output is JSON
      stream: false, // We want the full response at once for this structure
      keep_alive: "5m"
    });
    console.log("Received response from Ollama."); // Optional: Log

    // 4. Parse and validate the LLM's response
    let parsedResponse;
    console.log(response)
    try {
        // Ollama's generate (non-stream) puts the JSON string in response.response
        parsedResponse = JSON.parse(response.response);
    } catch (parseError) {
        console.error("Failed to parse LLM response JSON:", response.response);
        throw new Error(`LLM returned non-JSON response: ${response.response.substring(0, 100)}...`); // Provide snippet
    }
    console.log(parsedResponse)


    // Validate the structure of the parsed response
    if (!parsedResponse.storySegment || typeof parsedResponse.storySegment !== 'string' ||
        !Array.isArray(parsedResponse.choices) || parsedResponse.choices.length !== 3 ||
        !parsedResponse.choices.every(c => typeof c === 'string')) {
      console.error("Invalid response structure from LLM:", parsedResponse);
      throw new Error("LLM response has invalid structure (expected storySegment string and choices array of 3 strings).");
    }

    // 5. Return the successful response
    // Use NextResponse.json to automatically set Content-Type and stringify
    return NextResponse.json(parsedResponse, { status: 200 });

  } catch (error) {
    // 6. Handle errors gracefully
    console.error('Error in /api/generate route:', error);

    // Determine if it's an error from Ollama connection or processing
    let errorMessage = 'Failed to generate story segment.';
    if (error.message) {
        errorMessage = error.message;
    } else if (error.cause) {
        // Handle potential fetch errors if using raw fetch instead of ollama library
        errorMessage = `Connection error: ${error.cause}`;
    }

    return NextResponse.json(
      { message: errorMessage, error: error.toString() }, // Include more error detail if helpful for debugging
      { status: 500 } // Internal Server Error
    );
  }
}

// Optional: Add a GET handler for basic testing or info
export async function GET() {
  return NextResponse.json({ message: 'This is the generate story API endpoint. Use POST with { history, choice }.' });
}