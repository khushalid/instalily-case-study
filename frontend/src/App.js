// frontend/src/App.js

import React, { useState, useEffect, useRef } from 'react'; // Added useRef
import MessageInput from './components/MessageInput';
import MessageList from './components/MessageList';
import './App.css';

function App() {
  // messages now holds the entire conversation history
  const [messages, setMessages] = useState([
    {
      sender: 'agent',
      text: "Hi there! I'm PartSelect's chat agent. I can help you with Refrigerator and Dishwasher parts. How can I assist you today?",
      id: Date.now() // Initial greeting from the agent
    }
  ]);
  const [isTyping, setIsTyping] = useState(false); // New state for typing indicator
  const messageListRef = useRef(null); // Ref for scrolling to bottom

  // Scroll to bottom whenever messages update
  useEffect(() => {
    if (messageListRef.current) {
      messageListRef.current.scrollTop = messageListRef.current.scrollHeight;
    }
  }, [messages]);


  const handleSendMessage = async (text) => {
    const newUserMessage = { sender: 'user', text: text, id: Date.now() };
    // Add user message to state immediately
    setMessages((prevMessages) => [...prevMessages, newUserMessage]);
    setIsTyping(true); // Show typing indicator

    try {
      const conversationHistory = messages.map(msg => ({
        role: msg.sender === 'user' ? 'user' : 'assistant',
        content: msg.text // Only send content for now, backend will handle tool_calls
      }));

      // Append the new user message to the history we're sending
      conversationHistory.push({ role: 'user', content: text });

      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        // Send the entire conversation history to the backend
        body: JSON.stringify({ messages: conversationHistory }), // Changed from 'message' to 'messages'
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      const agentResponseText = data.response;

      // Add agent's response to state
      setMessages((prevMessages) => [
        ...prevMessages,
        { sender: 'agent', text: agentResponseText, id: Date.now() + 1 }
      ]);

    } catch (error) {
      console.error('Error sending message to backend:', error);
      setMessages((prevMessages) => [
        ...prevMessages,
        { sender: 'agent', text: 'Oops! Something went wrong. Please try again.', id: Date.now() + 2, error: true }
      ]);
    } finally {
      setIsTyping(false); // Hide typing indicator
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>PartSelect Chat Agent</h1>
      </header>
      <div className="chat-container">
        {/* Pass ref to MessageList for scrolling */}
        <MessageList messages={messages} ref={messageListRef} />
        {isTyping && <div className="typing-indicator">Agent is typing...</div>} {/* Typing indicator */}
        <MessageInput onSendMessage={handleSendMessage} />
      </div>
    </div>
  );
}

export default App;