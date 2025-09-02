export default function LoadingSpinner({ 
  size = 16, 
  border = 2, 
  className = "" 
}) {
  const s = `${size}px`;
  
  return (
    <div
      className={`animate-spin rounded-full border-b-2 ${className}`}
      style={{ 
        width: s, 
        height: s, 
        borderWidth: `${border}px` 
      }}
      aria-label="Loading"
      role="status"
    />
  );
}