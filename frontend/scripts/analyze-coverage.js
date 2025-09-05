#!/usr/bin/env node

const fs = require('fs')
const path = require('path')

/**
 * Analyze test coverage and generate actionable recommendations
 */
function analyzeCoverage() {
  const coverageFile = path.join(process.cwd(), 'coverage', 'coverage-summary.json')
  
  if (!fs.existsSync(coverageFile)) {
    console.error('❌ Coverage file not found. Run tests with coverage first: npm run test:coverage')
    process.exit(1)
  }

  const coverage = JSON.parse(fs.readFileSync(coverageFile, 'utf8'))
  const { total } = coverage

  console.log('\n📊 Test Coverage Analysis')
  console.log('=========================')
  
  // Overall statistics
  console.log(`\n📈 Overall Coverage:`)
  console.log(`  Lines:      ${total.lines.pct}% (${total.lines.covered}/${total.lines.total})`)
  console.log(`  Functions:  ${total.functions.pct}% (${total.functions.covered}/${total.functions.total})`)
  console.log(`  Branches:   ${total.branches.pct}% (${total.branches.covered}/${total.branches.total})`)
  console.log(`  Statements: ${total.statements.pct}% (${total.statements.covered}/${total.statements.total})`)

  // Quality assessment
  const linesCoverage = parseFloat(total.lines.pct)
  const functionsCoverage = parseFloat(total.functions.pct)
  const branchesCoverage = parseFloat(total.branches.pct)
  
  console.log(`\n🎯 Quality Assessment:`)
  
  if (linesCoverage >= 80) {
    console.log('  ✅ Excellent line coverage')
  } else if (linesCoverage >= 70) {
    console.log('  ⚠️  Good line coverage, room for improvement')
  } else {
    console.log('  ❌ Line coverage needs improvement')
  }
  
  if (functionsCoverage >= 85) {
    console.log('  ✅ Excellent function coverage')
  } else if (functionsCoverage >= 75) {
    console.log('  ⚠️  Good function coverage, room for improvement') 
  } else {
    console.log('  ❌ Function coverage needs improvement')
  }
  
  if (branchesCoverage >= 75) {
    console.log('  ✅ Excellent branch coverage')
  } else if (branchesCoverage >= 65) {
    console.log('  ⚠️  Good branch coverage, room for improvement')
  } else {
    console.log('  ❌ Branch coverage needs improvement')
  }

  // File-by-file analysis
  console.log(`\n📁 Files needing attention:`)
  
  const files = Object.entries(coverage)
    .filter(([path]) => path !== 'total')
    .filter(([, data]) => data.lines.pct < 70)
    .sort(([, a], [, b]) => a.lines.pct - b.lines.pct)
    .slice(0, 10)

  if (files.length === 0) {
    console.log('  ✅ All files meet minimum coverage threshold!')
  } else {
    files.forEach(([filePath, data]) => {
      const relativePath = filePath.replace(process.cwd(), '.')
      console.log(`  📄 ${relativePath}: ${data.lines.pct}% lines covered`)
    })
  }

  // Recommendations
  console.log(`\n💡 Recommendations:`)
  
  if (linesCoverage < 75) {
    console.log('  • Add unit tests for utility functions and helper methods')
    console.log('  • Focus on testing edge cases and error conditions')
  }
  
  if (functionsCoverage < 80) {
    console.log('  • Test all exported functions and class methods')
    console.log('  • Add tests for event handlers and callbacks')
  }
  
  if (branchesCoverage < 70) {
    console.log('  • Test all conditional branches (if/else, switch cases)')
    console.log('  • Add tests for error handling paths')
    console.log('  • Test different prop combinations for React components')
  }

  // Exit with appropriate code
  const meetsThreshold = linesCoverage >= 70 && functionsCoverage >= 75 && branchesCoverage >= 65
  
  console.log(`\n${meetsThreshold ? '✅' : '❌'} Coverage ${meetsThreshold ? 'meets' : 'does not meet'} quality thresholds`)
  
  process.exit(meetsThreshold ? 0 : 1)
}

if (require.main === module) {
  analyzeCoverage()
}

module.exports = { analyzeCoverage }