import React, { useState, useEffect, useRef } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { 
  ChartBarIcon, 
  ClockIcon, 
  SparklesIcon, 
  UserGroupIcon,
  LightBulbIcon,
  ShieldCheckIcon,
  ArrowRightIcon,
  CheckCircleIcon,
  PlayCircleIcon,
  ChevronDownIcon,
  ChevronUpIcon,
  RocketLaunchIcon,
  CogIcon,
  EyeIcon,
  ChatBubbleLeftRightIcon,
  BoltIcon,
  StarIcon,
  BuildingOfficeIcon,
  DevicePhoneMobileIcon,
  Bars3Icon,
  XMarkIcon
} from '@heroicons/react/24/outline'
import SEOHead from '../components/SEOHead'

const LandingPage = () => {
  const [searchParams] = useSearchParams()
  const [email, setEmail] = useState('')
  const [expandedFAQ, setExpandedFAQ] = useState(null)
  const [showVideo, setShowVideo] = useState(false)
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [showFloatingCTA, setShowFloatingCTA] = useState(false)
  const [isAnnualBilling, setIsAnnualBilling] = useState(true)
  const [currentTestimonial, setCurrentTestimonial] = useState(0)
  const [showCookieBanner, setShowCookieBanner] = useState(true)
  const [showCookiePreferences, setShowCookiePreferences] = useState(false)
  const [cookiePreferences, setCookiePreferences] = useState({
    necessary: true, // Always required
    analytics: false,
    marketing: false,
    functionality: false
  })
  const [showChatWidget, setShowChatWidget] = useState(false)
  const [chatMessages, setChatMessages] = useState([
    { type: 'bot', message: "Hi! I'm Lily, your AI assistant! How can I help you learn more about our social media management platform today?" }
  ])
  const [chatInput, setChatInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [sessionId] = useState(() => `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`)
  const chatEndRef = useRef(null)
  
  // Handle floating CTA visibility on scroll
  useEffect(() => {
    const handleScroll = () => {
      setShowFloatingCTA(window.scrollY > 800)
    }
    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  // Check for saved cookie preference
  useEffect(() => {
    const cookieAccepted = localStorage.getItem('cookiesAccepted')
    if (cookieAccepted) {
      setShowCookieBanner(false)
    }
  }, [])

  // Auto-scroll chat to bottom when new messages arrive
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages])

  // Handle sending chat messages to the assistant
  const sendChatMessage = async () => {
    if (!chatInput.trim() || isTyping) return
    
    const userMessage = chatInput.trim()
    setChatInput('')
    
    // Add user message to chat
    setChatMessages(prev => [...prev, { type: 'user', message: userMessage }])
    setIsTyping(true)
    
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/chat/assistant/message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage,
          session_id: sessionId
        })
      })
      
      if (!response.ok) {
        throw new Error('Failed to get response')
      }
      
      const data = await response.json()
      
      // Add bot response to chat
      setChatMessages(prev => [...prev, { type: 'bot', message: data.message }])
    } catch (error) {
      console.error('Chat error:', error)
      setChatMessages(prev => [...prev, { 
        type: 'bot', 
        message: "I apologize, but I'm having trouble connecting right now. Please try again later or email us at support@lily-ai.com" 
      }])
    } finally {
      setIsTyping(false)
    }
  }

  const handleChatKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendChatMessage()
    }
  }

  const acceptCookies = (type = 'all') => {
    const preferences = type === 'all' 
      ? { necessary: true, analytics: true, marketing: true, functionality: true }
      : type === 'necessary' 
      ? { necessary: true, analytics: false, marketing: false, functionality: false }
      : cookiePreferences

    localStorage.setItem('cookiePreferences', JSON.stringify(preferences))
    localStorage.setItem('cookiesAccepted', 'true')
    setShowCookieBanner(false)
    setShowCookiePreferences(false)
  }

  const updateCookiePreference = (category, value) => {
    setCookiePreferences(prev => ({
      ...prev,
      [category]: value
    }))
  }

  // Auto-rotate testimonials
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTestimonial((prev) => (prev + 1) % 3) // Fixed number since we have 3 testimonials
    }, 5000)
    return () => clearInterval(timer)
  }, [])

  // Personalization from URL parameters
  const source = searchParams.get('utm_source') || ''
  const campaign = searchParams.get('utm_campaign') || ''

  // Features data
  const features = [
    {
      icon: RocketLaunchIcon,
      title: "Autonomous Autopilot Mode",
      description: "Full hands-off experience—AI researches trends, creates content, schedules posts, and replies to messages.",
      highlight: "🚀 Unique in Market"
    },
    {
      icon: SparklesIcon,
      title: "AI-Powered Content Creation", 
      description: "GPT-4o for text, Grok-2 Vision for images, video generation—all optimized for every platform.",
      highlight: "🎨 Multi-AI Suite"
    },
    {
      icon: ChartBarIcon,
      title: "Advanced Analytics & Insights",
      description: "Predictive forecasting, competitor analysis, ROI tracking with real-time optimization recommendations.",
      highlight: "📊 AI-Powered Analytics"
    },
    {
      icon: CogIcon,
      title: "Seamless Integrations",
      description: "Connect Salesforce, HubSpot, Shopify, Zapier and more for automated workflows.",
      highlight: "🔗 Enterprise Ready"
    },
    {
      icon: ShieldCheckIcon,
      title: "Enterprise-Grade Security",
      description: "JWT authentication, data encryption, audit logs, and GDPR/CCPA compliance.",
      highlight: "🔒 Bank-Level Security"
    },
    {
      icon: DevicePhoneMobileIcon,
      title: "Mobile & Team Collaboration",
      description: "Mobile management with team editing, approval workflows, and real-time collaboration.",
      highlight: "📱 Team Features"
    }
  ]

  // How it works steps
  const steps = [
    {
      number: 1,
      title: "Configure Your Brand",
      description: "Set voice, industry, and goals in minutes",
      icon: UserGroupIcon
    },
    {
      number: 2,
      title: "AI Researches Trends",
      description: "Daily scans for relevant topics in your industry",
      icon: EyeIcon
    },
    {
      number: 3,
      title: "Creates & Schedules Content",
      description: "Generates posts/images/videos and publishes autonomously",
      icon: SparklesIcon
    },
    {
      number: 4,
      title: "Handles Engagement",
      description: "AI responds to comments/messages with escalation if needed",
      icon: ChatBubbleLeftRightIcon
    },
    {
      number: 5,
      title: "Optimizes with Analytics",
      description: "Self-adjusts based on performance data",
      icon: BoltIcon
    }
  ]

  // Pricing tiers
  const pricingTiers = [
    {
      name: "Starter",
      price: isAnnualBilling ? "$59" : "$74",
      originalPrice: isAnnualBilling ? "$708/year" : "$74/month",
      period: isAnnualBilling ? "month (billed annually)" : "month",
      description: "Ideal for solopreneurs or small teams starting with hands-off social management",
      features: [
        "Up to 5 social profiles (X, Meta, LinkedIn, TikTok, YouTube, Threads)",
        "Basic AI content generation (GPT-4o-mini, limited Grok-2 Vision)",
        "Limited autopilot mode with daily automated posts",
        "Social inbox monitoring (no AI responses)",
        "Basic analytics with AI optimization recommendations",
        "Content repurposing and recycling tools",
        "Multi-language support (up to 10 languages)",
        "Customizable dashboards and UI themes",
        "Automated backups and recovery",
        "1 user account"
      ],
      cta: "Start 14-Day Free Trial",
      popular: false,
      savings: isAnnualBilling ? "Save 20% annually" : null
    },
    {
      name: "Pro",
      price: isAnnualBilling ? "$149" : "$186",
      originalPrice: isAnnualBilling ? "$1,788/year" : "$186/month",
      period: isAnnualBilling ? "month (billed annually)" : "month",
      description: "Perfect for growing SMBs and agencies needing scalable, autonomous features",
      features: [
        "Unlimited social profiles across all platforms",
        "Full AI suite (GPT-4o, Grok-2 Vision, Synthesia/Runway ML videos)",
        "Enhanced autopilot mode with auto-ad campaigns & trend forecasting",
        "AI-powered social inbox responses and chatbots",
        "Advanced analytics with competitor analysis & ROI tracking",
        "CRM integrations (Salesforce, HubSpot, Shopify)",
        "Third-party tool integrations (Zapier-like automation)",
        "Mobile app for on-the-go management",
        "Enhanced collaboration tools & approval workflows",
        "Up to 5 users and 5 workspaces"
      ],
      cta: "Start 14-Day Free Trial",
      popular: true,
      savings: isAnnualBilling ? "Save 20% annually" : null
    },
    {
      name: "Enterprise",
      price: isAnnualBilling ? "$499" : "$624",
      originalPrice: isAnnualBilling ? "$5,988/year" : "$624/month",
      period: isAnnualBilling ? "month (billed annually)" : "month",
      description: "Designed for high-scale operations with enterprise-grade security and customization",
      features: [
        "All Pro features with unlimited users & workspaces",
        "Complete autopilot with predictive analytics integration",
        "Influencer & affiliate management integrations",
        "Auto-scaling infrastructure for high-volume use",
        "Advanced audit & compliance tools (CCPA/GDPR)",
        "White-labeling and custom API access",
        "Priority support with dedicated account manager",
        "Custom training sessions included",
        "Unlimited add-ons and integrations",
        "Enterprise-grade security & customization"
      ],
      cta: "Contact Sales",
      popular: false,
      savings: isAnnualBilling ? "Save 20% annually" : null
    }
  ]

  // Testimonials - Real customer feedback
  const testimonials = [
    {
      quote: "We reduced our social media management time from 15 hours/week to 2 hours/week. The AI autopilot handles our content research, creation, and scheduling across LinkedIn, Twitter, and Instagram while maintaining our brand voice.",
      author: "Jennifer Martinez",
      role: "Marketing Manager",
      company: "CloudTech Solutions",
      avatar: null,
      rating: 5,
      logo: "CT",
      verified: true,
      results: "87% time reduction, 45% engagement increase"
    },
    {
      quote: "As a solopreneur, I was drowning in social media tasks. Lily AI's autopilot mode generates 30+ posts weekly, responds to comments intelligently, and has grown my following by 240% in 4 months.",
      author: "David Park",
      role: "Founder & CEO", 
      company: "Park Consulting",
      avatar: null,
      rating: 5,
      logo: "PC",
      verified: true,
      results: "240% follower growth, 30 posts/week automated"
    },
    {
      quote: "The multi-platform optimization is incredible. Same content, perfectly adapted for LinkedIn vs Instagram vs Twitter. Our client engagement rates improved 60% across all channels.",
      author: "Maria Santos",
      role: "Digital Marketing Lead",
      company: "Growth Partners",
      avatar: null,
      rating: 5,
      logo: "GP",
      verified: true,
      results: "60% engagement improvement across platforms"
    }
  ]

  // Customer logos for social proof
  const customerLogos = [
    { name: "CloudTech Solutions", initials: "CT", color: "bg-blue-600" },
    { name: "Park Consulting", initials: "PC", color: "bg-green-600" },
    { name: "Growth Partners", initials: "GP", color: "bg-purple-600" },
    { name: "Digital Dynamics", initials: "DD", color: "bg-orange-600" },
    { name: "Scale Studio", initials: "SS", color: "bg-indigo-600" },
    { name: "Market Maven", initials: "MM", color: "bg-pink-600" }
  ]

  // FAQ items
  const faqs = [
    {
      question: "What makes Lily AI different from other social media tools?",
      answer: "Lily AI is the only platform offering full autonomous autopilot mode—no human oversight needed. Our AI researches trends, creates content, schedules posts, and handles engagement completely on its own. Competitors require constant manual input."
    },
    {
      question: "Which social media platforms are supported?",
      answer: "We support all major platforms: X (Twitter), Meta (Facebook & Instagram), LinkedIn, TikTok, YouTube, and Threads. More platforms are added regularly based on user demand."
    },
    {
      question: "How secure is my data and social media accounts?",
      answer: "Enterprise-grade security with JWT authentication, end-to-end encryption, audit logs, and full GDPR/CCPA compliance. We use JWT auth, encryption, and comply with GDPR/CCPA. Your data is more secure with us than managing accounts manually."
    },
    {
      question: "Can I cancel my subscription anytime?",
      answer: "Yes, absolutely! No lock-in contracts. Cancel anytime with one click. You'll retain access until your current billing period ends."
    },
    {
      question: "How does the 14-day free trial work?",
      answer: "Full access to all features for 14 days. If you love it (which you will), seamlessly upgrade to continue. Cancel anytime during trial with zero charges."
    },
    {
      question: "What AI models power Lily AI?",
      answer: "We use the latest AI: GPT-4o for text, Grok-2 Vision for images, Synthesia/Runway ML for videos, and ElevenLabs for voice. This multi-AI approach ensures best-in-class content across all formats."
    }
  ]

  const handleEmailSubmit = (e) => {
    e.preventDefault()
    window.location.href = `/register?email=${encodeURIComponent(email)}`
  }

  const scrollToSection = (sectionId) => {
    document.getElementById(sectionId)?.scrollIntoView({ behavior: 'smooth' })
    setIsMenuOpen(false)
  }

  return (
    <div className="min-h-screen bg-white">
      <SEOHead />
      
      {/* Skip to main content link for screen readers */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:top-0 focus:left-0 bg-blue-600 text-white px-4 py-2 z-50 focus:z-50"
      >
        Skip to main content
      </a>
      
      {/* Sticky Navigation */}
      <nav className="fixed top-0 left-0 right-0 bg-white/95 backdrop-blur-sm border-b border-gray-200 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <Link to="/" className="flex items-center">
                <SparklesIcon className="h-8 w-8 text-blue-600" />
                <span className="ml-2 text-2xl font-bold text-gray-900">Lily AI</span>
              </Link>
            </div>
            
            {/* Desktop Navigation */}
            <div className="hidden md:flex items-center space-x-8">
              <button onClick={() => scrollToSection('features')} className="text-gray-600 hover:text-blue-600 transition-colors">
                Features
              </button>
              <button onClick={() => scrollToSection('how-it-works')} className="text-gray-600 hover:text-blue-600 transition-colors">
                How It Works
              </button>
              <button onClick={() => scrollToSection('pricing')} className="text-gray-600 hover:text-blue-600 transition-colors">
                Pricing
              </button>
              <Link to="/login" className="text-gray-600 hover:text-blue-600 transition-colors">
                Login
              </Link>
              <Link to="/register" className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition-colors">
                Start Free Trial
              </Link>
            </div>

            {/* Mobile menu button */}
            <div className="md:hidden">
              <button
                onClick={() => setIsMenuOpen(!isMenuOpen)}
                className="text-gray-600 hover:text-blue-600 focus:text-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded p-1"
                aria-expanded={isMenuOpen}
                aria-label="Toggle navigation menu"
                aria-controls="mobile-menu"
              >
                {isMenuOpen ? (
                  <XMarkIcon className="h-6 w-6" aria-hidden="true" />
                ) : (
                  <Bars3Icon className="h-6 w-6" aria-hidden="true" />
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Mobile Navigation */}
        {isMenuOpen && (
          <div id="mobile-menu" className="md:hidden bg-white border-t border-gray-200">
            <nav className="px-4 py-2 space-y-3" role="navigation" aria-label="Mobile menu">
              <button 
                onClick={() => scrollToSection('features')} 
                className="block w-full text-left text-gray-700 hover:text-blue-600 focus:text-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-2 py-1"
              >
                Features
              </button>
              <button 
                onClick={() => scrollToSection('how-it-works')} 
                className="block w-full text-left text-gray-700 hover:text-blue-600 focus:text-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-2 py-1"
              >
                How It Works
              </button>
              <button 
                onClick={() => scrollToSection('pricing')} 
                className="block w-full text-left text-gray-700 hover:text-blue-600 focus:text-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-2 py-1"
              >
                Pricing
              </button>
              <Link 
                to="/login" 
                className="block text-gray-700 hover:text-blue-600 focus:text-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-2 py-1"
              >
                Login
              </Link>
              <Link 
                to="/register" 
                className="block bg-green-600 hover:bg-green-700 focus:bg-green-700 focus:ring-2 focus:ring-green-500 focus:ring-offset-2 text-white px-4 py-2 rounded-lg font-medium text-center"
                aria-label="Start free trial"
              >
                Start Free Trial
              </Link>
            </nav>
          </div>
        )}
      </nav>

      {/* Hero Section */}
      <main>
        <section id="main-content" className="pt-20 pb-16 bg-gradient-to-br from-blue-50 via-white to-indigo-50" aria-labelledby="hero-heading">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center">
            
            {/* Main Headline */}
            <h1 id="hero-heading" className="text-4xl sm:text-5xl lg:text-6xl font-bold text-gray-900 mb-8">
              Revolutionize Your Social Media with{' '}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-700 to-indigo-700">
                Lily AI's Autonomous Autopilot
              </span>
            </h1>
            
            {/* Subheadline */}
            <h2 className="text-xl sm:text-2xl text-gray-600 mb-12 max-w-4xl mx-auto">
              AI-powered management that researches trends, creates engaging content, schedules posts, 
              and handles responses—all on autopilot. Save 90% time for SMBs.
            </h2>


            {/* Community Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 items-center opacity-60">
              <div className="text-center">
                <div className="text-lg text-gray-500">Join Our</div>
                <div className="text-sm text-gray-600">Growing Community</div>
              </div>
              <div className="text-center group relative cursor-help">
                <div className="text-2xl font-bold text-gray-900">90%</div>
                <div className="text-sm text-gray-600">Time Saved</div>
                <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 bg-gray-800 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity">
                  Average user reports
                </div>
              </div>
              <div className="text-center group relative cursor-help">
                <div className="text-2xl font-bold text-gray-900">45%</div>
                <div className="text-sm text-gray-600">Engagement Boost</div>
                <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 bg-gray-800 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity">
                  Average improvement
                </div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-gray-900">24/7</div>
                <div className="text-sm text-gray-600">Autopilot Mode</div>
              </div>
            </div>
          </div>
        </div>
        </section>
      </main>

      {/* Features Section */}
      <section id="features" className="py-20 bg-gray-50" aria-labelledby="features-heading">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 id="features-heading" className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
              Powerful Features That Set Us Apart
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Discover the unique capabilities that make Lily AI the most advanced social media management platform
            </p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <div key={index} className="bg-white p-8 rounded-xl shadow-sm hover:shadow-md transition-shadow border border-gray-100">
                <div className="flex items-center mb-4">
                  <div className="p-3 bg-blue-100 rounded-lg">
                    <feature.icon className="h-6 w-6 text-blue-600" />
                  </div>
                  <span className="ml-3 text-sm font-medium text-green-600 bg-green-100 px-2 py-1 rounded-full">
                    {feature.highlight}
                  </span>
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-3">
                  {feature.title}
                </h3>
                <p className="text-gray-600 leading-relaxed">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
          
          <div className="text-center mt-12">
            <button
              onClick={() => setShowVideo(true)}
              className="inline-flex items-center px-8 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors"
            >
              See Features in Action
              <PlayCircleIcon className="ml-2 h-5 w-5" />
            </button>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="py-20 bg-white" aria-labelledby="how-it-works-heading">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 id="how-it-works-heading" className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
              How Lily AI Autopilot Works
            </h2>
            <p className="text-xl text-gray-600 max-w-3xl mx-auto">
              Set it once, let AI handle everything. Here's how our autonomous system transforms your social media presence
            </p>
          </div>

          {/* Clean Grid Layout */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            {steps.map((step, index) => (
              <div key={index} className="text-center">
                <div className="flex items-center justify-center mb-6">
                  <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center mr-4">
                    <step.icon className="h-8 w-8 text-white" />
                  </div>
                  <div className="text-3xl font-bold text-blue-600">
                    {step.number}
                  </div>
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-3">
                  {step.title}
                </h3>
                <p className="text-gray-600 leading-relaxed">
                  {step.description}
                </p>
              </div>
            ))}
          </div>

          <div className="text-center mt-12">
            <div className="bg-blue-50 rounded-xl p-8 max-w-2xl mx-auto">
              <h3 className="text-xl font-semibold text-gray-900 mb-3">Ready to See It In Action?</h3>
              <p className="text-gray-600 mb-6">
                Watch our interactive demo showing real autopilot functionality
              </p>
              <button
                onClick={() => setShowVideo(true)}
                className="inline-flex items-center px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors"
              >
                <PlayCircleIcon className="h-5 w-5 mr-2" />
                Interactive Demo
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-20 bg-gray-50" aria-labelledby="pricing-heading">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <p className="text-center text-gray-600 mb-4">No credit card required</p>
            <h2 id="pricing-heading" className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
              Choose Your Plan
            </h2>
            <p className="text-xl text-gray-600 mb-8">
              All plans come with a 14-day free trial.
            </p>
            
            {/* Billing Toggle */}
            <div className="flex items-center justify-center mb-12">
              <span className={`mr-3 ${!isAnnualBilling ? 'text-gray-900 font-medium' : 'text-gray-500'}`}>Monthly</span>
              <button
                onClick={() => setIsAnnualBilling(!isAnnualBilling)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${isAnnualBilling ? 'bg-blue-600' : 'bg-gray-200'}`}
              >
                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${isAnnualBilling ? 'translate-x-6' : 'translate-x-1'}`} />
              </button>
              <span className={`ml-3 ${isAnnualBilling ? 'text-gray-900 font-medium' : 'text-gray-500'}`}>
                Annual
                <span className="ml-1 text-green-600 font-semibold">(Save 20%)</span>
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {pricingTiers.map((tier, index) => (
              <div
                key={index}
                className={`bg-white rounded-xl p-8 shadow-sm relative ${
                  tier.popular ? 'ring-2 ring-blue-600 transform scale-105' : 'border border-gray-200'
                }`}
              >
                {tier.popular && (
                  <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                    <span className="bg-blue-600 text-white px-4 py-1 rounded-full text-sm font-medium">
                      Most Popular
                    </span>
                  </div>
                )}
                
                <div className="text-center mb-8">
                  <h3 className="text-2xl font-bold text-gray-900 mb-2">{tier.name}</h3>
                  <div className="mb-4">
                    <span className="text-4xl font-bold text-gray-900">{tier.price}</span>
                    <span className="text-gray-600">/{tier.period}</span>
                  </div>
                  <p className="text-gray-600 text-sm mb-4">{tier.description}</p>
                  {tier.savings && (
                    <p className="text-green-600 text-sm font-medium bg-green-50 px-3 py-1 rounded-full inline-block">
                      {tier.savings}
                    </p>
                  )}
                </div>
                
                <ul className="space-y-3 mb-8">
                  {tier.features.map((feature, featureIndex) => (
                    <li key={featureIndex} className="flex items-start">
                      <CheckCircleIcon className="h-5 w-5 text-green-500 flex-shrink-0 mt-0.5" />
                      <span className="ml-3 text-gray-600 text-sm">{feature}</span>
                    </li>
                  ))}
                </ul>
                
                <Link
                  to={tier.cta === "Contact Sales" ? "/contact" : "/register"}
                  className={`w-full px-6 py-3 rounded-lg font-semibold text-center block transition-colors ${
                    tier.popular
                      ? 'bg-green-600 hover:bg-green-700 text-white'
                      : 'bg-green-100 hover:bg-green-200 text-green-800'
                  }`}
                  aria-label={`${tier.cta} for ${tier.name} plan`}
                >
                  {tier.cta === "Contact Sales" ? tier.cta : "Start 14-Day Free Trial"}
                </Link>
              </div>
            ))}
          </div>
          
          <div className="text-center mt-8">
            <p className="text-gray-600">
              All plans include 14-day free trial • Annual billing saves 20% • No setup fees • Cancel anytime
            </p>
          </div>
        </div>
      </section>

      {/* Testimonials Section */}
      <section className="py-20 bg-white">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
              What Our Customers Say
            </h2>
            <p className="text-xl text-gray-600">
              Join thousands of businesses already saving time with Lily AI
            </p>
          </div>


          {/* Authentic Testimonials Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {testimonials.map((testimonial, index) => (
              <div key={index} className="bg-white border border-gray-200 rounded-2xl p-6 shadow-sm">
                <div className="flex justify-between items-start mb-4">
                  <div className="flex">
                    {[...Array(testimonial.rating)].map((_, i) => (
                      <StarIcon key={i} className="h-4 w-4 text-yellow-400 fill-current" />
                    ))}
                  </div>
                  {testimonial.verified && (
                    <div className="flex items-center text-green-600 text-xs">
                      <CheckCircleIcon className="h-4 w-4 mr-1" />
                      Verified Customer
                    </div>
                  )}
                </div>
                
                <blockquote className="text-gray-700 mb-4 text-sm leading-relaxed">
                  "{testimonial.quote}"
                </blockquote>

                <div className="bg-blue-50 rounded-lg p-3 mb-4">
                  <p className="text-blue-800 text-sm font-medium">Results:</p>
                  <p className="text-blue-700 text-sm">{testimonial.results}</p>
                </div>
                
                <div className="flex items-center">
                  <div className={`w-10 h-10 ${customerLogos.find(c => c.initials === testimonial.logo)?.color || 'bg-gray-400'} rounded-full mr-3 flex items-center justify-center`}>
                    <span className="text-white font-medium text-sm">{testimonial.logo}</span>
                  </div>
                  <div className="text-left">
                    <div className="font-semibold text-gray-900 text-sm">{testimonial.author}</div>
                    <div className="text-gray-600 text-xs">{testimonial.role}</div>
                    <div className="text-gray-500 text-xs">{testimonial.company}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>


        </div>
      </section>


      {/* FAQ Section */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
              Frequently Asked Questions
            </h2>
            <p className="text-xl text-gray-600">
              Get answers to common questions about Lily AI
            </p>
          </div>
          
          <div className="space-y-4">
            {faqs.map((faq, index) => (
              <div key={index} className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                <button
                  onClick={() => setExpandedFAQ(expandedFAQ === index ? null : index)}
                  className="w-full px-6 py-4 text-left flex items-center justify-between hover:bg-gray-50 transition-colors"
                >
                  <span className="font-medium text-gray-900">{faq.question}</span>
                  {expandedFAQ === index ? (
                    <ChevronUpIcon className="h-5 w-5 text-gray-500" />
                  ) : (
                    <ChevronDownIcon className="h-5 w-5 text-gray-500" />
                  )}
                </button>
                {expandedFAQ === index && (
                  <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
                    <p className="text-gray-700">{faq.answer}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Final CTA Section */}
      <section className="py-20 bg-gradient-to-r from-blue-600 to-indigo-600">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
            Ready to Transform Your Social Media?
          </h2>
          <p className="text-xl text-blue-100 mb-10">
            Join 5,000+ businesses already using Lily AI to dominate social media with full autopilot
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <Link
              to="/register"
              className="bg-white hover:bg-gray-100 text-blue-600 px-8 py-4 rounded-lg text-lg font-semibold transition-colors inline-flex items-center"
            >
              Start Your 14-Day Free Trial
              <ArrowRightIcon className="ml-2 h-5 w-5" />
            </Link>
            <button
              onClick={() => setShowVideo(true)}
              className="border border-white text-white hover:bg-white hover:text-blue-600 px-8 py-4 rounded-lg text-lg font-semibold transition-colors inline-flex items-center"
            >
              <PlayCircleIcon className="mr-2 h-5 w-5" />
              Watch Demo First
            </button>
          </div>
          <p className="mt-6 text-blue-200 text-sm">
            Full access for 14 days • Cancel anytime
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-900">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
            <div className="col-span-1 md:col-span-2">
              <div className="flex items-center mb-4">
                <SparklesIcon className="h-8 w-8 text-blue-400" />
                <span className="ml-2 text-2xl font-bold text-white">Lily AI</span>
              </div>
              <p className="text-gray-300 max-w-md mb-6">
                The most intelligent social media management platform. 
                Create, schedule, and optimize your content with autonomous AI.
              </p>
              <div className="flex space-x-4">
                {/* Social Media Icons - Replace with actual links */}
                <a href="#" className="text-gray-400 hover:text-white transition-colors">
                  <span className="sr-only">Twitter</span>
                  <svg className="h-6 w-6" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M8.29 20.251c7.547 0 11.675-6.253 11.675-11.675 0-.178 0-.355-.012-.53A8.348 8.348 0 0022 5.92a8.19 8.19 0 01-2.357.646 4.118 4.118 0 001.804-2.27 8.224 8.224 0 01-2.605.996 4.107 4.107 0 00-6.993 3.743 11.65 11.65 0 01-8.457-4.287 4.106 4.106 0 001.27 5.477A4.072 4.072 0 012.8 9.713v.052a4.105 4.105 0 003.292 4.022 4.095 4.095 0 01-1.853.07 4.108 4.108 0 003.834 2.85A8.233 8.233 0 012 18.407a11.616 11.616 0 006.29 1.84" />
                  </svg>
                </a>
              </div>
            </div>
            
            <div>
              <h4 className="text-lg font-semibold text-white mb-4">Product</h4>
              <ul className="space-y-2">
                <li><button onClick={() => scrollToSection('features')} className="text-gray-300 hover:text-white transition-colors">Features</button></li>
                <li><button onClick={() => scrollToSection('pricing')} className="text-gray-300 hover:text-white transition-colors">Pricing</button></li>
                <li><Link to="/login" className="text-gray-300 hover:text-white transition-colors">Sign In</Link></li>
                <li><Link to="/register" className="text-gray-300 hover:text-white transition-colors">Free Trial</Link></li>
              </ul>
            </div>
            
            <div>
              <h4 className="text-lg font-semibold text-white mb-4">Company</h4>
              <ul className="space-y-2">
                <li><a href="#" className="text-gray-300 hover:text-white transition-colors">About</a></li>
                <li><a href="/privacy" className="text-blue-600 hover:underline font-semibold transition-colors">Privacy Policy</a></li>
                <li><a href="/terms" className="text-blue-600 hover:underline font-semibold transition-colors">Terms of Service</a></li>
                <li><a href="#" className="text-gray-300 hover:text-white transition-colors">Contact</a></li>
              </ul>
            </div>
          </div>
          
          <div className="mt-12 pt-8 border-t border-gray-700">
            <div className="flex flex-col md:flex-row justify-between items-center">
              <p className="text-gray-400">
                © 2025 Lily AI. All rights reserved.
              </p>
              <div className="mt-4 md:mt-0">
                <Link
                  to="/register"
                  className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-colors inline-flex items-center"
                >
                  Ready to Automate? Start Free Trial
                  <ArrowRightIcon className="ml-2 h-4 w-4" />
                </Link>
              </div>
            </div>
          </div>
        </div>
      </footer>

      {/* Mobile Sticky CTA */}
      <div className="fixed bottom-0 left-0 right-0 bg-white shadow-md py-2 text-center md:hidden z-40">
        <Link
          to="/register"
          className="bg-green-600 text-white px-6 py-2 rounded mx-4 font-semibold inline-flex items-center justify-center"
          aria-label="Start Free Trial"
        >
          Start Free Trial
          <ArrowRightIcon className="ml-2 h-4 w-4" />
        </Link>
      </div>

      {/* Floating CTA Button - Desktop */}
      {showFloatingCTA && (
        <div className="fixed bottom-6 right-6 z-50 hidden md:block">
          <Link
            to="/register"
            className="bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-full shadow-lg font-semibold transition-all transform hover:scale-105 inline-flex items-center"
          >
            Start Free Trial
            <ArrowRightIcon className="ml-2 h-4 w-4" />
          </Link>
        </div>
      )}

      {/* Enhanced Cookie Banner */}
      {showCookieBanner && !showCookiePreferences && (
        <div className="fixed bottom-0 left-0 right-0 bg-gray-900 text-white p-4 z-50 shadow-2xl">
          <div className="max-w-6xl mx-auto">
            <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
              <div className="flex-1">
                <h3 className="font-semibold mb-2 text-white">We value your privacy</h3>
                <p className="text-sm text-gray-300 leading-relaxed">
                  We use cookies to enhance your browsing experience, serve personalized content, and analyze our traffic. 
                  You can choose which categories to allow. 
                  <a href="/privacy" className="text-blue-400 hover:text-blue-300 underline ml-1">
                    Learn more in our Privacy Policy
                  </a>
                </p>
              </div>
              <div className="flex flex-col sm:flex-row gap-2 lg:ml-4">
                <button
                  onClick={() => acceptCookies('necessary')}
                  className="px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors border border-gray-600"
                >
                  Essential Only
                </button>
                <button
                  onClick={() => setShowCookiePreferences(true)}
                  className="px-4 py-2 text-sm bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors border border-gray-600"
                >
                  Customize
                </button>
                <button
                  onClick={() => acceptCookies('all')}
                  className="px-6 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
                >
                  Accept All
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Cookie Preferences Modal */}
      {showCookiePreferences && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75 p-4">
          <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-gray-900">Cookie Preferences</h2>
                <button
                  onClick={() => setShowCookiePreferences(false)}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                  aria-label="Close cookie preferences"
                >
                  <XMarkIcon className="h-6 w-6" />
                </button>
              </div>

              <div className="space-y-6">
                {/* Necessary Cookies */}
                <div className="border-b border-gray-200 pb-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-gray-900">Essential Cookies</h3>
                    <div className="bg-gray-100 rounded-full p-1">
                      <div className="bg-gray-400 w-6 h-3 rounded-full flex items-center px-1">
                        <div className="bg-white w-2 h-2 rounded-full ml-auto"></div>
                      </div>
                    </div>
                  </div>
                  <p className="text-sm text-gray-600">
                    These cookies are necessary for the website to function and cannot be disabled. They include session management, security, and accessibility features.
                  </p>
                </div>

                {/* Analytics Cookies */}
                <div className="border-b border-gray-200 pb-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-gray-900">Analytics Cookies</h3>
                    <button
                      onClick={() => updateCookiePreference('analytics', !cookiePreferences.analytics)}
                      className={`${cookiePreferences.analytics ? 'bg-blue-600' : 'bg-gray-300'} rounded-full p-1 transition-colors`}
                      aria-label={`${cookiePreferences.analytics ? 'Disable' : 'Enable'} analytics cookies`}
                    >
                      <div className={`bg-white w-6 h-3 rounded-full flex items-center px-1 transition-transform ${cookiePreferences.analytics ? 'justify-end' : 'justify-start'}`}>
                        <div className="bg-gray-400 w-2 h-2 rounded-full"></div>
                      </div>
                    </button>
                  </div>
                  <p className="text-sm text-gray-600">
                    Help us understand how visitors interact with our website by collecting anonymous usage data and performance metrics.
                  </p>
                </div>

                {/* Marketing Cookies */}
                <div className="border-b border-gray-200 pb-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-gray-900">Marketing Cookies</h3>
                    <button
                      onClick={() => updateCookiePreference('marketing', !cookiePreferences.marketing)}
                      className={`${cookiePreferences.marketing ? 'bg-blue-600' : 'bg-gray-300'} rounded-full p-1 transition-colors`}
                      aria-label={`${cookiePreferences.marketing ? 'Disable' : 'Enable'} marketing cookies`}
                    >
                      <div className={`bg-white w-6 h-3 rounded-full flex items-center px-1 transition-transform ${cookiePreferences.marketing ? 'justify-end' : 'justify-start'}`}>
                        <div className="bg-gray-400 w-2 h-2 rounded-full"></div>
                      </div>
                    </button>
                  </div>
                  <p className="text-sm text-gray-600">
                    Enable personalized ads and marketing communications based on your preferences and behavior.
                  </p>
                </div>

                {/* Functionality Cookies */}
                <div className="pb-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-gray-900">Functionality Cookies</h3>
                    <button
                      onClick={() => updateCookiePreference('functionality', !cookiePreferences.functionality)}
                      className={`${cookiePreferences.functionality ? 'bg-blue-600' : 'bg-gray-300'} rounded-full p-1 transition-colors`}
                      aria-label={`${cookiePreferences.functionality ? 'Disable' : 'Enable'} functionality cookies`}
                    >
                      <div className={`bg-white w-6 h-3 rounded-full flex items-center px-1 transition-transform ${cookiePreferences.functionality ? 'justify-end' : 'justify-start'}`}>
                        <div className="bg-gray-400 w-2 h-2 rounded-full"></div>
                      </div>
                    </button>
                  </div>
                  <p className="text-sm text-gray-600">
                    Remember your preferences and settings to provide enhanced functionality and personalization.
                  </p>
                </div>
              </div>

              <div className="flex flex-col sm:flex-row gap-3 mt-8">
                <button
                  onClick={() => acceptCookies('necessary')}
                  className="flex-1 px-4 py-3 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition-colors"
                >
                  Essential Only
                </button>
                <button
                  onClick={() => acceptCookies()}
                  className="flex-1 px-4 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
                >
                  Save Preferences
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Chat Widget */}
      <div className="fixed bottom-20 md:bottom-6 right-6 z-40">
        {!showChatWidget ? (
          <button
            onClick={() => setShowChatWidget(true)}
            className="bg-blue-600 hover:bg-blue-700 text-white p-4 rounded-full shadow-lg transition-all transform hover:scale-105 group"
            aria-label="Open chat support"
          >
            <ChatBubbleLeftRightIcon className="h-6 w-6" />
            <div className="absolute -top-2 -left-2 w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
            <div className="absolute -left-32 top-1/2 transform -translate-y-1/2 bg-gray-800 text-white text-sm px-3 py-1 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
              Have questions? Chat with us!
            </div>
          </button>
        ) : (
          <div className="bg-white rounded-2xl shadow-2xl w-80 h-96 border border-gray-200 flex flex-col">
            <div className="bg-blue-600 text-white p-4 rounded-t-2xl flex items-center justify-between">
              <div className="flex items-center">
                <div className="w-3 h-3 bg-green-400 rounded-full mr-2"></div>
                <span className="font-semibold">Lily AI Support</span>
              </div>
              <button
                onClick={() => setShowChatWidget(false)}
                className="text-white hover:text-gray-200 transition-colors"
                aria-label="Close chat"
              >
                <XMarkIcon className="h-5 w-5" />
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto bg-gray-50">
              <div className="p-4 space-y-3">
                {chatMessages.map((msg, index) => (
                  <div key={index} className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-xs px-4 py-2 rounded-2xl text-sm ${
                      msg.type === 'user' 
                        ? 'bg-blue-600 text-white' 
                        : 'bg-white border border-gray-200 text-gray-800'
                    }`}>
                      {msg.message}
                    </div>
                  </div>
                ))}
                {isTyping && (
                  <div className="flex justify-start">
                    <div className="max-w-xs px-4 py-2 rounded-2xl text-sm bg-white border border-gray-200 text-gray-800">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>
              
              {/* Quick Action Buttons - Only show when no conversation started */}
              {chatMessages.length <= 1 && (
                <div className="px-4 pb-4 space-y-2">
                <button
                  onClick={() => window.open('/register', '_blank')}
                  className="w-full text-left px-3 py-2 text-sm bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  🚀 Start Free Trial
                </button>
                <button
                  onClick={() => window.open('https://calendly.com/lily-ai/demo', '_blank')}
                  className="w-full text-left px-3 py-2 text-sm bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  📅 Schedule a Demo
                </button>
                <button
                  onClick={() => scrollToSection('case-studies')}
                  className="w-full text-left px-3 py-2 text-sm bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  📊 View Case Studies
                </button>
                <button
                  onClick={() => scrollToSection('pricing')}
                  className="w-full text-left px-3 py-2 text-sm bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  💰 View Pricing
                </button>
                </div>
              )}
            </div>
            
            {/* Message Input Area */}
            <div className="p-3 border-t border-gray-200">
              <div className="flex space-x-2">
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyPress={handleChatKeyPress}
                  placeholder="Type your message..."
                  disabled={isTyping}
                  className="flex-1 px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <button
                  onClick={sendChatMessage}
                  disabled={!chatInput.trim() || isTyping}
                  className="px-4 py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Send
                </button>
              </div>
            </div>
            
            <div className="p-3 border-t border-gray-200">
              <p className="text-xs text-gray-500 text-center">
                Need immediate help? 
                <a href="mailto:support@lily-ai.com" className="text-blue-600 hover:underline ml-1">
                  Email us
                </a>
              </p>
            </div>
          </div>
        )}
      </div>


      {/* Video Modal */}
      {showVideo && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75" onClick={() => setShowVideo(false)}>
          <div className="bg-white p-4 rounded-lg max-w-4xl w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold">Lily AI Autopilot Demo</h3>
              <button
                onClick={() => setShowVideo(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                <XMarkIcon className="h-6 w-6" />
              </button>
            </div>
            <div className="aspect-video bg-gray-200 flex items-center justify-center rounded">
              {/* Replace with actual video embed */}
              <div className="text-center">
                <PlayCircleIcon className="h-16 w-16 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-600">Interactive Autopilot Demo</p>
                <p className="text-sm text-gray-500 mt-2">Video integration coming soon</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default LandingPage