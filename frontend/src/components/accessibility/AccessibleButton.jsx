import React, { forwardRef } from 'react'
import { useAccessibleId } from '../../hooks/useAccessibleId'
import ScreenReaderOnly from './ScreenReaderOnly'

/**
 * P1-10c: WCAG 2.1 AA Compliant Button Component
 * 
 * Provides fully accessible button with proper labeling, states, and interactions
 * Implements WCAG 2.1 requirements:
 * - 2.1.1 Keyboard accessible
 * - 2.4.7 Focus Visible
 * - 3.2.2 On Input (predictable changes)
 * - 4.1.2 Name, Role, Value
 * 
 * European Accessibility Act 2025 compliant per EN 301 549 standards
 */
const AccessibleButton = forwardRef(({
  // Content
  children,
  
  // Button behavior
  onClick,
  onKeyDown,
  type = 'button',
  disabled = false,
  loading = false,
  
  // Accessibility
  ariaLabel,
  ariaDescribedBy,
  ariaPressed, // for toggle buttons
  ariaExpanded, // for disclosure buttons
  ariaControls, // for buttons that control other elements
  
  // Visual variants
  variant = 'primary', // primary, secondary, danger, ghost, outline
  size = 'medium', // small, medium, large
  
  // Icons and loading
  icon: Icon,
  iconPosition = 'left', // left, right, only
  loadingText = 'Loading...',
  
  // Custom styling
  className = '',
  id,
  
  // Other props
  ...rest
}, ref) => {
  const ids = useAccessibleId(id)
  
  // Build accessibility attributes
  const ariaAttributes = {
    'aria-label': ariaLabel,
    'aria-describedby': ariaDescribedBy,
    'aria-pressed': ariaPressed,
    'aria-expanded': ariaExpanded,
    'aria-controls': ariaControls,
    'aria-disabled': disabled || loading,
  }
  
  // Remove undefined values from aria attributes
  Object.keys(ariaAttributes).forEach(key => {
    if (ariaAttributes[key] === undefined) {
      delete ariaAttributes[key]
    }
  })
  
  // Enhanced keyboard handling
  const handleKeyDown = (event) => {
    // Space and Enter should trigger onClick for button elements
    if (event.key === ' ' || event.key === 'Enter') {
      if (!disabled && !loading) {
        event.preventDefault()
        onClick?.(event)
      }
    }
    
    // Call custom keydown handler
    onKeyDown?.(event)
  }
  
  // Handle click with loading and disabled states
  const handleClick = (event) => {
    if (disabled || loading) {
      event.preventDefault()
      return
    }
    onClick?.(event)
  }
  
  // Base button classes with accessibility focus indicators
  const getButtonClasses = () => {
    const baseClasses = `
      inline-flex items-center justify-center font-medium rounded-md
      transition-all duration-200 ease-in-out
      focus:outline-none focus:ring-2 focus:ring-offset-2
      disabled:cursor-not-allowed disabled:opacity-50
    `
    
    // Size classes
    const sizeClasses = {
      small: 'px-3 py-1.5 text-sm gap-1.5',
      medium: 'px-4 py-2 text-sm gap-2',
      large: 'px-6 py-3 text-base gap-2.5'
    }
    
    // Variant classes
    const variantClasses = {
      primary: `
        bg-blue-600 text-white border border-transparent
        hover:bg-blue-700 active:bg-blue-800
        focus:ring-blue-500
        disabled:bg-blue-300
      `,
      secondary: `
        bg-gray-200 text-gray-900 border border-gray-300
        hover:bg-gray-300 active:bg-gray-400
        focus:ring-gray-500
        dark:bg-gray-600 dark:text-gray-100 dark:border-gray-500
        dark:hover:bg-gray-500 dark:active:bg-gray-400
      `,
      danger: `
        bg-red-600 text-white border border-transparent
        hover:bg-red-700 active:bg-red-800
        focus:ring-red-500
        disabled:bg-red-300
      `,
      ghost: `
        bg-transparent text-gray-700 border border-transparent
        hover:bg-gray-100 active:bg-gray-200
        focus:ring-gray-500
        dark:text-gray-300 dark:hover:bg-gray-700 dark:active:bg-gray-600
      `,
      outline: `
        bg-transparent text-blue-600 border border-blue-600
        hover:bg-blue-50 active:bg-blue-100
        focus:ring-blue-500
        dark:text-blue-400 dark:border-blue-400
        dark:hover:bg-blue-900/20 dark:active:bg-blue-900/40
      `
    }
    
    return `
      ${baseClasses}
      ${sizeClasses[size] || sizeClasses.medium}
      ${variantClasses[variant] || variantClasses.primary}
      ${loading ? 'cursor-wait' : ''}
      ${className}
    `.replace(/\s+/g, ' ').trim()
  }
  
  // Render loading spinner
  const LoadingSpinner = () => (
    <div 
      className="animate-spin rounded-full h-4 w-4 border-2 border-current border-t-transparent"
      aria-hidden="true"
    />
  )
  
  // Render button content based on state and icon position
  const renderContent = () => {
    if (loading) {
      return (
        <>
          <LoadingSpinner />
          <span>{loadingText}</span>
          <ScreenReaderOnly>Loading, please wait</ScreenReaderOnly>
        </>
      )
    }
    
    if (iconPosition === 'only' && Icon) {
      return (
        <>
          <Icon className="h-4 w-4" aria-hidden="true" />
          {ariaLabel && <ScreenReaderOnly>{ariaLabel}</ScreenReaderOnly>}
        </>
      )
    }
    
    return (
      <>
        {Icon && iconPosition === 'left' && (
          <Icon className="h-4 w-4" aria-hidden="true" />
        )}
        {children && <span>{children}</span>}
        {Icon && iconPosition === 'right' && (
          <Icon className="h-4 w-4" aria-hidden="true" />
        )}
      </>
    )
  }
  
  return (
    <button
      ref={ref}
      id={ids.id}
      type={type}
      disabled={disabled || loading}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      className={getButtonClasses()}
      {...ariaAttributes}
      {...rest}
    >
      {renderContent()}
    </button>
  )
})

AccessibleButton.displayName = 'AccessibleButton'

export default AccessibleButton

/**
 * Specialized accessible button variants for common use cases
 */

// Toggle Button with aria-pressed support
export const ToggleButton = forwardRef(({ pressed, onToggle, children, ...props }, ref) => {
  return (
    <AccessibleButton
      ref={ref}
      ariaPressed={pressed}
      onClick={() => onToggle(!pressed)}
      {...props}
    >
      {children}
    </AccessibleButton>
  )
})

// Disclosure Button for expanding/collapsing content
export const DisclosureButton = forwardRef(({ expanded, onToggle, controls, children, ...props }, ref) => {
  return (
    <AccessibleButton
      ref={ref}
      ariaExpanded={expanded}
      ariaControls={controls}
      onClick={() => onToggle(!expanded)}
      {...props}
    >
      {children}
    </AccessibleButton>
  )
})

// Icon-only button with required accessible name
export const IconButton = forwardRef(({ ariaLabel, icon: Icon, ...props }, ref) => {
  if (!ariaLabel) {
    console.warn('IconButton requires ariaLabel for accessibility')
  }
  
  return (
    <AccessibleButton
      ref={ref}
      ariaLabel={ariaLabel}
      icon={Icon}
      iconPosition="only"
      {...props}
    />
  )
})