interface LorisIllustrationProps {
  variant?: 'standard' | 'transwarp' | 'research' | 'thinking' | 'celebration' | 'confused' | 'alert'
  size?: 'small' | 'medium' | 'large'
  caption?: string
}

// Map variants to image filenames
const variantImages: Record<string, string> = {
  standard: '/loris-images/Loris.png',
  transwarp: '/loris-images/TransWarp_Loris.png',
  research: '/loris-images/Scholar_Loris.png',
  thinking: '/loris-images/Thinking_Loris.png',
  celebration: '/loris-images/Celebration_Loris.png',
  confused: '/loris-images/Confused_Loris.png',
  alert: '/loris-images/Alert_Loris.png',
}

const sizeClasses = {
  small: 'max-w-[80px]',
  medium: 'max-w-[120px]',
  large: 'max-w-[180px]',
}

export default function LorisIllustration({
  variant = 'standard',
  size = 'medium',
  caption,
}: LorisIllustrationProps) {
  const imageSrc = variantImages[variant] || variantImages.standard

  return (
    <div className="loris-illustration">
      <img
        src={imageSrc}
        alt={`Loris - ${variant}`}
        className={`${sizeClasses[size]} h-auto mx-auto`}
      />
      {caption && <p className="loris-caption">{caption}</p>}
    </div>
  )
}
