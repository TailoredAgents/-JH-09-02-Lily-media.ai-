import React, { forwardRef } from 'react'
import { ExclamationCircleIcon, InformationCircleIcon } from '@heroicons/react/24/outline'
import { useAccessibleId, useAriaDescribedBy } from '../../hooks/useAccessibleId'
import ScreenReaderOnly from './ScreenReaderOnly'

/**
 * P1-10c: WCAG 2.1 AA Compliant Form Field Component
 * 
 * Provides fully accessible form inputs with proper labeling, error handling,
 * and ARIA attributes. Implements WCAG 2.1 requirements:
 * - 1.3.1 Info and Relationships: Proper form labeling
 * - 3.3.1 Error Identification: Clear error messages
 * - 3.3.2 Labels or Instructions: Descriptive labels and help text
 * - 4.1.2 Name, Role, Value: Proper accessible names
 * 
 * European Accessibility Act 2025 compliant per EN 301 549 standards
 */
const AccessibleFormField = forwardRef(({
  // Field identification
  label,
  id,
  name,
  type = 'text',
  
  // Field state
  value,
  onChange,
  onBlur,
  onFocus,
  
  // Validation
  error,
  required = false,
  
  // Help and description
  helpText,
  description,
  
  // Field properties
  placeholder,
  disabled = false,
  readOnly = false,
  autoComplete,
  maxLength,
  minLength,
  min,
  max,
  step,
  pattern,
  
  // Accessibility
  ariaLabel,
  ariaDescribedBy: customAriaDescribedBy,
  
  // Styling
  className = '',
  inputClassName = '',
  labelClassName = '',
  errorClassName = '',
  helpClassName = '',
  
  // Special field types
  as: Component = 'input',
  rows, // for textarea
  options, // for select
  children, // for select options or custom content
  
  ...rest
}, ref) => {
  const ids = useAccessibleId(id || name)
  
  // Build aria-describedby with all relevant descriptions
  const descriptionIds = [
    description && ids.descriptionId,
    helpText && ids.helpTextId,
    error && ids.errorId,
    customAriaDescribedBy
  ]
  const ariaDescribedBy = useAriaDescribedBy(descriptionIds)
  
  // Determine field status for styling and ARIA
  const hasError = Boolean(error)
  const isInvalid = hasError
  
  // Base input classes with accessibility focus indicators
  const baseInputClasses = `
    block w-full px-3 py-2 border rounded-md shadow-sm
    focus:outline-none focus:ring-2 focus:ring-offset-2
    disabled:opacity-50 disabled:cursor-not-allowed
    read-only:bg-gray-50 read-only:text-gray-500
    ${hasError 
      ? 'border-red-300 focus:border-red-500 focus:ring-red-500 text-red-900 placeholder-red-300' 
      : 'border-gray-300 focus:border-blue-500 focus:ring-blue-500'
    }
    ${inputClassName}
  `.trim().replace(/\s+/g, ' ')
  
  // Render the appropriate input component
  const renderInput = () => {
    const commonProps = {
      ref,
      id: ids.id,
      name: name || ids.id,
      value,
      onChange,
      onBlur,
      onFocus,
      disabled,
      readOnly,
      required,
      'aria-invalid': isInvalid,
      'aria-describedby': ariaDescribedBy,
      'aria-label': ariaLabel,
      className: baseInputClasses,
      ...rest
    }
    
    if (Component === 'textarea') {
      return (
        <textarea
          {...commonProps}
          rows={rows || 4}
          placeholder={placeholder}
          maxLength={maxLength}
          minLength={minLength}
        />
      )
    }
    
    if (Component === 'select') {
      return (
        <select {...commonProps}>
          {placeholder && (
            <option value="" disabled>
              {placeholder}
            </option>
          )}
          {options?.map((option, index) => (
            <option 
              key={option.value || index} 
              value={option.value}
              disabled={option.disabled}
            >
              {option.label}
            </option>
          ))}
          {children}
        </select>
      )
    }
    
    // Default input element
    return (
      <input
        {...commonProps}
        type={type}
        placeholder={placeholder}
        autoComplete={autoComplete}
        maxLength={maxLength}
        minLength={minLength}
        min={min}
        max={max}
        step={step}
        pattern={pattern}
      />
    )
  }
  
  return (
    <div className={`space-y-1 ${className}`}>
      {/* Field Label */}
      {label && (
        <label 
          htmlFor={ids.id}
          id={ids.labelId}
          className={`block text-sm font-medium text-gray-700 dark:text-gray-300 ${labelClassName}`}
        >
          {label}
          {required && (
            <>
              <span className="text-red-500 ml-1" aria-hidden="true">*</span>
              <ScreenReaderOnly>required</ScreenReaderOnly>
            </>
          )}
        </label>
      )}
      
      {/* Field Description */}
      {description && (
        <div 
          id={ids.descriptionId}
          className="text-sm text-gray-600 dark:text-gray-400"
        >
          {description}
        </div>
      )}
      
      {/* Input Field */}
      <div className="relative">
        {renderInput()}
        
        {/* Error Icon */}
        {hasError && (
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
            <ExclamationCircleIcon 
              className="h-5 w-5 text-red-500" 
              aria-hidden="true"
            />
          </div>
        )}
      </div>
      
      {/* Help Text */}
      {helpText && !hasError && (
        <div 
          id={ids.helpTextId}
          className={`flex items-start space-x-2 text-sm text-gray-600 dark:text-gray-400 ${helpClassName}`}
        >
          <InformationCircleIcon className="h-4 w-4 mt-0.5 flex-shrink-0" aria-hidden="true" />
          <span>{helpText}</span>
        </div>
      )}
      
      {/* Error Message */}
      {error && (
        <div 
          id={ids.errorId}
          className={`flex items-start space-x-2 text-sm text-red-600 dark:text-red-400 ${errorClassName}`}
          role="alert"
          aria-live="polite"
        >
          <ExclamationCircleIcon className="h-4 w-4 mt-0.5 flex-shrink-0" aria-hidden="true" />
          <span>{error}</span>
        </div>
      )}
      
      {/* Screen reader instructions for complex fields */}
      {(type === 'password' || pattern) && (
        <ScreenReaderOnly>
          {type === 'password' && 'Password field. Your input will not be displayed on screen.'}
          {pattern && `Input must match the pattern: ${pattern}`}
        </ScreenReaderOnly>
      )}
    </div>
  )
})

AccessibleFormField.displayName = 'AccessibleFormField'

export default AccessibleFormField