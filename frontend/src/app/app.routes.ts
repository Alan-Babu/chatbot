import { Routes } from '@angular/router';

export const routes: Routes = [
    {path: '', redirectTo: '/chatbot', pathMatch: 'full'},
    {path: 'chatbot', loadComponent: () => import('./chatbot/chatbot.component').then(m => m.ChatbotComponent)},
];
