/**
 * SSE Stream Utilities for Agent Analysis
 * Handle Server-Sent Events streaming responses
 */

export interface StreamChunk {
  type: 'analysis' | 'thinking_start' | 'thinking' | 'thinking_end' | 'chunk' | 'complete' | 'status';
  content?: string;
  one_liner?: string;
  detailed?: string;
  status?: string;
  data?: any; // For analysis data (Annual Summary, Progress Tracker widgets)
}

export interface StreamCallbacks {
  onThinkingStart?: () => void;
  onThinking?: (content: string) => void;
  onThinkingEnd?: () => void;
  onChunk?: (content: string) => void;
  onComplete?: (oneLiner: string, detailed: string) => void;
  onStatus?: (status: string) => void;
  onError?: (error: string) => void;
  onAnalysis?: (data: any) => void; // For analysis data widgets
}

/**
 * Handle SSE Stream responses
 * @param url - API endpoint URL
 * @param body - Request body (JSON)
 * @param callbacks - Stream event callback functions
 * @param abortController - Optional AbortController to cancel the request
 */
export async function handleSSEStream(
  url: string,
  body: any,
  callbacks: StreamCallbacks,
  abortController?: AbortController
): Promise<void> {
  let timeoutId: NodeJS.Timeout | null = null;
  let reader: ReadableStreamDefaultReader<Uint8Array> | null = null;

  try {
    console.log('[SSE] Starting stream request:', url);

    // Create timeout Promise (600 seconds = 10 minutes, for long-running agents like Annual Summary)
    // Annual Summary can take up to 3-5 minutes with Sonnet model
    const timeoutPromise = new Promise<never>((_, reject) => {
      timeoutId = setTimeout(() => {
        reject(new Error('Stream timeout after 600 seconds'));
      }, 600000);
    });

    // Create fetch Promise
    const fetchPromise = (async () => {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
        signal: abortController?.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      if (!response.body) {
        throw new Error('Response body is null');
      }

      reader = response.body.getReader();
      const decoder = new TextDecoder();

      let buffer = '';
      let detailedContent = '';
      let thinkingContent = '';
      let chunkCount = 0;

      while (true) {
        const { done, value } = await reader.read();

        if (done) {
          console.log('[SSE] Stream ended, total chunks:', chunkCount);
          // Stream ended without receiving complete, use accumulated content
          if (detailedContent) {
            console.warn('[SSE] Stream ended without complete message, using accumulated content');
            callbacks.onComplete?.('Analysis Complete', detailedContent);
          }
          break;
        }

        // Decode chunk and add to buffer
        buffer += decoder.decode(value, { stream: true });

        // Process complete lines
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          if (!line.trim() || !line.startsWith('data: ')) continue;

          try {
            const jsonStr = line.slice(6); // Remove 'data: ' prefix
            const chunk: StreamChunk = JSON.parse(jsonStr);
            chunkCount++;

            if (chunkCount <= 3 || chunk.type === 'complete') {
              console.log(`[SSE] Chunk ${chunkCount}:`, chunk.type, chunk.content?.slice(0, 50));
            }

            // Handle different message types
            if (chunk.type === 'analysis') {
              // Analysis data for widgets (Annual Summary, Progress Tracker)
              console.log('[SSE] Received analysis data for widgets');
              callbacks.onAnalysis?.(chunk.data);
            } else if (chunk.type === 'thinking_start') {
              thinkingContent = '';
              callbacks.onThinkingStart?.();
            } else if (chunk.type === 'thinking') {
              thinkingContent += chunk.content || '';
              callbacks.onThinking?.(chunk.content || '');
            } else if (chunk.type === 'thinking_end') {
              callbacks.onThinkingEnd?.();
            } else if (chunk.type === 'chunk') {
              detailedContent += chunk.content || '';
              callbacks.onChunk?.(chunk.content || '');
            } else if (chunk.type === 'complete') {
              console.log('[SSE] Received complete message, one_liner length:', chunk.one_liner?.length, 'detailed length:', chunk.detailed?.length);
              callbacks.onComplete?.(
                chunk.one_liner || '',
                chunk.detailed || detailedContent
              );
              return; // Stream completed
            } else if (chunk.status) {
              console.log('[SSE] Status update:', chunk.status);
              callbacks.onStatus?.(chunk.status);
            } else if ('error' in chunk) {
              throw new Error((chunk as any).error);
            }
          } catch (parseError) {
            console.warn('[SSE] Failed to parse chunk:', line.slice(0, 100), parseError);
          }
        }
      }
    })();

    // Wait for fetch or timeout
    await Promise.race([fetchPromise, timeoutPromise]);

  } catch (error) {
    // Don't throw error if aborted
    if (abortController?.signal.aborted) {
      console.log('[SSE] Stream aborted');
      return;
    }
    const errorMessage = error instanceof Error ? error.message : 'Stream error';
    console.error('[SSE] Stream error:', error);
    callbacks.onError?.(errorMessage);
    throw error;
  } finally {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    // Clean up reader if aborted
    if (reader && abortController?.signal.aborted) {
      try {
        reader.cancel();
      } catch (e) {
        // Ignore cancel errors
      }
    }
  }
}

/**
 * Simplified version: Only get final result (no intermediate stream processing)
 * @param url - API endpoint URL
 * @param body - Request body (JSON)
 * @returns Promise with one_liner, detailed, and optional analysis data
 */
export async function fetchAgentStream(
  url: string,
  body: any,
  abortController?: AbortController
): Promise<{ one_liner: string; detailed: string; analysis?: any }> {
  return new Promise((resolve, reject) => {
    let oneLiner = '';
    let detailed = '';
    let analysisData: any = undefined;

    handleSSEStream(url, body, {
      onAnalysis: (data) => {
        analysisData = data;
        console.log('[fetchAgentStream] Stored analysis data for widgets');
      },
      onComplete: (liner, det) => {
        oneLiner = liner;
        detailed = det;
        resolve({ one_liner: oneLiner, detailed, analysis: analysisData });
      },
      onError: (error) => {
        reject(new Error(error));
      },
    }, abortController).catch(reject);
  });
}
