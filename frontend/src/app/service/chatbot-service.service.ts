import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
@Injectable({
  providedIn: 'root'
})
export class ChatbotServiceService {

  constructor(private http: HttpClient) { }
  baseUrl = 'http://localhost:3000/api';

  sendMessage(message: string): Observable<any> {
    return this.http.post(`${this.baseUrl}/chat`, { "query": message, "k": 3 });
  }
}
