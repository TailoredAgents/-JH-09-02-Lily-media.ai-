// Accessibility utility functions for WCAG 2.1 AA compliance

/**
 * Check if color contrast meets WCAG AA standards
 * @param {string} foreground - Hex color code for foreground
 * @param {string} background - Hex color code for background
 * @returns {boolean} - True if contrast ratio meets AA standards (4.5:1)
 */
export const checkColorContrast = (foreground, background) => {
  const getLuminance = (color) => {
    const hex = color.replace('#', '')
    const r = parseInt(hex.substr(0, 2), 16) / 255
    const g = parseInt(hex.substr(2, 2), 16) / 255
    const b = parseInt(hex.substr(4, 2), 16) / 255

    const sRGB = [r, g, b].map((c) => {
      return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4)
    })

    return 0.2126 * sRGB[0] + 0.7152 * sRGB[1] + 0.0722 * sRGB[2]
  }

  const l1 = getLuminance(foreground)
  const l2 = getLuminance(background)
  const lighter = Math.max(l1, l2)
  const darker = Math.min(l1, l2)

  const contrastRatio = (lighter + 0.05) / (darker + 0.05)
  return contrastRatio >= 4.5 // WCAG AA standard
}

/**
 * Generate accessible IDs for form elements
 * @param {string} base - Base name for the ID
 * @returns {string} - Unique accessible ID
 */
export const generateAccessibleId = (base) => {
  const timestamp = Date.now()
  const random = Math.random().toString(36).substr(2, 5)
  return `${base}-${timestamp}-${random}`
    .toLowerCase()
    .replace(/[^a-z0-9-]/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
}

/**
 * Check if element has minimum touch target size (44x44px)
 * @param {HTMLElement} element - DOM element to check
 * @returns {boolean} - True if meets minimum size requirements
 */
export const checkTouchTargetSize = (element) => {
  if (!element || typeof element.getBoundingClientRect !== 'function') {
    return false
  }

  const rect = element.getBoundingClientRect()
  return rect.width >= 44 && rect.height >= 44
}

/**
 * Announce content to screen readers using live regions
 * @param {string} message - Message to announce
 * @param {string} priority - 'polite' or 'assertive'
 */
export const announceToScreenReader = (message, priority = 'polite') => {
  const liveRegion = document.createElement('div')
  liveRegion.setAttribute('aria-live', priority)
  liveRegion.setAttribute('aria-atomic', 'true')
  liveRegion.setAttribute('class', 'sr-only')
  liveRegion.textContent = message

  document.body.appendChild(liveRegion)

  // Remove after announcement
  setTimeout(() => {
    document.body.removeChild(liveRegion)
  }, 1000)
}

/**
 * Check if text has appropriate heading hierarchy
 * @param {HTMLElement} container - Container element to check
 * @returns {Object} - Analysis of heading structure
 */
export const checkHeadingHierarchy = (container) => {
  const headings = container.querySelectorAll('h1, h2, h3, h4, h5, h6')
  const hierarchy = []
  let hasH1 = false
  let violations = []

  headings.forEach((heading, index) => {
    const level = parseInt(heading.tagName.charAt(1))
    hierarchy.push({ element: heading, level, index })

    if (level === 1) hasH1 = true

    if (index > 0) {
      const prevLevel = hierarchy[index - 1].level
      if (level > prevLevel + 1) {
        violations.push({
          element: heading,
          issue: `Heading level jumps from h${prevLevel} to h${level}`,
        })
      }
    }
  })

  return {
    hasH1,
    violations,
    hierarchy: hierarchy.map((h) => ({
      level: h.level,
      text: h.element.textContent,
    })),
  }
}

/**
 * Check for keyboard accessibility issues
 * @param {HTMLElement} container - Container to check
 * @returns {Array} - List of potential keyboard navigation issues
 */
export const checkKeyboardAccessibility = (container) => {
  const issues = []

  // Check for elements that should be focusable but aren't
  const clickableElements = container.querySelectorAll(
    '[onclick], .cursor-pointer'
  )
  clickableElements.forEach((element) => {
    const isButton = element.tagName === 'BUTTON'
    const isLink = element.tagName === 'A' && element.hasAttribute('href')
    const hasTabIndex = element.hasAttribute('tabindex')
    const hasRole = element.getAttribute('role') === 'button'

    if (!isButton && !isLink && !hasTabIndex && !hasRole) {
      issues.push({
        element,
        issue: 'Clickable element is not keyboard accessible',
      })
    }
  })

  // Check for focus traps in modals
  const modals = container.querySelectorAll('[role="dialog"], .modal')
  modals.forEach((modal) => {
    const focusableElements = modal.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )

    if (focusableElements.length === 0) {
      issues.push({
        element: modal,
        issue: 'Modal has no focusable elements',
      })
    }
  })

  return issues
}

/**
 * Validate form accessibility
 * @param {HTMLFormElement} form - Form element to validate
 * @returns {Object} - Validation results
 */
