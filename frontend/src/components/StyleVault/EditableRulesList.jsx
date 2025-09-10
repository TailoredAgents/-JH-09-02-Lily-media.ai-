import { useState, useEffect } from 'react'
import {
  PlusIcon,
  XMarkIcon,
  CheckCircleIcon,
  EllipsisVerticalIcon,
  Bars3Icon,
} from '@heroicons/react/24/outline'
import KeyboardDragDrop from '../KeyboardDragDrop'
import AccessibleDragDrop from '../AccessibleDragDrop'

// Individual rule item component for both mouse and keyboard modes
const RuleItem = ({ 
  rule, 
  index, 
  isSelected, 
  colorClasses, 
  isDoType, 
  onUpdate, 
  onRemove, 
  inputMode 
}) => {
  return (
    <div className={`group relative ${isSelected ? 'ring-2 ring-blue-500 bg-blue-50' : ''}`}>
      <div className="flex items-center space-x-2">
        {inputMode === 'mouse' && (
          <div className="text-gray-400 hover:text-gray-600 cursor-grab active:cursor-grabbing">
            <Bars3Icon className="w-4 h-4" aria-hidden="true" />
          </div>
        )}
        
        <div className="flex-1">
          <textarea
            value={rule}
            onChange={(e) => onUpdate(index, e.target.value)}
            className={`w-full bg-white border border-gray-300 rounded-md px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-offset-2 ${colorClasses.input}`}
            rows={rule.length > 60 ? 2 : 1}
            placeholder={isDoType 
              ? 'Enter a brand guideline...' 
              : 'Enter a brand restriction...'
            }
            aria-label={`${isDoType ? 'Brand guideline' : 'Brand restriction'} ${index + 1}`}
          />
        </div>
        
        <button
          onClick={() => onRemove(index)}
          className="text-gray-400 hover:text-red-600 opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 rounded p-1"
          title={`Remove ${isDoType ? 'guideline' : 'restriction'}`}
          aria-label={`Remove ${isDoType ? 'guideline' : 'restriction'} ${index + 1}`}
          type="button"
        >
          <XMarkIcon className="w-4 h-4" aria-hidden="true" />
        </button>
      </div>
    </div>
  )
}

