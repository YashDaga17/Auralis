'use client';

import React, { useState, useRef, useEffect } from 'react';

interface VariableAutocompleteProps {
  value: string;
  onChange: (value: string) => void;
  availableVariables: string[];
  placeholder?: string;
  rows?: number;
}

export default function VariableAutocomplete({
  value,
  onChange,
  availableVariables,
  placeholder = '',
  rows = 3,
}: VariableAutocompleteProps) {
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [cursorPosition, setCursorPosition] = useState(0);
  const [filteredVariables, setFilteredVariables] = useState<string[]>([]);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const suggestionsRef = useRef<HTMLDivElement>(null);

  // Detect when user types {{ to show autocomplete
  useEffect(() => {
    const beforeCursor = value.substring(0, cursorPosition);
    const lastOpenBrace = beforeCursor.lastIndexOf('{{');
    const lastCloseBrace = beforeCursor.lastIndexOf('}}');

    // Check if we're inside {{ }}
    if (lastOpenBrace > lastCloseBrace && lastOpenBrace !== -1) {
      const searchTerm = beforeCursor.substring(lastOpenBrace + 2).toLowerCase();
      const filtered = availableVariables.filter((variable) =>
        variable.toLowerCase().includes(searchTerm)
      );
      setFilteredVariables(filtered);
      setShowSuggestions(filtered.length > 0);
    } else {
      setShowSuggestions(false);
    }
  }, [value, cursorPosition, availableVariables]);

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    onChange(e.target.value);
    setCursorPosition(e.target.selectionStart);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Update cursor position on arrow keys
    if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
      setTimeout(() => {
        setCursorPosition(textareaRef.current?.selectionStart || 0);
      }, 0);
    }
  };

  const handleClick = (e: React.MouseEvent<HTMLTextAreaElement>) => {
    setCursorPosition((e.target as HTMLTextAreaElement).selectionStart);
  };

  const insertVariable = (variable: string) => {
    const beforeCursor = value.substring(0, cursorPosition);
    const afterCursor = value.substring(cursorPosition);
    const lastOpenBrace = beforeCursor.lastIndexOf('{{');

    // Replace from {{ to cursor with the complete variable
    const newValue =
      beforeCursor.substring(0, lastOpenBrace) +
      `{{${variable}}}` +
      afterCursor;

    onChange(newValue);
    setShowSuggestions(false);

    // Set cursor after the inserted variable
    setTimeout(() => {
      const newPosition = lastOpenBrace + variable.length + 4; // {{ + variable + }}
      textareaRef.current?.setSelectionRange(newPosition, newPosition);
      textareaRef.current?.focus();
    }, 0);
  };

  return (
    <div className="relative">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        onClick={handleClick}
        placeholder={placeholder}
        rows={rows}
        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono text-sm"
      />

      {/* Autocomplete Suggestions */}
      {showSuggestions && (
        <div
          ref={suggestionsRef}
          className="absolute z-10 mt-1 w-full bg-white border border-gray-300 rounded-lg shadow-lg max-h-48 overflow-y-auto"
        >
          <div className="p-2">
            <p className="text-xs text-gray-500 mb-2">Available variables:</p>
            {filteredVariables.map((variable) => (
              <button
                key={variable}
                onClick={() => insertVariable(variable)}
                className="w-full text-left px-3 py-2 hover:bg-blue-50 rounded text-sm font-mono text-gray-800"
              >
                {`{{${variable}}}`}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="mt-1 text-xs text-gray-500">
        Type <code className="bg-gray-100 px-1 rounded">{'{{'}</code> to see available variables
      </div>
    </div>
  );
}