export const validateFormAccessibility = (form) => {
  const issues = []
  const inputs = form.querySelectorAll('input, select, textarea')

  inputs.forEach((input) => {
    const id = input.id
    const label = form.querySelector(`label[for="${id}"]`)
    const ariaLabel = input.getAttribute('aria-label')
    const ariaLabelledBy = input.getAttribute('aria-labelledby')

    if (!label && !ariaLabel && !ariaLabelledBy) {
      issues.push({
        element: input,
        issue: 'Form control lacks accessible label',
      })
    }

    // Check required field indicators
    if (input.hasAttribute('required')) {
      const hasAriaRequired = input.getAttribute('aria-required') === 'true'
      const hasVisualIndicator =
        input.classList.contains('required') ||
        form.querySelector(`[aria-describedby="${id}-required"]`)

      if (!hasAriaRequired || !hasVisualIndicator) {
        issues.push({
          element: input,
          issue: 'Required field lacks proper indicators',
        })
      }
    }
  })

  return {
    valid: issues.length === 0,
    issues,
  }
}

/**
 * WCAG 2.1 AA Compliance Checker
 * @param {HTMLElement} container - Container element to audit
 * @returns {Object} - Comprehensive accessibility audit results
 */
export const auditAccessibility = (container = document.body) => {
  const results = {
    timestamp: new Date().toISOString(),
    overall: { compliant: true, score: 100 },
    sections: {
      headings: checkHeadingHierarchy(container),
      keyboard: checkKeyboardAccessibility(container),
      forms: [],
      images: [],
      colors: {
        tested: false,
        message: 'Color contrast requires manual testing',
      },
    },
    recommendations: [],
  }

  // Check forms
  const forms = container.querySelectorAll('form')
  forms.forEach((form) => {
    results.sections.forms.push(validateFormAccessibility(form))
  })

  // Check images
  const images = container.querySelectorAll('img')
  images.forEach((img) => {
    const alt = img.getAttribute('alt')
    const ariaLabel = img.getAttribute('aria-label')
    const ariaHidden = img.getAttribute('aria-hidden') === 'true'

    if (!alt && !ariaLabel && !ariaHidden) {
      results.sections.images.push({
        element: img,
        issue: 'Image lacks alternative text',
      })
    }
  })

  // Generate score and recommendations
  const totalIssues =
    results.sections.headings.violations.length +
    results.sections.keyboard.length +
    results.sections.forms.reduce((sum, form) => sum + form.issues.length, 0) +
    results.sections.images.length

  results.overall.score = Math.max(0, 100 - totalIssues * 10)
  results.overall.compliant = totalIssues === 0

  if (!results.sections.headings.hasH1) {
    results.recommendations.push('Add a main h1 heading to the page')
  }

  if (totalIssues > 0) {
    results.recommendations.push(
      'Review and fix accessibility issues before production'
    )
  }

  return results
}

/**
 * Icon Alt Text Generation for WCAG 2.1 AA Compliance
 * @param {string} iconName - The icon component name
 * @param {string} context - Additional context for the icon usage
 * @returns {string} - Accessible alt text for the icon
 */
export const getIconAltText = (iconName, context = '') => {
  const iconMappings = {
    // Navigation icons
    HomeIcon: 'Home',
    UsersIcon: 'Team',
    DocumentTextIcon: 'Content',
    CalendarIcon: 'Calendar',
    ChartBarIcon: 'Analytics',
    CogIcon: 'Settings',
    Cog6ToothIcon: 'Settings',
    UserIcon: 'User profile',
    BellIcon: 'Notifications',

    // Action icons
    PlusIcon: 'Add',
    TrashIcon: 'Delete',
    PencilIcon: 'Edit',
    EyeIcon: 'View',
    EyeSlashIcon: 'Hide',
    ArrowPathIcon: 'Refresh',
    ShareIcon: 'Share',
    BookmarkIcon: 'Save',
    HeartIcon: 'Like',
    ChatBubbleLeftIcon: 'Comment',

    // Status icons
    CheckIcon: 'Success',
    XMarkIcon: 'Close',
    ExclamationCircleIcon: 'Warning',
    InformationCircleIcon: 'Information',
    ShieldCheckIcon: 'Verified',
    ClockIcon: 'Time',

    // Media icons
    PhotoIcon: 'Image',
    VideoCameraIcon: 'Video',
    MicrophoneIcon: 'Audio',
    DocumentIcon: 'Document',
    LinkIcon: 'Link',

    // Social platform icons
    facebook: 'Facebook',
    twitter: 'Twitter',
    instagram: 'Instagram',
    linkedin: 'LinkedIn',
    tiktok: 'TikTok',

    // UI elements
    ChevronDownIcon: 'Expand menu',
    ChevronUpIcon: 'Collapse menu',
    ChevronLeftIcon: 'Previous',
    ChevronRightIcon: 'Next',
    Bars3Icon: 'Menu',
    MagnifyingGlassIcon: 'Search',
    FunnelIcon: 'Filter',
    AdjustmentsHorizontalIcon: 'Adjust settings',

    // Special purpose icons
    SparklesIcon: 'AI generated',
    BoltIcon: 'Quick action',
    StarIcon: 'Favorite',
    FlagIcon: 'Flag',
    TagIcon: 'Tag',
    GlobeAltIcon: 'Website',
  }

  const baseAltText =
    iconMappings[iconName] ||
    iconName
      .replace('Icon', '')
      .replace(/([A-Z])/g, ' $1')
      .trim()
      .toLowerCase()

  if (context) {
    return `${baseAltText} - ${context}`
  }

  return baseAltText
}

