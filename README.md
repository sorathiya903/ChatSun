# 🌞 ChatSun

<div align="center">Modern Real-Time Messaging Platform

Fast • Beautiful • Real-Time

🌐 Live: https://chatsun.netlify.app

![Frontend](https://img.shields.io/badge/Frontend-Netlify-00C7B7?style=for-the-badge&logo=netlify&logoColor=white)
![Backend](https://img.shields.io/badge/Backend-FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Database](https://img.shields.io/badge/Database-MongoDB-47A248?style=for-the-badge&logo=mongodb&logoColor=white)
![WebSocket](https://img.shields.io/badge/WebSocket-Real--Time-blue?style=for-the-badge)
![License](https://img.shields.io/badge/License-Public-green?style=for-the-badge)

</div>

---

📑 Table of Contents

- Overview
- Features
- Tech Stack
- Architecture
- Deployment
- Local Development
- Roadmap
- Author

---

## 🚀 Overview

ChatSun is a modern real-time messaging platform designed for fast communication, smooth user experience, and beautiful UI.

Built with FastAPI, MongoDB Atlas, WebSockets, and a custom glassmorphism interface, ChatSun delivers instant messaging, group conversations, file sharing, live typing indicators, video calls, and much more.

Whether you're chatting with friends, collaborating in groups, or sharing media, ChatSun provides a seamless real-time experience directly in the browser.

---

## ✨ Features

💬 **Real-Time Messaging**

- Instant message delivery
- WebSocket-powered communication
- Live conversation updates
- Fast synchronization across devices

👤 **Private Chats**

- One-to-one conversations
- Real-time messaging
- Message history
- Unread tracking

👥 **Group Chats**

- Create groups
- Group conversations
- Shared messaging space
- Group profile support

📹 **Video Calling**

- Private video calls
- Real-time video communication
- Browser-based experience

📁 **File Sharing**

Send and receive:

- Images
- Videos
- Audio files
- PDFs
- Documents
- Other supported files

✏️ **Message Management**

- Edit messages
- Delete messages
- Real-time updates after edits

🔍 **User Search**

- Search by User ID
- Search by Phone Number
- Start conversations instantly

✍️ **Live Typing Indicator**

- Real-time typing detection
- Animated waveform effect
- Live activity feedback

🔔 **Smart Unread System**

- Per-user unread counts
- Live unread updates
- Mark chat as read
- Mark all chats as read

📧 **Email Verification**

- OTP verification
- Secure account activation
- Email confirmation flow

👤 **User Profiles**

- Profile pictures
- Custom names
- Account management

🎨 **Modern Interface**

- Glassmorphism design
- Dark mode experience
- Mobile responsive UI
- Smooth animations
- Modern dashboard

---

## 🏗️ Architecture

| Layer | Stack |
|--------|--------|
| Client Application | HTML, CSS, JavaScript |
| Design System | Tailwind CSS + Normal CSS |
| API Server | FastAPI |
| Authentication | JWT + Secure Session Cookies + Google Authentication|
| Database | MongoDB Atlas |
| Real-Time Engine | WebSockets |
| Password Hashing | Argon2 |
| Cloud Hosting | Render |
| CDN & Frontend Hosting | Netlify |

---

## 🏗 Architecture

Frontend (Netlify)

↓

FastAPI Backend (Render)

↓

MongoDB Atlas

↓

WebSockets for Real-Time Updates

---

## 🌐 Live Demo

Try ChatSun

https://chatsun.netlify.app

---



## 💻 Local Development

Clone the repository:

```
git clone https://github.com/sorathiya903/ChatSun.git
```

Enter project directory:

```
cd chatsun
```

Install backend build dependencies:

```
pip install -r requirements.txt
```

Run:

```
uvicorn main:app --reload
```

Open frontend:

index.html



---

## 📈 Project Goals

ChatSun aims to become a complete browser-based communication platform that combines:

- Real-time messaging
- Media sharing
- Group collaboration
- Video communication
- Modern user experience

without requiring users to install any software.

---

## 🐍 Why Python FastAPI?

ChatSun relies on **Python FastAPI** as its primary infrastructure and orchestration layer for several critical architectural reasons:

1. **Native Asynchronous WebSocket Handling:** Messaging apps require persistent, long-lived server connections. FastAPI is built natively on top of Starlette and ASGI, allowing it to handle thousands of concurrent WebSocket connections asynchronously (`async/def`) with minimal memory overhead.
2. **Blazing Fast Performance:** FastAPI matches the execution speeds of Node.js and Go. This ensures that typing indicators, reactions, and WebRTC signaling payloads travel between clients in under 5 milliseconds.
3. **Automated Pydantic Data Validation:** Managing unstructured JSON data coming out of MongoDB Atlas is simplified using Pydantic schemas. FastAPI validates user inputs, token payloads, and profile changes automatically at the API boundary, preventing runtime errors.
4. **Clean Concurrency for Background Tasks:** Sending OTP emails and updating dynamic global unread indicators are offloaded to background worker threads natively supported by FastAPI, keeping the main communication thread unblocked.


## 📊 Feature Matrix & Implementation

| Core Feature Category | Implementation Status & Architecture Badges |
| :--- | :--- |
| **Real-Time Engine** | ![WebSockets](https://img.shields.io/badge/WebSockets-Active-blue) ![Python](https://img.shields.io/badge/Python-Asyncio-blueviolet) |
| **Call Hardware Control** | ![Hardware](https://img.shields.io/badge/Accelerometer-Shake_to_End-red) ![WebRTC](https://img.shields.io/badge/WebRTC-Signaling-orange) |
| **Message States** | ![Status](https://img.shields.io/badge/Tracking-Sent_Delivered_Read-green) |
| **Advanced Messaging** | ![Actions](https://img.shields.io/badge/UI_Interactions-Swipe_Reply_Reactions-teal) |
| **Security & Auth** | ![JWT](https://img.shields.io/badge/Auth-JWT_Tokens-black) ![OAuth](https://img.shields.io/badge/OAuth-Google_Login-brightgreen) |
| **Media Operations** | ![Storage](https://img.shields.io/badge/File_Sharing-Images_Audio_PDFs-yellow) |


## 👨‍💻 Author

Aditya Sorathiya

GitHub: sorathiya903

> Building modern web applications with a focus on real-time experiences, UI design, and scalable systems.

---

<div align="center">🌞 Built with passion using FastAPI, MongoDB and WebSockets

ChatSun — Real-Time Conversations, Reimagined

</div>
