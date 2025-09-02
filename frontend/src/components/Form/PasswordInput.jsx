import React, { useState } from "react";

export default function PasswordInput({
  value,
  onChange,
  name = "password",
  id = "password",
  placeholder = "Password",
  disabled = false,
  autoComplete = "current-password",
  className = "appearance-none rounded-none relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-b-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
}) {
  const [show, setShow] = useState(false);
  
  return (
    <div className="relative">
      <input
        id={id}
        name={name}
        type={show ? "text" : "password"}
        autoComplete={autoComplete}
        required
        className={className}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        disabled={disabled}
        aria-label={placeholder}
      />
      <button
        type="button"
        className="absolute inset-y-0 right-0 pr-3 flex items-center"
        onClick={() => setShow((s) => !s)}
        disabled={disabled}
        aria-label={show ? "Hide password" : "Show password"}
      >
        {show ? (
          <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 013.23-4.568M6.228 6.228A9.956 9.956 0 0112 5c4.477 0 8.268 2.943 9.543 7a9.97 9.97 0 01-1.249 2.592M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        ) : (
          <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M3 3l18 18M9.878 9.878L3 3m6.878 6.878L21 21M4.457 4.457A10.05 10.05 0 0012 5c4.477 0 8.268 2.943 9.543 7a9.97 9.97 0 01-1.249 2.592M6.228 6.228A9.956 9.956 0 003 12c1.275 4.057 5.066 7 9.543 7 1.312 0 2.568-.252 3.72-.711" />
          </svg>
        )}
      </button>
    </div>
  );
}