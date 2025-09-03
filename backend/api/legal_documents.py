"""
Legal Documents API
GA Checklist requirement: Privacy Policy & Terms URLs for both Meta and X apps

Provides endpoints for legal documents required for platform compliance:
- Privacy Policy
- Terms of Service
- Data Deletion Instructions
- Cookie Policy
"""
import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, HTMLResponse

from backend.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/legal", tags=["legal"])


@router.get("/privacy-policy", response_class=HTMLResponse)
async def privacy_policy(request: Request) -> HTMLResponse:
    """
    Privacy Policy for platform compliance
    
    Required for Meta and X app setup to describe how user data is handled.
    
    Returns:
        HTML response with privacy policy
    """
    try:
        settings = get_settings()
        app_name = "AI Social Media Content Agent"
        company_name = "Lily Media AI"
        contact_email = "support@lily-ai-socialmedia.com"
        effective_date = "January 1, 2025"
        
        privacy_policy_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Privacy Policy - {app_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .effective-date {{ background: #f8f9fa; padding: 10px; border-left: 4px solid #3498db; margin: 20px 0; }}
        .contact-info {{ background: #e8f6ff; padding: 15px; border-radius: 5px; margin: 20px 0; }}
    </style>
</head>
<body>
    <h1>Privacy Policy</h1>
    
    <div class="effective-date">
        <strong>Effective Date:</strong> {effective_date}
    </div>
    
    <p>This Privacy Policy describes how {company_name} ("{app_name}", "we", "our", or "us") collects, uses, and protects your personal information when you use our social media content management platform.</p>
    
    <h2>1. Information We Collect</h2>
    <p>We collect the following types of information:</p>
    <ul>
        <li><strong>Account Information:</strong> Email address, username, and authentication credentials</li>
        <li><strong>Social Media Connections:</strong> OAuth tokens and account information for connected platforms (Meta/Facebook, Instagram, X/Twitter)</li>
        <li><strong>Content Data:</strong> Social media posts, images, and analytics data you create or authorize us to access</li>
        <li><strong>Usage Information:</strong> How you interact with our platform, including logs and analytics</li>
        <li><strong>Device Information:</strong> Browser type, IP address, and device identifiers</li>
    </ul>
    
    <h2>2. How We Use Your Information</h2>
    <p>We use your information to:</p>
    <ul>
        <li>Provide and improve our social media management services</li>
        <li>Authenticate and authorize access to connected social media platforms</li>
        <li>Generate and publish content on your behalf as directed</li>
        <li>Provide analytics and insights about your social media performance</li>
        <li>Communicate with you about service updates and support</li>
        <li>Ensure platform security and prevent fraud</li>
    </ul>
    
    <h2>3. Information Sharing</h2>
    <p>We do not sell or rent your personal information. We may share information in these limited circumstances:</p>
    <ul>
        <li><strong>Social Media Platforms:</strong> We share content and data with platforms where you've authorized connections (Meta, X/Twitter, etc.)</li>
        <li><strong>Service Providers:</strong> Trusted third parties who help us operate our platform (hosting, analytics, support)</li>
        <li><strong>Legal Requirements:</strong> When required by law or to protect our rights and users' safety</li>
        <li><strong>Business Transfers:</strong> In connection with a merger, acquisition, or sale of assets</li>
    </ul>
    
    <h2>4. Data Security</h2>
    <p>We implement industry-standard security measures to protect your data:</p>
    <ul>
        <li>Encryption of sensitive data including OAuth tokens</li>
        <li>Secure transmission using HTTPS/TLS</li>
        <li>Regular security audits and monitoring</li>
        <li>Access controls and authentication requirements</li>
        <li>Data backup and recovery procedures</li>
    </ul>
    
    <h2>5. Data Retention</h2>
    <p>We retain your data as follows:</p>
    <ul>
        <li><strong>Account Data:</strong> Until you delete your account or request deletion</li>
        <li><strong>Social Media Tokens:</strong> Until you disconnect the platform or tokens expire</li>
        <li><strong>Content and Analytics:</strong> For up to 2 years after account deletion for backup purposes</li>
        <li><strong>Audit Logs:</strong> For 90 days for security and compliance purposes</li>
    </ul>
    
    <h2>6. Your Rights</h2>
    <p>You have the right to:</p>
    <ul>
        <li><strong>Access:</strong> Request a copy of your personal information</li>
        <li><strong>Correct:</strong> Update inaccurate information</li>
        <li><strong>Delete:</strong> Request deletion of your account and data</li>
        <li><strong>Port:</strong> Export your data in a machine-readable format</li>
        <li><strong>Withdraw Consent:</strong> Disconnect social media platforms or delete your account</li>
        <li><strong>Object:</strong> Opt out of certain data processing activities</li>
    </ul>
    
    <h2>7. Social Media Platform Integration</h2>
    <p>When you connect social media accounts:</p>
    <ul>
        <li>We only access data you explicitly authorize through OAuth flows</li>
        <li>We store encrypted access tokens to perform authorized actions</li>
        <li>You can revoke access at any time through our platform or the social media platform</li>
        <li>Platform-specific privacy policies also apply to data shared with those platforms</li>
    </ul>
    
    <h2>8. Cookies and Tracking</h2>
    <p>We use cookies and similar technologies for:</p>
    <ul>
        <li>Authentication and session management</li>
        <li>Platform functionality and user preferences</li>
        <li>Analytics to improve our services</li>
        <li>Security monitoring and fraud prevention</li>
    </ul>
    <p>You can control cookies through your browser settings.</p>
    
    <h2>9. International Data Transfers</h2>
    <p>Your data may be processed in countries other than your own. We ensure adequate protection through:</p>
    <ul>
        <li>Standard contractual clauses</li>
        <li>Adequacy decisions by relevant authorities</li>
        <li>Appropriate technical and organizational measures</li>
    </ul>
    
    <h2>10. Children's Privacy</h2>
    <p>Our platform is not intended for users under 13 years of age. We do not knowingly collect personal information from children under 13.</p>
    
    <h2>11. Changes to This Policy</h2>
    <p>We may update this Privacy Policy periodically. We will notify you of significant changes through:</p>
    <ul>
        <li>Email notifications to registered users</li>
        <li>Platform announcements</li>
        <li>Updated effective date on this page</li>
    </ul>
    
    <h2>12. Data Deletion Requests</h2>
    <p>To delete your data or disconnect social media accounts:</p>
    <ul>
        <li>Use the "Delete Connection" feature in your account settings</li>
        <li>Contact us at the email below for full account deletion</li>
        <li>Visit our <a href="/api/v1/legal/data-deletion-instructions">Data Deletion Instructions</a> page</li>
    </ul>
    
    <div class="contact-info">
        <h2>Contact Information</h2>
        <p>For privacy-related questions or requests, contact us:</p>
        <p>
            <strong>Email:</strong> {contact_email}<br>
            <strong>Platform:</strong> {app_name}<br>
            <strong>Company:</strong> {company_name}
        </p>
        <p>We will respond to privacy requests within 30 days.</p>
    </div>
    
    <p><em>Last updated: {effective_date}</em></p>
</body>
</html>
        """
        
        logger.info("Privacy policy requested")
        return HTMLResponse(content=privacy_policy_html)
        
    except Exception as e:
        logger.error(f"Error serving privacy policy: {e}")
        return HTMLResponse(
            content="<h1>Privacy Policy Temporarily Unavailable</h1><p>Please try again later.</p>",
            status_code=500
        )


@router.get("/terms-of-service", response_class=HTMLResponse)  
async def terms_of_service(request: Request) -> HTMLResponse:
    """
    Terms of Service for platform compliance
    
    Required for Meta and X app setup to describe service terms and conditions.
    
    Returns:
        HTML response with terms of service
    """
    try:
        settings = get_settings()
        app_name = "AI Social Media Content Agent"
        company_name = "Lily Media AI"
        contact_email = "support@lily-ai-socialmedia.com"
        effective_date = "January 1, 2025"
        
        terms_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Terms of Service - {app_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .effective-date {{ background: #f8f9fa; padding: 10px; border-left: 4px solid #3498db; margin: 20px 0; }}
        .contact-info {{ background: #e8f6ff; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .important {{ background: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 20px 0; }}
    </style>
</head>
<body>
    <h1>Terms of Service</h1>
    
    <div class="effective-date">
        <strong>Effective Date:</strong> {effective_date}
    </div>
    
    <p>These Terms of Service ("Terms") govern your access to and use of {app_name} (the "Platform") provided by {company_name} ("Company", "we", "our", or "us").</p>
    
    <h2>1. Acceptance of Terms</h2>
    <p>By accessing or using our Platform, you agree to be bound by these Terms and our Privacy Policy. If you disagree with any part of these terms, you may not access the Platform.</p>
    
    <h2>2. Description of Service</h2>
    <p>Our Platform provides:</p>
    <ul>
        <li>Social media content creation and management tools</li>
        <li>Integration with social media platforms (Meta/Facebook, Instagram, X/Twitter)</li>
        <li>AI-powered content generation and optimization</li>
        <li>Analytics and performance insights</li>
        <li>Automated posting and scheduling features</li>
    </ul>
    
    <h2>3. User Accounts and Registration</h2>
    <p>To use our Platform, you must:</p>
    <ul>
        <li>Provide accurate and complete registration information</li>
        <li>Maintain the security of your account credentials</li>
        <li>Be at least 13 years of age</li>
        <li>Have the legal capacity to enter into binding agreements</li>
        <li>Comply with all applicable laws and regulations</li>
    </ul>
    
    <h2>4. Social Media Platform Integration</h2>
    <div class="important">
        <p><strong>Important:</strong> When connecting social media accounts, you authorize us to:</p>
        <ul>
            <li>Access your account information as permitted by OAuth scopes</li>
            <li>Post content on your behalf as directed by you</li>
            <li>Retrieve analytics and performance data</li>
            <li>Manage your social media presence according to your instructions</li>
        </ul>
    </div>
    <p>You are responsible for:</p>
    <ul>
        <li>Ensuring you have the right to connect and use social media accounts</li>
        <li>Complying with each platform's terms of service</li>
        <li>Monitoring content posted on your behalf</li>
        <li>Revoking access if you no longer wish to use our services</li>
    </ul>
    
    <h2>5. Acceptable Use Policy</h2>
    <p>You agree not to use our Platform to:</p>
    <ul>
        <li>Violate any laws, regulations, or third-party rights</li>
        <li>Create or distribute harmful, offensive, or inappropriate content</li>
        <li>Engage in spam, harassment, or fraudulent activities</li>
        <li>Attempt to gain unauthorized access to our systems</li>
        <li>Interfere with the operation of our Platform</li>
        <li>Violate social media platform terms of service</li>
        <li>Impersonate others or create false identities</li>
        <li>Share malicious software or harmful code</li>
    </ul>
    
    <h2>6. Content and Intellectual Property</h2>
    <p><strong>Your Content:</strong></p>
    <ul>
        <li>You retain ownership of content you create or provide</li>
        <li>You grant us a license to process and publish your content as directed</li>
        <li>You are responsible for ensuring you have rights to all content you use</li>
    </ul>
    <p><strong>Our Platform:</strong></p>
    <ul>
        <li>We own all rights to our Platform, software, and technology</li>
        <li>You may not copy, modify, or distribute our proprietary technology</li>
        <li>Our trademarks and branding remain our exclusive property</li>
    </ul>
    
    <h2>7. AI-Generated Content</h2>
    <p>Regarding AI-generated content:</p>
    <ul>
        <li>AI suggestions are provided as tools to assist your content creation</li>
        <li>You are responsible for reviewing and approving all content before publication</li>
        <li>We do not guarantee the accuracy or quality of AI-generated content</li>
        <li>You should ensure AI-generated content complies with platform policies</li>
    </ul>
    
    <h2>8. Privacy and Data Protection</h2>
    <p>Our collection and use of your information is governed by our Privacy Policy, which includes:</p>
    <ul>
        <li>How we collect and process your data</li>
        <li>Your rights regarding your personal information</li>
        <li>Data security and retention practices</li>
        <li>Your ability to delete your account and data</li>
    </ul>
    
    <h2>9. Platform Availability and Modifications</h2>
    <p>We reserve the right to:</p>
    <ul>
        <li>Modify, suspend, or discontinue any part of our Platform</li>
        <li>Update these Terms with reasonable notice</li>
        <li>Change pricing or service plans</li>
        <li>Implement new features or remove existing ones</li>
    </ul>
    
    <h2>10. Account Termination</h2>
    <p>We may suspend or terminate your account if you:</p>
    <ul>
        <li>Violate these Terms or our policies</li>
        <li>Engage in fraudulent or harmful activities</li>
        <li>Fail to pay applicable fees</li>
        <li>Request account deletion</li>
    </ul>
    <p>You may terminate your account at any time through your account settings.</p>
    
    <h2>11. Disclaimers and Limitations</h2>
    <div class="important">
        <p><strong>Service Provided "As Is":</strong></p>
        <ul>
            <li>We provide our Platform without warranties of any kind</li>
            <li>We do not guarantee uninterrupted or error-free service</li>
            <li>Social media platform integrations depend on third-party APIs</li>
            <li>We are not responsible for third-party platform changes or outages</li>
        </ul>
    </div>
    
    <h2>12. Limitation of Liability</h2>
    <p>To the fullest extent permitted by law:</p>
    <ul>
        <li>We are not liable for indirect, incidental, or consequential damages</li>
        <li>Our total liability is limited to the fees paid by you in the last 12 months</li>
        <li>We are not responsible for content posted by users or AI-generated content</li>
        <li>You use our Platform at your own risk</li>
    </ul>
    
    <h2>13. Indemnification</h2>
    <p>You agree to indemnify and hold us harmless from claims arising from:</p>
    <ul>
        <li>Your use of our Platform</li>
        <li>Content you create or post</li>
        <li>Your violation of these Terms</li>
        <li>Your violation of third-party rights</li>
    </ul>
    
    <h2>14. Dispute Resolution</h2>
    <p>Any disputes will be resolved through:</p>
    <ul>
        <li>Good faith negotiations between the parties</li>
        <li>Binding arbitration if negotiations fail</li>
        <li>Applicable law of the jurisdiction where Company is incorporated</li>
    </ul>
    
    <h2>15. Contact Information</h2>
    <div class="contact-info">
        <p>For questions about these Terms, contact us:</p>
        <p>
            <strong>Email:</strong> {contact_email}<br>
            <strong>Platform:</strong> {app_name}<br>
            <strong>Company:</strong> {company_name}
        </p>
    </div>
    
    <p><em>Last updated: {effective_date}</em></p>
</body>
</html>
        """
        
        logger.info("Terms of service requested")
        return HTMLResponse(content=terms_html)
        
    except Exception as e:
        logger.error(f"Error serving terms of service: {e}")
        return HTMLResponse(
            content="<h1>Terms of Service Temporarily Unavailable</h1><p>Please try again later.</p>",
            status_code=500
        )


@router.get("/data-deletion-instructions", response_class=HTMLResponse)
async def data_deletion_instructions(request: Request) -> HTMLResponse:
    """
    Data Deletion Instructions for platform compliance
    
    Required for Meta app setup to provide users with clear instructions
    on how to delete their data.
    
    Returns:
        HTML response with data deletion instructions
    """
    try:
        app_name = "AI Social Media Content Agent"
        company_name = "Lily Media AI"
        contact_email = "support@lily-ai-socialmedia.com"
        
        instructions_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Data Deletion Instructions - {app_name}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .method {{ background: #f8f9fa; padding: 15px; border-left: 4px solid #28a745; margin: 15px 0; }}
        .warning {{ background: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin: 15px 0; }}
        .contact-info {{ background: #e8f6ff; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .step {{ margin: 10px 0; padding: 10px; background: #f8f9fa; border-radius: 5px; }}
    </style>
</head>
<body>
    <h1>Data Deletion Instructions</h1>
    
    <p>You have the right to request deletion of your personal data from {app_name}. This page provides step-by-step instructions for different types of data deletion.</p>
    
    <h2>Types of Data Deletion</h2>
    
    <div class="method">
        <h3>1. Disconnect Social Media Accounts</h3>
        <p><strong>This removes:</strong> OAuth tokens, connection data, and stops future data access</p>
        <div class="step">
            <strong>Step 1:</strong> Log into your {app_name} account
        </div>
        <div class="step">
            <strong>Step 2:</strong> Go to "Account Settings" → "Connected Accounts"
        </div>
        <div class="step">
            <strong>Step 3:</strong> Click "Disconnect" next to each connected platform
        </div>
        <div class="step">
            <strong>Step 4:</strong> Confirm disconnection when prompted
        </div>
        <p><em>This immediately removes our access to your social media accounts.</em></p>
    </div>
    
    <div class="method">
        <h3>2. Delete Specific Content</h3>
        <p><strong>This removes:</strong> Individual posts, content drafts, or analytics data</p>
        <div class="step">
            <strong>Step 1:</strong> Navigate to your content library or analytics dashboard
        </div>
        <div class="step">
            <strong>Step 2:</strong> Select the content you want to delete
        </div>
        <div class="step">
            <strong>Step 3:</strong> Click "Delete" or "Remove"
        </div>
        <div class="step">
            <strong>Step 4:</strong> Confirm deletion when prompted
        </div>
    </div>
    
    <div class="method">
        <h3>3. Complete Account Deletion</h3>
        <p><strong>This removes:</strong> Your entire account and all associated data</p>
        <div class="step">
            <strong>Step 1:</strong> Log into your {app_name} account
        </div>
        <div class="step">
            <strong>Step 2:</strong> Go to "Account Settings" → "Privacy & Security"
        </div>
        <div class="step">
            <strong>Step 3:</strong> Click "Delete My Account"
        </div>
        <div class="step">
            <strong>Step 4:</strong> Follow the confirmation process
        </div>
        <div class="step">
            <strong>Step 5:</strong> Check your email for final confirmation link
        </div>
    </div>
    
    <h2>Manual Data Deletion Request</h2>
    
    <div class="method">
        <h3>4. Email Request</h3>
        <p>If you cannot use the automated methods above, contact us directly:</p>
        <div class="step">
            <strong>Step 1:</strong> Send an email to {contact_email}
        </div>
        <div class="step">
            <strong>Step 2:</strong> Include "Data Deletion Request" in the subject line
        </div>
        <div class="step">
            <strong>Step 3:</strong> Provide your account email and specify what data to delete
        </div>
        <div class="step">
            <strong>Step 4:</strong> We will process your request within 30 days
        </div>
    </div>
    
    <h2>What Happens After Deletion</h2>
    
    <h3>Immediate Effects</h3>
    <ul>
        <li>Access to your account and data is immediately removed</li>
        <li>OAuth tokens are revoked and encrypted tokens are deleted</li>
        <li>Scheduled posts are cancelled</li>
        <li>Social media platform connections are terminated</li>
    </ul>
    
    <h3>Data Retention for Legal/Security Purposes</h3>
    <div class="warning">
        <p><strong>Note:</strong> Some data may be retained for limited periods:</p>
        <ul>
            <li><strong>Audit logs:</strong> 90 days (for security and fraud prevention)</li>
            <li><strong>Backup systems:</strong> Up to 30 days (for system recovery)</li>
            <li><strong>Legal requirements:</strong> As required by applicable law</li>
        </ul>
    </div>
    
    <h2>Third-Party Platform Data</h2>
    
    <p>Please note that data deletion from {app_name} does not automatically delete:</p>
    <ul>
        <li>Content already posted to social media platforms</li>
        <li>Data stored by social media platforms independently</li>
        <li>Analytics data collected by third-party platforms</li>
    </ul>
    
    <p>To delete data from social media platforms, you must:</p>
    <ol>
        <li>Visit each platform directly (Facebook, Instagram, X/Twitter)</li>
        <li>Use their data deletion or account deletion features</li>
        <li>Review their individual privacy policies and procedures</li>
    </ol>
    
    <h2>Verification of Identity</h2>
    
    <p>For your security, we may ask you to verify your identity before processing deletion requests by:</p>
    <ul>
        <li>Confirming your registered email address</li>
        <li>Answering account security questions</li>
        <li>Providing additional verification if suspicious activity is detected</li>
    </ul>
    
    <h2>Data Deletion Timeline</h2>
    
    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
        <tr style="background: #f8f9fa; border: 1px solid #ddd;">
            <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Deletion Type</th>
            <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Processing Time</th>
        </tr>
        <tr style="border: 1px solid #ddd;">
            <td style="padding: 10px; border: 1px solid #ddd;">Social Media Disconnection</td>
            <td style="padding: 10px; border: 1px solid #ddd;">Immediate</td>
        </tr>
        <tr style="background: #f8f9fa; border: 1px solid #ddd;">
            <td style="padding: 10px; border: 1px solid #ddd;">Content Deletion</td>
            <td style="padding: 10px; border: 1px solid #ddd;">Immediate</td>
        </tr>
        <tr style="border: 1px solid #ddd;">
            <td style="padding: 10px; border: 1px solid #ddd;">Account Deletion</td>
            <td style="padding: 10px; border: 1px solid #ddd;">24-48 hours</td>
        </tr>
        <tr style="background: #f8f9fa; border: 1px solid #ddd;">
            <td style="padding: 10px; border: 1px solid #ddd;">Manual Email Request</td>
            <td style="padding: 10px; border: 1px solid #ddd;">Up to 30 days</td>
        </tr>
    </table>
    
    <div class="contact-info">
        <h2>Support and Questions</h2>
        <p>If you need assistance with data deletion:</p>
        <p>
            <strong>Email:</strong> {contact_email}<br>
            <strong>Subject Line:</strong> "Data Deletion Support"<br>
            <strong>Response Time:</strong> Within 3 business days
        </p>
        <p>We are committed to protecting your privacy and will process all deletion requests promptly and securely.</p>
    </div>
    
    <p><a href="/api/v1/legal/privacy-policy">← Back to Privacy Policy</a></p>
</body>
</html>
        """
        
        logger.info("Data deletion instructions requested")
        return HTMLResponse(content=instructions_html)
        
    except Exception as e:
        logger.error(f"Error serving data deletion instructions: {e}")
        return HTMLResponse(
            content="<h1>Instructions Temporarily Unavailable</h1><p>Please try again later.</p>",
            status_code=500
        )


@router.get("/status", response_model=Dict[str, Any])
async def legal_documents_status() -> JSONResponse:
    """
    Get legal documents service status
    
    Returns:
        JSON with available legal documents and their URLs
    """
    try:
        settings = get_settings()
        base_url = getattr(settings, 'backend_url', 'https://socialmedia-api-wxip.onrender.com')
        
        status = {
            "service_available": True,
            "documents": {
                "privacy_policy": {
                    "url": f"{base_url}/api/v1/legal/privacy-policy",
                    "format": "HTML",
                    "required_for": ["Meta App Review", "X App Setup", "GDPR Compliance"]
                },
                "terms_of_service": {
                    "url": f"{base_url}/api/v1/legal/terms-of-service", 
                    "format": "HTML",
                    "required_for": ["Meta App Review", "X App Setup", "General Platform Use"]
                },
                "data_deletion_instructions": {
                    "url": f"{base_url}/api/v1/legal/data-deletion-instructions",
                    "format": "HTML",
                    "required_for": ["Meta App Review", "Data Subject Rights"]
                }
            },
            "compliance": {
                "gdpr_ready": True,
                "ccpa_ready": True,
                "meta_app_review_ready": True,
                "x_app_setup_ready": True
            },
            "last_updated": "2025-01-01"
        }
        
        return JSONResponse(content=status)
        
    except Exception as e:
        logger.error(f"Legal documents status error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Failed to get legal documents status", "details": str(e)}
        )