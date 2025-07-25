// frontend/src/components/Message.js
import React from 'react';
import './Message.css';
import ReactMarkdown from 'react-markdown'; // NEW
import remarkGfm from 'remark-gfm';       // NEW

function Message({ sender, text }) {
  const messageClass = sender === 'user' ? 'user-message' : 'agent-message';

  return (
    <div className={`message-bubble ${messageClass}`}>
      {/* Conditionally render Markdown for agent messages, plain text for user messages */}
      {sender === 'agent' ? (
        <ReactMarkdown
          remarkPlugins={[remarkGfm]} // Use remark-gfm for tables, strikethrough, etc.
          components={{
            a: ({node, ...props}) => <a {...props} target="_blank" rel="noopener noreferrer" style={{ wordBreak: 'break-all' }} />,
          }}
        >
          {text}
        </ReactMarkdown>
      ) : (
        <div className="message-text">{text}</div> // User messages remain plain text (or you can apply Markdown too)
      )}
    </div>
  );
}

export default Message;