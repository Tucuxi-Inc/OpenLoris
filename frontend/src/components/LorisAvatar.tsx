/**
 * LorisAvatar Component
 *
 * A reusable component for displaying Loris mascot images throughout the app.
 * Each "mood" corresponds to a specific Loris illustration that conveys
 * context and adds personality to the user experience.
 *
 * Usage:
 *   <LorisAvatar mood="thinking" size="md" />
 *   <LorisAvatar mood="celebration" size="lg" animate />
 */

import { useState } from 'react'

export type LorisMood =
  | 'default'        // Main Loris - welcome, general use
  | 'turbo'          // TransWarp Loris - fast answers, automation
  | 'molten'         // Molten Loris - MoltenLoris feature
  | 'scholar'        // Scholar Loris - knowledge base, learning
  | 'legal-scholar'  // Legal Scholar Loris - legal domain content
  | 'thinking'       // Thinking Loris - processing, loading
  | 'studying'       // Studying Loris - analysis, research
  | 'celebration'    // Celebration Loris - success, milestones
  | 'alert'          // Alert Loris - warnings, low confidence
  | 'confused'       // Confused Loris - no results, escalation
  | 'detective'      // Detective Loris - search, investigation
  | 'architect'      // Architect Loris - settings, configuration
  | 'battle'         // Battle Loris - expert queue, ready to work
  | 'mediator'       // Mediator Loris - conflict resolution
  | 'traffic-cop'    // Traffic Cop Loris - routing, queue management

export type LorisSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl'

interface LorisAvatarProps {
  mood: LorisMood
  size?: LorisSize
  className?: string
  animate?: boolean
  alt?: string
}

// Map moods to image filenames
const MOOD_TO_IMAGE: Record<LorisMood, string> = {
  'default': 'Loris.png',
  'turbo': 'TransWarp_Loris.png',
  'molten': 'Molten_Loris.png',
  'scholar': 'Scholar_Loris.png',
  'legal-scholar': 'LegalScholar_Loris.png',
  'thinking': 'Thinking_Loris.png',
  'studying': 'Studying_Loris.png',
  'celebration': 'Celebration_Loris.png',
  'alert': 'Alert_Loris.png',
  'confused': 'Confused_Loris.png',
  'detective': 'DetectiveLoris.png',
  'architect': 'Architect_Loris.png',
  'battle': 'Battle_Loris.png',
  'mediator': 'Mediator_Loris.png',
  'traffic-cop': 'TrafficCop_Loris.png',
}

// Map moods to descriptive alt text
const MOOD_TO_ALT: Record<LorisMood, string> = {
  'default': 'Loris mascot',
  'turbo': 'Turbo Loris - fast answers',
  'molten': 'Molten Loris - Slack integration',
  'scholar': 'Scholar Loris - knowledge expert',
  'legal-scholar': 'Legal Scholar Loris - legal expertise',
  'thinking': 'Thinking Loris - processing',
  'studying': 'Studying Loris - analyzing',
  'celebration': 'Celebrating Loris - success!',
  'alert': 'Alert Loris - attention needed',
  'confused': 'Confused Loris - need help',
  'detective': 'Detective Loris - searching',
  'architect': 'Architect Loris - building',
  'battle': 'Battle-ready Loris - ready to help',
  'mediator': 'Mediator Loris - resolving',
  'traffic-cop': 'Traffic Cop Loris - directing',
}

// Size classes
const SIZE_CLASSES: Record<LorisSize, string> = {
  'xs': 'h-8 w-auto',
  'sm': 'h-12 w-auto',
  'md': 'h-20 w-auto',
  'lg': 'h-32 w-auto',
  'xl': 'h-48 w-auto',
  '2xl': 'h-64 w-auto',
}

export default function LorisAvatar({
  mood,
  size = 'md',
  className = '',
  animate = false,
  alt,
}: LorisAvatarProps) {
  const [imageError, setImageError] = useState(false)

  const imagePath = `/loris-images/${MOOD_TO_IMAGE[mood]}`
  const altText = alt || MOOD_TO_ALT[mood]
  const sizeClass = SIZE_CLASSES[size]

  // Animation classes
  const animationClass = animate
    ? mood === 'thinking'
      ? 'animate-pulse'
      : mood === 'celebration'
        ? 'animate-bounce'
        : 'hover:scale-105 transition-transform'
    : ''

  if (imageError) {
    // Fallback to default Loris if specific image fails
    return (
      <img
        src="/loris-images/Loris.png"
        alt={altText}
        className={`${sizeClass} ${animationClass} ${className}`}
      />
    )
  }

  return (
    <img
      src={imagePath}
      alt={altText}
      className={`${sizeClass} ${animationClass} ${className}`}
      onError={() => setImageError(true)}
    />
  )
}

/**
 * LorisWithMessage Component
 *
 * Combines LorisAvatar with a text message for empty states, loading, etc.
 */
interface LorisWithMessageProps {
  mood: LorisMood
  title?: string
  message: string
  size?: LorisSize
  action?: {
    label: string
    onClick: () => void
  }
}

export function LorisWithMessage({
  mood,
  title,
  message,
  size = 'lg',
  action,
}: LorisWithMessageProps) {
  return (
    <div className="flex flex-col items-center text-center py-8">
      <LorisAvatar mood={mood} size={size} animate={mood === 'thinking'} />
      {title && (
        <h3 className="mt-4 text-lg text-ink-primary">{title}</h3>
      )}
      <p className="mt-2 font-serif text-ink-secondary max-w-md">{message}</p>
      {action && (
        <button onClick={action.onClick} className="btn-primary mt-4">
          {action.label}
        </button>
      )}
    </div>
  )
}

/**
 * Contextual helper to suggest which mood to use
 */
export const MOOD_SUGGESTIONS = {
  // Loading/Processing states
  loading: 'thinking' as LorisMood,
  processing: 'thinking' as LorisMood,
  analyzing: 'studying' as LorisMood,
  searching: 'detective' as LorisMood,

  // Success states
  success: 'celebration' as LorisMood,
  answered: 'celebration' as LorisMood,
  completed: 'celebration' as LorisMood,

  // Warning/Error states
  warning: 'alert' as LorisMood,
  lowConfidence: 'alert' as LorisMood,
  error: 'confused' as LorisMood,
  notFound: 'confused' as LorisMood,
  escalation: 'confused' as LorisMood,

  // Feature-specific
  turboAnswer: 'turbo' as LorisMood,
  autoAnswer: 'turbo' as LorisMood,
  moltenLoris: 'molten' as LorisMood,
  slackIntegration: 'molten' as LorisMood,

  // Knowledge/Learning
  knowledge: 'scholar' as LorisMood,
  facts: 'scholar' as LorisMood,
  documents: 'studying' as LorisMood,
  legal: 'legal-scholar' as LorisMood,

  // Admin/Expert
  settings: 'architect' as LorisMood,
  configuration: 'architect' as LorisMood,
  queue: 'battle' as LorisMood,
  expertWork: 'battle' as LorisMood,
  routing: 'traffic-cop' as LorisMood,
  assignment: 'traffic-cop' as LorisMood,

  // General
  welcome: 'default' as LorisMood,
  empty: 'default' as LorisMood,
}
