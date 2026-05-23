import "./globals.css";

export const metadata = {
  title: "CivicPulse AI",
  description: "Real-time global event intelligence dashboard",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-gray-950 text-gray-100 antialiased">
        <header className="border-b border-gray-800 bg-gray-950/80 backdrop-blur-sm sticky top-0 z-50">
          <div className="mx-auto max-w-7xl px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-7 w-7 rounded-lg bg-blue-600 flex items-center justify-center text-xs font-bold">
                CP
              </div>
              <h1 className="text-base font-semibold tracking-tight">
                CivicPulse AI
              </h1>
            </div>
            <span className="text-xs text-gray-500">
              Global Event Intelligence
            </span>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
