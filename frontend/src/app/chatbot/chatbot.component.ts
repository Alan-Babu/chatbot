import { Component, OnInit, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';
import { ChatbotServiceService } from '../service/chatbot-service.service';

@Component({
  selector: 'app-chatbot',
  standalone: true,
  imports: [CommonModule, FormsModule, HttpClientModule],
  templateUrl: './chatbot.component.html',
  styleUrl: './chatbot.component.scss'
})
export class ChatbotComponent implements OnInit, AfterViewChecked {

  @ViewChild('messagesContainer') private messagesContainer!: ElementRef;

  messages: ChatMessage[] = [
    {
      id: 1,
      text: 'Hello! I\'m your AI assistant. How can I help you today?',
      sender: 'bot',
      timestamp: new Date()
    }
  ];
  menuItems: string[] = [];
  suggestions: string[] = [];

  newMessage = '';
  isTyping = false;
  chatEnded = false;
  selectedRating = 0;
  feedbackSubmitted = false;
  showRatingPopup = false;
  sessionId = "";

  searchQuery = '';
  searchResults: any[] = [];
  autocompleteOptions: string[] = [];
  highlightedIndex: number = -1;


  constructor(private chatbotService: ChatbotServiceService) {}

  ngOnInit() {
      this.chatbotService.getMenuOptions().subscribe({
        next: (items) => this.menuItems = items,
        error: (err) => console.error("Menu fetch error:", err)
      });

      this.sessionId = this.chatbotService.getSessionId();

      this.chatbotService.getHistory(this.sessionId).subscribe({
      next: (history) => {
        if (history.length) {
          this.messages = history.map((m, idx) => ({
            id: idx + 1,
            text: m.content,
            sender: m.role === 'user' ? 'user' : 'bot',
            timestamp: new Date(m.timestamp),
            isComplete: true
          }));
        }
      },
      error: (err) => console.error("History fetch error:", err)
    });

  }

  ngAfterViewChecked() {
    this.scrollToBottom();
  }

  scrollToBottom(): void {
    try {
      this.messagesContainer.nativeElement.scrollTop =
        this.messagesContainer.nativeElement.scrollHeight;
    } catch (err) {}
  }

  async sendMessage() {
    if (this.newMessage.trim() && !this.chatEnded) {
      const userMessage = this.newMessage;
      this.newMessage = '';

      // Push user message
      this.messages.push({
        id: this.messages.length + 1,
        text: userMessage,
        sender: 'user',
        timestamp: new Date()
      });

      this.isTyping = true;

      // Create bot message placeholder with isComplete: false
      let botMessage: ChatMessage = { 
        id: this.messages.length + 1, 
        text: '', 
        sender: 'bot', 
        timestamp: new Date(),
        isComplete: false
      };
      this.messages.push(botMessage);

      // Stream response from backend
      await this.chatbotService.sendMessage(userMessage, (chunk: string) => {
        if(chunk.startsWith('Message ID:')) {
          const match = chunk.match(/Message ID: (\d+)/);
          if (match) {
            botMessage.id = parseInt(match[1], 10);
          }
          return;

        }
        if (chunk.trim()) {
          botMessage.text += chunk;
          // 🔥 Force UI refresh (Angular doesn’t detect += mutations well)
          this.messages = [...this.messages];
        }
      });

      // Mark message as complete after streaming
      botMessage.isComplete = true;
      this.messages = [...this.messages];

      this.isTyping = false;

      // Fetch suggestions for next steps based on the full bot message
      try {
        const latest = botMessage.text;
        this.chatbotService.getSuggestions(latest).subscribe({
          next: (res) => this.suggestions = res?.suggestions ?? [],
          error: () => this.suggestions = []
        });
      } catch {
        this.suggestions = [];
      }
    }
  }

  
  onInputChange() {
    const query = this.newMessage.trim().toLowerCase();
    if (!query) {
      this.autocompleteOptions = [];
      return;
    }

    // Option 1: filter locally from menuItems
    this.autocompleteOptions = this.menuItems.filter(item =>
      item.toLowerCase().includes(query)
    ).slice(0, 5);

    // Option 2 (better): call backend /suggestions
    this.chatbotService.getSuggestions(query).subscribe({
      next: (res) => {
        this.autocompleteOptions = res?.suggestions ?? [];
      },
      error: () => this.autocompleteOptions = []
    });
  }

  highlightSuggestion(direction: number) {
    if (!this.autocompleteOptions.length) return;
    this.highlightedIndex =
      (this.highlightedIndex + direction + this.autocompleteOptions.length) %
      this.autocompleteOptions.length;
  }

  useHighlightedSuggestion(event: Event) {
    if (this.highlightedIndex >= 0 && this.highlightedIndex < this.autocompleteOptions.length) {
      event.preventDefault();
      this.useSuggestion(this.autocompleteOptions[this.highlightedIndex]);
    }
  }

  useSuggestion(suggestion: string) {
    this.newMessage = suggestion;
    this.autocompleteOptions = [];
    this.highlightedIndex = -1;
    this.sendMessage();
  }


  onMenuClick(item: string) {
    this.newMessage = item;
    this.sendMessage();
  }


  addBotMessage(text: string) {
    this.messages.push({
      id: this.messages.length + 1,
      text: text,
      sender: 'bot',
      timestamp: new Date()
    });
  }

  getMessageClass(message: ChatMessage): string {
    return message.sender === 'user'
      ? 'bg-blue-600 text-white ml-auto'
      : 'bg-gray-100 text-gray-900';
  }

  giveFeedback(message: ChatMessage, feedback: 'up' | 'down') {
    this.chatbotService.sendMessageFeedback(message.id, feedback).subscribe({
      next: () => console.log(`Feedback saved for message ${message.id}`),
      error: (err) => console.error("Feedback error:", err)
    });
  }

  // End chat → star rating
  endChat() {
    this.showRatingPopup = true;
  }

  submitRating(rating: number) {
    this.selectedRating = rating;
    this.chatbotService.sendSessionFeedback(this.selectedRating).subscribe({
      next: () => {
        this.showRatingPopup = false;
        this.addBotMessage("🙏 Thank you for your feedback!");
        this.chatEnded = true; // Disable input and buttons
      },
      error: (err) => console.error("Session feedback error:", err)
    });
  }
  showMainMenu() {
    this.suggestions = [];  
  }


  getMessageAlignment(message: ChatMessage): string {
    return message.sender === 'user' ? 'justify-end' : 'justify-start';
  }

  resetChat() {
    this.messages = [
      {
        id: 1,
        text: 'Hello! I\'m your AI assistant. How can I help you today?',
        sender: 'bot',
        timestamp: new Date(),
        isComplete: true
      }
    ];
    this.newMessage = '';
    this.selectedRating = 0;
    this.feedbackSubmitted = false;
    this.showRatingPopup = false;
    this.chatEnded = false;
  }

  onSearch() {
    if (!this.searchQuery.trim()) return;
    this.chatbotService.search(this.searchQuery).subscribe({
      next: (results) => this.searchResults = results,
      error: (err) => {
        console.error("Search error:", err);
        this.searchResults = [];
      }
    });
  }
}


type SenderRole = 'user' | 'bot';
interface ChatMessage {
  id: number;
  text: string;
  sender: SenderRole;
  timestamp: Date;
  isComplete?: boolean;
}
