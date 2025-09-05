import React from 'react'
import { motion } from 'framer-motion'

/**
 * @param {{ title: string, value: string|number, growth?: number, icon?: React.ReactNode, darkMode?: boolean, delay?: number }} props
 */
export default function MetricCard({
  title,
  value,
  growth,
  icon,
  darkMode,
  delay = 0,
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay }}
      className={`p-6 rounded-xl backdrop-blur-md ${darkMode ? 'bg-gray-800/80' : 'bg-white/80'} border border-gray-200/20 shadow-lg`}
    >
      <div className="flex items-center justify-between">
        <div>
          <p
            className={`text-sm font-medium ${darkMode ? 'text-gray-400' : 'text-gray-600'}`}
          >
            {title}
          </p>
          <p
            className={`text-2xl font-bold mt-2 ${darkMode ? 'text-white' : 'text-gray-900'}`}
          >
            {value}
          </p>
        </div>
        {icon}
      </div>
      {typeof growth === 'number' && (
        <p
          className={`text-xs mt-3 ${growth >= 0 ? 'text-green-600' : 'text-red-600'}`}
        >
          {growth >= 0 ? '▲' : '▼'} {Math.abs(growth)}%
        </p>
      )}
    </motion.div>
  )
}
