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

  constructor(private chatbotService: ChatbotServiceService) {}

  ngOnInit() {
      this.chatbotService.getMenuOptions().subscribe({
        next: (items) => this.menuItems = items,
        error: (err) => console.error("Menu fetch error:", err)
      });
      console.log("Chatbot component initialized");
      console.log("Menu items:", this.menuItems);
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

  onMenuClick(item: string) {
    this.newMessage = item;
    this.sendMessage();
  }

  useSuggestion(s: string) {
    this.newMessage = s;
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
}


type SenderRole = 'user' | 'bot';
interface ChatMessage {
  id: number;
  text: string;
  sender: SenderRole;
  timestamp: Date;
  isComplete?: boolean;
}
