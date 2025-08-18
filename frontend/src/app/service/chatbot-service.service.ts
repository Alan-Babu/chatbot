import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
@Injectable({
  providedIn: 'root'
})
export class ChatbotServiceService {

  constructor(private http: HttpClient) { }
  baseUrl = 'http://localhost:3000/api';

 /* sendMessage(message: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/chat`, { "query": message, "k": 3 });
  }*/

  async sendMessage(message: string, onChunk: (chunk: string) => void) {
    const response = await fetch(`${this.baseUrl}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: message, k: 3 })
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
        onChunk(chunk); // ✅ callback to update UI
      }
    }
  }

  getMenuOptions(): Observable<string[]> {
    return this.http.get<string[]>(`${this.baseUrl}/menu`);
  }

}
