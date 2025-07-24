// frontend/src/components/MessageList.js
import React, { forwardRef } from 'react'; // Import forwardRef
import Message from './Message';

// Use forwardRef to allow parent to pass a ref to this component's DOM element
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