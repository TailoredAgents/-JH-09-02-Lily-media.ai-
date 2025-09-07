#!/usr/bin/env node
/**
 * Security Validation Script for P0-13a
 * 
 * Validates that access tokens are no longer stored in localStorage
 * and that the secure authentication system is properly implemented.
 * 
 * Usage: node scripts/validate-secure-auth.js
 */

const fs = require('fs')
const path = require('path')
const { execSync } = require('child_process')

class SecureAuthValidator {
  constructor() {
    this.frontendDir = path.join(__dirname, '..', 'frontend')
    this.backendDir = path.join(__dirname, '..', 'backend')
    this.issues = []
    this.successes = []
  }

  log(message, type = 'info') {
    const timestamp = new Date().toISOString()
    const prefix = type === 'error' ? '❌' : type === 'success' ? '✅' : '🔍'
    console.log(`${prefix} [${timestamp}] ${message}`)
    
    if (type === 'error') {
      this.issues.push(message)
    } else if (type === 'success') {
      this.successes.push(message)
    }
  }

  async validateNoLocalStorageTokens() {
    this.log('Validating no localStorage access tokens in active codebase...')
    
    try {
      // Search for localStorage.setItem with token patterns, excluding deprecated files
      const searchResult = execSync(
        `grep -r "localStorage\\.setItem.*[Tt]oken" ${this.frontendDir}/src --exclude-dir=node_modules | grep -v DEPRECATED`,
        { encoding: 'utf-8', stdio: 'pipe' }
      ).trim()
      
      if (searchResult) {
        const lines = searchResult.split('\n')
        for (const line of lines) {
          // Allow documentation and comments, skip deprecated files
          if (!line.includes('//') && !line.includes('/*') && !line.includes('* ') && !line.includes('DEPRECATED')) {
            this.log(`Found localStorage token storage in active code: ${line}`, 'error')
          }
        }
        
        if (lines.length === 0 || lines.every(line => 
          line.includes('//') || line.includes('/*') || line.includes('* ') || line.includes('DEPRECATED')
        )) {
          this.log('No localStorage token storage found in active code (only deprecated files)', 'success')
        }
      } else {
        this.log('No localStorage token storage found in active code', 'success')
      }
    } catch (error) {
      if (error.status === 1) {
        // grep returns 1 when no matches found - this is good
        this.log('No localStorage token storage found in active code', 'success')
      } else {
        this.log(`Error searching for localStorage usage: ${error.message}`, 'error')
      }
    }
  }

  async validateSecureContextsExist() {
    this.log('Validating secure authentication contexts exist...')
    
    const requiredFiles = [
      'frontend/src/contexts/SecureAuthContext.jsx',
      'frontend/src/contexts/SecureAdminAuthContext.jsx',
      'frontend/src/services/secureApiService.js'
    ]

    for (const file of requiredFiles) {
      const filePath = path.join(__dirname, '..', file)
      if (fs.existsSync(filePath)) {
        this.log(`Secure context file exists: ${file}`, 'success')
      } else {
        this.log(`Missing secure context file: ${file}`, 'error')
      }
    }
  }

  async validateAppUsesSecureContexts() {
    this.log('Validating App.jsx uses secure authentication contexts...')
    
    const appPath = path.join(this.frontendDir, 'src', 'App.jsx')
    if (fs.existsSync(appPath)) {
      const content = fs.readFileSync(appPath, 'utf-8')
      
      if (content.includes("from './contexts/SecureAuthContext'")) {
        this.log('App.jsx imports SecureAuthContext', 'success')
      } else {
        this.log('App.jsx does not import SecureAuthContext', 'error')
      }
      
      if (content.includes("from './contexts/SecureAdminAuthContext'")) {
        this.log('App.jsx imports SecureAdminAuthContext', 'success')
      } else {
        this.log('App.jsx does not import SecureAdminAuthContext', 'error')
      }
    } else {
      this.log('App.jsx not found', 'error')
    }
  }

  async validateSecureApiServiceUsage() {
    this.log('Validating secure API service usage...')
    
    try {
      const searchResult = execSync(
        `grep -r "secureApiService" ${this.frontendDir}/src --exclude-dir=node_modules`,
        { encoding: 'utf-8', stdio: 'pipe' }
      ).trim()
      
      if (searchResult) {
        const lines = searchResult.split('\n')
        this.log(`Found ${lines.length} references to secureApiService`, 'success')
      } else {
        this.log('No references to secureApiService found', 'error')
      }
    } catch (error) {
      if (error.status === 1) {
        this.log('No references to secureApiService found', 'error')
      } else {
        this.log(`Error searching for secureApiService usage: ${error.message}`, 'error')
      }
    }
  }

  async validateBackendSupportsHttpOnlyCookies() {
    this.log('Validating backend supports HTTP-only refresh token cookies...')
    
    const authFiles = [
      'backend/api/auth_open.py',
      'backend/core/security.py'
    ]

    for (const file of authFiles) {
      const filePath = path.join(__dirname, '..', file)
      if (fs.existsSync(filePath)) {
        const content = fs.readFileSync(filePath, 'utf-8')
        
        if (content.includes('httponly=True')) {
          this.log(`${file} contains HTTP-only cookie configuration`, 'success')
        }
        
        if (content.includes('refresh_token')) {
          this.log(`${file} contains refresh token handling`, 'success')
        }
      }
    }
  }

