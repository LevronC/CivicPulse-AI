export const metadata = {
  title: "CivicPulse AI",
  description: "Real-time global event intelligence dashboard"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "Arial, sans-serif", margin: 0, background: "#0b1220", color: "#e5e7eb" }}>
        {children}
      </body>
    </html>
  );
}
