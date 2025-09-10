"""
CI/CD Pipeline Maturity Assessment Service
P0-12a: Conduct current CI/CD pipeline maturity assessment

Assesses the maturity level of CI/CD pipeline practices across multiple dimensions
following industry standards and DevOps best practices.

Maturity Levels:
- Level 0: Ad-hoc (No structured process)
- Level 1: Initial (Basic automation)  
- Level 2: Managed (Standardized processes)
- Level 3: Defined (Comprehensive automation)
- Level 4: Optimized (Continuous improvement)
"""

import json
import logging
import os
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class MaturityLevel(Enum):
    """CI/CD Maturity levels based on industry standards"""
    AD_HOC = 0          # No structured process
    INITIAL = 1         # Basic automation
    MANAGED = 2         # Standardized processes  
    DEFINED = 3         # Comprehensive automation
    OPTIMIZED = 4       # Continuous improvement

@dataclass
class MaturityScore:
    """Individual dimension maturity score"""
    level: MaturityLevel
    score: int          # 0-100 percentage
    evidence: List[str]
    gaps: List[str]
    recommendations: List[str]

@dataclass
class CICDMaturityAssessment:
    """Complete CI/CD maturity assessment result"""
    overall_level: MaturityLevel
    overall_score: int
    dimension_scores: Dict[str, MaturityScore]
    assessment_date: datetime
    project_path: str
    workflow_count: int
    assessment_summary: Dict[str, Any]
    improvement_roadmap: List[Dict[str, Any]]

