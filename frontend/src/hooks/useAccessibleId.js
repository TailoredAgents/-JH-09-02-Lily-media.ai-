import { useId } from 'react'

/**
 * P1-10c: WCAG 2.1 AA Accessible ID Hook
 * 
 * Provides unique, stable IDs for form controls, labels, and ARIA relationships
 * Implements WCAG 2.1 requirements:
 * - 1.3.1 Info and Relationships: Proper labeling relationships
 * - 4.1.2 Name, Role, Value: Accessible names through proper ID associations
 * 
 * European Accessibility Act 2025 compliant per EN 301 549 standards
 */

/**
 * Generate unique, accessible IDs for form controls and ARIA attributes
 * @param {string} prefix - Optional prefix for the ID
 * @returns {object} Object containing various ID combinations for accessibility
 */
export const useAccessibleId = (prefix = '') => {
  const id = useId()
  const baseId = prefix ? `${prefix}-${id}` : id.replace(/:/g, '-')
  
  return {
    // Base ID for the main element
    id: baseId,
    
    // Form control relationships
    labelId: `${baseId}-label`,
    descriptionId: `${baseId}-description`,
    errorId: `${baseId}-error`,
    helpTextId: `${baseId}-help`,
    
    // ARIA relationships
    describedBy: `${baseId}-description`,
    labelledBy: `${baseId}-label`,
    
    // Modal and dialog IDs
    modalId: `${baseId}-modal`,
    modalTitleId: `${baseId}-modal-title`,
    modalDescId: `${baseId}-modal-description`,
    
    // List and option IDs
    listId: `${baseId}-list`,
    optionId: (index) => `${baseId}-option-${index}`,
    
    // Tab panel IDs
    tabId: (index) => `${baseId}-tab-${index}`,
    panelId: (index) => `${baseId}-panel-${index}`,
    
    // Generate related ID with suffix
    relatedId: (suffix) => `${baseId}-${suffix}`,
    
    // Group IDs for related controls
    groupId: `${baseId}-group`,
    fieldsetId: `${baseId}-fieldset`,
    legendId: `${baseId}-legend`
  }
}

/**
 * Hook for managing ARIA describedby attribute with multiple descriptions
 * @param {Array<string>} descriptionIds - Array of description element IDs
 * @returns {string|undefined} Space-separated string of IDs or undefined if empty
 */
export const useAriaDescribedBy = (descriptionIds = []) => {
  const validIds = descriptionIds.filter(Boolean)
  return validIds.length > 0 ? validIds.join(' ') : undefined
}

/**
 * Hook for managing ARIA labelledby attribute with multiple labels
 * @param {Array<string>} labelIds - Array of label element IDs
 * @returns {string|undefined} Space-separated string of IDs or undefined if empty
 */
export const useAriaLabelledBy = (labelIds = []) => {
  const validIds = labelIds.filter(Boolean)
  return validIds.length > 0 ? validIds.join(' ') : undefined
}

export default useAccessibleId