import React, { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { usePlan } from '../contexts/PlanContext'
import api from '../services/api'
import {
  CogIcon,
  CurrencyDollarIcon,
  CloudIcon,
  CalendarDaysIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  CheckCircleIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'

const TABS = [
  {
    id: 'pricing',
    name: 'Pricing',
    icon: CurrencyDollarIcon,
    description: 'Configure pricing rules, rates, and bundles',
  },
  {
    id: 'weather',
    name: 'Weather',
    icon: CloudIcon,
    description: 'Set weather thresholds and rescheduling policies',
  },
  {
    id: 'booking',
    name: 'Booking Policies',
    icon: CalendarDaysIcon,
    description: 'Configure booking rules and requirements',
  },
]

export default function Settings() {
  const { user } = useAuth()
  const { plan } = usePlan()

  const [activeTab, setActiveTab] = useState('pricing')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [errors, setErrors] = useState({})
  const [successMessage, setSuccessMessage] = useState('')

  // Settings state
  const [pricingSettings, setPricingSettings] = useState({
    base_rates: {
      house_washing: 0.15,
      pressure_washing: 0.12,
      soft_wash: 0.18,
      deck_cleaning: 0.20,
      concrete_cleaning: 0.10,
      gutter_cleaning: 0.08,
    },
    min_job_total: 150.0,
    bundles: [
      {
        name: 'House + Driveway',
        services: ['house_washing', 'concrete_cleaning'],
        discount_percent: 15,
      },
    ],
    seasonal_modifiers: [
      {
        season: 'spring',
        multiplier: 1.1,
        description: 'High demand season',
      },
    ],
  })

  const [weatherSettings, setWeatherSettings] = useState({
    rain_probability_threshold: 30,
    wind_speed_threshold: 25,
    temperature_threshold: 40,
    lookahead_days: 3,
    auto_reschedule: true,
    notification_hours_ahead: 24,
  })

  const [bookingSettings, setBookingSettings] = useState({
    intent_threshold: 0.75,
    require_photos: true,
    required_fields: ['customer_name', 'phone', 'address', 'service_type'],
    auto_followup_hours: 24,
    quiet_hours: {
      enabled: true,
      start: '20:00',
      end: '08:00',
    },
    business_hours: {
      monday: { enabled: true, start: '08:00', end: '18:00' },
      tuesday: { enabled: true, start: '08:00', end: '18:00' },
      wednesday: { enabled: true, start: '08:00', end: '18:00' },
      thursday: { enabled: true, start: '08:00', end: '18:00' },
      friday: { enabled: true, start: '08:00', end: '18:00' },
      saturday: { enabled: true, start: '09:00', end: '17:00' },
      sunday: { enabled: false, start: '10:00', end: '16:00' },
    },
    buffer_minutes: 30,
  })

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      setLoading(true)
      
      const [pricingData, weatherData, bookingData] = await Promise.allSettled([
        api.getPricingSettings(),
        api.getWeatherSettings(),
        api.getBookingSettings(),
      ])

      if (pricingData.status === 'fulfilled' && pricingData.value) {
        setPricingSettings({ ...pricingSettings, ...pricingData.value })
      }

      if (weatherData.status === 'fulfilled' && weatherData.value) {
        setWeatherSettings({ ...weatherSettings, ...weatherData.value })
      }

      if (bookingData.status === 'fulfilled' && bookingData.value) {
        setBookingSettings({ ...bookingSettings, ...bookingData.value })
      }
    } catch (error) {
      console.error('Failed to load settings:', error)
      setErrors({ general: 'Failed to load settings. Using defaults.' })
    } finally {
      setLoading(false)
    }
  }

  const saveSettings = async (settingsType) => {
    try {
      setSaving(true)
      setErrors({})

      let response
      switch (settingsType) {
        case 'pricing':
          response = await api.updatePricingSettings(pricingSettings)
          break
        case 'weather':
          response = await api.updateWeatherSettings(weatherSettings)
          break
        case 'booking':
          response = await api.updateBookingSettings(bookingSettings)
          break
        default:
          throw new Error('Invalid settings type')
      }

      setSuccessMessage(`${settingsType} settings saved successfully!`)
      setTimeout(() => setSuccessMessage(''), 3000)
    } catch (error) {
      console.error('Failed to save settings:', error)
      setErrors({ [settingsType]: error.message || `Failed to save ${settingsType} settings` })
    } finally {
      setSaving(false)
    }
  }

  const isFieldDisabled = (feature) => {
    // Check if field is plan-gated
    const planGatedFeatures = {
      seasonal_modifiers: ['pro', 'enterprise'],
      bundles: ['pro', 'enterprise'], 
      auto_reschedule: ['basic', 'pro', 'enterprise'],
      advanced_booking: ['pro', 'enterprise'],
    }

    return planGatedFeatures[feature] && !planGatedFeatures[feature].includes(plan?.tier)
  }

  const PlanGateTooltip = ({ feature, children, disabled = false }) => {
    if (!disabled) return children

    return (
      <div className="relative group">
        {children}
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-sm rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
          Upgrade to access {feature} feature
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900"></div>
        </div>
      </div>
    )
  }

  const renderPricingTab = () => (
    <div className="space-y-6">
      {/* Base Rates */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Base Rates (per sq ft)</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {Object.entries(pricingSettings.base_rates).map(([service, rate]) => (
            <div key={service}>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {service.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
              </label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500">$</span>
                <input
                  type="number"
                  step="0.01"
                  min="0"
                  value={rate}
                  onChange={(e) =>
                    setPricingSettings(prev => ({
                      ...prev,
                      base_rates: {
                        ...prev.base_rates,
                        [service]: parseFloat(e.target.value) || 0,
                      },
                    }))
                  }
                  className="pl-8 w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Minimum Job Total */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Minimum Job Total</h3>
        <div className="max-w-xs">
          <div className="relative">
            <span className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500">$</span>
            <input
              type="number"
              min="0"
              value={pricingSettings.min_job_total}
              onChange={(e) =>
                setPricingSettings(prev => ({
                  ...prev,
                  min_job_total: parseFloat(e.target.value) || 0,
                }))
              }
              className="pl-8 w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
          <p className="text-sm text-gray-500 mt-1">Minimum charge for any job</p>
        </div>
      </div>

      {/* Service Bundles */}
      <PlanGateTooltip feature="service bundles" disabled={isFieldDisabled('bundles')}>
        <div className={`bg-white rounded-lg border border-gray-200 p-6 ${isFieldDisabled('bundles') ? 'opacity-50' : ''}`}>
          <h3 className="text-lg font-medium text-gray-900 mb-4">Service Bundles</h3>
          <div className="space-y-4">
            {pricingSettings.bundles.map((bundle, index) => (
              <div key={index} className="border border-gray-200 rounded-lg p-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Bundle Name</label>
                    <input
                      type="text"
                      value={bundle.name}
                      onChange={(e) => {
                        const newBundles = [...pricingSettings.bundles]
                        newBundles[index].name = e.target.value
                        setPricingSettings(prev => ({ ...prev, bundles: newBundles }))
                      }}
                      disabled={isFieldDisabled('bundles')}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-gray-50"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Services</label>
                    <select
                      multiple
                      value={bundle.services}
                      onChange={(e) => {
                        const newBundles = [...pricingSettings.bundles]
                        newBundles[index].services = Array.from(e.target.selectedOptions, option => option.value)
                        setPricingSettings(prev => ({ ...prev, bundles: newBundles }))
                      }}
                      disabled={isFieldDisabled('bundles')}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-gray-50"
                    >
                      {Object.keys(pricingSettings.base_rates).map(service => (
                        <option key={service} value={service}>
                          {service.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Discount %</label>
                    <input
                      type="number"
                      min="0"
                      max="50"
                      value={bundle.discount_percent}
                      onChange={(e) => {
                        const newBundles = [...pricingSettings.bundles]
                        newBundles[index].discount_percent = parseInt(e.target.value) || 0
                        setPricingSettings(prev => ({ ...prev, bundles: newBundles }))
                      }}
                      disabled={isFieldDisabled('bundles')}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-gray-50"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </PlanGateTooltip>

      {/* Seasonal Modifiers */}
      <PlanGateTooltip feature="seasonal pricing" disabled={isFieldDisabled('seasonal_modifiers')}>
        <div className={`bg-white rounded-lg border border-gray-200 p-6 ${isFieldDisabled('seasonal_modifiers') ? 'opacity-50' : ''}`}>
          <h3 className="text-lg font-medium text-gray-900 mb-4">Seasonal Modifiers</h3>
          <div className="space-y-4">
            {pricingSettings.seasonal_modifiers.map((modifier, index) => (
              <div key={index} className="border border-gray-200 rounded-lg p-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Season</label>
                    <select
                      value={modifier.season}
                      onChange={(e) => {
                        const newModifiers = [...pricingSettings.seasonal_modifiers]
                        newModifiers[index].season = e.target.value
                        setPricingSettings(prev => ({ ...prev, seasonal_modifiers: newModifiers }))
                      }}
                      disabled={isFieldDisabled('seasonal_modifiers')}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-gray-50"
                    >
                      <option value="spring">Spring</option>
                      <option value="summer">Summer</option>
                      <option value="fall">Fall</option>
                      <option value="winter">Winter</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Price Multiplier</label>
                    <input
                      type="number"
                      step="0.1"
                      min="0.5"
                      max="2.0"
                      value={modifier.multiplier}
                      onChange={(e) => {
                        const newModifiers = [...pricingSettings.seasonal_modifiers]
                        newModifiers[index].multiplier = parseFloat(e.target.value) || 1.0
                        setPricingSettings(prev => ({ ...prev, seasonal_modifiers: newModifiers }))
                      }}
                      disabled={isFieldDisabled('seasonal_modifiers')}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-gray-50"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                    <input
                      type="text"
                      value={modifier.description}
                      onChange={(e) => {
                        const newModifiers = [...pricingSettings.seasonal_modifiers]
                        newModifiers[index].description = e.target.value
                        setPricingSettings(prev => ({ ...prev, seasonal_modifiers: newModifiers }))
                      }}
                      disabled={isFieldDisabled('seasonal_modifiers')}
                      className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-gray-50"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </PlanGateTooltip>

      <div className="flex justify-end">
        <button
          onClick={() => saveSettings('pricing')}
          disabled={saving}
          className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? 'Saving...' : 'Save Pricing Settings'}
        </button>
      </div>
    </div>
  )

  const renderWeatherTab = () => (
    <div className="space-y-6">
      {/* Weather Thresholds */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Weather Thresholds</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Rain Probability Threshold
            </label>
            <div className="flex items-center space-x-3">
              <input
                type="range"
                min="10"
                max="90"
                step="5"
                value={weatherSettings.rain_probability_threshold}
                onChange={(e) =>
                  setWeatherSettings(prev => ({
                    ...prev,
                    rain_probability_threshold: parseInt(e.target.value),
                  }))
                }
                className="flex-1"
              />
              <span className="text-sm font-medium text-gray-900 min-w-[3rem]">
                {weatherSettings.rain_probability_threshold}%
              </span>
            </div>
            <p className="text-sm text-gray-500 mt-1">
              Cancel/reschedule jobs if rain probability exceeds this threshold
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Wind Speed Threshold
            </label>
            <div className="flex items-center space-x-3">
              <input
                type="range"
                min="10"
                max="50"
                step="5"
                value={weatherSettings.wind_speed_threshold}
                onChange={(e) =>
                  setWeatherSettings(prev => ({
                    ...prev,
                    wind_speed_threshold: parseInt(e.target.value),
                  }))
                }
                className="flex-1"
              />
              <span className="text-sm font-medium text-gray-900 min-w-[3rem]">
                {weatherSettings.wind_speed_threshold} mph
              </span>
            </div>
            <p className="text-sm text-gray-500 mt-1">
              Cancel jobs if wind speed exceeds this threshold
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Temperature Threshold
            </label>
            <div className="flex items-center space-x-3">
              <input
                type="range"
                min="25"
                max="50"
                step="5"
                value={weatherSettings.temperature_threshold}
                onChange={(e) =>
                  setWeatherSettings(prev => ({
                    ...prev,
                    temperature_threshold: parseInt(e.target.value),
                  }))
                }
                className="flex-1"
              />
              <span className="text-sm font-medium text-gray-900 min-w-[3rem]">
                {weatherSettings.temperature_threshold}°F
              </span>
            </div>
            <p className="text-sm text-gray-500 mt-1">
              Cancel jobs if temperature is below this threshold
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Weather Lookahead Days
            </label>
            <select
              value={weatherSettings.lookahead_days}
              onChange={(e) =>
                setWeatherSettings(prev => ({
                  ...prev,
                  lookahead_days: parseInt(e.target.value),
                }))
              }
              className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value={1}>1 day</option>
              <option value={2}>2 days</option>
              <option value={3}>3 days</option>
              <option value={5}>5 days</option>
              <option value={7}>7 days</option>
            </select>
            <p className="text-sm text-gray-500 mt-1">
              How many days ahead to check weather forecasts
            </p>
          </div>
        </div>
      </div>

      {/* Auto-Reschedule Settings */}
      <PlanGateTooltip feature="auto-rescheduling" disabled={isFieldDisabled('auto_reschedule')}>
        <div className={`bg-white rounded-lg border border-gray-200 p-6 ${isFieldDisabled('auto_reschedule') ? 'opacity-50' : ''}`}>
          <h3 className="text-lg font-medium text-gray-900 mb-4">Auto-Rescheduling</h3>
          
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="font-medium text-gray-900">Enable Auto-Reschedule</p>
              <p className="text-sm text-gray-600">
                Automatically reschedule jobs when weather conditions are unsuitable
              </p>
            </div>
            <button
              onClick={() =>
                setWeatherSettings(prev => ({
                  ...prev,
                  auto_reschedule: !prev.auto_reschedule,
                }))
              }
              disabled={isFieldDisabled('auto_reschedule')}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 ${
                weatherSettings.auto_reschedule ? 'bg-indigo-600' : 'bg-gray-200'
              } disabled:opacity-50`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  weatherSettings.auto_reschedule ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {weatherSettings.auto_reschedule && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Notification Hours Ahead
              </label>
              <select
                value={weatherSettings.notification_hours_ahead}
                onChange={(e) =>
                  setWeatherSettings(prev => ({
                    ...prev,
                    notification_hours_ahead: parseInt(e.target.value),
                  }))
                }
                disabled={isFieldDisabled('auto_reschedule')}
                className="w-full max-w-xs border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:bg-gray-50"
              >
                <option value={12}>12 hours</option>
                <option value={24}>24 hours</option>
                <option value={48}>48 hours</option>
                <option value={72}>72 hours</option>
              </select>
              <p className="text-sm text-gray-500 mt-1">
                How far in advance to notify customers about weather-related rescheduling
              </p>
            </div>
          )}
        </div>
      </PlanGateTooltip>

      <div className="flex justify-end">
        <button
          onClick={() => saveSettings('weather')}
          disabled={saving}
          className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? 'Saving...' : 'Save Weather Settings'}
        </button>
      </div>
    </div>
  )

  const renderBookingTab = () => (
    <div className="space-y-6">
      {/* Lead Qualification */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Lead Qualification</h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Intent Confidence Threshold
            </label>
            <div className="flex items-center space-x-3">
              <input
                type="range"
                min="0.5"
                max="1.0"
                step="0.05"
                value={bookingSettings.intent_threshold}
                onChange={(e) =>
                  setBookingSettings(prev => ({
                    ...prev,
                    intent_threshold: parseFloat(e.target.value),
                  }))
                }
                className="flex-1"
              />
              <span className="text-sm font-medium text-gray-900 min-w-[3rem]">
                {Math.round(bookingSettings.intent_threshold * 100)}%
              </span>
            </div>
            <p className="text-sm text-gray-500 mt-1">
              Minimum AI confidence required to qualify a lead as booking intent
            </p>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-900">Require Photos</p>
              <p className="text-sm text-gray-600">
                Require customers to upload photos for accurate quotes
              </p>
            </div>
            <button
              onClick={() =>
                setBookingSettings(prev => ({
                  ...prev,
                  require_photos: !prev.require_photos,
                }))
              }
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 ${
                bookingSettings.require_photos ? 'bg-indigo-600' : 'bg-gray-200'
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  bookingSettings.require_photos ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Required Fields
            </label>
            <div className="space-y-2">
              {['customer_name', 'phone', 'email', 'address', 'service_type', 'property_size', 'special_instructions'].map(field => (
                <label key={field} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={bookingSettings.required_fields.includes(field)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setBookingSettings(prev => ({
                          ...prev,
                          required_fields: [...prev.required_fields, field],
                        }))
                      } else {
                        setBookingSettings(prev => ({
                          ...prev,
                          required_fields: prev.required_fields.filter(f => f !== field),
                        }))
                      }
                    }}
                    className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <span className="ml-2 text-sm text-gray-700">
                    {field.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                  </span>
                </label>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Follow-up Settings */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Follow-up Automation</h3>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Auto Follow-up Hours
          </label>
          <select
            value={bookingSettings.auto_followup_hours}
            onChange={(e) =>
              setBookingSettings(prev => ({
                ...prev,
                auto_followup_hours: parseInt(e.target.value),
              }))
            }
            className="w-full max-w-xs border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value={0}>Disabled</option>
            <option value={2}>2 hours</option>
            <option value={6}>6 hours</option>
            <option value={12}>12 hours</option>
            <option value={24}>24 hours</option>
            <option value={48}>48 hours</option>
            <option value={72}>72 hours</option>
          </select>
          <p className="text-sm text-gray-500 mt-1">
            Automatically follow up with leads after this time if no response
          </p>
        </div>
      </div>

      {/* Business Hours */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Business Hours</h3>
        
        <div className="space-y-4">
          {/* Quiet Hours */}
          <div className="border-b border-gray-200 pb-4">
            <div className="flex items-center justify-between mb-3">
              <div>
                <p className="font-medium text-gray-900">Enable Quiet Hours</p>
                <p className="text-sm text-gray-600">
                  Don't send notifications during specified hours
                </p>
              </div>
              <button
                onClick={() =>
                  setBookingSettings(prev => ({
                    ...prev,
                    quiet_hours: {
                      ...prev.quiet_hours,
                      enabled: !prev.quiet_hours.enabled,
                    },
                  }))
                }
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 ${
                  bookingSettings.quiet_hours.enabled ? 'bg-indigo-600' : 'bg-gray-200'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    bookingSettings.quiet_hours.enabled ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            {bookingSettings.quiet_hours.enabled && (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Start Time</label>
                  <input
                    type="time"
                    value={bookingSettings.quiet_hours.start}
                    onChange={(e) =>
                      setBookingSettings(prev => ({
                        ...prev,
                        quiet_hours: {
                          ...prev.quiet_hours,
                          start: e.target.value,
                        },
                      }))
                    }
                    className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">End Time</label>
                  <input
                    type="time"
                    value={bookingSettings.quiet_hours.end}
                    onChange={(e) =>
                      setBookingSettings(prev => ({
                        ...prev,
                        quiet_hours: {
                          ...prev.quiet_hours,
                          end: e.target.value,
                        },
                      }))
                    }
                    className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Daily Business Hours */}
          <div>
            <h4 className="font-medium text-gray-900 mb-3">Daily Operating Hours</h4>
            <div className="space-y-3">
              {Object.entries(bookingSettings.business_hours).map(([day, hours]) => (
                <div key={day} className="flex items-center space-x-4">
                  <div className="w-20">
                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={hours.enabled}
                        onChange={(e) =>
                          setBookingSettings(prev => ({
                            ...prev,
                            business_hours: {
                              ...prev.business_hours,
                              [day]: {
                                ...prev.business_hours[day],
                                enabled: e.target.checked,
                              },
                            },
                          }))
                        }
                        className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                      />
                      <span className="ml-2 text-sm font-medium text-gray-700 capitalize">
                        {day}
                      </span>
                    </label>
                  </div>
                  
                  {hours.enabled && (
                    <>
                      <input
                        type="time"
                        value={hours.start}
                        onChange={(e) =>
                          setBookingSettings(prev => ({
                            ...prev,
                            business_hours: {
                              ...prev.business_hours,
                              [day]: {
                                ...prev.business_hours[day],
                                start: e.target.value,
                              },
                            },
                          }))
                        }
                        className="border border-gray-300 rounded-md px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                      />
                      <span className="text-gray-500">to</span>
                      <input
                        type="time"
                        value={hours.end}
                        onChange={(e) =>
                          setBookingSettings(prev => ({
                            ...prev,
                            business_hours: {
                              ...prev.business_hours,
                              [day]: {
                                ...prev.business_hours[day],
                                end: e.target.value,
                              },
                            },
                          }))
                        }
                        className="border border-gray-300 rounded-md px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                      />
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Buffer Minutes */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Booking Buffer Minutes
            </label>
            <select
              value={bookingSettings.buffer_minutes}
              onChange={(e) =>
                setBookingSettings(prev => ({
                  ...prev,
                  buffer_minutes: parseInt(e.target.value),
                }))
              }
              className="w-full max-w-xs border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value={15}>15 minutes</option>
              <option value={30}>30 minutes</option>
              <option value={60}>1 hour</option>
              <option value={120}>2 hours</option>
            </select>
            <p className="text-sm text-gray-500 mt-1">
              Minimum time between consecutive job bookings
            </p>
          </div>
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={() => saveSettings('booking')}
          disabled={saving}
          className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? 'Saving...' : 'Save Booking Settings'}
        </button>
      </div>
    </div>
  )

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">Business Settings</h1>
          <p className="text-gray-600 mt-1">
            Configure pricing, weather policies, and booking requirements for your pressure washing business
          </p>
        </div>

        {/* Success Message */}
        {successMessage && (
          <div className="mb-6 bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex items-center">
              <CheckCircleIcon className="h-5 w-5 text-green-400" />
              <p className="ml-2 text-green-800">{successMessage}</p>
            </div>
          </div>
        )}

        {/* Error Messages */}
        {Object.keys(errors).length > 0 && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-start">
              <ExclamationTriangleIcon className="h-5 w-5 text-red-400 mt-0.5" />
              <div className="ml-2">
                {Object.entries(errors).map(([key, error]) => (
                  <p key={key} className="text-red-800 text-sm">
                    {error}
                  </p>
                ))}
              </div>
              <button
                onClick={() => setErrors({})}
                className="ml-auto text-red-400 hover:text-red-600"
              >
                <XMarkIcon className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}

        <div className="flex flex-col lg:flex-row lg:space-x-8">
          {/* Navigation */}
          <div className="lg:w-64 mb-6 lg:mb-0">
            <nav className="space-y-2">
              {TABS.map((tab) => {
                const Icon = tab.icon
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`w-full text-left px-4 py-3 rounded-lg transition-colors ${
                      activeTab === tab.id
                        ? 'bg-indigo-50 text-indigo-700 border border-indigo-200'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
                    }`}
                  >
                    <div className="flex items-center">
                      <Icon className="h-5 w-5 mr-3" />
                      <div>
                        <p className="font-medium">{tab.name}</p>
                        <p className="text-xs opacity-75 mt-1">{tab.description}</p>
                      </div>
                    </div>
                  </button>
                )
              })}
            </nav>
          </div>

          {/* Content */}
          <div className="flex-1">
            {activeTab === 'pricing' && renderPricingTab()}
            {activeTab === 'weather' && renderWeatherTab()}
            {activeTab === 'booking' && renderBookingTab()}
          </div>
        </div>
      </div>
    </div>
  )
}