  async validateSecurityDocumentation() {
    this.log('Validating security documentation exists...')
    
    const docFiles = [
      'docs/secure-auth-migration.md'
    ]

    for (const file of docFiles) {
      const filePath = path.join(__dirname, '..', file)
      if (fs.existsSync(filePath)) {
        this.log(`Documentation file exists: ${file}`, 'success')
      } else {
        this.log(`Missing documentation file: ${file}`, 'error')
      }
    }
  }

  async validateMemoryOnlyTokenStorage() {
    this.log('Validating memory-only token storage patterns...')
    
    try {
      // Search for multiple memory-only token patterns
      const patterns = [
        'accessTokenRef',
        'tokenRef',
        'useRef(null)', // General useRef pattern for token storage
        'current.*[Tt]oken'
      ]
      
      let foundPatterns = 0
      for (const pattern of patterns) {
        try {
          const searchResult = execSync(
            `grep -r "${pattern}" ${this.frontendDir}/src/contexts/Secure* --exclude-dir=node_modules`,
            { encoding: 'utf-8', stdio: 'pipe' }
          ).trim()
          
          if (searchResult) {
            foundPatterns++
            this.log(`Found memory-only token pattern: ${pattern}`, 'success')
          }
        } catch (error) {
          // Pattern not found, continue to next
        }
      }
      
      if (foundPatterns === 0) {
        this.log('No memory-only token storage patterns found', 'error')
      }
    } catch (error) {
      this.log(`Error searching for memory-only token patterns: ${error.message}`, 'error')
    }
  }

  async validateAutomaticTokenRefresh() {
    this.log('Validating automatic token refresh implementation...')
    
    const secureApiPath = path.join(this.frontendDir, 'src', 'services', 'secureApiService.js')
    if (fs.existsSync(secureApiPath)) {
      const content = fs.readFileSync(secureApiPath, 'utf-8')
      
      if (content.includes('_refreshAccessToken')) {
        this.log('Secure API service includes automatic token refresh', 'success')
      } else {
        this.log('Secure API service missing automatic token refresh', 'error')
      }
      
      if (content.includes('response.status === 401')) {
        this.log('Secure API service handles 401 unauthorized responses', 'success')
      } else {
        this.log('Secure API service does not handle 401 responses', 'error')
      }
    } else {
      this.log('Secure API service file not found', 'error')
    }
  }

  async validateCsrfProtection() {
    this.log('Validating CSRF protection in secure implementation...')
    
    const secureApiPath = path.join(this.frontendDir, 'src', 'services', 'secureApiService.js')
    if (fs.existsSync(secureApiPath)) {
      const content = fs.readFileSync(secureApiPath, 'utf-8')
      
      if (content.includes('X-CSRF-Token')) {
        this.log('Secure API service includes CSRF protection', 'success')
      } else {
        this.log('Secure API service missing CSRF protection', 'error')
      }
      
      if (content.includes("credentials: 'include'")) {
        this.log('Secure API service includes credentials for HTTP-only cookies', 'success')
      } else {
        this.log('Secure API service missing credentials configuration', 'error')
      }
    }
  }

  generateReport() {
    console.log('\n' + '='.repeat(60))
    console.log('🔒 SECURE AUTHENTICATION VALIDATION REPORT')
    console.log('='.repeat(60))
    
    console.log(`\n📊 Summary:`)
    console.log(`   ✅ Successes: ${this.successes.length}`)
    console.log(`   ❌ Issues: ${this.issues.length}`)
    
    if (this.issues.length === 0) {
      console.log('\n🎉 ALL SECURITY VALIDATIONS PASSED!')
      console.log('✅ P0-13a implementation appears to be secure')
      console.log('✅ Access tokens are no longer stored in localStorage')
      console.log('✅ Secure authentication patterns implemented correctly')
    } else {
      console.log('\n⚠️ SECURITY ISSUES FOUND:')
      this.issues.forEach(issue => {
        console.log(`   • ${issue}`)
      })
      console.log('\n🔧 Please address the above issues before deployment')
    }
    
    console.log('\n' + '='.repeat(60))
    
    return this.issues.length === 0
  }

  async runAllValidations() {
    console.log('🔒 Starting P0-13a Security Validation...')
    console.log('   Task: Move access tokens out of localStorage to mitigate XSS risks')
    console.log('')
    
    await this.validateNoLocalStorageTokens()
    await this.validateSecureContextsExist()
    await this.validateAppUsesSecureContexts()
    await this.validateSecureApiServiceUsage()
    await this.validateBackendSupportsHttpOnlyCookies()
    await this.validateSecurityDocumentation()
    await this.validateMemoryOnlyTokenStorage()
    await this.validateAutomaticTokenRefresh()
    await this.validateCsrfProtection()
    
    return this.generateReport()
  }
}

// Run validation if called directly
if (require.main === module) {
  const validator = new SecureAuthValidator()
  validator.runAllValidations()
    .then(success => {
      process.exit(success ? 0 : 1)
    })
    .catch(error => {
      console.error('❌ Validation failed with error:', error)
      process.exit(1)
    })
}

module.exports = { SecureAuthValidator }