class CICDMaturityAssessor:
    """
    Comprehensive CI/CD pipeline maturity assessment service
    """
    
    def __init__(self, project_root: Optional[str] = None):
        """Initialize the CI/CD maturity assessor"""
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.workflows_path = self.project_root / ".github" / "workflows"
        self.assessment_dimensions = {
            "source_control": "Source Control & Branching Strategy",
            "build_automation": "Build Automation & Packaging",
            "testing_strategy": "Testing Strategy & Coverage",
            "security_integration": "Security & Compliance Integration",
            "deployment_automation": "Deployment Automation & Strategy", 
            "monitoring_observability": "Monitoring & Observability",
            "environment_management": "Environment Management",
            "rollback_recovery": "Rollback & Recovery Capabilities",
            "pipeline_efficiency": "Pipeline Efficiency & Performance",
            "collaboration_governance": "Collaboration & Governance"
        }
        
    def conduct_full_assessment(self) -> CICDMaturityAssessment:
        """
        Conduct comprehensive CI/CD maturity assessment
        """
        logger.info("Starting CI/CD maturity assessment")
        
        # Analyze existing workflows
        workflow_analysis = self._analyze_workflows()
        
        # Assess each dimension
        dimension_scores = {}
        for dimension_key, dimension_name in self.assessment_dimensions.items():
            score = self._assess_dimension(dimension_key, workflow_analysis)
            dimension_scores[dimension_key] = score
            
        # Calculate overall maturity
        overall_score, overall_level = self._calculate_overall_maturity(dimension_scores)
        
        # Generate improvement roadmap
        roadmap = self._generate_improvement_roadmap(dimension_scores, overall_level)
        
        # Create assessment summary
        summary = self._create_assessment_summary(dimension_scores, workflow_analysis)
        
        assessment = CICDMaturityAssessment(
            overall_level=overall_level,
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            assessment_date=datetime.utcnow(),
            project_path=str(self.project_root),
            workflow_count=len(workflow_analysis.get("workflows", [])),
            assessment_summary=summary,
            improvement_roadmap=roadmap
        )
        
        logger.info(f"CI/CD maturity assessment completed: Level {overall_level.value} ({overall_score}%)")
        return assessment
        
    def _analyze_workflows(self) -> Dict[str, Any]:
        """Analyze GitHub Actions workflows"""
        analysis = {
            "workflows": [],
            "triggers": set(),
            "jobs": [],
            "actions_used": set(),
            "security_features": [],
            "deployment_strategies": [],
            "testing_coverage": {},
            "environment_usage": set()
        }
        
        if not self.workflows_path.exists():
            logger.warning("No .github/workflows directory found")
            return analysis
            
        # Analyze each workflow file
        for workflow_file in self.workflows_path.glob("*.yml"):
            try:
                workflow_content = workflow_file.read_text(encoding='utf-8')
                workflow_analysis = self._analyze_single_workflow(workflow_file.name, workflow_content)
                analysis["workflows"].append(workflow_analysis)
                
                # Aggregate data
                analysis["triggers"].update(workflow_analysis.get("triggers", []))
                analysis["jobs"].extend(workflow_analysis.get("jobs", []))
                analysis["actions_used"].update(workflow_analysis.get("actions_used", []))
                analysis["security_features"].extend(workflow_analysis.get("security_features", []))
                analysis["deployment_strategies"].extend(workflow_analysis.get("deployment_strategies", []))
                analysis["environment_usage"].update(workflow_analysis.get("environments", []))
                
            except Exception as e:
                logger.error(f"Error analyzing workflow {workflow_file.name}: {e}")
                
        # Convert sets to lists for JSON serialization
        analysis["triggers"] = list(analysis["triggers"])
        analysis["actions_used"] = list(analysis["actions_used"])
        analysis["environment_usage"] = list(analysis["environment_usage"])
        
        return analysis
        
    def _analyze_single_workflow(self, filename: str, content: str) -> Dict[str, Any]:
        """Analyze a single workflow file"""
        analysis = {
            "filename": filename,
            "triggers": [],
            "jobs": [],
            "actions_used": [],
            "security_features": [],
            "deployment_strategies": [],
            "environments": [],
            "complexity_score": 0
        }
        
        # Extract triggers
        if "on:" in content or "on :" in content:
            triggers = re.findall(r'on:\s*\n\s*([^:\n]+)', content, re.MULTILINE)
            analysis["triggers"].extend([t.strip() for t in triggers if t.strip()])
            
        # Extract job names
        jobs = re.findall(r'^\s*([a-zA-Z0-9_-]+):\s*$', content, re.MULTILINE)
        analysis["jobs"] = [job for job in jobs if job not in ['on', 'env', 'jobs']]
        
        # Extract actions used
        actions = re.findall(r'uses:\s*([^\s@]+)', content)
        analysis["actions_used"] = list(set(actions))
        
        # Detect security features
        security_patterns = {
            "CodeQL": r'github/codeql-action',
            "Trivy": r'aquasecurity/trivy-action',
            "Security Scanning": r'security-scan|bandit|semgrep',
            "SARIF Upload": r'upload-sarif',
            "Dependency Check": r'safety|npm audit|yarn audit',
            "Secret Scanning": r'gitleaks|truffleHog'
        }
        
        for feature, pattern in security_patterns.items():
            if re.search(pattern, content, re.IGNORECASE):
                analysis["security_features"].append(feature)
                
        # Detect deployment strategies
        deployment_patterns = {
            "Blue-Green": r'blue-green',
            "Canary": r'canary',
            "Rolling": r'rolling',
            "Multi-environment": r'environment.*production|staging|development'
        }
        
        for strategy, pattern in deployment_patterns.items():
            if re.search(pattern, content, re.IGNORECASE):
                analysis["deployment_strategies"].append(strategy)
                
        # Extract environments
        environments = re.findall(r'environment:\s*["\']?([^"\'\s]+)', content)
        analysis["environments"] = list(set(environments))
        
        # Calculate complexity score
        analysis["complexity_score"] = (
            len(analysis["jobs"]) * 10 +
            len(analysis["actions_used"]) * 5 +
            len(analysis["security_features"]) * 15 +
            len(analysis["deployment_strategies"]) * 20
        )
        
        return analysis
        
    def _assess_dimension(self, dimension: str, workflow_analysis: Dict[str, Any]) -> MaturityScore:
        """Assess maturity for a specific dimension"""
        
        assessors = {
            "source_control": self._assess_source_control,
            "build_automation": self._assess_build_automation,
            "testing_strategy": self._assess_testing_strategy,
            "security_integration": self._assess_security_integration,
            "deployment_automation": self._assess_deployment_automation,
            "monitoring_observability": self._assess_monitoring,
            "environment_management": self._assess_environment_management,
            "rollback_recovery": self._assess_rollback_recovery,
            "pipeline_efficiency": self._assess_pipeline_efficiency,
            "collaboration_governance": self._assess_collaboration_governance
        }
        
        assessor = assessors.get(dimension)
        if assessor:
            return assessor(workflow_analysis)
        else:
            return MaturityScore(
                level=MaturityLevel.AD_HOC,
                score=0,
                evidence=[],
                gaps=[f"Unknown dimension: {dimension}"],
                recommendations=[f"Implement assessment for {dimension}"]
            )
            
    def _assess_source_control(self, analysis: Dict[str, Any]) -> MaturityScore:
        """Assess source control maturity"""
        evidence = []
        gaps = []
        score = 0
        
        # Check for Git usage (assumed if .github exists)
        if self.workflows_path.exists():
            evidence.append("Git version control with GitHub Actions")
            score += 20
            
        # Check for branch protection
        triggers = analysis.get("triggers", [])
        if any("pull_request" in str(trigger) for trigger in triggers):
            evidence.append("Pull request workflow protection")
            score += 25
        else:
            gaps.append("No pull request validation workflows")
            
        # Check for multiple branch strategies
        if any("main" in str(trigger) or "master" in str(trigger) for trigger in triggers):
            evidence.append("Main branch protection workflows")
            score += 20
        else:
            gaps.append("No main branch protection workflows")
            
        if any("develop" in str(trigger) or "dev" in str(trigger) for trigger in triggers):
            evidence.append("Development branch workflows")
            score += 15
        else:
            gaps.append("No development branch workflows")
            
        # Check for semantic versioning
        workflows = analysis.get("workflows", [])
        has_versioning = any("tag" in str(workflow) or "version" in str(workflow) 
                           for workflow in workflows)
        if has_versioning:
            evidence.append("Automated versioning workflows")
            score += 20
        else:
            gaps.append("No automated versioning detected")
            
        recommendations = [
            "Implement branch protection rules",
            "Add automated semantic versioning", 
            "Set up commit message standards",
            "Configure merge policies"
        ]
        
        level = self._score_to_level(score)
        
        return MaturityScore(
            level=level,
            score=score,
            evidence=evidence,
            gaps=gaps,
            recommendations=recommendations
        )
        
    def _assess_build_automation(self, analysis: Dict[str, Any]) -> MaturityScore:
        """Assess build automation maturity"""
        evidence = []
        gaps = []
        score = 0
        
        workflows = analysis.get("workflows", [])
        actions_used = analysis.get("actions_used", [])
        
        # Check for build workflows
        build_workflows = [w for w in workflows if "build" in w.get("filename", "").lower()]
        if build_workflows:
            evidence.append(f"{len(build_workflows)} build automation workflows")
            score += 30
        else:
            gaps.append("No dedicated build workflows found")
            
        # Check for containerization
        if any("docker" in str(action).lower() for action in actions_used):
            evidence.append("Docker containerization workflows")
            score += 25
        else:
            gaps.append("No containerization detected")
            
        # Check for multi-language support
        language_actions = [action for action in actions_used 
                          if any(lang in action.lower() for lang in ['python', 'node', 'java', 'go'])]
        if language_actions:
            evidence.append(f"Multi-language build support: {len(set(language_actions))}")
            score += 20
        else:
            gaps.append("Limited language support in build")
            
        # Check for caching
        if any("cache" in str(action).lower() for action in actions_used):
            evidence.append("Build caching optimization")
            score += 15
        else:
            gaps.append("No build caching optimization")
            
        # Check for artifact management
        if any("upload-artifact" in str(action) for action in actions_used):
            evidence.append("Build artifact management")
            score += 10
        else:
            gaps.append("No build artifact management")
            
        recommendations = [
            "Implement parallel build jobs",
            "Add build artifact caching",
            "Set up multi-stage Docker builds",
            "Optimize build performance"
        ]
        
        level = self._score_to_level(score)
        
        return MaturityScore(
            level=level,
            score=score,
            evidence=evidence,
            gaps=gaps,
            recommendations=recommendations
        )
        
    def _assess_testing_strategy(self, analysis: Dict[str, Any]) -> MaturityScore:
        """Assess testing strategy maturity"""
        evidence = []
        gaps = []
        score = 0
        
        workflows = analysis.get("workflows", [])
        
        # Check for test workflows
        test_workflows = [w for w in workflows 
                         if any(keyword in w.get("filename", "").lower() 
                               for keyword in ["test", "ci", "comprehensive"])]
        if test_workflows:
            evidence.append(f"{len(test_workflows)} testing workflows")
            score += 25
            
        # Check for different test types
        test_types = []
        for workflow in workflows:
            content = str(workflow)
            if "unit" in content.lower():
                test_types.append("Unit Tests")
            if "integration" in content.lower():
                test_types.append("Integration Tests")
            if "e2e" in content.lower() or "end-to-end" in content.lower():
                test_types.append("E2E Tests")
            if "performance" in content.lower():
                test_types.append("Performance Tests")
            if "contract" in content.lower():
                test_types.append("Contract Tests")
                
        if test_types:
            evidence.append(f"Multiple test types: {', '.join(set(test_types))}")
            score += len(set(test_types)) * 10
        else:
            gaps.append("No comprehensive testing strategy")
            
        # Check for code coverage
        actions_used = analysis.get("actions_used", [])
        if any("codecov" in str(action).lower() or "coverage" in str(action).lower() 
               for action in actions_used):
            evidence.append("Code coverage tracking")
            score += 15
        else:
            gaps.append("No code coverage tracking")
            
        # Check for test databases
        has_test_db = any("postgres" in str(workflow).lower() or "redis" in str(workflow).lower()
                         for workflow in workflows)
        if has_test_db:
            evidence.append("Test database services")
            score += 10
        else:
            gaps.append("No test database infrastructure")
            
        recommendations = [
            "Implement comprehensive test coverage",
            "Add parallel test execution",
            "Set up test result reporting",
            "Implement test performance monitoring"
        ]
        
        level = self._score_to_level(score)
        
        return MaturityScore(
            level=level,
            score=score,
            evidence=evidence,
            gaps=gaps,
            recommendations=recommendations
        )
        
    def _assess_security_integration(self, analysis: Dict[str, Any]) -> MaturityScore:
        """Assess security integration maturity"""
        evidence = []
        gaps = []
        score = 0
        
        security_features = analysis.get("security_features", [])
        
        if "CodeQL" in security_features:
            evidence.append("CodeQL static analysis")
            score += 20
            
        if "Trivy" in security_features:
            evidence.append("Container vulnerability scanning")
            score += 20
            
        if "Security Scanning" in security_features:
            evidence.append("Additional security scanning tools")
            score += 15
            
        if "SARIF Upload" in security_features:
            evidence.append("SARIF security reporting")
            score += 10
            
        if "Dependency Check" in security_features:
            evidence.append("Dependency vulnerability scanning")
            score += 15
            
        if "Secret Scanning" in security_features:
            evidence.append("Secret scanning protection")
            score += 20
        else:
            gaps.append("No secret scanning detected")
            
        # Check for security workflows
        workflows = analysis.get("workflows", [])
        security_workflows = [w for w in workflows 
                            if "security" in w.get("filename", "").lower()]
        if security_workflows:
            evidence.append(f"{len(security_workflows)} dedicated security workflows")
            score += 10
            
        if not security_features:
            gaps.extend([
                "No automated security scanning",
                "No vulnerability assessment",
                "No compliance checks"
            ])
            
        recommendations = [
            "Implement SAST/DAST scanning",
            "Add dependency vulnerability checks",
            "Set up security baseline monitoring",
            "Implement security gate policies"
        ]
        
        level = self._score_to_level(score)
        
        return MaturityScore(
            level=level,
            score=score,
            evidence=evidence,
            gaps=gaps,
            recommendations=recommendations
        )
        
    def _assess_deployment_automation(self, analysis: Dict[str, Any]) -> MaturityScore:
        """Assess deployment automation maturity"""
        evidence = []
        gaps = []
        score = 0
        
        deployment_strategies = analysis.get("deployment_strategies", [])
        environments = analysis.get("environment_usage", [])
        
        # Check for deployment workflows
        workflows = analysis.get("workflows", [])
        deploy_workflows = [w for w in workflows 
                          if "deploy" in w.get("filename", "").lower()]
        if deploy_workflows:
            evidence.append(f"{len(deploy_workflows)} deployment workflows")
            score += 20
            
        # Check deployment strategies
        if "Blue-Green" in deployment_strategies:
            evidence.append("Blue-green deployment strategy")
            score += 30
        if "Canary" in deployment_strategies:
            evidence.append("Canary deployment strategy") 
            score += 30
        if "Rolling" in deployment_strategies:
            evidence.append("Rolling deployment strategy")
            score += 25
            
        if not deployment_strategies:
            gaps.append("No advanced deployment strategies")
            
        # Check for multi-environment support
        if len(environments) >= 3:
            evidence.append(f"Multi-environment support: {', '.join(environments)}")
            score += 15
        elif len(environments) >= 2:
            evidence.append(f"Basic environment support: {', '.join(environments)}")
            score += 10
        else:
            gaps.append("Limited environment management")
            
        # Check for approval gates
        has_approval = any("workflow_dispatch" in str(workflow) for workflow in workflows)
        if has_approval:
            evidence.append("Manual approval gates")
            score += 10
        else:
            gaps.append("No deployment approval gates")
            
        recommendations = [
            "Implement zero-downtime deployments",
            "Add automated rollback triggers",
            "Set up deployment validation gates",
            "Implement infrastructure as code"
        ]
        
        level = self._score_to_level(score)
        
        return MaturityScore(
            level=level,
            score=score,
            evidence=evidence,
            gaps=gaps,
            recommendations=recommendations
        )
        
    def _assess_monitoring(self, analysis: Dict[str, Any]) -> MaturityScore:
        """Assess monitoring and observability maturity"""
        evidence = []
        gaps = []
        score = 0
        
        workflows = analysis.get("workflows", [])
        
        # Check for monitoring workflows
        monitoring_workflows = [w for w in workflows 
                              if "monitoring" in w.get("filename", "").lower()]
        if monitoring_workflows:
            evidence.append(f"{len(monitoring_workflows)} monitoring workflows")
            score += 20
            
        # Check for observability features
        has_health_checks = any("health" in str(workflow).lower() for workflow in workflows)
        if has_health_checks:
            evidence.append("Automated health checks")
            score += 15
            
        has_performance_tests = any("performance" in str(workflow).lower() for workflow in workflows)
        if has_performance_tests:
            evidence.append("Performance monitoring")
            score += 20
            
        # Check for notification integrations
        has_notifications = any("slack" in str(workflow).lower() or "notification" in str(workflow).lower() 
                              for workflow in workflows)
        if has_notifications:
            evidence.append("Automated notifications")
            score += 15
            
        # Check for metrics collection
        actions_used = analysis.get("actions_used", [])
        has_metrics = any("metric" in str(action).lower() or "grafana" in str(action).lower()
                         for action in actions_used)
        if has_metrics:
            evidence.append("Metrics collection integration")
            score += 20
        else:
            gaps.append("No metrics collection")
            
        # Check for logging
        has_logging = any("log" in str(workflow).lower() for workflow in workflows)
        if has_logging:
            evidence.append("Centralized logging")
            score += 10
        else:
            gaps.append("No centralized logging")
            
        if not evidence:
            gaps.extend([
                "No monitoring automation",
                "No observability integration",
                "No alerting mechanisms"
            ])
            
        recommendations = [
            "Implement comprehensive monitoring",
            "Add distributed tracing",
            "Set up automated alerting",
            "Create monitoring dashboards"
        ]
        
        level = self._score_to_level(score)
        
        return MaturityScore(
            level=level,
            score=score,
            evidence=evidence,
            gaps=gaps,
            recommendations=recommendations
        )
        
    def _assess_environment_management(self, analysis: Dict[str, Any]) -> MaturityScore:
        """Assess environment management maturity"""
        evidence = []
        gaps = []
        score = 0
        
        environments = analysis.get("environment_usage", [])
        workflows = analysis.get("workflows", [])
        
        # Environment variety
        if "production" in environments:
            evidence.append("Production environment management")
            score += 25
        if "staging" in environments:
            evidence.append("Staging environment")
            score += 20  
        if "development" in environments or "dev" in environments:
            evidence.append("Development environment")
            score += 15
        if "testing" in environments or "test" in environments:
            evidence.append("Testing environment")
            score += 15
            
        # Infrastructure as Code
        iac_actions = [action for action in analysis.get("actions_used", [])
                      if any(iac in action.lower() for iac in ["terraform", "aws", "azure", "gcp"])]
        if iac_actions:
            evidence.append(f"Infrastructure automation: {len(iac_actions)} tools")
            score += 20
        else:
            gaps.append("No infrastructure as code")
            
        # Environment isolation
        if len(environments) >= 3:
            evidence.append("Multiple environment isolation")
            score += 15
        elif len(environments) == 0:
            gaps.append("No environment management")
            
        recommendations = [
            "Implement environment parity",
            "Add infrastructure as code",
            "Set up environment promotion",
            "Implement environment security"
        ]
        
        level = self._score_to_level(score)
        
        return MaturityScore(
            level=level,
            score=score,
            evidence=evidence,
            gaps=gaps,
            recommendations=recommendations
        )
        
    def _assess_rollback_recovery(self, analysis: Dict[str, Any]) -> MaturityScore:
        """Assess rollback and recovery capabilities"""
        evidence = []
        gaps = []
        score = 0
        
        workflows = analysis.get("workflows", [])
        
        # Check for rollback workflows
        rollback_workflows = [w for w in workflows 
                            if "rollback" in w.get("filename", "").lower()]
        if rollback_workflows:
            evidence.append(f"{len(rollback_workflows)} rollback workflows")
            score += 30
        else:
            gaps.append("No automated rollback workflows")
            
        # Check for backup workflows  
        backup_workflows = [w for w in workflows 
                          if "backup" in w.get("filename", "").lower()]
        if backup_workflows:
            evidence.append(f"{len(backup_workflows)} backup workflows")
            score += 20
        else:
            gaps.append("No automated backup procedures")
            
        # Check for recovery testing
        recovery_workflows = [w for w in workflows 
                            if "recovery" in w.get("filename", "").lower()]
        if recovery_workflows:
            evidence.append("Disaster recovery testing")
            score += 25
        else:
            gaps.append("No disaster recovery testing")
            
        # Check for deployment validation
        has_validation = any("validation" in str(workflow).lower() or "smoke" in str(workflow).lower()
                           for workflow in workflows)
        if has_validation:
            evidence.append("Deployment validation checks")
            score += 15
        else:
            gaps.append("No deployment validation")
            
        # Check for monitoring integration
        has_monitoring = any("monitor" in str(workflow).lower() for workflow in workflows)
        if has_monitoring:
            evidence.append("Automated failure detection")
            score += 10
        else:
            gaps.append("No automated failure detection")
            
        recommendations = [
            "Implement automated rollback triggers",
            "Add deployment validation gates",
            "Set up disaster recovery procedures",
            "Implement backup verification"
        ]
        
        level = self._score_to_level(score)
        
        return MaturityScore(
            level=level,
            score=score,
            evidence=evidence,
            gaps=gaps,
            recommendations=recommendations
        )
        
    def _assess_pipeline_efficiency(self, analysis: Dict[str, Any]) -> MaturityScore:
        """Assess pipeline efficiency and performance"""
        evidence = []
        gaps = []
        score = 0
        
        workflows = analysis.get("workflows", [])
        actions_used = analysis.get("actions_used", [])
        
        # Check for parallel execution
        parallel_jobs = sum(len(w.get("jobs", [])) for w in workflows if len(w.get("jobs", [])) > 1)
        if parallel_jobs > 10:
            evidence.append(f"High parallelization: {parallel_jobs} parallel jobs")
            score += 25
        elif parallel_jobs > 5:
            evidence.append(f"Moderate parallelization: {parallel_jobs} parallel jobs")
            score += 15
        else:
            gaps.append("Limited parallel execution")
            
        # Check for caching
        if any("cache" in str(action).lower() for action in actions_used):
            evidence.append("Build and dependency caching")
            score += 20
        else:
            gaps.append("No caching optimization")
            
        # Check for conditional execution
        has_conditions = any("if:" in str(workflow) for workflow in workflows)
        if has_conditions:
            evidence.append("Conditional workflow execution")
            score += 15
        else:
            gaps.append("No conditional execution optimization")
            
        # Check for matrix builds
        has_matrix = any("matrix" in str(workflow).lower() for workflow in workflows)
        if has_matrix:
            evidence.append("Matrix build strategies")
            score += 20
        else:
            gaps.append("No matrix build optimization")
            
        # Check workflow complexity (efficiency through automation)
        total_complexity = sum(w.get("complexity_score", 0) for w in workflows)
        if total_complexity > 1000:
            evidence.append(f"High automation complexity: {total_complexity}")
            score += 20
        elif total_complexity > 500:
            evidence.append(f"Moderate automation: {total_complexity}")
            score += 10
        else:
            gaps.append("Limited automation complexity")
            
        recommendations = [
            "Optimize pipeline execution time",
            "Implement intelligent caching",
            "Add parallel job execution",
            "Set up pipeline performance monitoring"
        ]
        
        level = self._score_to_level(score)
        
        return MaturityScore(
            level=level,
            score=score,
            evidence=evidence,
            gaps=gaps,
            recommendations=recommendations
        )
        
    def _assess_collaboration_governance(self, analysis: Dict[str, Any]) -> MaturityScore:
        """Assess collaboration and governance maturity"""
        evidence = []
        gaps = []
        score = 0
        
        workflows = analysis.get("workflows", [])
        triggers = analysis.get("triggers", [])
        
        # Check for PR workflows
        if "pull_request" in str(triggers):
            evidence.append("Pull request automation")
            score += 20
            
        # Check for code review automation
        has_review_automation = any("review" in str(workflow).lower() or "quality" in str(workflow).lower()
                                  for workflow in workflows)
        if has_review_automation:
            evidence.append("Automated code review")
            score += 15
            
        # Check for compliance workflows
        compliance_workflows = [w for w in workflows 
                              if "compliance" in w.get("filename", "").lower()]
        if compliance_workflows:
            evidence.append("Compliance automation")
            score += 20
        else:
            gaps.append("No compliance automation")
            
        # Check for documentation workflows
        doc_workflows = [w for w in workflows 
                        if any(doc in w.get("filename", "").lower() 
                              for doc in ["doc", "api", "schema"])]
        if doc_workflows:
            evidence.append("Documentation automation")
            score += 15
        else:
            gaps.append("No documentation automation")
            
        # Check for notification systems
        has_notifications = any("slack" in str(workflow).lower() or "notification" in str(workflow).lower()
                              for workflow in workflows)
        if has_notifications:
            evidence.append("Team notification systems")
            score += 10
            
        # Check for approval gates
        has_approval = any("workflow_dispatch" in str(workflow) for workflow in workflows)
        if has_approval:
            evidence.append("Manual approval processes")
            score += 10
        else:
            gaps.append("No governance approval gates")
            
        # Check for multiple triggers (complexity of collaboration)
        if len(triggers) >= 5:
            evidence.append(f"Multiple collaboration triggers: {len(triggers)}")
            score += 10
        elif len(triggers) == 0:
            gaps.append("No automated collaboration triggers")
            
        recommendations = [
            "Implement automated code reviews",
            "Add compliance checking",
            "Set up team notifications",
            "Create governance policies"
        ]
        
        level = self._score_to_level(score)
        
        return MaturityScore(
            level=level,
            score=score,
            evidence=evidence,
            gaps=gaps,
            recommendations=recommendations
        )
        
    def _score_to_level(self, score: int) -> MaturityLevel:
        """Convert numeric score to maturity level"""
        if score >= 80:
            return MaturityLevel.OPTIMIZED
        elif score >= 60:
            return MaturityLevel.DEFINED
        elif score >= 40:
            return MaturityLevel.MANAGED
        elif score >= 20:
            return MaturityLevel.INITIAL
        else:
            return MaturityLevel.AD_HOC
            
    def _calculate_overall_maturity(self, dimension_scores: Dict[str, MaturityScore]) -> Tuple[int, MaturityLevel]:
        """Calculate overall maturity level"""
        if not dimension_scores:
            return 0, MaturityLevel.AD_HOC
            
        # Weighted average (some dimensions are more critical)
        weights = {
            "source_control": 0.10,
            "build_automation": 0.15,
            "testing_strategy": 0.15,
            "security_integration": 0.15,
            "deployment_automation": 0.15,
            "monitoring_observability": 0.10,
            "environment_management": 0.05,
            "rollback_recovery": 0.05,
            "pipeline_efficiency": 0.05,
            "collaboration_governance": 0.05
        }
        
        weighted_score = 0
        total_weight = 0
        
        for dimension, score_obj in dimension_scores.items():
            weight = weights.get(dimension, 0.05)
            weighted_score += score_obj.score * weight
            total_weight += weight
            
        overall_score = int(weighted_score / total_weight) if total_weight > 0 else 0
        overall_level = self._score_to_level(overall_score)
        
        return overall_score, overall_level
        
    def _generate_improvement_roadmap(self, dimension_scores: Dict[str, MaturityScore], 
                                    overall_level: MaturityLevel) -> List[Dict[str, Any]]:
        """Generate improvement roadmap based on assessment"""
        roadmap = []
        
        # Priority order for improvements
        priority_dimensions = [
            "security_integration",
            "testing_strategy", 
            "deployment_automation",
            "build_automation",
            "monitoring_observability",
            "rollback_recovery",
            "environment_management",
            "pipeline_efficiency",
            "source_control",
            "collaboration_governance"
        ]
        
        for dimension in priority_dimensions:
            if dimension in dimension_scores:
                score_obj = dimension_scores[dimension]
                
                # Focus on dimensions below Defined level
                if score_obj.level.value < MaturityLevel.DEFINED.value and score_obj.recommendations:
                    roadmap_item = {
                        "dimension": dimension,
                        "current_level": score_obj.level.name,
                        "current_score": score_obj.score,
                        "target_level": "DEFINED" if score_obj.level.value < 3 else "OPTIMIZED",
                        "priority": "HIGH" if score_obj.score < 40 else "MEDIUM",
                        "effort_estimate": "2-4 weeks" if score_obj.score < 20 else "1-2 weeks",
                        "recommendations": score_obj.recommendations[:3],  # Top 3
                        "gaps": score_obj.gaps[:3],  # Top 3 gaps
                        "business_impact": self._get_business_impact(dimension, score_obj.level)
                    }
                    roadmap.append(roadmap_item)
                    
        # Limit to top 8 items
        return roadmap[:8]
        
    def _get_business_impact(self, dimension: str, level: MaturityLevel) -> str:
        """Get business impact description for improvement"""
        impact_map = {
            "security_integration": "Reduce security vulnerabilities and compliance risks",
            "testing_strategy": "Improve software quality and reduce production bugs",
            "deployment_automation": "Faster time-to-market and reduced deployment risks",
            "build_automation": "Improved developer productivity and faster releases",
            "monitoring_observability": "Better system reliability and faster incident resolution",
            "rollback_recovery": "Minimize downtime and business disruption",
            "environment_management": "Consistent deployments and reduced environment drift",
            "pipeline_efficiency": "Reduced CI/CD costs and faster feedback loops",
            "source_control": "Better code collaboration and change tracking",
            "collaboration_governance": "Improved team efficiency and compliance"
        }
        
        base_impact = impact_map.get(dimension, "General process improvement")
        
        if level.value < MaturityLevel.INITIAL.value:
            return f"Critical: {base_impact}"
        elif level.value < MaturityLevel.MANAGED.value:
            return f"High: {base_impact}"
        else:
            return f"Medium: {base_impact}"
            
    def _create_assessment_summary(self, dimension_scores: Dict[str, MaturityScore], 
                                 workflow_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create comprehensive assessment summary"""
        
        # Calculate statistics
        total_evidence = sum(len(score.evidence) for score in dimension_scores.values())
        total_gaps = sum(len(score.gaps) for score in dimension_scores.values())
        total_recommendations = sum(len(score.recommendations) for score in dimension_scores.values())
        
        # Get level distribution
        level_distribution = {}
        for level in MaturityLevel:
            count = sum(1 for score in dimension_scores.values() if score.level == level)
            level_distribution[level.name] = count
            
        # Identify strengths and weaknesses
        strengths = []
        weaknesses = []
        
        for dimension, score_obj in dimension_scores.items():
            if score_obj.score >= 70:
                strengths.append({
                    "dimension": dimension,
                    "score": score_obj.score,
                    "level": score_obj.level.name
                })
            elif score_obj.score < 40:
                weaknesses.append({
                    "dimension": dimension, 
                    "score": score_obj.score,
                    "level": score_obj.level.name,
                    "top_gap": score_obj.gaps[0] if score_obj.gaps else "Multiple gaps"
                })
                
        return {
            "assessment_date": datetime.utcnow().isoformat(),
            "total_workflows": len(workflow_analysis.get("workflows", [])),
            "total_jobs": len(workflow_analysis.get("jobs", [])),
            "unique_actions": len(workflow_analysis.get("actions_used", [])),
            "security_features_count": len(workflow_analysis.get("security_features", [])),
            "environments_count": len(workflow_analysis.get("environment_usage", [])),
            "deployment_strategies_count": len(workflow_analysis.get("deployment_strategies", [])),
            "evidence_count": total_evidence,
            "gaps_count": total_gaps,
            "recommendations_count": total_recommendations,
            "maturity_level_distribution": level_distribution,
            "top_strengths": strengths[:3],
            "top_weaknesses": weaknesses[:3],
            "workflow_complexity": sum(w.get("complexity_score", 0) for w in workflow_analysis.get("workflows", []))
        }
        
    def export_assessment_report(self, assessment: CICDMaturityAssessment, 
                               output_path: Optional[str] = None) -> str:
        """Export assessment as JSON report"""
        if not output_path:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_path = f"cicd_maturity_assessment_{timestamp}.json"
            
        # Convert assessment to dict for JSON serialization
        report_data = {
            "assessment_metadata": {
                "overall_level": assessment.overall_level.name,
                "overall_score": assessment.overall_score,
                "assessment_date": assessment.assessment_date.isoformat(),
                "project_path": assessment.project_path,
                "workflow_count": assessment.workflow_count
            },
            "dimension_assessments": {
                dimension: {
                    "level": score.level.name,
                    "score": score.score,
                    "evidence": score.evidence,
                    "gaps": score.gaps,
                    "recommendations": score.recommendations
                }
                for dimension, score in assessment.dimension_scores.items()
            },
            "improvement_roadmap": assessment.improvement_roadmap,
            "assessment_summary": assessment.assessment_summary
        }
        
        # Write JSON report
        output_file = Path(output_path)
        output_file.write_text(json.dumps(report_data, indent=2), encoding='utf-8')
        
        logger.info(f"CI/CD maturity assessment report exported to {output_path}")
        return str(output_file)


# Service factory function
def get_cicd_maturity_assessor(project_root: Optional[str] = None) -> CICDMaturityAssessor:
    """Get CI/CD maturity assessor instance"""
    return CICDMaturityAssessor(project_root)


# Export key classes and functions
__all__ = [
    'CICDMaturityAssessor',
    'CICDMaturityAssessment',
    'MaturityScore',
    'MaturityLevel',
    'get_cicd_maturity_assessor'
]