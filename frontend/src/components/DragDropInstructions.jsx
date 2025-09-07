import React, { useState } from 'react'
import {
  InformationCircleIcon,
  ComputerDesktopIcon,
  CursorArrowRaysIcon,
  ChevronDownIcon,
  ChevronUpIcon,
} from '@heroicons/react/24/outline'

const DragDropInstructions = ({
  type = 'calendar', // 'calendar', 'list', 'general'
  compact = false,
}) => {
  const [isExpanded, setIsExpanded] = useState(false)

  const getInstructions = () => {
    switch (type) {
      case 'calendar':
        return {
          mouse: [
            'Click and drag posts between calendar dates',
            'Drop posts onto different dates to reschedule',
            'Visual feedback shows valid drop zones',
            'Drag multiple selected posts at once',
          ],
          keyboard: [
            'Tab to navigate between posts and calendar dates',
            'Space or Enter to select a post for moving',
            'Arrow keys to navigate between calendar dates',
            'Space or Enter on a date to move the selected post',
            'Escape to cancel the current move operation',
          ],
        }
      case 'list':
        return {
          mouse: [
            'Click and drag items to reorder',
            'Drop items in the desired position',
            'Visual indicators show drop zones',
          ],
          keyboard: [
            'Tab to navigate between list items',
            'Space or Enter to select an item',
            'Arrow keys to choose new position',
            'Space or Enter to confirm placement',
            'Escape to cancel reordering',
          ],
        }
      default:
        return {
          mouse: [
            'Click and drag items to move them',
            'Drop items in valid drop zones',
            'Visual feedback guides your actions',
          ],
          keyboard: [
            'Tab to navigate between items',
            'Space or Enter to select/move items',
            'Arrow keys for navigation',
            'Escape to cancel operations',
          ],
        }
    }
  }

  const instructions = getInstructions()

  if (compact) {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-md p-3 mb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <ComputerDesktopIcon className="h-4 w-4 text-blue-600" />
            <span className="text-sm font-medium text-blue-900">
              Keyboard Navigation Available
            </span>
          </div>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-blue-600 hover:text-blue-500"
            aria-expanded={isExpanded}
            aria-label="Toggle keyboard instructions"
          >
            {isExpanded ? (
              <ChevronUpIcon className="h-4 w-4" />
            ) : (
              <ChevronDownIcon className="h-4 w-4" />
            )}
          </button>
        </div>

        {isExpanded && (
          <div className="mt-3 pt-3 border-t border-blue-200">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div>
                <h4 className="font-semibold text-blue-900 mb-2 flex items-center">
                  <CursorArrowRaysIcon className="h-3 w-3 mr-1" />
                  Mouse/Touch
                </h4>
                <ul className="space-y-1 text-blue-800">
                  {instructions.mouse.map((instruction, index) => (
                    <li key={index}>• {instruction}</li>
                  ))}
                </ul>
              </div>
              <div>
                <h4 className="font-semibold text-blue-900 mb-2 flex items-center">
                  <ComputerDesktopIcon className="h-3 w-3 mr-1" />
                  Keyboard
                </h4>
                <ul className="space-y-1 text-blue-800">
                  {instructions.keyboard.map((instruction, index) => (
                    <li key={index}>• {instruction}</li>
                  ))}
                </ul>
              </div>
            </div>
            <div className="mt-3 pt-2 border-t border-blue-200">
              <p className="text-xs text-blue-700">
                <strong>Screen Reader:</strong> Actions and status changes are
                announced automatically.
              </p>
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div
      className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6"
      role="region"
      aria-labelledby="drag-drop-instructions"
    >
      <div className="flex items-start space-x-3">
        <InformationCircleIcon className="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <h3
            id="drag-drop-instructions"
            className="text-sm font-semibold text-blue-900 mb-3"
          >
            How to Move Items
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Mouse/Touch Instructions */}
            <div>
              <h4 className="text-sm font-medium text-blue-900 mb-2 flex items-center">
                <CursorArrowRaysIcon className="h-4 w-4 mr-2" />
                Mouse & Touch
              </h4>
              <ul className="space-y-2 text-sm text-blue-800">
                {instructions.mouse.map((instruction, index) => (
                  <li key={index} className="flex items-start">
                    <span className="inline-block w-1.5 h-1.5 bg-blue-400 rounded-full mt-2 mr-3 flex-shrink-0" />
                    {instruction}
                  </li>
                ))}
              </ul>
            </div>

            {/* Keyboard Instructions */}
            <div>
              <h4 className="text-sm font-medium text-blue-900 mb-2 flex items-center">
                <ComputerDesktopIcon className="h-4 w-4 mr-2" />
                Keyboard Navigation
              </h4>
              <ul className="space-y-2 text-sm text-blue-800">
                {instructions.keyboard.map((instruction, index) => (
                  <li key={index} className="flex items-start">
                    <span className="inline-block w-1.5 h-1.5 bg-blue-400 rounded-full mt-2 mr-3 flex-shrink-0" />
                    {instruction}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Common keyboard shortcuts */}
          <div className="mt-4 pt-4 border-t border-blue-200">
            <h4 className="text-sm font-medium text-blue-900 mb-2">
              Key Shortcuts
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
              <div className="flex items-center space-x-1">
                <kbd className="px-1.5 py-0.5 bg-white rounded border text-gray-700 font-mono">
                  Tab
                </kbd>
                <span className="text-blue-800">Navigate</span>
              </div>
              <div className="flex items-center space-x-1">
                <kbd className="px-1.5 py-0.5 bg-white rounded border text-gray-700 font-mono">
                  Space
                </kbd>
                <span className="text-blue-800">Select/Move</span>
              </div>
              <div className="flex items-center space-x-1">
                <kbd className="px-1.5 py-0.5 bg-white rounded border text-gray-700 font-mono">
                  ↑↓←→
                </kbd>
                <span className="text-blue-800">Navigate</span>
              </div>
              <div className="flex items-center space-x-1">
                <kbd className="px-1.5 py-0.5 bg-white rounded border text-gray-700 font-mono">
                  Esc
                </kbd>
                <span className="text-blue-800">Cancel</span>
              </div>
            </div>
          </div>

          {/* Screen reader note */}
          <div className="mt-3 p-2 bg-blue-100 rounded text-xs text-blue-800">
            <strong>For screen reader users:</strong> All drag and drop actions
            are announced with audio feedback. Status updates and instructions
            are provided as you navigate.
          </div>
        </div>
      </div>
    </div>
  )
}

export default DragDropInstructions
