import React, { useState, useCallback } from 'react'
import {
  ComputerDesktopIcon,
  CursorArrowRaysIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline'

/**
 * AccessibleDragDrop - Higher-order component that wraps drag-drop interfaces
 * to provide keyboard alternatives and accessibility enhancements
 */
const AccessibleDragDrop = ({
  children,
  keyboardAlternative,
  showToggle = true,
  defaultMode = 'mouse',
  instructions = true,
}) => {
  const [inputMode, setInputMode] = useState(defaultMode) // 'mouse' or 'keyboard'
  const [showInstructions, setShowInstructions] = useState(false)

  const toggleInputMode = useCallback(() => {
    setInputMode((prev) => (prev === 'mouse' ? 'keyboard' : 'mouse'))
  }, [])

  const InputModeToggle = () => (
    <div className="flex items-center space-x-4 mb-4 p-3 bg-gray-50 rounded-lg border">
      <span className="text-sm font-medium text-gray-700">Input Method:</span>

      <div className="flex bg-white rounded-md shadow-sm border">
        <button
          onClick={() => setInputMode('mouse')}
          className={`
            flex items-center space-x-2 px-3 py-2 text-sm font-medium rounded-l-md transition-colors
            ${
              inputMode === 'mouse'
                ? 'bg-blue-600 text-white'
                : 'text-gray-700 hover:text-gray-900 hover:bg-gray-50'
            }
          `}
          aria-pressed={inputMode === 'mouse'}
        >
          <CursorArrowRaysIcon className="h-4 w-4" />
          <span>Mouse/Touch</span>
        </button>

        <button
          onClick={() => setInputMode('keyboard')}
          className={`
            flex items-center space-x-2 px-3 py-2 text-sm font-medium rounded-r-md transition-colors border-l
            ${
              inputMode === 'keyboard'
                ? 'bg-blue-600 text-white'
                : 'text-gray-700 hover:text-gray-900 hover:bg-gray-50'
            }
          `}
          aria-pressed={inputMode === 'keyboard'}
        >
          <ComputerDesktopIcon className="h-4 w-4" />
          <span>Keyboard</span>
        </button>
      </div>

      {instructions && (
        <button
          onClick={() => setShowInstructions(!showInstructions)}
          className="flex items-center space-x-1 text-sm text-blue-600 hover:text-blue-500"
          aria-expanded={showInstructions}
        >
          <InformationCircleIcon className="h-4 w-4" />
          <span>Help</span>
        </button>
      )}
    </div>
  )

  const InstructionPanel = () =>
    showInstructions && (
      <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <h3 className="text-sm font-semibold text-blue-900 mb-3">
          How to Move Items
        </h3>

        {inputMode === 'mouse' ? (
          <div className="text-sm text-blue-800">
            <p className="mb-2">
              <strong>Mouse/Touch:</strong>
            </p>
            <ul className="list-disc list-inside space-y-1">
              <li>Click and drag items to move them</li>
              <li>Drop items in the desired location</li>
              <li>Visual feedback shows valid drop zones</li>
            </ul>
          </div>
        ) : (
          <div className="text-sm text-blue-800">
            <p className="mb-2">
              <strong>Keyboard Navigation:</strong>
            </p>
            <ul className="list-disc list-inside space-y-1">
              <li>
                <kbd className="px-1.5 py-0.5 bg-white rounded border text-gray-700 font-mono">
                  Tab
                </kbd>{' '}
                - Navigate between items and zones
              </li>
              <li>
                <kbd className="px-1.5 py-0.5 bg-white rounded border text-gray-700">
                  Space
                </kbd>
                /
                <kbd className="px-1.5 py-0.5 bg-white rounded border text-gray-700">
                  Enter
                </kbd>{' '}
                - Select/move items
              </li>
              <li>
                <kbd className="px-1.5 py-0.5 bg-white rounded border text-gray-700">
                  Arrow keys
                </kbd>{' '}
                - Navigate within sections
              </li>
              <li>
                <kbd className="px-1.5 py-0.5 bg-white rounded border text-gray-700">
                  Escape
                </kbd>{' '}
                - Cancel current operation
              </li>
            </ul>
            <p className="mt-2 text-xs">
              Screen readers will announce your actions and provide guidance.
            </p>
          </div>
        )}
      </div>
    )

  return (
    <div>
      {/* Toggle between input modes */}
      {showToggle && <InputModeToggle />}

      {/* Instructions panel */}
      <InstructionPanel />

      {/* Render appropriate interface based on mode */}
      <div role="region" aria-label={`${inputMode} drag and drop interface`}>
        {inputMode === 'keyboard' ? keyboardAlternative : children}
      </div>

      {/* Skip link for keyboard users when in mouse mode */}
      {inputMode === 'mouse' && (
        <div className="sr-only">
          <button
            onClick={() => setInputMode('keyboard')}
            className="focus:not-sr-only focus:absolute focus:top-0 focus:left-0 bg-blue-600 text-white px-4 py-2 z-50 rounded"
          >
            Switch to keyboard accessible mode
          </button>
        </div>
      )}

      {/* Hidden status for screen readers */}
      <div className="sr-only" aria-live="polite">
        {inputMode === 'keyboard'
          ? 'Keyboard navigation mode active. Use Tab, Space, and arrow keys to move items.'
          : 'Mouse/touch mode active. Click and drag to move items.'}
      </div>
    </div>
  )
}

export default AccessibleDragDrop
