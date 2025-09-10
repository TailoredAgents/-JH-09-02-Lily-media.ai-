import React, { useEffect, useRef, useState } from 'react'

/**
 * P1-10c: WCAG 2.1 AA Compliant Focus Trap Component
 * 
 * Implements focus management for modals and dialogs per WCAG 2.1 requirements:
 * - 2.4.3 Focus Order: Logical focus sequence
 * - 2.4.7 Focus Visible: Clear focus indicators
 * - 2.1.2 No Keyboard Trap: Users can navigate out with keyboard
 * 
 * European Accessibility Act 2025 compliance through EN 301 549 standards
 */
const FocusTrap = ({ 
  children, 
  active = true, 
  restoreFocus = true,
  initialFocusRef = null,
  onEscape = () => {},
  className = "",
  role = "dialog",
  ariaLabel = "",
  ariaLabelledBy = "",
  ariaDescribedBy = ""
}) => {
  const trapRef = useRef(null)
  const previouslyFocusedElement = useRef(null)
  const [focusableElements, setFocusableElements] = useState([])

  // Define focusable element selectors per WCAG guidelines
  const focusableSelectors = [
    'a[href]',
    'button:not([disabled])',
    'input:not([disabled]):not([type="hidden"])',
    'textarea:not([disabled])',
    'select:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
    '[contenteditable="true"]',
    'audio[controls]',
    'video[controls]',
    'iframe',
    'embed',
    'object',
    'summary'
  ].join(', ')

  // Get all focusable elements within the trap
  const getFocusableElements = () => {
    if (!trapRef.current) return []
    
    const elements = trapRef.current.querySelectorAll(focusableSelectors)
    return Array.from(elements).filter(element => {
      // Additional checks for truly focusable elements
      const style = window.getComputedStyle(element)
      return (
        style.display !== 'none' &&
        style.visibility !== 'hidden' &&
        !element.hasAttribute('aria-hidden') &&
        element.tabIndex !== -1
      )
    })
  }

  // Handle keyboard navigation within focus trap
  const handleKeyDown = (event) => {
    if (!active) return

    const { key, shiftKey } = event
    const focusables = getFocusableElements()
    
    if (focusables.length === 0) return

    const firstFocusable = focusables[0]
    const lastFocusable = focusables[focusables.length - 1]
    const activeElement = document.activeElement

    // Handle Escape key - WCAG 2.1.2 No Keyboard Trap
    if (key === 'Escape') {
      event.preventDefault()
      onEscape()
      return
    }

    // Handle Tab navigation - WCAG 2.4.3 Focus Order
    if (key === 'Tab') {
      // If no element is focused within trap, focus first element
      if (!trapRef.current.contains(activeElement)) {
        event.preventDefault()
        firstFocusable.focus()
        return
      }

      // Shift+Tab on first element -> focus last element
      if (shiftKey && activeElement === firstFocusable) {
        event.preventDefault()
        lastFocusable.focus()
        return
      }

      // Tab on last element -> focus first element
      if (!shiftKey && activeElement === lastFocusable) {
        event.preventDefault()
        firstFocusable.focus()
        return
      }
    }

    // Handle arrow keys for enhanced navigation in certain contexts
    if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(key)) {
      const currentIndex = focusables.indexOf(activeElement)
      if (currentIndex === -1) return

      let nextIndex
      switch (key) {
        case 'ArrowUp':
        case 'ArrowLeft':
          nextIndex = currentIndex > 0 ? currentIndex - 1 : focusables.length - 1
          break
        case 'ArrowDown':
        case 'ArrowRight':
          nextIndex = currentIndex < focusables.length - 1 ? currentIndex + 1 : 0
          break
        default:
          return
      }

      // Only handle arrow navigation for certain element types
      const currentElement = focusables[currentIndex]
      const isListLike = currentElement.closest('[role="menu"], [role="listbox"], [role="tablist"], [role="radiogroup"]')
      
      if (isListLike) {
        event.preventDefault()
        focusables[nextIndex].focus()
      }
    }
  }

  useEffect(() => {
    if (!active) return

    // Store the previously focused element for restoration
    previouslyFocusedElement.current = document.activeElement

    // Get focusable elements and focus initial element
    const focusables = getFocusableElements()
    setFocusableElements(focusables)

    if (focusables.length > 0) {
      // Focus initial element (specified ref, first focusable, or trap container)
      const initialElement = initialFocusRef?.current || focusables[0] || trapRef.current
      
      // Small delay to ensure DOM is ready
      setTimeout(() => {
        if (initialElement) {
          initialElement.focus()
        }
      }, 0)
    }

    // Add keyboard event listeners
    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      
      // Restore focus to previously focused element - WCAG 2.4.3 Focus Order
      if (restoreFocus && previouslyFocusedElement.current) {
        previouslyFocusedElement.current.focus()
      }
    }
  }, [active, initialFocusRef])

  // Update focusable elements when children change
  useEffect(() => {
    if (active) {
      const focusables = getFocusableElements()
      setFocusableElements(focusables)
    }
  }, [children, active])

  if (!active) {
    return <>{children}</>
  }

  return (
    <div
      ref={trapRef}
      className={className}
      role={role}
      aria-label={ariaLabel || undefined}
      aria-labelledby={ariaLabelledBy || undefined}
      aria-describedby={ariaDescribedBy || undefined}
      aria-modal={role === "dialog" ? "true" : undefined}
      onKeyDown={handleKeyDown}
    >
      {children}
    </div>
  )
}

export default FocusTrap