const EditableRulesList = ({ rules, type, onUpdate, onCancel }) => {
  const [localRules, setLocalRules] = useState(rules || [])
  const [newRule, setNewRule] = useState('')

  useEffect(() => {
    setLocalRules(rules || [])
  }, [rules])

  const addRule = () => {
    if (newRule.trim()) {
      const updatedRules = [...localRules, newRule.trim()]
      setLocalRules(updatedRules)
      setNewRule('')
    }
  }

  const removeRule = (index) => {
    const updatedRules = localRules.filter((_, i) => i !== index)
    setLocalRules(updatedRules)
  }

  const updateRule = (index, value) => {
    const updatedRules = localRules.map((rule, i) => 
      i === index ? value : rule
    )
    setLocalRules(updatedRules)
  }

  const handleRuleMove = (fromIndex, toIndex) => {
    const items = Array.from(localRules)
    const [reorderedItem] = items.splice(fromIndex, 1)
    items.splice(toIndex, 0, reorderedItem)
    setLocalRules(items)
  }

  const handleSave = () => {
    onUpdate(localRules.filter(rule => rule.trim()))
  }

  const isDoType = type === 'dos'
  const colorClasses = isDoType 
    ? {
        bg: 'bg-green-50',
        border: 'border-green-200',
        text: 'text-green-800',
        icon: 'text-green-500',
        button: 'bg-green-600 hover:bg-green-700',
        input: 'focus:ring-green-500 focus:border-green-500'
      }
    : {
        bg: 'bg-red-50',
        border: 'border-red-200', 
        text: 'text-red-800',
        icon: 'text-red-500',
        button: 'bg-red-600 hover:bg-red-700',
        input: 'focus:ring-red-500 focus:border-red-500'
      }

  return (
    <div className="space-y-4">
      <div className={`border rounded-lg p-4 ${colorClasses.border} ${colorClasses.bg}`}>
        <div className="mb-4">
          <h4 className={`font-medium text-sm ${colorClasses.text} mb-2`}>
            {isDoType ? 'Brand Guidelines (Things to do)' : 'Brand Restrictions (Things to avoid)'}
          </h4>
          <p className="text-xs text-gray-600">
            {isDoType 
              ? 'Add guidelines that define what should be included in your brand content.'
              : 'Add restrictions that define what should be avoided in your brand content.'
            }
          </p>
        </div>

        {/* Existing Rules with Accessible Drag and Drop */}
        {localRules.length > 0 && (
          <div className="mb-4">
            <AccessibleDragDrop
              showToggle={localRules.length > 1}
              defaultMode="mouse"
              instructions={true}
              keyboardAlternative={
                <KeyboardDragDrop
                  items={localRules.map((rule, index) => ({ 
                    id: index, 
                    content: rule, 
                    index 
                  }))}
                  onMove={(fromId, toId) => {
                    const fromIndex = typeof fromId === 'number' ? fromId : parseInt(fromId)
                    const toIndex = typeof toId === 'number' ? toId : parseInt(toId)
                    handleRuleMove(fromIndex, toIndex)
                  }}
                  renderItem={(item, isSelected) => (
                    <RuleItem
                      rule={item.content}
                      index={item.index}
                      isSelected={isSelected}
                      colorClasses={colorClasses}
                      isDoType={isDoType}
                      onUpdate={updateRule}
                      onRemove={removeRule}
                      inputMode="keyboard"
                    />
                  )}
                  instructions={false}
                  className="space-y-2"
                />
              }
            >
              <div className="space-y-2">
                {localRules.map((rule, index) => (
                  <RuleItem
                    key={index}
                    rule={rule}
                    index={index}
                    isSelected={false}
                    colorClasses={colorClasses}
                    isDoType={isDoType}
                    onUpdate={updateRule}
                    onRemove={removeRule}
                    inputMode="mouse"
                  />
                ))}
              </div>
            </AccessibleDragDrop>
          </div>
        )}

        {/* Add New Rule */}
        <div className="space-y-3">
          <div className="flex space-x-2">
            <textarea
              value={newRule}
              onChange={(e) => setNewRule(e.target.value)}
              className={`flex-1 bg-white border border-gray-300 rounded-md px-3 py-2 text-sm resize-none ${colorClasses.input}`}
              rows={1}
              placeholder={isDoType 
                ? 'Add a new brand guideline...' 
                : 'Add a new brand restriction...'
              }
              onKeyPress={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  addRule()
                }
              }}
            />
            <button
              onClick={addRule}
              disabled={!newRule.trim()}
              className={`px-3 py-2 text-white text-sm font-medium rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${colorClasses.button}`}
            >
              <PlusIcon className="w-4 h-4" />
            </button>
          </div>
          
          <p className="text-xs text-gray-500">
            Press Enter to add, or use Shift+Enter for line breaks. Use drag-and-drop or keyboard navigation to reorder.
          </p>
        </div>

        {/* Quick Add Templates */}
        <div className="mt-4 pt-4 border-t border-gray-200">
          <p className="text-xs text-gray-600 mb-2">Quick add common {isDoType ? 'guidelines' : 'restrictions'}:</p>
          <div className="flex flex-wrap gap-2">
            {getTemplateRules(isDoType).map((template, index) => (
              <button
                key={index}
                onClick={() => {
                  if (!localRules.includes(template)) {
                    setLocalRules(prev => [...prev, template])
                  }
                }}
                disabled={localRules.includes(template)}
                className="px-2 py-1 text-xs bg-white border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                + {template}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Save/Cancel Actions */}
      <div className="flex justify-end space-x-3">
        <button
          onClick={onCancel}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
        >
          Cancel
        </button>
        <button
          onClick={handleSave}
          className="px-4 py-2 text-sm font-medium text-white bg-purple-600 border border-transparent rounded-md hover:bg-purple-700"
        >
          Save Changes
        </button>
      </div>

      {/* Rules Summary */}
      {localRules.length > 0 && (
        <div className="text-xs text-gray-500 text-center">
          {localRules.length} {type === 'dos' ? 'guideline' : 'restriction'}{localRules.length !== 1 ? 's' : ''} configured
        </div>
      )}
    </div>
  )
}

function getTemplateRules(isDoType) {
  if (isDoType) {
    return [
      'Use consistent color palette',
      'Maintain professional tone',
      'Include brand elements',
      'Follow typography guidelines',
      'Use high-quality images',
      'Keep messaging clear and concise',
      'Include call-to-action when appropriate',
      'Maintain brand voice consistency',
      'Use approved logo variations',
      'Follow accessibility guidelines'
    ]
  } else {
    return [
      'Avoid competitor mentions',
      'No inappropriate content',
      'Don\'t use unauthorized fonts',
      'Avoid off-brand colors',
      'No low-quality images',
      'Don\'t break accessibility rules',
      'Avoid outdated information',
      'No unauthorized logo modifications',
      'Don\'t use competing messaging',
      'Avoid inconsistent tone'
    ]
  }
}

export default EditableRulesList