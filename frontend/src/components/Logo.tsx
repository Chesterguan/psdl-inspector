'use client';

interface LogoProps {
  size?: number;
  className?: string;
}

export default function Logo({ size = 32, className = '' }: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 100 100"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Outer square brackets - cyan */}
      <path
        d="M10 10 L10 30 M10 10 L30 10"
        stroke="#4DD0E1"
        strokeWidth="6"
        strokeLinecap="square"
      />
      <path
        d="M90 10 L90 30 M90 10 L70 10"
        stroke="#4DD0E1"
        strokeWidth="6"
        strokeLinecap="square"
      />
      <path
        d="M10 90 L10 70 M10 90 L30 90"
        stroke="#4DD0E1"
        strokeWidth="6"
        strokeLinecap="square"
      />
      <path
        d="M90 90 L90 70 M90 90 L70 90"
        stroke="#4DD0E1"
        strokeWidth="6"
        strokeLinecap="square"
      />

      {/* Circular arrows - dark blue */}
      <path
        d="M50 22 A28 28 0 0 1 78 50"
        stroke="#0D47A1"
        strokeWidth="8"
        strokeLinecap="round"
        fill="none"
      />
      <path
        d="M78 50 A28 28 0 0 1 50 78"
        stroke="#0D47A1"
        strokeWidth="8"
        strokeLinecap="round"
        fill="none"
      />
      <path
        d="M50 78 A28 28 0 0 1 22 50"
        stroke="#0D47A1"
        strokeWidth="8"
        strokeLinecap="round"
        fill="none"
      />
      <path
        d="M22 50 A28 28 0 0 1 50 22"
        stroke="#0D47A1"
        strokeWidth="8"
        strokeLinecap="round"
        fill="none"
      />

      {/* Arrow heads */}
      <polygon points="50,14 58,26 42,26" fill="#0D47A1" />
      <polygon points="86,50 74,42 74,58" fill="#0D47A1" />
      <polygon points="50,86 42,74 58,74" fill="#0D47A1" />
      <polygon points="14,50 26,58 26,42" fill="#0D47A1" />
    </svg>
  );
}
