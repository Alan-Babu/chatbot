import { Component, OnInit, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ChatbotServiceService } from '../service/chatbot-service.service';

@Component({
  selector: 'app-chatbot',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './chatbot.component.html',
  styleUrl: './chatbot.component.scss'
})
export class ChatbotComponent implements OnInit, AfterViewChecked {

  @ViewChild('messagesContainer') private messagesContainer!: ElementRef;

  messages: any[] = [
    {
      id: 1,
      text: 'Hello! I\'m your AI assistant. How can I help you today?',
      sender: 'bot',
      timestamp: new Date()
    }
  ];
  menuItems: string[] = [];

  newMessage = '';
  isTyping = false;

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
    if (this.newMessage.trim()) {
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

      // Create bot message placeholder
      let botMessage = { 
        id: this.messages.length + 1, 
        text: '', 
        sender: 'bot', 
        timestamp: new Date() 
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

      this.isTyping = false;
    }
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

  getMessageClass(message: any): string {
    return message.sender === 'user'
      ? 'bg-blue-600 text-white ml-auto'
      : 'bg-gray-100 text-gray-900';
  }

  getMessageAlignment(message: any): string {
    return message.sender === 'user' ? 'justify-end' : 'justify-start';
  }
}
