import React, { useState, useEffect } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import { useNotifications } from '../../hooks/useNotifications'
import api from '../../services/api'
import {
  DocumentArrowDownIcon,
  CalendarIcon,
  CreditCardIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  ArrowTopRightOnSquareIcon
} from '@heroicons/react/24/outline'

/**
 * Billing History Component
 * 
 * Displays invoice history, payment methods, and billing details
 * with Stripe customer portal integration
 */
const BillingHistory = () => {
  const { user } = useAuth()
  const { showSuccess, showError } = useNotifications()
  
  const [invoices, setInvoices] = useState([])
  const [paymentMethods, setPaymentMethods] = useState([])
  const [loading, setLoading] = useState(true)
  const [downloadingInvoice, setDownloadingInvoice] = useState(null)
  
  useEffect(() => {
    loadBillingHistory()
  }, [])
  
  const loadBillingHistory = async () => {
    try {
      setLoading(true)
      const [invoicesResponse, paymentMethodsResponse] = await Promise.all([
        api.getInvoices().catch(() => ({ invoices: [] })),
        api.request('/api/billing/payment-methods').catch(() => ({ payment_methods: [] }))
      ])
      
      setInvoices(invoicesResponse.invoices || [])
      setPaymentMethods(paymentMethodsResponse.payment_methods || [])
    } catch (error) {
      console.error('Failed to load billing history:', error)
      showError('Failed to load billing history')
    } finally {
      setLoading(false)
    }
  }
  
  const downloadInvoice = async (invoiceId) => {
    try {
      setDownloadingInvoice(invoiceId)
      const response = await api.request(`/api/billing/invoices/${invoiceId}/download`, {
        method: 'POST'
      })
      
      // Open the invoice URL in a new tab
      if (response.invoice_url) {
        window.open(response.invoice_url, '_blank')
        showSuccess('Invoice opened in new tab')
      }
    } catch (error) {
      console.error('Failed to download invoice:', error)
      showError('Failed to download invoice')
    } finally {
      setDownloadingInvoice(null)
    }
  }
  
  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short', 
      day: 'numeric'
    })
  }
  
  const formatAmount = (amount, currency = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency.toUpperCase(),
      minimumFractionDigits: 2
    }).format(amount / 100) // Stripe amounts are in cents
  }
  
  const getStatusIcon = (status) => {
    switch (status) {
      case 'paid':
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />
      case 'open':
      case 'draft':
        return <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />
      default:
        return <ExclamationTriangleIcon className="h-5 w-5 text-red-500" />
    }
  }
  
  const getStatusText = (status) => {
    switch (status) {
      case 'paid':
        return 'Paid'
      case 'open':
        return 'Pending'
      case 'draft':
        return 'Draft'
      case 'void':
        return 'Void'
      case 'uncollectible':
        return 'Uncollectible'
      default:
        return status
    }
  }
  
  const getStatusColor = (status) => {
    switch (status) {
      case 'paid':
        return 'text-green-700 bg-green-50 border-green-200'
      case 'open':
      case 'draft':
        return 'text-yellow-700 bg-yellow-50 border-yellow-200'
      default:
        return 'text-red-700 bg-red-50 border-red-200'
    }
  }
  
  if (loading) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded w-5/6"></div>
            <div className="h-4 bg-gray-200 rounded w-4/6"></div>
          </div>
        </div>
      </div>
    )
  }
  
  return (
    <div className="space-y-6">
      {/* Payment Methods */}
      {paymentMethods.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
              <CreditCardIcon className="h-5 w-5 mr-2" />
              Payment Methods
            </h3>
          </div>
          
          <div className="p-6">
            <div className="space-y-4">
              {paymentMethods.map((method) => (
                <div key={method.id} className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                  <div className="flex items-center space-x-3">
                    <div className="bg-white dark:bg-gray-600 p-2 rounded">
                      <CreditCardIcon className="h-5 w-5 text-gray-600 dark:text-gray-400" />
                    </div>
                    <div>
                      <div className="font-medium text-gray-900 dark:text-white">
                        •••• •••• •••• {method.card?.last4 || '••••'}
                      </div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        {method.card?.brand?.toUpperCase() || 'Card'} • Expires {method.card?.exp_month}/{method.card?.exp_year}
                      </div>
                    </div>
                  </div>
                  
                  {method.is_default && (
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                      Default
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
      
      {/* Invoice History */}
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center">
            <DocumentArrowDownIcon className="h-5 w-5 mr-2" />
            Billing History
          </h3>
        </div>
        
        <div className="p-6">
          {invoices.length === 0 ? (
            <div className="text-center py-8">
              <DocumentArrowDownIcon className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <h4 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                No invoices yet
              </h4>
              <p className="text-gray-500 dark:text-gray-400">
                Your billing history will appear here once you have active subscriptions.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {invoices.map((invoice) => (
                <div key={invoice.id} className="flex items-center justify-between p-4 border border-gray-200 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
                  <div className="flex items-center space-x-4">
                    <div className="flex-shrink-0">
                      {getStatusIcon(invoice.status)}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-3">
                        <div className="font-medium text-gray-900 dark:text-white">
                          Invoice #{invoice.number}
                        </div>
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(invoice.status)}`}>
                          {getStatusText(invoice.status)}
                        </span>
                      </div>
                      
                      <div className="mt-1 flex items-center space-x-4 text-sm text-gray-500 dark:text-gray-400">
                        <div className="flex items-center">
                          <CalendarIcon className="h-4 w-4 mr-1" />
                          {formatDate(invoice.created)}
                        </div>
                        <div>
                          {invoice.period_start && invoice.period_end && (
                            `${formatDate(invoice.period_start)} - ${formatDate(invoice.period_end)}`
                          )}
                        </div>
                      </div>
                    </div>
                    
                    <div className="text-right">
                      <div className="font-semibold text-gray-900 dark:text-white">
                        {formatAmount(invoice.amount_paid || invoice.total, invoice.currency)}
                      </div>
                      {invoice.amount_due > 0 && invoice.status !== 'paid' && (
                        <div className="text-sm text-red-600 dark:text-red-400">
                          {formatAmount(invoice.amount_due, invoice.currency)} due
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2 ml-4">
                    {invoice.hosted_invoice_url && (
                      <button
                        onClick={() => window.open(invoice.hosted_invoice_url, '_blank')}
                        className="inline-flex items-center px-3 py-1.5 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
                      >
                        <ArrowTopRightOnSquareIcon className="h-4 w-4 mr-1" />
                        View
                      </button>
                    )}
                    
                    {invoice.invoice_pdf && (
                      <button
                        onClick={() => downloadInvoice(invoice.id)}
                        disabled={downloadingInvoice === invoice.id}
                        className="inline-flex items-center px-3 py-1.5 border border-gray-300 dark:border-gray-600 text-sm font-medium rounded text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 transition-colors"
                      >
                        {downloadingInvoice === invoice.id ? (
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-1"></div>
                        ) : (
                          <DocumentArrowDownIcon className="h-4 w-4 mr-1" />
                        )}
                        Download
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default BillingHistory