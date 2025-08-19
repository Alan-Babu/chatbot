import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
@Injectable({
  providedIn: 'root'
})
export class ChatbotServiceService {

  constructor(private http: HttpClient) { }
  baseUrl = (window as any)?.__CHATBOT_API__ ?? 'http://localhost:3000/api';

 /* sendMessage(message: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/chat`, { "query": message, "k": 3 });
  }*/

  async sendMessage(
    message: string,
    onChunk: (chunk: string) => void,
    onError?: (errorMsg: string) => void
  ) {
    try {
      const response = await fetch(`${this.baseUrl}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: message, k: 3, session_id: this.getOrCreateSessionId() })
      });

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No stream reader');

      const decoder = new TextDecoder();
      let done = false;

      while (!done) {
        const { value, done: isDone } = await reader.read();
        done = isDone;
        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          if (chunk.toLowerCase().includes("error")) {
            if (onError) {
              onError("something went wrong, please try again later");
            } else {
              onChunk(`something went wrong, please try again later`);
            }
            break;
          }
          onChunk(chunk); // ✅ callback to update UI
        }
      }
    } catch (error: any) {
      const errorMsg = error?.message || 'Unknown error occurred';
      if (onError) {
        onError(errorMsg);
      } else {
        onChunk(`Error: ${errorMsg}`);
      }
    }
  }

  getSuggestions(latestBotText: string): Observable<{ suggestions: string[] }> {
    return this.http.post<{ suggestions: string[] }>(`${this.baseUrl}/suggestions`, { text: latestBotText });
  }

  
  sendMessageFeedback(messageId: number, feedback: 'up' | 'down'): Observable<any> {
    return this.http.post(`${this.baseUrl}/feedback/message`, { messageId, feedback });
  }

  sendSessionFeedback(rating: number): Observable<any> {
    return this.http.post(`${this.baseUrl}/feedback/session`, { rating });
  }

  getMenuOptions(): Observable<string[]> {
    return this.http.get<string[]>(`${this.baseUrl}/menu`);
  }

  private getOrCreateSessionId(): string {
    const key = 'chatbot_session_id';
    let id = localStorage.getItem(key);
    if (!id) {
      id = Math.random().toString(36).slice(2) + Date.now().toString(36);
      localStorage.setItem(key, id);
    }
    return id;
  }

}
