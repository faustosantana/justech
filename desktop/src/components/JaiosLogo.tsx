type Props = {
  size?: number;
  showWordmark?: boolean;
};

export function JaiosLogo({ size = 56, showWordmark = true }: Props) {
  return (
    <div className="jaios-logo" style={{ gap: showWordmark ? 14 : 0 }}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 64 64"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden
      >
        <defs>
          <linearGradient id="jaiosGrad" x1="8" y1="8" x2="56" y2="56" gradientUnits="userSpaceOnUse">
            <stop stopColor="#3b82f6" />
            <stop offset="1" stopColor="#1d4ed8" />
          </linearGradient>
        </defs>
        <rect x="4" y="4" width="56" height="56" rx="14" fill="url(#jaiosGrad)" />
        <path
          d="M24 18h16v6H30v20c0 8 10 10 14 6l3 5c-6 5-18 4-18-11V18z"
          fill="#ffffff"
        />
      </svg>
      {showWordmark && (
        <div className="jaios-wordmark">
          <span className="jaios-wordmark-title">JAIOS</span>
          <span className="jaios-wordmark-sub">Justech</span>
        </div>
      )}
    </div>
  );
}