/**
 * Generate comprehensive ARIA labels for interactive elements
 * @param {string} element - Type of element (button, link, input, etc.)
 * @param {string} action - Action the element performs
 * @param {string} context - Additional context
 * @returns {string} - Complete ARIA label
 */
export const generateAriaLabel = (element, action, context = '') => {
  const actionMappings = {
    button: 'button',
    link: 'link',
    input: 'input field',
    select: 'dropdown',
    textarea: 'text area',
    checkbox: 'checkbox',
    radio: 'radio button',
    tab: 'tab',
    modal: 'dialog',
    menu: 'menu',
    menuitem: 'menu item',
  }

  const baseLabel = actionMappings[element] || element

  if (action && context) {
    return `${action} ${context} ${baseLabel}`
  } else if (action) {
    return `${action} ${baseLabel}`
  } else if (context) {
    return `${context} ${baseLabel}`
  }

  return baseLabel
}

/**
 * Get enhanced form field accessibility properties
 * @param {string} fieldName - Name of the form field
 * @param {boolean} isRequired - Whether the field is required
 * @param {boolean} hasError - Whether the field has an error
 * @param {string} errorMessage - The error message text
 * @returns {Object} - Accessibility props for form fields
 */
export const getFormFieldProps = (
  fieldName,
  isRequired = false,
  hasError = false,
  errorMessage = ''
) => {
  const baseProps = {
    'aria-required': isRequired,
    'aria-invalid': hasError,
  }

  if (hasError && errorMessage) {
    baseProps['aria-describedby'] = `${fieldName}-error`
  }

  return baseProps
}

/**
 * Get button accessibility properties with enhanced states
 * @param {string} action - The action the button performs
 * @param {boolean} isDisabled - Whether the button is disabled
 * @param {boolean} isLoading - Whether the button is in loading state
 * @param {boolean} hasIcon - Whether the button contains an icon
 * @returns {Object} - Accessibility props for buttons
 */
export const getButtonProps = (
  action,
  isDisabled = false,
  isLoading = false,
  hasIcon = false
) => {
  const props = {
    'aria-disabled': isDisabled,
    'aria-busy': isLoading,
    type: 'button',
  }

  if (isLoading) {
    props['aria-live'] = 'polite'
    props['aria-describedby'] = 'loading-status'
  }

  if (hasIcon) {
    props['aria-describedby'] =
      `${action.toLowerCase().replace(/\s+/g, '-')}-description`
  }

  return props
}

/**
 * Generate image alt text based on context and type
 * @param {string} type - Type of image (avatar, logo, banner, etc.)
 * @param {string} description - Description of the image content
 * @param {string} platform - Platform the image is for
 * @returns {string} - Descriptive alt text
 */
export const getImageAltText = (type, description = '', platform = '') => {
  const typeMapping = {
    avatar: 'Profile picture',
    logo: 'Logo',
    banner: 'Banner image',
    post: 'Post image',
    thumbnail: 'Thumbnail',
    icon: 'Icon',
    chart: 'Chart',
    graph: 'Graph',
  }

  const baseText = typeMapping[type] || 'Image'

  if (description && platform) {
    return `${baseText}: ${description} for ${platform}`
  } else if (description) {
    return `${baseText}: ${description}`
  } else if (platform) {
    return `${baseText} for ${platform}`
  }

  return baseText
}

/**
 * Get loading state accessibility properties
 * @param {boolean} isLoading - Whether element is in loading state
 * @param {string} loadingText - Custom loading announcement text
 * @returns {Object} - Loading state accessibility props
 */
export const getLoadingProps = (isLoading = false, loadingText = 'Loading') => {
  if (!isLoading) return {}

  return {
    'aria-live': 'polite',
    'aria-busy': 'true',
    'aria-label': loadingText,
    role: 'status',
  }
}

/**
 * Get navigation link accessibility properties
 * @param {boolean} isActive - Whether the nav link is currently active
 * @param {boolean} isDisabled - Whether the nav link is disabled
 * @returns {Object} - Navigation accessibility props
 */
export const getNavLinkProps = (isActive = false, isDisabled = false) => {
  const props = {
    'aria-current': isActive ? 'page' : undefined,
    'aria-disabled': isDisabled,
    role: 'menuitem',
  }

  return props
}

export default {
  checkColorContrast,
  generateAccessibleId,
  checkTouchTargetSize,
  announceToScreenReader,
  checkHeadingHierarchy,
  checkKeyboardAccessibility,
  validateFormAccessibility,
  auditAccessibility,
  getIconAltText,
  generateAriaLabel,
  getFormFieldProps,
  getButtonProps,
  getImageAltText,
  getLoadingProps,
  getNavLinkProps,
}
