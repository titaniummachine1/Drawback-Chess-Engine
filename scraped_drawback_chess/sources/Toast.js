import React from 'react';
import './Toast.css';

const Toast = ({ message, onClose, style, isError=true }) => {
  return (
    <div className={isError ? "error-toast" : "happy-toast"} style={style}>
      <div className="error-toast-content">
        <span className="error-toast-message">{message}</span>
        <button className="error-toast-close" onClick={onClose}>
          &times;
        </button>
      </div>
    </div>
  );
};

export default Toast;
