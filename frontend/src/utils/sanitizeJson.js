/**
 * Attempts to sanitize a potentially malformed JSON string from an LLM
 * to match the expected { storySegment: string, choices: string[] } structure.
 * Includes an early exit if the input is already valid JSON meeting the criteria.
 * Handles missing quotes in choices, missing final brace, and markdown fences.
 *
 * @param {string | null | undefined} rawJsonString The raw string output from the LLM.
 * @returns {object | null} The parsed JSON object if successful, otherwise null.
 */
export default function sanitizeLlmJsonResponse(rawJsonString) {
    if (!rawJsonString || typeof rawJsonString !== 'string') {
      console.error("Sanitize Error: Input is not a valid string.");
      return null;
    }
  
    const trimmedInput = rawJsonString.trim();
  
    // --- Early Exit Check ---
    try {
      const parsedQuick = JSON.parse(trimmedInput);
  
      // Validate the structure of the initially parsed object
      if (
        typeof parsedQuick === 'object' &&
        parsedQuick !== null &&
        typeof parsedQuick.storySegment === 'string' &&
        Array.isArray(parsedQuick.choices) &&
        parsedQuick.choices.length === 3 && // Specifically check for 3 choices
        parsedQuick.choices.every(c => typeof c === 'string')
      ) {
        // If parsing and structure validation succeed, return immediately
        console.log("Sanitize Info: Input is valid JSON matching expected structure. Skipping full sanitization.");
        return parsedQuick;
      } else {
        // Parsed successfully, but didn't match the exact structure (e.g., wrong number of choices)
        // Proceed to full sanitization which might fix other issues,
        // but log that the initial structure wasn't perfect.
        console.warn("Sanitize Warning: Input parsed as JSON but did not match the required structure (e.g., number of choices). Proceeding with full sanitization.");
      }
    } catch (initialParseError) {
      // Initial parsing failed, definitely need sanitization.
      // Log the failure reason? Optional, might be noisy.
      console.log("Sanitize Info: Initial JSON parse failed, proceeding with full sanitization.",initialParseError);
    }
    // --- End Early Exit Check ---
  
  
    // If we reached here, the initial check failed or structure was wrong. Proceed with full sanitization.
    console.log("Sanitize Info: Running full sanitization logic.");
    let sanitized = trimmedInput; // Start full sanitization with the trimmed input
  
    // 1. Remove markdown fences (```json ... ``` or ``` ... ```)
    sanitized = sanitized.replace(/^```(?:json)?\s*/, '').replace(/\s*```$/, '').trim();
  
    // 2. Attempt to find the primary JSON structure boundaries
    const firstBrace = sanitized.indexOf('{');
    const lastBrace = sanitized.lastIndexOf('}');
  
    if (firstBrace === -1) {
      console.error("Sanitize Error (Full): No opening '{' found.");
      return null;
    }
  
    if (lastBrace === -1 || lastBrace < firstBrace) {
      if (sanitized.endsWith('"') || sanitized.endsWith(']')) {
        sanitized += '}';
        console.warn("Sanitize Warning (Full): Attempted to append missing closing '}'.");
      } else {
        console.warn("Sanitize Warning (Full): Closing '}' seems missing or misplaced.");
      }
    } else {
      // Extract content between outermost braces if they exist
       sanitized = sanitized.substring(firstBrace, lastBrace + 1);
    }
  
    // 3. Fix missing quotes within the "choices" array
    const choicesRegex = /"choices"\s*:\s*\[([^\]]*)\]/;
    const choicesMatch = sanitized.match(choicesRegex);
  
    if (choicesMatch && typeof choicesMatch[1] === 'string') {
      const originalChoicesBlock = choicesMatch[0];
      let choicesContent = choicesMatch[1].trim();
  
      if (choicesContent.endsWith(',')) {
        choicesContent = choicesContent.substring(0, choicesContent.length - 1).trim();
        console.warn("Sanitize Warning (Full): Removed trailing comma inside choices array.");
      }
  
      const items = choicesContent.split(',')
        .map(item => item.trim())
        .filter(item => item);
  
      const fixedItems = items.map(item => {
        if (item.startsWith('"') && item.endsWith('"')) return item;
        if (item.startsWith("'") && item.endsWith("'")) {
            const innerContent = item.substring(1, item.length - 1);
            return `"${innerContent.replace(/"/g, '\\"')}"`;
        }
         if (!isNaN(item) && item !== '') return item; // Keep numbers unquoted
        const escapedItem = item.replace(/"/g, '\\"');
        return `"${escapedItem}"`;
      });
  
      const fixedChoicesContent = fixedItems.join(', ');
      const fixedChoicesBlock = `"choices": [${fixedChoicesContent}]`;
      sanitized = sanitized.replace(originalChoicesBlock, fixedChoicesBlock);
    }
  
  
    // 4. Final check for braces (redundant? Maybe useful if regex altered structure)
    if (!(sanitized.startsWith('{') && sanitized.endsWith('}'))) {
         console.warn("Sanitize Warning (Full): Structure might still be missing braces after fixes.");
         // Maybe don't return null here, let the final parse attempt decide.
    }
  
    // 5. Attempt final parse
    try {
      const finalParsed = JSON.parse(sanitized);
  
      // 6. Final structure validation after sanitization
      // Note: Even if initial check passed parse but failed structure, we re-validate here.
      if (
        typeof finalParsed !== 'object' || finalParsed === null ||
        typeof finalParsed.storySegment !== 'string' ||
        !Array.isArray(finalParsed.choices) ||
        finalParsed.choices.length !== 3 || // Re-check length specifically
        !finalParsed.choices.every(c => typeof c === 'string')
      ) {
         console.warn("Sanitize Warning (Full): Parsed object structure is invalid AFTER sanitization. Required: {storySegment: string, choices: string[3]}");
         // Decide whether to return the partially valid object or null.
         // Returning null might be safer if the structure is critical downstream.
         return null;
      }
  
      return finalParsed; // Success after full sanitization!
  
    } catch (finalParseError) {
      console.error("Sanitize Error (Full): Failed to parse JSON even after sanitization.", finalParseError.message);
      console.error("Final sanitized string was:", sanitized);
      return null;
    }
  }
  