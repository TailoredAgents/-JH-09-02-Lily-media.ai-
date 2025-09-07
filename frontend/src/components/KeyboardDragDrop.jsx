import React, { useState, useCallback, useRef, useEffect } from 'react'
import {
  ArrowsRightLeftIcon,
  ArrowUpIcon,
  ArrowDownIcon,
  ArrowLeftIcon,
  ArrowRightIcon,
  InformationCircleIcon,
} from '@heroicons/react/24/outline'

/**
 * KeyboardDragDrop - Accessible keyboard alternative to drag-and-drop
 * Provides keyboard navigation and movement for drag-drop interfaces
 */
const KeyboardDragDrop = ({
  items,
  onMove,
  renderItem,
  dropZones = [],
  className = '',
  instructions = true,
  announceChanges = true,
}) => {
  const [selectedItem, setSelectedItem] = useState(null)
  const [selectedDropZone, setSelectedDropZone] = useState(null)
  const [keyboardMode, setKeyboardMode] = useState(false)
  const [announcement, setAnnouncement] = useState('')
  const itemRefs = useRef({})
  const dropZoneRefs = useRef({})

  // Announce changes to screen readers
  const announce = useCallback(
    (message) => {
      if (announceChanges) {
        setAnnouncement(message)
        setTimeout(() => setAnnouncement(''), 1000)
      }
    },
    [announceChanges]
  )

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (e, itemId, itemType = 'item') => {
      const isItem = itemType === 'item'
      const currentItems = isItem ? items : dropZones
      const currentIndex = currentItems.findIndex((item) =>
        isItem ? item.id === itemId : item.id === itemId
      )

      switch (e.key) {
        case 'Enter':
        case ' ':
          e.preventDefault()
          if (isItem) {
            if (selectedItem === itemId) {
              // Deselect item
              setSelectedItem(null)
              announce('Item deselected')
            } else {
              // Select item for moving
              setSelectedItem(itemId)
              setKeyboardMode(true)
              announce(
                `Item ${itemId} selected for moving. Use arrow keys to navigate to destination.`
              )
            }
          } else if (selectedItem && !isItem) {
            // Move item to drop zone
            onMove(selectedItem, itemId)
            setSelectedItem(null)
            setSelectedDropZone(null)
            setKeyboardMode(false)
            announce(`Item moved to ${itemId}`)
          }
          break

        case 'Escape':
          setSelectedItem(null)
          setSelectedDropZone(null)
          setKeyboardMode(false)
          announce('Move cancelled')
          break

        case 'ArrowDown':
          if (keyboardMode && selectedItem) {
            e.preventDefault()
            const nextIndex = Math.min(
              currentIndex + 1,
              currentItems.length - 1
            )
            const nextItem = currentItems[nextIndex]
            if (isItem) {
              itemRefs.current[nextItem.id]?.focus()
            } else {
              setSelectedDropZone(nextItem.id)
              dropZoneRefs.current[nextItem.id]?.focus()
            }
            announce(`Navigated to ${nextItem.id}`)
          }
          break

        case 'ArrowUp':
          if (keyboardMode && selectedItem) {
            e.preventDefault()
            const prevIndex = Math.max(currentIndex - 1, 0)
            const prevItem = currentItems[prevIndex]
            if (isItem) {
              itemRefs.current[prevItem.id]?.focus()
            } else {
              setSelectedDropZone(prevItem.id)
              dropZoneRefs.current[prevItem.id]?.focus()
            }
            announce(`Navigated to ${prevItem.id}`)
          }
          break

        case 'Tab':
          // Allow normal tab behavior but update announcements
          if (keyboardMode && selectedItem) {
            setTimeout(() => {
              if (document.activeElement) {
                const activeElement = document.activeElement
                const isDropZone = activeElement.dataset.dropzone
                if (isDropZone) {
                  setSelectedDropZone(activeElement.dataset.dropzoneId)
                  announce(
                    `Drop zone ${activeElement.dataset.dropzoneId} focused`
                  )
                }
              }
            }, 0)
          }
          break

        default:
          break
      }
    },
    [items, dropZones, selectedItem, keyboardMode, onMove, announce]
  )

  // Instructions component
  const KeyboardInstructions = () => (
    <div
      className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4"
      role="region"
      aria-label="Keyboard navigation instructions"
    >
      <div className="flex items-start space-x-3">
        <InformationCircleIcon className="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" />
        <div>
          <h4 className="text-sm font-semibold text-blue-900 mb-2">
            Keyboard Navigation
          </h4>
          <ul className="text-xs text-blue-800 space-y-1">
            <li>
              <kbd className="px-1.5 py-0.5 bg-white rounded border text-gray-700">
                Space
              </kbd>{' '}
              or{' '}
              <kbd className="px-1.5 py-0.5 bg-white rounded border text-gray-700">
                Enter
              </kbd>{' '}
              - Select/deselect item for moving
            </li>
            <li>
              <kbd className="px-1.5 py-0.5 bg-white rounded border text-gray-700">
                Tab
              </kbd>{' '}
              - Navigate between drop zones
            </li>
            <li>
              <kbd className="px-1.5 py-0.5 bg-white rounded border text-gray-700">
                ↑
              </kbd>
              <kbd className="px-1.5 py-0.5 bg-white rounded border text-gray-700">
                ↓
              </kbd>{' '}
              - Navigate within current area
            </li>
            <li>
              <kbd className="px-1.5 py-0.5 bg-white rounded border text-gray-700">
                Space
              </kbd>{' '}
              on drop zone - Move selected item here
            </li>
            <li>
              <kbd className="px-1.5 py-0.5 bg-white rounded border text-gray-700">
                Escape
              </kbd>{' '}
              - Cancel move operation
            </li>
          </ul>
        </div>
      </div>
    </div>
  )

  return (
    <div className={className}>
      {/* Screen reader announcements */}
      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {announcement}
      </div>

      {/* Keyboard instructions */}
      {instructions && <KeyboardInstructions />}

      {/* Status indicator */}
      {keyboardMode && selectedItem && (
        <div
          className="bg-yellow-100 border border-yellow-300 rounded-lg p-3 mb-4"
          role="status"
        >
          <div className="flex items-center space-x-2">
            <ArrowsRightLeftIcon className="h-4 w-4 text-yellow-600" />
            <span className="text-sm font-medium text-yellow-800">
              Moving item: {selectedItem}
            </span>
            <span className="text-xs text-yellow-600">
              Navigate to destination and press Space/Enter
            </span>
          </div>
        </div>
      )}

      {/* Render draggable items */}
      <div className="space-y-2">
        {items.map((item) => (
          <div
            key={item.id}
            ref={(el) => (itemRefs.current[item.id] = el)}
            tabIndex={0}
            role="button"
            aria-grabbed={selectedItem === item.id}
            aria-describedby={`item-${item.id}-instructions`}
            className={`
              focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-lg
              ${selectedItem === item.id ? 'ring-2 ring-blue-500 bg-blue-50' : ''}
              ${keyboardMode ? 'cursor-move' : 'cursor-pointer'}
            `}
            onKeyDown={(e) => handleKeyDown(e, item.id, 'item')}
            onClick={() => {
              if (selectedItem === item.id) {
                setSelectedItem(null)
                setKeyboardMode(false)
              } else {
                setSelectedItem(item.id)
                setKeyboardMode(true)
              }
            }}
          >
            {renderItem(item, selectedItem === item.id)}

            {/* Hidden instructions for screen readers */}
            <div id={`item-${item.id}-instructions`} className="sr-only">
              {selectedItem === item.id
                ? 'Selected for moving. Navigate to a drop zone and press Space or Enter to move here.'
                : 'Press Space or Enter to select this item for moving.'}
            </div>
          </div>
        ))}
      </div>

      {/* Render drop zones if provided */}
      {dropZones.length > 0 && (
        <div className="mt-6">
          <h3 className="text-sm font-semibold text-gray-900 mb-3">
            Drop Zones
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {dropZones.map((zone) => (
              <div
                key={zone.id}
                ref={(el) => (dropZoneRefs.current[zone.id] = el)}
                data-dropzone="true"
                data-dropzone-id={zone.id}
                tabIndex={keyboardMode && selectedItem ? 0 : -1}
                role="button"
                aria-label={`Drop zone: ${zone.name}`}
                aria-describedby={`dropzone-${zone.id}-instructions`}
                className={`
                  border-2 border-dashed rounded-lg p-4 min-h-24 transition-all
                  focus:outline-none focus:ring-2 focus:ring-blue-500
                  ${selectedDropZone === zone.id ? 'border-blue-500 bg-blue-50' : 'border-gray-300'}
                  ${selectedItem ? 'hover:border-blue-400 hover:bg-blue-50' : ''}
                  ${!keyboardMode || !selectedItem ? 'opacity-50' : 'opacity-100'}
                `}
                onKeyDown={(e) => handleKeyDown(e, zone.id, 'dropzone')}
                onClick={() => {
                  if (selectedItem && keyboardMode) {
                    onMove(selectedItem, zone.id)
                    setSelectedItem(null)
                    setSelectedDropZone(null)
                    setKeyboardMode(false)
                  }
                }}
              >
                <div className="text-center">
                  <div className="text-lg font-medium text-gray-900">
                    {zone.name}
                  </div>
                  {zone.description && (
                    <div className="text-sm text-gray-600 mt-1">
                      {zone.description}
                    </div>
                  )}
                  {selectedItem && keyboardMode && (
                    <div className="text-xs text-blue-600 mt-2">
                      Press Space/Enter to move here
                    </div>
                  )}
                </div>

                {/* Hidden instructions for screen readers */}
                <div
                  id={`dropzone-${zone.id}-instructions`}
                  className="sr-only"
                >
                  {selectedItem && keyboardMode
                    ? `Drop zone ${zone.name}. Press Space or Enter to move the selected item here.`
                    : `Drop zone ${zone.name}. Select an item first to move it here.`}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default KeyboardDragDrop
