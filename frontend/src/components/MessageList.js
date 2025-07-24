// frontend/src/components/MessageList.js
import React, { forwardRef } from 'react';
import Message from './Message';

const MessageList = forwardRef(({ messages }, ref) => {
  return (
    <div className="message-list" ref={ref}> {/* Assign ref here */}
      {messages.map((msg) => (
        <Message key={msg.id} sender={msg.sender} text={msg.text} />
      ))}
    </div>
  );
});

export default MessageList;