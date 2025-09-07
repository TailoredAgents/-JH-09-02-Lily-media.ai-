import React, { useEffect } from 'react'
import FocusTrap from 'focus-trap-react'
import { XMarkIcon } from '@heroicons/react/24/outline'

/**
 * WCAG 2.1 AA Compliant Modal Component with Focus Trap
 *
 * Features:
 * - Focus trap keeps keyboard navigation within modal
 * - Escape key closes modal (WCAG 2.1.2 No Keyboard Trap)
 * - Focus returns to trigger element on close
 * - ARIA attributes for screen readers
 * - Background scrolling prevention
 * - High contrast focus indicators (3:1 contrast ratio minimum)
 *
 * @param {Object} props
 * @param {boolean} props.isOpen - Whether modal is open
 * @param {function} props.onClose - Function to close modal
 * @param {string} props.title - Modal title for accessibility
 * @param {React.ReactNode} props.children - Modal content
 * @param {string} props.size - Modal size: 'sm', 'md', 'lg', 'xl'
 * @param {boolean} props.showCloseButton - Whether to show X close button (default: true)
 * @param {function} props.onAfterOpen - Callback after modal opens
 * @param {function} props.onBeforeClose - Callback before modal closes
 * @param {string} props.className - Additional classes for modal content
 * @param {string} props.overlayClassName - Additional classes for overlay
 * @param {boolean} props.closeOnOverlayClick - Whether clicking overlay closes modal (default: true)
 */
export default function FocusTrappedModal({
  isOpen,
  onClose,
  title,
  children,
  size = 'md',
  showCloseButton = true,
  onAfterOpen,
  onBeforeClose,
  className = '',
  overlayClassName = '',
  closeOnOverlayClick = true,
}) {
  // Size classes for responsive modal sizing
  const sizeClasses = {
    sm: 'max-w-sm',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
  }

  // Handle escape key press (WCAG 2.1.2 compliance)
  useEffect(() => {
    const handleEscapeKey = (event) => {
      if (event.key === 'Escape' && isOpen) {
        if (onBeforeClose) {
          onBeforeClose()
        }
        onClose()
      }
    }

    if (isOpen) {
      document.addEventListener('keydown', handleEscapeKey)
      // Prevent background scrolling when modal is open
      document.body.style.overflow = 'hidden'

      if (onAfterOpen) {
        onAfterOpen()
      }
    } else {
      document.body.style.overflow = 'unset'
    }

    return () => {
      document.removeEventListener('keydown', handleEscapeKey)
      document.body.style.overflow = 'unset'
    }
  }, [isOpen, onClose, onAfterOpen, onBeforeClose])

  // Handle overlay click
  const handleOverlayClick = (event) => {
    if (event.target === event.currentTarget && closeOnOverlayClick) {
      if (onBeforeClose) {
        onBeforeClose()
      }
      onClose()
    }
  }

  // Handle close button click
  const handleCloseClick = () => {
    if (onBeforeClose) {
      onBeforeClose()
    }
    onClose()
  }

  if (!isOpen) return null

  return (
    <div
      className={`fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 ${overlayClassName}`}
      onClick={handleOverlayClick}
      aria-labelledby={title ? 'modal-title' : undefined}
      aria-modal="true"
      role="dialog"
    >
      <FocusTrap
        focusTrapOptions={{
          initialFocus: false, // Let the modal content determine initial focus
          allowOutsideClick: true,
          clickOutsideDeactivates: closeOnOverlayClick,
          escapeDeactivates: true,
          returnFocusOnDeactivate: true,
        }}
      >
        <div
          className={`
            bg-white dark:bg-gray-800 
            rounded-lg shadow-xl 
            ${sizeClasses[size]} 
            w-full 
            max-h-[90vh] 
            overflow-hidden
            focus:outline-none 
            focus:ring-4 
            focus:ring-blue-500 
            focus:ring-opacity-50
            ${className}
          `}
          tabIndex={-1}
        >
          {/* Header with title and close button */}
          {(title || showCloseButton) && (
            <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
              {title && (
                <h2
                  id="modal-title"
                  className="text-lg font-semibold text-gray-900 dark:text-white"
                >
                  {title}
                </h2>
              )}

              {showCloseButton && (
                <button
                  type="button"
                  onClick={handleCloseClick}
                  className="
                    text-gray-400 hover:text-gray-500 dark:text-gray-300 dark:hover:text-gray-400
                    transition-colors duration-200
                    focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
                    dark:focus:ring-offset-gray-800
                    p-2 -m-2 rounded-md
                  "
                  aria-label={`Close ${title || 'modal'}`}
                >
                  <XMarkIcon className="h-5 w-5" aria-hidden="true" />
                </button>
              )}
            </div>
          )}

          {/* Modal content with scroll */}
          <div className="overflow-y-auto max-h-[calc(90vh-120px)]">
            {children}
          </div>
        </div>
      </FocusTrap>
    </div>
  )
}

/**
 * Hook for managing modal state with accessibility features
 *
 * @param {boolean} initialOpen - Initial open state
 * @returns {Object} Modal state and controls
 */
export function useModal(initialOpen = false) {
  const [isOpen, setIsOpen] = React.useState(initialOpen)
  const [triggerElement, setTriggerElement] = React.useState(null)

  const open = React.useCallback((trigger) => {
    if (trigger && trigger.current) {
      setTriggerElement(trigger.current)
    }
    setIsOpen(true)
  }, [])

  const close = React.useCallback(() => {
    setIsOpen(false)
    // Return focus to trigger element after modal closes
    if (triggerElement) {
      setTimeout(() => {
        triggerElement.focus()
      }, 100)
    }
  }, [triggerElement])

  return {
    isOpen,
    open,
    close,
    toggle: () => (isOpen ? close() : open()),
  }
}
