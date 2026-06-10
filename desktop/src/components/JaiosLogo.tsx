type Props = {
  size?: number;
  showWordmark?: boolean;
};

/** Logo alineado con icono de app: fondo claro + J azul grande. */
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
          <linearGradient id="jaiosBg" x1="8" y1="8" x2="56" y2="56" gradientUnits="userSpaceOnUse">
            <stop stopColor="#ffffff" />
            <stop offset="1" stopColor="#eff6ff" />
          </linearGradient>
          <linearGradient id="jaiosJ" x1="22" y1="14" x2="42" y2="50" gradientUnits="userSpaceOnUse">
            <stop stopColor="#3b82f6" />
            <stop offset="1" stopColor="#1d4ed8" />
          </linearGradient>
        </defs>
        <rect x="2" y="2" width="60" height="60" rx="14" fill="url(#jaiosBg)" stroke="#bfdbfe" strokeWidth="1.5" />
        <path
          d="M22 16h20v7H28v18c0 7.5 9.5 9.5 13.5 5.5l3.5 5.5c-6.5 5-20 4-20-11V16z"
          fill="url(#jaiosJ)"
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
