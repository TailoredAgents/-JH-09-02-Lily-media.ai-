import React from 'react'

/**
 * P1-10c: WCAG 2.1 AA Screen Reader Only Content Component
 * 
 * Provides content that is only visible to screen readers and other assistive technologies
 * while remaining visually hidden. Implements WCAG 2.1 requirements:
 * - 1.1.1 Non-text Content: Provides text alternatives
 * - 1.3.1 Info and Relationships: Programmatically available information
 * - 4.1.2 Name, Role, Value: Provides accessible names and descriptions
 * 
 * European Accessibility Act 2025 compliant per EN 301 549 standards
 */
const ScreenReaderOnly = ({ 
  children, 
  as: Component = 'span',
  className = '',
  focusable = false,
  ...props 
}) => {
  // WCAG 2.1 compliant visually hidden styles
  // These styles ensure content is available to screen readers but not visually displayed
  const visuallyHiddenStyles = {
    position: 'absolute',
    width: '1px',
    height: '1px',
    padding: '0',
    margin: '-1px',
    overflow: 'hidden',
    clip: 'rect(0, 0, 0, 0)',
    whiteSpace: 'nowrap',
    border: '0'
  }

  // If focusable, modify styles to show when focused (for skip links, etc.)
  const focusableStyles = focusable ? {
    ...visuallyHiddenStyles,
    ':focus': {
      position: 'static',
      width: 'auto',
      height: 'auto',
      padding: '8px',
      margin: '0',
      overflow: 'visible',
      clip: 'auto',
      whiteSpace: 'normal',
      border: '2px solid #0066cc',
      backgroundColor: '#ffffff',
      color: '#000000',
      zIndex: 9999
    }
  } : visuallyHiddenStyles

  return (
    <Component
      className={`sr-only ${className}`}
      style={focusableStyles}
      aria-hidden={false}
      {...props}
    >
      {children}
    </Component>
  )
}

/**
 * Skip Link Component for keyboard navigation
 * WCAG 2.4.1 Bypass Blocks - provides a way to skip repetitive content
 */
export const SkipLink = ({ href, children, className = '' }) => {
  return (
    <ScreenReaderOnly
      as="a"
      href={href}
      focusable={true}
      className={`skip-link ${className}`}
      style={{
        position: 'absolute',
        left: '-9999px',
        zIndex: 9999,
        padding: '8px 16px',
        backgroundColor: '#000000',
        color: '#ffffff',
        textDecoration: 'none',
        borderRadius: '4px',
        fontSize: '14px',
        fontWeight: 'bold'
      }}
      onFocus={(e) => {
        e.target.style.left = '6px'
        e.target.style.top = '6px'
      }}
      onBlur={(e) => {
        e.target.style.left = '-9999px'
      }}
    >
      {children}
    </ScreenReaderOnly>
  )
}

/**
 * Live Region Component for dynamic content announcements
 * WCAG 4.1.3 Status Messages - announces important changes to users
 */
export const LiveRegion = ({ 
  children, 
  level = 'polite', 
  atomic = false,
  relevant = 'additions text',
  className = ''
}) => {
  return (
    <div
      className={`live-region ${className}`}
      aria-live={level}
      aria-atomic={atomic}
      aria-relevant={relevant}
      style={{
        position: 'absolute',
        left: '-9999px',
        width: '1px',
        height: '1px',
        overflow: 'hidden'
      }}
    >
      {children}
    </div>
  )
}

export default ScreenReaderOnly