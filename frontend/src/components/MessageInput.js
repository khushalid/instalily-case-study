// frontend/src/components/MessageInput.js
import React, { useState } from 'react';

function MessageInput({ onSendMessage }) { // onSendMessage prop will be a function to call the API
  const [message, setMessage] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault(); // Prevent default form submission behavior (page reload)
    if (message.trim()) {
      onSendMessage(message); // Call the function passed from parent
      setMessage(''); // Clear input
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        placeholder="Type your message..."
      />
      <button type="submit">Send</button>
    </form>
  );
}

export default MessageInput;